"""
Tests for Phase 5.0: Feedback-aware style tuning.

Tests the aggregator's ability to select best-performing generation styles
based on user feedback (helpful/unhelpful) and edit distance metrics.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.autofill_aggregator import (
    _compute_style_stats,
    _pick_best_style,
    _update_style_hints,
    StyleStats,
)
from app.models_learning_db import AutofillEvent, FormProfile
from app.db import SessionLocal


pytestmark = pytest.mark.skipif(
    True, reason="Requires PostgreSQL - skipping in SQLite mode"
)


def test_style_stats_dataclass():
    """StyleStats computes helpful_ratio correctly."""
    stats = StyleStats(style_id="bullets_v1")

    # Initially 0
    assert stats.helpful_ratio == 0.0

    # 8/10 helpful
    stats.helpful = 8
    stats.unhelpful = 2
    stats.total_runs = 10

    assert stats.helpful_ratio == 0.8

    # 0/5 helpful
    stats2 = StyleStats(style_id="bad_style", helpful=0, unhelpful=5, total_runs=5)
    assert stats2.helpful_ratio == 0.0


def test_compute_style_stats_basic(postgresql_db):
    """compute_style_stats aggregates feedback correctly."""
    db = postgresql_db
    now = datetime.utcnow()
    user_id = uuid4()

    # Create events with different styles
    events = [
        # bullets_v1: 8 helpful, 1 unhelpful
        *[
            AutofillEvent(
                user_id=user_id,
                host="example.com",
                schema_hash="schema1",
                gen_style_id="bullets_v1",
                feedback_status="helpful",
                edit_chars=100 + i * 10,
                created_at=now,
            )
            for i in range(8)
        ],
        AutofillEvent(
            user_id=user_id,
            host="example.com",
            schema_hash="schema1",
            gen_style_id="bullets_v1",
            feedback_status="unhelpful",
            edit_chars=200,
            created_at=now,
        ),
        # narrative_v1: 2 helpful, 5 unhelpful
        *[
            AutofillEvent(
                user_id=user_id,
                host="example.com",
                schema_hash="schema1",
                gen_style_id="narrative_v1",
                feedback_status="unhelpful",
                edit_chars=600 + i * 50,
                created_at=now,
            )
            for i in range(5)
        ],
        *[
            AutofillEvent(
                user_id=user_id,
                host="example.com",
                schema_hash="schema1",
                gen_style_id="narrative_v1",
                feedback_status="helpful",
                edit_chars=400,
                created_at=now,
            )
            for _ in range(2)
        ],
    ]

    for evt in events:
        db.add(evt)
    db.commit()

    # Compute stats
    style_map = _compute_style_stats(db, lookback_days=30)

    key = ("example.com", "schema1")
    assert key in style_map

    styles = style_map[key]
    assert "bullets_v1" in styles
    assert "narrative_v1" in styles

    # bullets_v1: 8 helpful, 1 unhelpful, 9 total
    bullets = styles["bullets_v1"]
    assert bullets.helpful == 8
    assert bullets.unhelpful == 1
    assert bullets.total_runs == 9
    assert 0.88 < bullets.helpful_ratio < 0.89

    # narrative_v1: 2 helpful, 5 unhelpful, 7 total
    narrative = styles["narrative_v1"]
    assert narrative.helpful == 2
    assert narrative.unhelpful == 5
    assert narrative.total_runs == 7
    assert 0.28 < narrative.helpful_ratio < 0.29


def test_pick_best_style_by_helpful_ratio():
    """pick_best_style chooses style with highest helpful_ratio."""
    styles = {
        "bullets_v1": StyleStats(
            style_id="bullets_v1",
            helpful=8,
            unhelpful=2,
            total_runs=10,
            avg_edit_chars=150,
        ),
        "narrative_v1": StyleStats(
            style_id="narrative_v1",
            helpful=3,
            unhelpful=7,
            total_runs=10,
            avg_edit_chars=400,
        ),
    }

    best = _pick_best_style(styles)
    assert best is not None
    assert best.style_id == "bullets_v1"
    assert best.helpful_ratio == 0.8


def test_pick_best_style_tiebreaker_edit_chars():
    """If helpful_ratio ties, prefer lower avg_edit_chars."""
    styles = {
        "bullets_v1": StyleStats(
            style_id="bullets_v1",
            helpful=5,
            unhelpful=5,
            total_runs=10,
            avg_edit_chars=100,  # Less editing needed
        ),
        "narrative_v1": StyleStats(
            style_id="narrative_v1",
            helpful=5,
            unhelpful=5,
            total_runs=10,
            avg_edit_chars=500,  # More editing needed
        ),
    }

    best = _pick_best_style(styles)
    assert best is not None
    assert best.style_id == "bullets_v1"  # Lower edit chars wins


def test_pick_best_style_empty():
    """pick_best_style returns None for empty dict."""
    assert _pick_best_style({}) is None


def test_update_style_hints_integration(postgresql_db):
    """update_style_hints sets preferred_style_id on profiles."""
    db = postgresql_db
    now = datetime.utcnow()
    user_id = uuid4()

    # Create profile
    profile = FormProfile(
        host="ats.example.com",
        schema_hash="hash123",
        fields={},
    )
    db.add(profile)
    db.commit()

    # Create events with feedback
    events = [
        # Good style: bullets_v1
        *[
            AutofillEvent(
                user_id=user_id,
                host="ats.example.com",
                schema_hash="hash123",
                gen_style_id="bullets_v1",
                feedback_status="helpful",
                edit_chars=120,
                created_at=now,
            )
            for _ in range(9)
        ],
        AutofillEvent(
            user_id=user_id,
            host="ats.example.com",
            schema_hash="hash123",
            gen_style_id="bullets_v1",
            feedback_status="unhelpful",
            edit_chars=150,
            created_at=now,
        ),
        # Bad style: narrative_v1
        *[
            AutofillEvent(
                user_id=user_id,
                host="ats.example.com",
                schema_hash="hash123",
                gen_style_id="narrative_v1",
                feedback_status="unhelpful",
                edit_chars=700,
                created_at=now,
            )
            for _ in range(6)
        ],
        *[
            AutofillEvent(
                user_id=user_id,
                host="ats.example.com",
                schema_hash="hash123",
                gen_style_id="narrative_v1",
                feedback_status="helpful",
                edit_chars=400,
                created_at=now,
            )
            for _ in range(2)
        ],
    ]

    for evt in events:
        db.add(evt)
    db.commit()

    # Run style hint update
    updated = _update_style_hints(db, lookback_days=30)
    assert updated == 1

    # Reload profile
    db.refresh(profile)
    hint = profile.style_hint or {}

    # Should prefer bullets_v1 (90% helpful) over narrative_v1 (25% helpful)
    assert hint.get("preferred_style_id") == "bullets_v1"

    # Check style_stats included
    stats = hint.get("style_stats", {})
    assert "bullets_v1" in stats
    assert "narrative_v1" in stats

    bullets_stats = stats["bullets_v1"]
    assert bullets_stats["helpful"] == 9
    assert bullets_stats["unhelpful"] == 1
    assert bullets_stats["total_runs"] == 10
    assert 0.89 < bullets_stats["helpful_ratio"] < 0.91

    narrative_stats = stats["narrative_v1"]
    assert narrative_stats["helpful"] == 2
    assert narrative_stats["unhelpful"] == 6
    assert narrative_stats["total_runs"] == 8


def test_update_style_hints_no_data():
    """update_style_hints handles profiles with no feedback data."""
    db = SessionLocal()

    # Create profile with no events
    profile = FormProfile(
        host="empty.com",
        schema_hash="nofeedback",
        fields={},
    )
    db.add(profile)
    db.commit()

    # Run update - should not modify profile
    _update_style_hints(db, lookback_days=30)

    db.refresh(profile)
    assert profile.style_hint is None or "preferred_style_id" not in (
        profile.style_hint or {}
    )

    db.close()


def test_lookback_window_filters_old_events(postgresql_db):
    """Lookback window filters out events older than N days."""
    db = postgresql_db
    user_id = uuid4()
    now = datetime.utcnow()
    old = now - timedelta(days=60)

    # Create old events that should be ignored
    old_event = AutofillEvent(
        user_id=user_id,
        host="test.com",
        schema_hash="old",
        gen_style_id="old_style",
        feedback_status="helpful",
        created_at=old,
    )
    db.add(old_event)

    # Create recent event
    recent_event = AutofillEvent(
        user_id=user_id,
        host="test.com",
        schema_hash="recent",
        gen_style_id="new_style",
        feedback_status="helpful",
        created_at=now,
    )
    db.add(recent_event)
    db.commit()

    # Query with 30-day window
    style_map = _compute_style_stats(db, lookback_days=30)

    # Old event should not appear
    assert ("test.com", "old") not in style_map

    # Recent event should appear
    assert ("test.com", "recent") in style_map
    assert "new_style" in style_map[("test.com", "recent")]
