"""
Tests for Phase 2.0 learning endpoints with database persistence.

Tests cover:
- Event persistence to autofill_events table
- Profile creation and updates
- Query of learned profiles
- SQLite vs PostgreSQL behavior
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models_learning_db import FormProfile, AutofillEvent
from app.settings import settings


client = TestClient(app)

# Determine if we're on PostgreSQL or SQLite
IS_POSTGRES = "postgresql" in settings.DATABASE_URL.lower()


@pytest.mark.skipif(not IS_POSTGRES, reason="Requires PostgreSQL")
def test_learning_sync_persists_to_database(db_session: Session):
    """
    Phase 2.0: Learning sync persists events to autofill_events table.

    Given: A batch of learning events
    When: POSTing to /api/extension/learning/sync
    Then: Events are saved to database and profile is created/updated
    """
    payload = {
        "host": "greenhouse.io",
        "schema_hash": "abc123",
        "events": [
            {
                "host": "greenhouse.io",
                "schema_hash": "abc123",
                "suggested_map": {"first_name": "input_1", "last_name": "input_2"},
                "final_map": {"first_name": "input_1", "last_name": "input_2"},
                "gen_style_id": "concise_bullets_v1",
                "edit_stats": {
                    "total_chars_added": 5,
                    "total_chars_deleted": 2,
                    "per_field": {},
                },
                "duration_ms": 1500,
                "validation_errors": {},
                "status": "ok",
            }
        ],
    }

    # Send events
    response = client.post("/api/extension/learning/sync", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["persisted"] is True
    assert data["events_saved"] == 1

    # Verify event was saved
    events = (
        db_session.query(AutofillEvent)
        .filter(
            AutofillEvent.host == "greenhouse.io", AutofillEvent.schema_hash == "abc123"
        )
        .all()
    )
    assert len(events) >= 1

    # Verify profile was created/updated
    profile = (
        db_session.query(FormProfile)
        .filter(
            FormProfile.host == "greenhouse.io", FormProfile.schema_hash == "abc123"
        )
        .first()
    )
    assert profile is not None
    assert profile.last_seen_at is not None


@pytest.mark.skipif(not IS_POSTGRES, reason="Requires PostgreSQL")
def test_learning_profile_returns_database_data(db_session: Session):
    """
    Phase 2.0: Profile endpoint queries database for learned mappings.

    Given: A form profile exists in database
    When: GETting /api/extension/learning/profile
    Then: Returns the stored canonical mappings
    """
    # Create a profile in database
    profile = FormProfile(
        host="greenhouse.io",
        schema_hash="xyz789",
        fields={"first_name": "input_first", "email": "input_email"},
        success_rate=0.95,
        avg_edit_chars=10.5,
        avg_duration_ms=1200,
    )
    db_session.add(profile)
    db_session.commit()

    # Query profile
    response = client.get(
        "/api/extension/learning/profile?host=greenhouse.io&schema_hash=xyz789"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["host"] == "greenhouse.io"
    assert data["schema_hash"] == "xyz789"
    assert data["canonical_map"] == {
        "first_name": "input_first",
        "email": "input_email",
    }


@pytest.mark.skipif(not IS_POSTGRES, reason="Requires PostgreSQL")
def test_learning_profile_returns_empty_for_unknown_form(db_session: Session):
    """
    Phase 2.0: Profile endpoint returns empty for unknown forms.

    Given: No profile exists for a form
    When: GETting /api/extension/learning/profile
    Then: Returns empty canonical_map
    """
    response = client.get(
        "/api/extension/learning/profile?host=unknown.io&schema_hash=never_seen"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["host"] == "unknown.io"
    assert data["schema_hash"] == "never_seen"
    assert data["canonical_map"] == {}
    assert data["style_hint"] is None


@pytest.mark.skipif(IS_POSTGRES, reason="SQLite-specific test")
def test_learning_sync_skips_persistence_on_sqlite():
    """
    Phase 2.0: On SQLite, sync skips database persistence.

    Given: Running on SQLite database
    When: POSTing to /api/extension/learning/sync
    Then: Returns accepted but persisted=False
    """
    payload = {
        "host": "test.io",
        "schema_hash": "test123",
        "events": [
            {
                "host": "test.io",
                "schema_hash": "test123",
                "suggested_map": {},
                "final_map": {},
                "edit_stats": {
                    "total_chars_added": 0,
                    "total_chars_deleted": 0,
                    "per_field": {},
                },
                "duration_ms": 0,
                "validation_errors": {},
                "status": "ok",
            }
        ],
    }

    response = client.post("/api/extension/learning/sync", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["persisted"] is False
    assert data["reason"] == "sqlite"


@pytest.mark.skipif(IS_POSTGRES, reason="SQLite-specific test")
def test_learning_profile_returns_empty_on_sqlite():
    """
    Phase 2.0: On SQLite, profile returns empty (no persistence).

    Given: Running on SQLite database
    When: GETting /api/extension/learning/profile
    Then: Always returns empty profile
    """
    response = client.get("/api/extension/learning/profile?host=any.io&schema_hash=any")
    assert response.status_code == 200
    data = response.json()

    assert data["host"] == "any.io"
    assert data["schema_hash"] == "any"
    assert data["canonical_map"] == {}


@pytest.mark.skipif(not IS_POSTGRES, reason="Requires PostgreSQL")
def test_learning_sync_handles_multiple_events(db_session: Session):
    """
    Phase 2.0: Sync handles batch of multiple events.

    Given: A batch with 3 events
    When: POSTing to /api/extension/learning/sync
    Then: All 3 events are persisted
    """
    payload = {
        "host": "lever.co",
        "schema_hash": "batch123",
        "events": [
            {
                "host": "lever.co",
                "schema_hash": "batch123",
                "suggested_map": {"q1": "a1"},
                "final_map": {"q1": "a1"},
                "edit_stats": {
                    "total_chars_added": 0,
                    "total_chars_deleted": 0,
                    "per_field": {},
                },
                "duration_ms": 1000,
                "validation_errors": {},
                "status": "ok",
            },
            {
                "host": "lever.co",
                "schema_hash": "batch123",
                "suggested_map": {"q2": "a2"},
                "final_map": {"q2": "a2_edited"},
                "edit_stats": {
                    "total_chars_added": 7,
                    "total_chars_deleted": 0,
                    "per_field": {},
                },
                "duration_ms": 1500,
                "validation_errors": {},
                "status": "ok",
            },
            {
                "host": "lever.co",
                "schema_hash": "batch123",
                "suggested_map": {"q3": "a3"},
                "final_map": {"q3": "a3"},
                "edit_stats": {
                    "total_chars_added": 0,
                    "total_chars_deleted": 0,
                    "per_field": {},
                },
                "duration_ms": 800,
                "validation_errors": {},
                "status": "ok",
            },
        ],
    }

    response = client.post("/api/extension/learning/sync", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["events_saved"] == 3

    # Verify all events saved
    events = (
        db_session.query(AutofillEvent)
        .filter(
            AutofillEvent.host == "lever.co", AutofillEvent.schema_hash == "batch123"
        )
        .all()
    )
    assert len(events) >= 3


@pytest.mark.skipif(not IS_POSTGRES, reason="Requires PostgreSQL")
def test_learning_sync_validates_schema(db_session: Session):
    """
    Phase 2.0: Sync validates request schema.

    Given: Invalid payload (missing required field)
    When: POSTing to /api/extension/learning/sync
    Then: Returns 422 validation error
    """
    invalid_payload = {
        "host": "test.io",
        # Missing schema_hash
        "events": [],
    }

    response = client.post("/api/extension/learning/sync", json=invalid_payload)
    assert response.status_code == 422


@pytest.mark.skipif(not IS_POSTGRES, reason="Requires PostgreSQL")
def test_learning_sync_increments_prometheus_metric(db_session: Session):
    """
    Phase 2.0: Sync still increments Prometheus metrics.

    Given: A valid learning event
    When: POSTing to /api/extension/learning/sync
    Then: Prometheus counter is incremented with status="persisted"
    """
    from app.core.metrics import learning_sync_counter

    before = learning_sync_counter.labels(status="persisted")._value.get()

    payload = {
        "host": "metrics.io",
        "schema_hash": "metrics123",
        "events": [
            {
                "host": "metrics.io",
                "schema_hash": "metrics123",
                "suggested_map": {},
                "final_map": {},
                "edit_stats": {
                    "total_chars_added": 0,
                    "total_chars_deleted": 0,
                    "per_field": {},
                },
                "duration_ms": 100,
                "validation_errors": {},
                "status": "ok",
            }
        ],
    }

    response = client.post("/api/extension/learning/sync", json=payload)
    assert response.status_code == 202

    after = learning_sync_counter.labels(status="persisted")._value.get()
    assert after > before
