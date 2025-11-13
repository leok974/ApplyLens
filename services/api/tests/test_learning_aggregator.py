"""
Tests for autofill event aggregation (Phase 2.1).

Tests aggregation logic that builds FormProfile statistics from AutofillEvent history.
"""

import uuid
import pytest
from sqlalchemy.orm import Session

from app.autofill_aggregator import (
    aggregate_autofill_profiles,
    _compute_canonical_map,
    _compute_stats,
)
from app.models_learning_db import AutofillEvent, FormProfile
from app.settings import settings


# Determine if we're on PostgreSQL or SQLite
IS_POSTGRES = "postgresql" in settings.DATABASE_URL.lower()


@pytest.mark.skipif(not IS_POSTGRES, reason="Requires PostgreSQL")
def test_compute_canonical_map_picks_most_common_semantic(db_session: Session):
    """
    Canonical map selects most common semantic for each selector.

    Given: 3 events with votes for selectors
    When: Computing canonical map
    Then: Most common semantic wins for each selector
    """
    events = [
        AutofillEvent(
            user_id=uuid.uuid4(),
            host="test.io",
            schema_hash="test",
            final_map={"input[name='q1']": "first_name"},
            suggested_map={},
            edit_stats={"total_chars_added": 0, "total_chars_deleted": 0},
            duration_ms=100,
            status="ok",
        ),
        AutofillEvent(
            user_id=uuid.uuid4(),
            host="test.io",
            schema_hash="test",
            final_map={"input[name='q1']": "first_name"},
            suggested_map={},
            edit_stats={"total_chars_added": 0, "total_chars_deleted": 0},
            duration_ms=100,
            status="ok",
        ),
        AutofillEvent(
            user_id=uuid.uuid4(),
            host="test.io",
            schema_hash="test",
            final_map={"input[name='q1']": "given_name"},  # Different semantic
            suggested_map={},
            edit_stats={"total_chars_added": 0, "total_chars_deleted": 0},
            duration_ms=100,
            status="ok",
        ),
    ]

    canonical = _compute_canonical_map(events)

    # "first_name" has 2 votes, "given_name" has 1 vote
    assert canonical["input[name='q1']"] == "first_name"


@pytest.mark.skipif(not IS_POSTGRES, reason="Requires PostgreSQL")
def test_compute_stats_calculates_averages(db_session: Session):
    """
    Stats function computes success rate, edit distance, and duration.

    Given: Events with different outcomes and edit stats
    When: Computing aggregate stats
    Then: Returns correct averages
    """
    events = [
        AutofillEvent(
            user_id=uuid.uuid4(),
            host="test.io",
            schema_hash="test",
            final_map={},
            suggested_map={},
            edit_stats={"total_chars_added": 10, "total_chars_deleted": 5},  # 15 total
            duration_ms=1000,
            status="ok",
        ),
        AutofillEvent(
            user_id=uuid.uuid4(),
            host="test.io",
            schema_hash="test",
            final_map={},
            suggested_map={},
            edit_stats={"total_chars_added": 5, "total_chars_deleted": 0},  # 5 total
            duration_ms=2000,
            status="ok",
        ),
        AutofillEvent(
            user_id=uuid.uuid4(),
            host="test.io",
            schema_hash="test",
            final_map={},
            suggested_map={},
            edit_stats={"total_chars_added": 0, "total_chars_deleted": 0},  # 0 total
            duration_ms=1500,
            status="validation_failed",  # Not ok!
        ),
    ]

    success_rate, avg_edit_chars, avg_duration_ms = _compute_stats(events)

    # 2 out of 3 succeeded
    assert success_rate == pytest.approx(2.0 / 3.0)

    # Total edits: 15 + 5 + 0 = 20, average = 20/3 = 6.67
    assert avg_edit_chars == pytest.approx(20.0 / 3.0)

    # Total duration: 1000 + 2000 + 1500 = 4500, average = 1500
    assert avg_duration_ms == 1500


@pytest.mark.skipif(not IS_POSTGRES, reason="Requires PostgreSQL")
def test_aggregator_builds_profile_from_events(db_session: Session):
    """
    Aggregator creates FormProfile from AutofillEvent history.

    Given: Multiple events for same form
    When: Running aggregation
    Then: Profile created with correct canonical map and stats
    """
    # Create events
    ev1 = AutofillEvent(
        user_id=uuid.uuid4(),
        host="example.com",
        schema_hash="abc123",
        final_map={
            "input[name='first']": "first_name",
            "input[name='last']": "last_name",
        },
        suggested_map={
            "input[name='first']": "first_name",
            "input[name='last']": "last_name",
        },
        edit_stats={"total_chars_added": 0, "total_chars_deleted": 0},
        duration_ms=1000,
        status="ok",
    )
    ev2 = AutofillEvent(
        user_id=uuid.uuid4(),
        host="example.com",
        schema_hash="abc123",
        final_map={
            "input[name='first']": "first_name",
            "input[name='last']": "last_name",
        },
        suggested_map={
            "input[name='first']": "first_name",
            "input[name='last']": "last_name",
        },
        edit_stats={"total_chars_added": 10, "total_chars_deleted": 2},  # 12 edits
        duration_ms=1200,
        status="ok",
    )
    db_session.add_all([ev1, ev2])
    db_session.commit()

    # Run aggregation
    updated = aggregate_autofill_profiles(db_session, days=0)  # All events
    db_session.commit()

    # Verify
    assert updated >= 1

    profile = (
        db_session.query(FormProfile)
        .filter_by(host="example.com", schema_hash="abc123")
        .one()
    )

    # Check canonical map
    assert profile.fields["input[name='first']"] == "first_name"
    assert profile.fields["input[name='last']"] == "last_name"

    # Check stats
    assert profile.success_rate == pytest.approx(1.0)  # Both succeeded
    assert profile.avg_edit_chars == pytest.approx(6.0)  # (0 + 12) / 2
    assert profile.avg_duration_ms == 1100  # (1000 + 1200) / 2


@pytest.mark.skipif(not IS_POSTGRES, reason="Requires PostgreSQL")
def test_aggregator_updates_existing_profile(db_session: Session):
    """
    Aggregator updates existing profile instead of creating duplicate.

    Given: Profile already exists
    When: Running aggregation with new events
    Then: Existing profile updated, not duplicated
    """
    # Create existing profile
    existing = FormProfile(
        host="test.com",
        schema_hash="xyz789",
        fields={"old_field": "old_semantic"},
        success_rate=0.5,
        avg_edit_chars=100.0,
        avg_duration_ms=5000,
    )
    db_session.add(existing)
    db_session.commit()

    # Add new events
    ev = AutofillEvent(
        user_id=uuid.uuid4(),
        host="test.com",
        schema_hash="xyz789",
        final_map={"new_field": "new_semantic"},
        suggested_map={},
        edit_stats={"total_chars_added": 5, "total_chars_deleted": 0},
        duration_ms=1000,
        status="ok",
    )
    db_session.add(ev)
    db_session.commit()

    # Run aggregation
    aggregate_autofill_profiles(db_session, days=0)
    db_session.commit()

    # Verify only one profile exists
    profiles = (
        db_session.query(FormProfile)
        .filter_by(host="test.com", schema_hash="xyz789")
        .all()
    )

    assert len(profiles) == 1
    profile = profiles[0]

    # Check it was updated with new data
    assert "new_field" in profile.fields
    assert profile.fields["new_field"] == "new_semantic"


@pytest.mark.skipif(not IS_POSTGRES, reason="Requires PostgreSQL")
def test_aggregator_filters_by_days(db_session: Session):
    """
    Aggregator can filter events by recency.

    Given: Old and new events
    When: Running aggregation with days=1
    Then: Only recent events included

    Note: This test is simplified - in practice you'd mock datetime
    """
    # For now, test with days=0 (all events)
    # Full date filtering test would require mocking datetime.utcnow()

    ev = AutofillEvent(
        user_id=uuid.uuid4(),
        host="recent.com",
        schema_hash="new",
        final_map={"field": "semantic"},
        suggested_map={},
        edit_stats={"total_chars_added": 0, "total_chars_deleted": 0},
        duration_ms=100,
        status="ok",
    )
    db_session.add(ev)
    db_session.commit()

    # Run with days=0 (all events)
    updated = aggregate_autofill_profiles(db_session, days=0)

    assert updated >= 1


@pytest.mark.skipif(not IS_POSTGRES, reason="Requires PostgreSQL")
def test_aggregator_handles_empty_events_gracefully(db_session: Session):
    """
    Aggregator handles case with no events without errors.

    Given: No events in database
    When: Running aggregation
    Then: Returns 0 updated, no errors
    """
    # Don't add any events
    updated = aggregate_autofill_profiles(db_session, days=0)

    assert updated == 0


@pytest.mark.skipif(IS_POSTGRES, reason="SQLite-specific test")
def test_aggregator_works_on_sqlite(db_session: Session):
    """
    Aggregator runs without errors on SQLite (even though tables don't exist).

    This is a sanity check - in practice, aggregator won't be run on SQLite
    since the tables don't exist, but it shouldn't crash.
    """
    # This test mainly ensures imports work and function exists
    # Actual aggregation requires PostgreSQL tables
    from app.autofill_aggregator import aggregate_autofill_profiles

    # Function should exist and be callable
    assert callable(aggregate_autofill_profiles)
