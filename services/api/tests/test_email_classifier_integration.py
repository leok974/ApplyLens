# services/api/tests/test_email_classifier_integration.py

from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from app.classification.email_classifier import (
    HybridEmailClassifier,
    ClassificationResult,
    build_email_text,
)


def test_build_email_text():
    """Test that build_email_text handles various field combinations."""
    from app.models import Email

    # All fields present
    email = Email(
        subject="Interview for Senior Engineer",
        body_text="We'd like to schedule a call next week",
        sender="recruiter@tech.com",
        thread_id="test-123",
    )
    text = build_email_text(email)
    assert "Interview for Senior Engineer" in text
    assert "We'd like to schedule a call next week" in text
    assert "recruiter@tech.com" in text

    # Some fields None
    email_partial = Email(
        subject="Test Subject",
        body_text=None,
        sender="sender@test.com",
        thread_id="test-456",
    )
    text_partial = build_email_text(email_partial)
    assert "Test Subject" in text_partial
    assert "sender@test.com" in text_partial
    # Should handle None gracefully (no crash)

    # All fields None
    email_empty = Email(
        subject=None,
        body_text=None,
        sender=None,
        thread_id="test-789",
    )
    text_empty = build_email_text(email_empty)
    # Should return empty or minimal string, not crash
    assert isinstance(text_empty, str)


def create_in_memory_session():
    """Create a fresh in-memory SQLite session backed by simplified test models."""
    from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
    from sqlalchemy.sql import func
    from sqlalchemy import create_engine
    from sqlalchemy.orm import declarative_base

    # Create new base for test models
    TestBase = declarative_base()

    class Email(TestBase):
        """Simplified Email model for SQLite testing."""

        __tablename__ = "emails"

        id = Column(Integer, primary_key=True)
        subject = Column(String(500))
        snippet = Column(Text)
        from_address = Column(String(255))
        thread_id = Column(String(255))

        # Classification fields
        category = Column(String(64), index=True)
        is_real_opportunity = Column(Boolean, index=True)
        category_confidence = Column(Float)
        classifier_version = Column(String(64))

    class EmailClassificationEvent(TestBase):
        """Simplified EmailClassificationEvent model for SQLite testing."""

        __tablename__ = "email_classification_events"

        id = Column(Integer, primary_key=True)
        email_id = Column(Integer)
        thread_id = Column(String(255))
        model_version = Column(String(64))
        predicted_category = Column(String(64))
        predicted_is_real_opportunity = Column(Boolean)
        confidence = Column(Float)
        source = Column(String(64))
        created_at = Column(DateTime, default=func.now())

    # Create engine and tables
    engine = create_engine("sqlite:///:memory:")
    TestBase.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Return session and models as tuple
    session = TestingSessionLocal()
    session.Email = Email
    session.EmailClassificationEvent = EmailClassificationEvent
    return session


def classify_and_persist(
    db, classifier: HybridEmailClassifier, email, EmailClassificationEventModel
) -> ClassificationResult:
    """
    Minimal helper that mirrors the recommended ingest behavior:

        - classify()
        - write classification fields onto Email
        - insert EmailClassificationEvent
    """
    result = classifier.classify(email)

    email.category = result.category
    email.is_real_opportunity = result.is_real_opportunity
    email.category_confidence = result.confidence
    email.classifier_version = result.model_version

    event = EmailClassificationEventModel(
        email_id=email.id,
        thread_id=email.thread_id,
        model_version=result.model_version,
        predicted_category=result.category,
        predicted_is_real_opportunity=result.is_real_opportunity,
        confidence=result.confidence,
        source=result.source,
    )

    db.add(email)
    db.add(event)
    db.commit()
    db.refresh(email)

    return result


def test_hybrid_email_classifier_heuristic_mode_logs_event(monkeypatch):
    """
    Ensures that HybridEmailClassifier in heuristic-only mode:
        - Produces a ClassificationResult
        - Updates the Email row
        - Writes an EmailClassificationEvent row with matching values
    """
    db = create_in_memory_session()
    EmailModel = db.Email
    EmailClassificationEventModel = db.EmailClassificationEvent

    # Seed a minimal email that looks like a recruiter/interview message
    email = EmailModel(
        subject="Interview for Junior AI Engineer at Acme Corp",
        snippet="We would like to schedule a phone screen with you...",
        from_address="recruiter@acme-corp.com",
        thread_id="test-thread-1",
    )
    db.add(email)
    db.commit()
    db.refresh(email)

    # Force classifier into heuristic-only mode by making sure no ML artifacts are loaded
    from app.classification.email_classifier import get_classifier

    # Monkeypatch settings so classifier.mode is "heuristic"
    from app import config as app_config

    monkeypatch.setattr(app_config.agent_settings, "EMAIL_CLASSIFIER_MODE", "heuristic")
    # Also ensure no model paths are set (so get_classifier returns heuristics-only)
    monkeypatch.setattr(
        app_config.agent_settings, "EMAIL_CLASSIFIER_MODEL_PATH", "nonexistent"
    )
    monkeypatch.setattr(
        app_config.agent_settings, "EMAIL_CLASSIFIER_VECTORIZER_PATH", "nonexistent"
    )

    classifier = get_classifier()
    # Sanity: mode should be heuristic (may be set in __init__)
    assert isinstance(classifier, HybridEmailClassifier)

    result = classify_and_persist(db, classifier, email, EmailClassificationEventModel)

    # --- Assertions on Email row ---
    db.refresh(email)
    assert email.category in (
        "recruiter_outreach",
        "interview_invite",
        "newsletter_marketing",
    )
    assert email.is_real_opportunity in (True, False)
    assert email.classifier_version is not None

    # --- Assertions on ClassificationResult coherence ---
    assert result.category == email.category
    assert result.is_real_opportunity == email.is_real_opportunity
    assert result.model_version == email.classifier_version

    # --- Assertions on EmailClassificationEvent row ---
    events = (
        db.query(EmailClassificationEventModel)
        .filter(EmailClassificationEventModel.email_id == email.id)
        .order_by(EmailClassificationEventModel.created_at.asc())
        .all()
    )

    assert len(events) == 1
    evt = events[0]
    assert evt.thread_id == email.thread_id
    assert evt.model_version == email.classifier_version
    assert evt.predicted_category == email.category
    assert evt.predicted_is_real_opportunity == email.is_real_opportunity
    assert evt.confidence == email.category_confidence

    db.close()
