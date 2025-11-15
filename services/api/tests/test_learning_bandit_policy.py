"""Phase 5.4: Tests for bandit policy tracking in learning sync."""

import uuid
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models_learning import (
    AutofillLearningEvent,
    EditStats,
    LearningSyncRequest,
)
from app.models_learning_db import AutofillEvent


def _create_sync_request(policy: str | None = None) -> dict:
    """Create a learning sync request with optional policy."""
    event = AutofillLearningEvent(
        host="greenhouse.io",
        schema_hash="abc123",
        suggested_map={"name": "John Doe"},
        final_map={"name": "John Doe"},
        gen_style_id=str(uuid.uuid4()),
        segment_key="tech",
        policy=policy,  # Phase 5.4
        edit_stats=EditStats(total_chars_added=0, total_chars_deleted=0, per_field={}),
        duration_ms=1234,
        validation_errors={},
        status="accepted",
    )
    return LearningSyncRequest(
        host="greenhouse.io",
        schema_hash="abc123",
        events=[event],
    ).model_dump()


def test_sync_with_policy_explore(client: TestClient, db_session: Session):
    """Test that policy='explore' is persisted to database."""
    payload = _create_sync_request(policy="explore")

    response = client.post("/api/extension/learning/sync", json=payload)
    assert response.status_code == 202

    # Verify database record has policy='explore'
    db_event = (
        db_session.query(AutofillEvent)
        .filter(AutofillEvent.host == "greenhouse.io")
        .filter(AutofillEvent.schema_hash == "abc123")
        .filter(AutofillEvent.policy == "explore")
        .first()
    )
    assert db_event is not None
    assert db_event.policy == "explore"
    assert db_event.segment_key == "tech"


def test_sync_with_policy_exploit(client: TestClient, db_session: Session):
    """Test that policy='exploit' is persisted to database."""
    payload = _create_sync_request(policy="exploit")

    response = client.post("/api/extension/learning/sync", json=payload)
    assert response.status_code == 202

    # Verify database record has policy='exploit'
    db_event = (
        db_session.query(AutofillEvent)
        .filter(AutofillEvent.host == "greenhouse.io")
        .filter(AutofillEvent.schema_hash == "abc123")
        .filter(AutofillEvent.policy == "exploit")
        .first()
    )
    assert db_event is not None
    assert db_event.policy == "exploit"


def test_sync_without_policy_defaults_to_exploit(
    client: TestClient, db_session: Session
):
    """Test that missing policy defaults to 'exploit'."""
    payload = _create_sync_request(policy=None)

    response = client.post("/api/extension/learning/sync", json=payload)
    assert response.status_code == 202

    # Verify database record defaults to policy='exploit'
    db_event = (
        db_session.query(AutofillEvent)
        .filter(AutofillEvent.host == "greenhouse.io")
        .filter(AutofillEvent.schema_hash == "abc123")
        .order_by(AutofillEvent.created_at.desc())
        .first()
    )
    assert db_event is not None
    assert db_event.policy == "exploit"


def test_sync_with_policy_fallback(client: TestClient, db_session: Session):
    """Test that policy='fallback' is persisted to database."""
    payload = _create_sync_request(policy="fallback")

    response = client.post("/api/extension/learning/sync", json=payload)
    assert response.status_code == 202

    # Verify database record has policy='fallback'
    db_event = (
        db_session.query(AutofillEvent)
        .filter(AutofillEvent.host == "greenhouse.io")
        .filter(AutofillEvent.schema_hash == "abc123")
        .filter(AutofillEvent.policy == "fallback")
        .first()
    )
    assert db_event is not None
    assert db_event.policy == "fallback"


def test_sync_increments_policy_metrics(client: TestClient):
    """Test that policy metrics are incremented (smoke test - no crash)."""
    payload = _create_sync_request(policy="explore")

    # Should not raise an exception
    response = client.post("/api/extension/learning/sync", json=payload)
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
