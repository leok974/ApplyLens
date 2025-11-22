"""
Tests for Thread Detail API
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Email, User


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user (OAuth-based, no password)."""
    user = User(
        id="test-user-123", email="test@example.com", name="Test User", is_demo=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_thread(db_session: Session, test_user):
    """Create a test thread with multiple messages."""
    thread_id = "thread-123"

    # Create 3 emails in the thread (newest first for insertion order)
    email1 = Email(
        user_id=test_user.id,
        gmail_id="msg-1",
        thread_id=thread_id,
        subject="Test Thread",
        sender="alice@example.com",
        recipient="test@example.com",
        body_preview="First message in thread",
        body_text="First message in thread - full body",
        received_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        risk_score=0.1,
    )

    email2 = Email(
        user_id=test_user.id,
        gmail_id="msg-2",
        thread_id=thread_id,
        subject="Re: Test Thread",
        sender="bob@example.com",
        recipient="alice@example.com",
        body_preview="Second message in thread",
        body_text="Second message in thread - full body",
        received_at=datetime(2025, 1, 2, 10, 0, 0, tzinfo=timezone.utc),
        risk_score=0.5,
    )

    email3 = Email(
        user_id=test_user.id,
        gmail_id="msg-3",
        thread_id=thread_id,
        subject="Re: Test Thread",
        sender="alice@example.com",
        recipient="bob@example.com",
        body_preview="Third message in thread (most recent)",
        body_text="Third message in thread - full body",
        received_at=datetime(2025, 1, 3, 10, 0, 0, tzinfo=timezone.utc),
        risk_score=0.2,
    )

    db_session.add_all([email1, email2, email3])
    db_session.commit()

    return thread_id


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_get_thread_detail_success(client, test_thread, db_session):
    """Test successful thread detail retrieval."""
    response = client.get(f"/api/threads/{test_thread}")

    assert response.status_code == 200
    data = response.json()

    # Verify basic thread info
    assert data["threadId"] == test_thread
    assert data["subject"] == "Re: Test Thread"  # Subject from most recent message
    assert data["from"] == "alice@example.com"  # Sender from most recent message

    # Verify messages are present and sorted desc (most recent first)
    assert len(data["messages"]) == 3
    assert data["messages"][0]["from"] == "alice@example.com"  # Most recent
    assert data["messages"][1]["from"] == "bob@example.com"
    assert data["messages"][2]["from"] == "alice@example.com"  # Oldest

    # Verify timestamps are in descending order
    msg_times = [msg["sentAt"] for msg in data["messages"]]
    assert msg_times == sorted(msg_times, reverse=True)

    # Verify gmailUrl is present
    assert "mail.google.com" in data["gmailUrl"]
    assert test_thread in data["gmailUrl"]


def test_get_thread_detail_not_found(client):
    """Test 404 when thread doesn't exist."""
    response = client.get("/api/threads/nonexistent-thread-id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_thread_detail_messages_sorted(client, test_thread, db_session):
    """Test that messages are sorted by sentAt descending."""
    response = client.get(f"/api/threads/{test_thread}")

    assert response.status_code == 200
    data = response.json()

    # Extract sentAt times
    sent_at_times = [datetime.fromisoformat(msg["sentAt"]) for msg in data["messages"]]

    # Verify descending order (most recent first)
    for i in range(len(sent_at_times) - 1):
        assert (
            sent_at_times[i] >= sent_at_times[i + 1]
        ), "Messages should be sorted desc by sentAt"


def test_get_thread_detail_includes_body_text(client, test_thread, db_session):
    """Test that message body text is included."""
    response = client.get(f"/api/threads/{test_thread}")

    assert response.status_code == 200
    data = response.json()

    # Check that at least one message has bodyText
    body_texts = [msg.get("bodyText") for msg in data["messages"]]
    assert any(body_texts), "At least one message should have bodyText"
    assert (
        "full body" in body_texts[0]
        or "full body" in body_texts[1]
        or "full body" in body_texts[2]
    )


def test_get_thread_detail_snippet(client, test_thread, db_session):
    """Test that snippet is populated from body_preview."""
    response = client.get(f"/api/threads/{test_thread}")

    assert response.status_code == 200
    data = response.json()

    # Snippet should come from the most recent message's body_preview
    assert data["snippet"]
    assert (
        "most recent" in data["snippet"].lower() or "Third message" in data["snippet"]
    )
