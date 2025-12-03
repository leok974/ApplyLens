"""
Tests for email classification backfill script.

Tests the backfill_email_classification script's core logic:
- Dry-run mode (no commits)
- Limit enforcement
- Email field updates
- User filtering
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from app.classification.email_classifier import ClassificationResult
from scripts.backfill_email_classification import run_backfill

# Create test-specific Base and Email model for SQLite compatibility
TestBase = declarative_base()


class Email(TestBase):
    """Simplified Email model for SQLite testing (no ARRAY types)."""

    __tablename__ = "emails"

    id = Column(Integer, primary_key=True)
    gmail_id = Column(String(128))
    thread_id = Column(String(128))
    subject = Column(Text)
    body_text = Column(Text)
    sender = Column(String(512))
    received_at = Column(DateTime(timezone=True))
    owner_email = Column(String(320))

    # Classification fields
    category = Column(String(64))
    is_real_opportunity = Column(Boolean)
    category_confidence = Column(Float)
    classifier_version = Column(String(64))


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    TestBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_backfill_updates_emails(in_memory_db):
    """Test that backfill updates email classification fields."""
    db = in_memory_db

    # Seed 3 unclassified emails
    for i in range(3):
        email = Email(
            gmail_id=f"test-{i}",
            thread_id=f"thread-{i}",
            subject=f"Test Email {i}",
            body_text=f"Body {i}",
            sender=f"sender{i}@test.com",
            received_at=datetime(2025, 1, i + 1, tzinfo=timezone.utc),
            is_real_opportunity=None,  # Unclassified
            category=None,
            category_confidence=None,
        )
        db.add(email)
    db.commit()

    # Mock classify_and_persist_email to set fields
    call_count = 0

    def mock_classify(db_session, email):
        nonlocal call_count
        call_count += 1

        # Update email fields (simulate real classifier)
        email.category = "recruiter_outreach"
        email.is_real_opportunity = True
        email.category_confidence = 0.85
        email.classifier_version = "heuristic_v1"

        # Return fake result
        return ClassificationResult(
            category="recruiter_outreach",
            is_real_opportunity=True,
            confidence=0.85,
            model_version="heuristic_v1",
            source="heuristic",
        )

    with patch(
        "scripts.backfill_email_classification.classify_and_persist_email",
        side_effect=mock_classify,
    ):
        counters = run_backfill(db, limit=10, dry_run=False)

    # Assert all 3 emails were classified
    assert counters["total"] == 3
    assert counters["classified_ok"] == 3
    assert counters["errors"] == 0
    assert call_count == 3

    # Check database - emails should be updated
    emails = db.query(Email).all()
    for email in emails:
        assert email.is_real_opportunity is True
        assert email.category == "recruiter_outreach"
        assert email.category_confidence == 0.85


def test_backfill_dry_run_no_commit(in_memory_db):
    """Test that dry-run mode doesn't commit changes."""
    db = in_memory_db

    # Seed 2 unclassified emails
    for i in range(2):
        email = Email(
            gmail_id=f"test-{i}",
            thread_id=f"thread-{i}",
            subject=f"Test Email {i}",
            body_text=f"Body {i}",
            sender=f"sender{i}@test.com",
            received_at=datetime(2025, 1, i + 1, tzinfo=timezone.utc),
            is_real_opportunity=None,
        )
        db.add(email)
    db.commit()

    # Mock classifier
    def mock_classify(db_session, email):
        email.is_real_opportunity = True
        email.category = "interview_invite"
        email.category_confidence = 0.9
        return ClassificationResult(
            category="interview_invite",
            is_real_opportunity=True,
            confidence=0.9,
            model_version="heuristic_v1",
            source="heuristic",
        )

    with patch(
        "scripts.backfill_email_classification.classify_and_persist_email",
        side_effect=mock_classify,
    ):
        counters = run_backfill(db, limit=10, dry_run=True)

    # Classifier should have been called
    assert counters["classified_ok"] == 2

    # But changes should NOT be in database (rolled back)
    emails = db.query(Email).all()
    for email in emails:
        # Should still be None because dry-run rolled back
        assert email.is_real_opportunity is None
        assert email.category is None


def test_backfill_respects_limit(in_memory_db):
    """Test that limit parameter is respected."""
    db = in_memory_db

    # Seed 5 emails but limit to 2
    for i in range(5):
        email = Email(
            gmail_id=f"test-{i}",
            thread_id=f"thread-{i}",
            subject=f"Test Email {i}",
            body_text=f"Body {i}",
            sender=f"sender{i}@test.com",
            received_at=datetime(2025, 1, i + 1, tzinfo=timezone.utc),
            is_real_opportunity=None,
        )
        db.add(email)
    db.commit()

    # Mock classifier
    call_count = 0

    def mock_classify(db_session, email):
        nonlocal call_count
        call_count += 1
        email.is_real_opportunity = False
        return ClassificationResult(
            category="newsletter_marketing",
            is_real_opportunity=False,
            confidence=0.7,
            model_version="heuristic_v1",
            source="heuristic",
        )

    with patch(
        "scripts.backfill_email_classification.classify_and_persist_email",
        side_effect=mock_classify,
    ):
        counters = run_backfill(db, limit=2, dry_run=False)

    # Only 2 emails should be processed
    assert counters["total"] == 2
    assert counters["classified_ok"] == 2
    assert call_count == 2

    # Check that only 2 were updated
    classified = db.query(Email).filter(Email.is_real_opportunity.isnot(None)).count()
    assert classified == 2


def test_backfill_user_filter(in_memory_db):
    """Test that user_id filtering works."""
    db = in_memory_db

    # Seed emails for different users
    for i in range(3):
        email = Email(
            gmail_id=f"test-alice-{i}",
            thread_id=f"thread-{i}",
            subject=f"Alice Email {i}",
            body_text=f"Body {i}",
            sender=f"sender{i}@test.com",
            received_at=datetime(2025, 1, i + 1, tzinfo=timezone.utc),
            owner_email="alice@test.com",
            is_real_opportunity=None,
        )
        db.add(email)

    for i in range(2):
        email = Email(
            gmail_id=f"test-bob-{i}",
            thread_id=f"thread-{i + 10}",
            subject=f"Bob Email {i}",
            body_text=f"Body {i}",
            sender=f"sender{i}@test.com",
            received_at=datetime(2025, 1, i + 1, tzinfo=timezone.utc),
            owner_email="bob@test.com",
            is_real_opportunity=None,
        )
        db.add(email)
    db.commit()

    # Mock classifier
    def mock_classify(db_session, email):
        email.is_real_opportunity = True
        return ClassificationResult(
            category="recruiter_outreach",
            is_real_opportunity=True,
            confidence=0.8,
            model_version="heuristic_v1",
            source="heuristic",
        )

    with patch(
        "scripts.backfill_email_classification.classify_and_persist_email",
        side_effect=mock_classify,
    ):
        # Backfill only Alice's emails
        counters = run_backfill(db, limit=10, dry_run=False, user_id="alice@test.com")

    # Only Alice's 3 emails should be processed
    assert counters["total"] == 3
    assert counters["classified_ok"] == 3

    # Verify: Alice's emails classified, Bob's not
    alice_classified = (
        db.query(Email)
        .filter(
            Email.owner_email == "alice@test.com",
            Email.is_real_opportunity.isnot(None),
        )
        .count()
    )
    bob_classified = (
        db.query(Email)
        .filter(
            Email.owner_email == "bob@test.com",
            Email.is_real_opportunity.isnot(None),
        )
        .count()
    )

    assert alice_classified == 3
    assert bob_classified == 0


def test_backfill_handles_errors(in_memory_db):
    """Test that errors are caught and counted."""
    db = in_memory_db

    # Seed 3 emails
    for i in range(3):
        email = Email(
            gmail_id=f"test-{i}",
            thread_id=f"thread-{i}",
            subject=f"Test Email {i}",
            body_text=f"Body {i}",
            sender=f"sender{i}@test.com",
            received_at=datetime(2025, 1, i + 1, tzinfo=timezone.utc),
            is_real_opportunity=None,
        )
        db.add(email)
    db.commit()

    # Mock classifier to fail on second email
    call_count = 0

    def mock_classify(db_session, email):
        nonlocal call_count
        call_count += 1

        if call_count == 2:
            raise RuntimeError("Simulated classification error")

        email.is_real_opportunity = True
        return ClassificationResult(
            category="recruiter_outreach",
            is_real_opportunity=True,
            confidence=0.8,
            model_version="heuristic_v1",
            source="heuristic",
        )

    with patch(
        "scripts.backfill_email_classification.classify_and_persist_email",
        side_effect=mock_classify,
    ):
        counters = run_backfill(db, limit=10, dry_run=False)

    # All 3 processed, 2 ok, 1 error
    assert counters["total"] == 3
    assert counters["classified_ok"] == 2
    assert counters["errors"] == 1


def test_backfill_empty_result(in_memory_db):
    """Test that backfill handles empty results gracefully."""
    db = in_memory_db

    # No emails in database
    counters = run_backfill(db, limit=100, dry_run=False)

    assert counters["total"] == 0
    assert counters["classified_ok"] == 0
    assert counters["errors"] == 0
