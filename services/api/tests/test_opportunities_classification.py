"""
Tests for is_real_opportunity field integration in opportunities endpoint.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models import Email, Application
from app.routers.opportunities import is_real_opportunity


def test_is_real_opportunity_respects_classifier_field_true(db: Session):
    """Test that is_real_opportunity=True from classifier is respected."""
    email = Email(
        gmail_id="test1",
        thread_id="thread1",
        subject="Interview for Senior Engineer",
        sender="recruiter@company.com",
        body_text="We'd like to schedule an interview...",
        received_at=datetime.now(timezone.utc),
        owner_email="user@example.com",
        is_real_opportunity=True,  # Classifier says TRUE
        category="interview_invite",
        category_confidence=0.95,
        classifier_version="ml_v1",
    )

    # Should be True even without application
    assert is_real_opportunity(email, None) is True


def test_is_real_opportunity_respects_classifier_field_false(db: Session):
    """Test that is_real_opportunity=False from classifier is respected."""
    email = Email(
        gmail_id="test2",
        thread_id="thread2",
        subject="Your LinkedIn Job Alert",
        sender="jobs-noreply@linkedin.com",
        body_text="New jobs matching your preferences...",
        received_at=datetime.now(timezone.utc),
        owner_email="user@example.com",
        is_real_opportunity=False,  # Classifier says FALSE
        category="job_alert_digest",
        category_confidence=0.98,
        classifier_version="ml_v1",
    )

    # Should be False based on classifier
    assert is_real_opportunity(email, None) is False


def test_is_real_opportunity_classifier_true_but_app_closed(db: Session):
    """Test that closed applications are filtered even if classifier says True."""
    email = Email(
        gmail_id="test3",
        thread_id="thread3",
        subject="Interview for Senior Engineer",
        sender="recruiter@company.com",
        body_text="We'd like to schedule an interview...",
        received_at=datetime.now(timezone.utc),
        owner_email="user@example.com",
        is_real_opportunity=True,  # Classifier says TRUE
        category="interview_invite",
        category_confidence=0.95,
        classifier_version="ml_v1",
    )

    # Application is rejected
    app = Application(
        owner_email="user@example.com",
        company="Company Inc",
        role="Senior Engineer",
        status="rejected",  # Closed status
        thread_id="thread3",
    )

    # Should be False because app is closed (overrides classifier)
    assert is_real_opportunity(email, app) is False


def test_is_real_opportunity_fallback_to_heuristics(db: Session):
    """Test that heuristics work when is_real_opportunity is None."""
    email = Email(
        gmail_id="test4",
        thread_id="thread4",
        subject="Interview for Senior Engineer",
        sender="recruiter@company.com",
        body_text="We'd like to schedule an interview...",
        received_at=datetime.now(timezone.utc),
        owner_email="user@example.com",
        is_real_opportunity=None,  # No classifier data (old email)
        category="interview_invite",  # Category set but no is_real_opportunity
    )

    # Should fall back to heuristics and return True
    assert is_real_opportunity(email, None) is True


def test_is_real_opportunity_fallback_filters_job_alerts(db: Session):
    """Test that heuristics filter job alerts when classifier data is missing."""
    email = Email(
        gmail_id="test5",
        thread_id="thread5",
        subject="Your Daily Job Alert",
        sender="jobs-noreply@indeed.com",
        body_text="New jobs matching your search...",
        received_at=datetime.now(timezone.utc),
        owner_email="user@example.com",
        is_real_opportunity=None,  # No classifier data
        category=None,
    )

    # Should be filtered by heuristics
    assert is_real_opportunity(email, None) is False


def test_compute_priority_with_high_confidence():
    """Test that high confidence boosts priority score."""
    from app.routers.opportunities import compute_opportunity_priority

    # Same stage and time, but one has high confidence
    last_message = datetime.now(timezone.utc) - timedelta(days=5)

    priority_without_confidence = compute_opportunity_priority(
        application_status="interview",
        email_category="interview_invite",
        email_category_confidence=0.7,  # Low confidence
        last_message_at=last_message,
    )

    priority_with_high_confidence = compute_opportunity_priority(
        application_status="interview",
        email_category="interview_invite",
        email_category_confidence=0.95,  # High confidence -> +1 boost
        last_message_at=last_message,
    )

    # High confidence should result in higher or equal priority
    # Exact values depend on scoring logic, but high confidence should not decrease priority
    priority_order = {"high": 3, "medium": 2, "low": 1}
    assert (
        priority_order[priority_with_high_confidence]
        >= priority_order[priority_without_confidence]
    )


def test_compute_priority_uses_category():
    """Test that email category influences priority scoring."""
    from app.routers.opportunities import compute_opportunity_priority

    last_message = datetime.now(timezone.utc) - timedelta(days=2)

    # Offer category should have higher weight
    priority_offer = compute_opportunity_priority(
        application_status=None,  # No app status
        email_category="offer",
        email_category_confidence=None,
        last_message_at=last_message,
    )

    # Low-value category
    priority_newsletter = compute_opportunity_priority(
        application_status=None,
        email_category="newsletter_marketing",
        email_category_confidence=None,
        last_message_at=last_message,
    )

    priority_order = {"high": 3, "medium": 2, "low": 1}
    assert priority_order[priority_offer] > priority_order[priority_newsletter]
