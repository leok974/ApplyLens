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
    _compute_family_style_stats,
    _compute_segment_style_stats,
    _pick_best_style,
    _pick_style_for_profile,
    _update_style_hints,
    StyleStats,
    derive_segment_key,
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


# ============================================================================
# Phase 5.1: Host-family bundle tests
# ============================================================================


@pytest.mark.postgres
def test_prefers_form_stats_when_enough_samples(postgresql_db):
    """
    Phase 5.1: When form has >= MIN_FORM_RUNS samples, use form-level stats.

    Even if family stats exist, form-level data should take precedence
    when we have enough samples for confidence.
    """
    db = postgresql_db
    now = datetime.utcnow()
    user_id = uuid4()

    # Create profile for a greenhouse form
    profile = FormProfile(
        host="boards.greenhouse.io",
        schema_hash="engineer-form",
        fields={},
    )
    db.add(profile)
    db.commit()

    # Create events for THIS SPECIFIC FORM with style_a being best
    # 10 runs (>= MIN_FORM_RUNS=5) with 80% helpful
    form_events = [
        *[
            AutofillEvent(
                user_id=user_id,
                host="boards.greenhouse.io",
                schema_hash="engineer-form",
                gen_style_id="style_a",
                feedback_status="helpful",
                edit_chars=100,
                created_at=now,
            )
            for _ in range(8)
        ],
        *[
            AutofillEvent(
                user_id=user_id,
                host="boards.greenhouse.io",
                schema_hash="engineer-form",
                gen_style_id="style_a",
                feedback_status="unhelpful",
                edit_chars=150,
                created_at=now,
            )
            for _ in range(2)
        ],
        # style_b also on this form but worse (20% helpful)
        *[
            AutofillEvent(
                user_id=user_id,
                host="boards.greenhouse.io",
                schema_hash="engineer-form",
                gen_style_id="style_b",
                feedback_status="unhelpful",
                edit_chars=500,
                created_at=now,
            )
            for _ in range(4)
        ],
        AutofillEvent(
            user_id=user_id,
            host="boards.greenhouse.io",
            schema_hash="engineer-form",
            gen_style_id="style_b",
            feedback_status="helpful",
            edit_chars=200,
            created_at=now,
        ),
    ]

    # Add family-level noise: many events on OTHER greenhouse forms
    # with style_b being dominant (to test that we ignore family when form has data)
    family_noise = [
        AutofillEvent(
            user_id=user_id,
            host="greenhouse.io",  # Different subdomain, same family
            schema_hash="other-form",
            gen_style_id="style_b",
            feedback_status="helpful",
            edit_chars=120,
            created_at=now,
        )
        for _ in range(20)
    ]

    for evt in form_events + family_noise:
        db.add(evt)
    db.commit()

    # Run aggregation
    updated = _update_style_hints(db, lookback_days=30)
    assert updated == 1

    # Check profile
    db.refresh(profile)
    hint = profile.style_hint or {}

    # Should use form-level best (style_a with 80% helpful)
    # NOT family-level best (style_b)
    assert hint.get("preferred_style_id") == "style_a"

    # Should have form-level stats in style_stats
    assert "style_stats" in hint
    assert "style_a" in hint["style_stats"]
    assert hint["style_stats"]["style_a"]["total_runs"] == 10


@pytest.mark.postgres
def test_fallback_to_family_when_form_samples_low(postgresql_db):
    """
    Phase 5.1: When form has < MIN_FORM_RUNS samples, fall back to family stats.

    If we don't have enough data for a specific form, we should use
    aggregated statistics from other forms in the same ATS family.
    """
    db = postgresql_db
    now = datetime.utcnow()
    user_id = uuid4()

    # Create profile for a greenhouse form
    profile = FormProfile(
        host="boards.greenhouse.io",
        schema_hash="sparse-form",
        fields={},
    )
    db.add(profile)
    db.commit()

    # Create FEW events for this specific form (< MIN_FORM_RUNS=5)
    # Not enough to make a confident decision
    sparse_form_events = [
        AutofillEvent(
            user_id=user_id,
            host="boards.greenhouse.io",
            schema_hash="sparse-form",
            gen_style_id="style_a",
            feedback_status="helpful",
            edit_chars=100,
            created_at=now,
        ),
        AutofillEvent(
            user_id=user_id,
            host="boards.greenhouse.io",
            schema_hash="sparse-form",
            gen_style_id="style_b",
            feedback_status="unhelpful",
            edit_chars=300,
            created_at=now,
        ),
    ]

    # Create MANY events across the greenhouse family (>= MIN_FAMILY_RUNS=10)
    # with friendly_bullets clearly winning
    family_events = [
        # friendly_bullets: 18/20 helpful (90%)
        *[
            AutofillEvent(
                user_id=user_id,
                host=host,
                schema_hash=f"form-{i}",
                gen_style_id="friendly_bullets",
                feedback_status="helpful",
                edit_chars=120,
                created_at=now,
            )
            for i, host in enumerate(
                ["greenhouse.io"] * 10 + ["boards.greenhouse.io"] * 8
            )
        ],
        *[
            AutofillEvent(
                user_id=user_id,
                host="greenhouse.io",
                schema_hash=f"form-unhelpful-{i}",
                gen_style_id="friendly_bullets",
                feedback_status="unhelpful",
                edit_chars=150,
                created_at=now,
            )
            for i in range(2)
        ],
        # professional_narrative: 3/15 helpful (20%)
        *[
            AutofillEvent(
                user_id=user_id,
                host="greenhouse.io",
                schema_hash=f"form-pro-{i}",
                gen_style_id="professional_narrative",
                feedback_status="unhelpful",
                edit_chars=600,
                created_at=now,
            )
            for i in range(12)
        ],
        *[
            AutofillEvent(
                user_id=user_id,
                host="greenhouse.io",
                schema_hash=f"form-pro-good-{i}",
                gen_style_id="professional_narrative",
                feedback_status="helpful",
                edit_chars=400,
                created_at=now,
            )
            for i in range(3)
        ],
    ]

    for evt in sparse_form_events + family_events:
        db.add(evt)
    db.commit()

    # Run aggregation
    updated = _update_style_hints(db, lookback_days=30)
    assert updated == 1

    # Check profile
    db.refresh(profile)
    hint = profile.style_hint or {}

    # Should use family-level best (friendly_bullets with 90% helpful)
    assert hint.get("preferred_style_id") == "friendly_bullets"

    # Should have bundle_stats (family-level) since we fell back
    assert "bundle_stats" in hint
    assert "friendly_bullets" in hint["bundle_stats"]
    assert hint["bundle_stats"]["friendly_bullets"]["source"] == "family:greenhouse"
    assert hint["bundle_stats"]["friendly_bullets"]["total_runs"] >= 10


@pytest.mark.postgres
def test_no_recommendation_when_no_form_or_family_stats(postgresql_db):
    """
    Phase 5.1: When neither form nor family has enough data, no recommendation.

    If we don't have enough samples at either level, we should not
    set a preferred_style_id to avoid making uninformed recommendations.
    """
    db = postgresql_db
    now = datetime.utcnow()
    user_id = uuid4()

    # Create profile for an unknown/rare ATS
    profile = FormProfile(
        host="rare-ats.com",  # Not in ATS_FAMILIES
        schema_hash="lonely-form",
        fields={},
    )
    db.add(profile)
    db.commit()

    # Create just ONE event (way below MIN_FORM_RUNS=5)
    single_event = AutofillEvent(
        user_id=user_id,
        host="rare-ats.com",
        schema_hash="lonely-form",
        gen_style_id="some_style",
        feedback_status="helpful",
        edit_chars=100,
        created_at=now,
    )
    db.add(single_event)
    db.commit()

    # Run aggregation
    updated = _update_style_hints(db, lookback_days=30)

    # Should not update profile (no confident recommendation)
    assert updated == 0

    # Check profile - should not have preferred_style_id
    db.refresh(profile)
    hint = profile.style_hint or {}
    assert "preferred_style_id" not in hint


@pytest.mark.postgres
def test_family_stats_computation(postgresql_db):
    """
    Phase 5.1: _compute_family_style_stats aggregates correctly across hosts.

    Verify that events from different subdomains within the same ATS family
    are correctly aggregated together.
    """
    from app.autofill_aggregator import _compute_family_style_stats

    db = postgresql_db
    now = datetime.utcnow()
    user_id = uuid4()

    # Create events across multiple greenhouse subdomains
    events = [
        # boards.greenhouse.io
        *[
            AutofillEvent(
                user_id=user_id,
                host="boards.greenhouse.io",
                schema_hash=f"form-{i}",
                gen_style_id="bullets_v1",
                feedback_status="helpful",
                edit_chars=100,
                created_at=now,
            )
            for i in range(5)
        ],
        # greenhouse.io (main domain)
        *[
            AutofillEvent(
                user_id=user_id,
                host="greenhouse.io",
                schema_hash=f"form-{i}",
                gen_style_id="bullets_v1",
                feedback_status="helpful",
                edit_chars=120,
                created_at=now,
            )
            for i in range(3)
        ],
        # Different family (lever)
        *[
            AutofillEvent(
                user_id=user_id,
                host="jobs.lever.co",
                schema_hash=f"form-{i}",
                gen_style_id="narrative_v1",
                feedback_status="helpful",
                edit_chars=200,
                created_at=now,
            )
            for i in range(4)
        ],
    ]

    for evt in events:
        db.add(evt)
    db.commit()

    # Compute family stats
    family_stats = _compute_family_style_stats(db, lookback_days=30)

    # Should have aggregated greenhouse events together
    greenhouse_key = ("greenhouse", "bullets_v1")
    assert greenhouse_key in family_stats

    greenhouse_bullets = family_stats[greenhouse_key]
    assert greenhouse_bullets.total_runs == 8  # 5 + 3 from both subdomains
    assert greenhouse_bullets.helpful == 8
    assert greenhouse_bullets.unhelpful == 0

    # Should have separate stats for lever
    lever_key = ("lever", "narrative_v1")
    assert lever_key in family_stats

    lever_narrative = family_stats[lever_key]
    assert lever_narrative.total_runs == 4
    assert lever_narrative.helpful == 4


# ============================================================================
# Phase 5.2: Segment-Aware Style Tuning Tests
# ============================================================================


def test_derive_segment_key():
    """derive_segment_key correctly classifies job titles into segments."""
    # Intern variants
    assert (
        derive_segment_key({"title": "Summer Intern - Software Engineering"})
        == "intern"
    )
    assert derive_segment_key({"title": "Co-op Developer"}) == "intern"
    assert derive_segment_key({"normalized_title": "intern ml engineer"}) == "intern"

    # Junior variants
    assert derive_segment_key({"title": "Junior Software Engineer"}) == "junior"
    assert derive_segment_key({"title": "Jr. Developer"}) == "junior"
    assert derive_segment_key({"title": "Entry Level Data Scientist"}) == "junior"

    # Senior variants
    assert derive_segment_key({"title": "Senior Software Engineer"}) == "senior"
    assert derive_segment_key({"title": "Sr. DevOps Engineer"}) == "senior"
    assert derive_segment_key({"title": "Lead Frontend Developer"}) == "senior"
    assert derive_segment_key({"title": "Principal Engineer"}) == "senior"

    # Default for mid-level or unclear
    assert derive_segment_key({"title": "Software Engineer"}) == "default"
    assert derive_segment_key({"title": "Full Stack Developer"}) == "default"

    # None for missing data
    assert derive_segment_key(None) is None
    assert derive_segment_key({}) is None
    assert derive_segment_key({"other_field": "value"}) is None


@pytest.mark.postgres
def test_compute_segment_style_stats(postgresql_db):
    """_compute_segment_style_stats aggregates by (family, segment, style)."""
    db = postgresql_db
    user_id = uuid4()
    now = datetime.utcnow()

    # Create events with different segments
    events = [
        # Greenhouse senior: style_senior performs well
        *[
            AutofillEvent(
                user_id=user_id,
                host="boards.greenhouse.io",
                schema_hash="senior-form",
                gen_style_id="style_senior",
                segment_key="senior",
                feedback_status="helpful",
                edit_chars=100,
                created_at=now,
            )
            for _ in range(12)
        ],
        *[
            AutofillEvent(
                user_id=user_id,
                host="boards.greenhouse.io",
                schema_hash="senior-form",
                gen_style_id="style_senior",
                segment_key="senior",
                feedback_status="unhelpful",
                edit_chars=200,
                created_at=now,
            )
            for _ in range(2)
        ],
        # Greenhouse intern: style_intern performs well
        *[
            AutofillEvent(
                user_id=user_id,
                host="greenhouse.io",
                schema_hash="intern-form",
                gen_style_id="style_intern",
                segment_key="intern",
                feedback_status="helpful",
                edit_chars=80,
                created_at=now,
            )
            for _ in range(8)
        ],
        # Lever senior: different family, same segment
        *[
            AutofillEvent(
                user_id=user_id,
                host="jobs.lever.co",
                schema_hash="senior-form",
                gen_style_id="style_professional",
                segment_key="senior",
                feedback_status="helpful",
                edit_chars=120,
                created_at=now,
            )
            for _ in range(6)
        ],
    ]

    for evt in events:
        db.add(evt)
    db.commit()

    # Compute segment stats
    segment_stats = _compute_segment_style_stats(db, lookback_days=30)

    # Greenhouse senior
    gh_senior_key = ("greenhouse", "senior", "style_senior")
    assert gh_senior_key in segment_stats
    gh_senior = segment_stats[gh_senior_key]
    assert gh_senior.total_runs == 14
    assert gh_senior.helpful == 12
    assert gh_senior.unhelpful == 2
    assert gh_senior.helpful_ratio == pytest.approx(12 / 14)

    # Greenhouse intern
    gh_intern_key = ("greenhouse", "intern", "style_intern")
    assert gh_intern_key in segment_stats
    gh_intern = segment_stats[gh_intern_key]
    assert gh_intern.total_runs == 8
    assert gh_intern.helpful == 8

    # Lever senior (different family)
    lever_senior_key = ("lever", "senior", "style_professional")
    assert lever_senior_key in segment_stats
    lever_senior = segment_stats[lever_senior_key]
    assert lever_senior.total_runs == 6
    assert lever_senior.helpful == 6


@pytest.mark.postgres
def test_segment_preferred_over_family_when_enough_data(postgresql_db):
    """Segment-level stats are preferred over family-level when sufficient data."""
    db = postgresql_db
    user_id = uuid4()
    now = datetime.utcnow()

    # Form has insufficient data (3 runs < MIN_FORM_RUNS=5)
    # Segment (greenhouse, senior) has 15 runs (>= MIN_SEGMENT_RUNS=5)
    # Family (greenhouse) has 20 runs (>= MIN_FAMILY_RUNS=10)
    # Expected: Use segment-level recommendation

    events = [
        # Form-level: Not enough data
        *[
            AutofillEvent(
                user_id=user_id,
                host="acme.greenhouse.io",
                schema_hash="new-form",
                gen_style_id="style_form",
                segment_key="senior",
                feedback_status="helpful",
                edit_chars=100,
                created_at=now,
            )
            for _ in range(3)
        ],
        # Segment-level (greenhouse, senior): High-performing style
        *[
            AutofillEvent(
                user_id=user_id,
                host="boards.greenhouse.io",
                schema_hash="other-form",
                gen_style_id="style_senior",
                segment_key="senior",
                feedback_status="helpful",
                edit_chars=80,
                created_at=now,
            )
            for _ in range(12)
        ],
        *[
            AutofillEvent(
                user_id=user_id,
                host="greenhouse.io",
                schema_hash="another-form",
                gen_style_id="style_senior",
                segment_key="senior",
                feedback_status="helpful",
                edit_chars=90,
                created_at=now,
            )
            for _ in range(3)
        ],
        # Family-level (greenhouse, all segments): Lower-performing style
        *[
            AutofillEvent(
                user_id=user_id,
                host="greenhouse.io",
                schema_hash="various",
                gen_style_id="style_family",
                segment_key="junior",
                feedback_status="helpful",
                edit_chars=150,
                created_at=now,
            )
            for _ in range(20)
        ],
    ]

    for evt in events:
        db.add(evt)
    db.commit()

    # Compute all stats
    form_stats = _compute_style_stats(db, 30)
    family_stats = _compute_family_style_stats(db, 30)
    segment_stats = _compute_segment_style_stats(db, 30)

    # Pick style for the new form
    best, meta = _pick_style_for_profile(
        host="acme.greenhouse.io",
        schema_hash="new-form",
        form_stats=form_stats,
        family_stats=family_stats,
        segment_stats=segment_stats,
        segment_key="senior",
    )

    # Should choose segment-level style
    assert best is not None
    assert best.style_id == "style_senior"
    assert meta["source"] == "segment"
    assert meta["segment_key"] == "senior"


@pytest.mark.postgres
def test_family_used_when_segment_too_sparse(postgresql_db):
    """Falls back to family-level when segment data is insufficient."""
    db = postgresql_db
    user_id = uuid4()
    now = datetime.utcnow()

    # Form: 2 runs (< MIN_FORM_RUNS=5)
    # Segment (greenhouse, senior): 3 runs (< MIN_SEGMENT_RUNS=5)
    # Family (greenhouse): 15 runs (>= MIN_FAMILY_RUNS=10)
    # Expected: Use family-level recommendation

    events = [
        # Form-level: Not enough
        *[
            AutofillEvent(
                user_id=user_id,
                host="acme.greenhouse.io",
                schema_hash="sparse-form",
                gen_style_id="style_form",
                segment_key="senior",
                feedback_status="helpful",
                edit_chars=100,
                created_at=now,
            )
            for _ in range(2)
        ],
        # Segment-level: Not enough
        *[
            AutofillEvent(
                user_id=user_id,
                host="boards.greenhouse.io",
                schema_hash="other-form",
                gen_style_id="style_segment",
                segment_key="senior",
                feedback_status="helpful",
                edit_chars=80,
                created_at=now,
            )
            for _ in range(3)
        ],
        # Family-level: Enough data
        *[
            AutofillEvent(
                user_id=user_id,
                host="greenhouse.io",
                schema_hash=f"form-{i}",
                gen_style_id="style_family",
                segment_key="junior",  # Different segment, same family
                feedback_status="helpful",
                edit_chars=90,
                created_at=now,
            )
            for i in range(15)
        ],
    ]

    for evt in events:
        db.add(evt)
    db.commit()

    form_stats = _compute_style_stats(db, 30)
    family_stats = _compute_family_style_stats(db, 30)
    segment_stats = _compute_segment_style_stats(db, 30)

    best, meta = _pick_style_for_profile(
        host="acme.greenhouse.io",
        schema_hash="sparse-form",
        form_stats=form_stats,
        family_stats=family_stats,
        segment_stats=segment_stats,
        segment_key="senior",
    )

    # Should fall back to family-level
    assert best is not None
    assert best.style_id == "style_family"
    assert meta["source"] == "family"


@pytest.mark.postgres
def test_no_segment_no_family_returns_none(postgresql_db):
    """Returns None when all data sources are too sparse."""
    db = postgresql_db
    user_id = uuid4()
    now = datetime.utcnow()

    # Form: 1 run (< MIN_FORM_RUNS)
    # Segment: 2 runs (< MIN_SEGMENT_RUNS)
    # Family: 4 runs (< MIN_FAMILY_RUNS)
    # Expected: No recommendation

    events = [
        AutofillEvent(
            user_id=user_id,
            host="acme.greenhouse.io",
            schema_hash="very-sparse",
            gen_style_id="style1",
            segment_key="senior",
            feedback_status="helpful",
            edit_chars=100,
            created_at=now,
        ),
        AutofillEvent(
            user_id=user_id,
            host="boards.greenhouse.io",
            schema_hash="other",
            gen_style_id="style2",
            segment_key="senior",
            feedback_status="helpful",
            edit_chars=100,
            created_at=now,
        ),
        *[
            AutofillEvent(
                user_id=user_id,
                host="greenhouse.io",
                schema_hash=f"form-{i}",
                gen_style_id="style3",
                segment_key="junior",
                feedback_status="helpful",
                edit_chars=100,
                created_at=now,
            )
            for i in range(4)
        ],
    ]

    for evt in events:
        db.add(evt)
    db.commit()

    form_stats = _compute_style_stats(db, 30)
    family_stats = _compute_family_style_stats(db, 30)
    segment_stats = _compute_segment_style_stats(db, 30)

    best, meta = _pick_style_for_profile(
        host="acme.greenhouse.io",
        schema_hash="very-sparse",
        form_stats=form_stats,
        family_stats=family_stats,
        segment_stats=segment_stats,
        segment_key="senior",
    )

    # Should return None
    assert best is None
    assert meta["source"] is None
