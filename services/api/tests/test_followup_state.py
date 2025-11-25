"""
Tests for followup queue state persistence.

Tests the POST /v2/followups/state endpoint for marking items done/not done.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import FollowupQueueState


@pytest.fixture
def mock_session_user(mocker):
    """Mock authenticated session user."""

    def mock_middleware(request, call_next):
        request.state.session_user_id = "test-user-123"
        return call_next(request)

    mocker.patch("app.main.app.middleware", return_value=mock_middleware)
    return "test-user-123"


def test_create_followup_state(client: TestClient, db: Session, mock_session_user):
    """Test creating a new followup state row."""
    payload = {
        "thread_id": "thread-abc",
        "application_id": 42,
        "is_done": True,
    }

    response = client.post("/v2/agent/followups/state", json=payload)

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    # Verify database state
    state = (
        db.query(FollowupQueueState)
        .filter(
            FollowupQueueState.user_id == mock_session_user,
            FollowupQueueState.thread_id == "thread-abc",
        )
        .first()
    )

    assert state is not None
    assert state.is_done is True
    assert state.application_id == 42
    assert state.done_at is not None


def test_update_followup_state_to_done(
    client: TestClient, db: Session, mock_session_user
):
    """Test updating existing state from not done to done."""
    # Create initial state (not done)
    state = FollowupQueueState(
        user_id=mock_session_user,
        thread_id="thread-xyz",
        application_id=None,
        is_done=False,
        done_at=None,
    )
    db.add(state)
    db.commit()

    # Update to done
    payload = {
        "thread_id": "thread-xyz",
        "is_done": True,
    }

    response = client.post("/v2/agent/followups/state", json=payload)

    assert response.status_code == 200

    # Verify state updated
    db.refresh(state)
    assert state.is_done is True
    assert state.done_at is not None


def test_update_followup_state_to_not_done(
    client: TestClient, db: Session, mock_session_user
):
    """Test updating existing state from done to not done."""
    from datetime import datetime, timezone

    # Create initial state (done)
    state = FollowupQueueState(
        user_id=mock_session_user,
        thread_id="thread-reset",
        application_id=99,
        is_done=True,
        done_at=datetime.now(timezone.utc),
    )
    db.add(state)
    db.commit()

    # Update to not done
    payload = {
        "thread_id": "thread-reset",
        "is_done": False,
    }

    response = client.post("/v2/agent/followups/state", json=payload)

    assert response.status_code == 200

    # Verify state updated
    db.refresh(state)
    assert state.is_done is False
    assert state.done_at is None


def test_followup_state_requires_authentication(client: TestClient, db: Session):
    """Test that state endpoint requires authentication."""
    payload = {
        "thread_id": "thread-123",
        "is_done": True,
    }

    # Mock no session user
    response = client.post("/v2/agent/followups/state", json=payload)

    assert response.status_code == 401
