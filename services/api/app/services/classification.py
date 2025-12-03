"""
Email classification service for production ingest pipeline.

Usage in Gmail ingest:
    from app.services.classification import classify_and_persist_email

    email = Email(...)
    db.add(email)
    db.flush()  # Populate email.id

    classify_and_persist_email(db, email)
    db.commit()
"""

from sqlalchemy.orm import Session

from app.classification.email_classifier import (
    get_classifier,
    ClassificationResult,
    HybridEmailClassifier,
)
from app.models import Email, EmailClassificationEvent

# Global classifier instance (lazy-loaded)
_classifier: HybridEmailClassifier | None = None


def get_global_classifier() -> HybridEmailClassifier:
    """
    Get or create the global classifier instance.

    This avoids reloading ML models on every classification.
    Thread-safe for read-only operations (classify).
    """
    global _classifier
    if _classifier is None:
        _classifier = get_classifier()
    return _classifier


def classify_and_persist_email(db: Session, email: Email) -> ClassificationResult:
    """
    Classify an email and persist classification results.

    Updates the email row with:
        - category
        - is_real_opportunity
        - category_confidence
        - classifier_version

    Logs an EmailClassificationEvent for analytics.

    Args:
        db: Database session
        email: Email object (must have id populated via flush/commit)

    Returns:
        ClassificationResult with category, confidence, etc.

    Raises:
        ValueError: If email.id is None (call db.flush() first)
    """
    if email.id is None:
        raise ValueError(
            "Email must be flushed to DB before classification (email.id is None)"
        )

    classifier = get_global_classifier()
    result = classifier.classify(email)

    # Update email fields
    email.category = result.category
    email.is_real_opportunity = result.is_real_opportunity
    email.category_confidence = result.confidence
    email.classifier_version = result.model_version

    # Log classification event for analytics
    event = EmailClassificationEvent(
        email_id=email.id,
        thread_id=email.thread_id,
        model_version=result.model_version,
        predicted_category=result.category,
        predicted_is_real_opportunity=result.is_real_opportunity,
        confidence=result.confidence,
        source=result.source,
    )

    db.add(event)
    # Caller is responsible for commit

    return result


def reload_classifier() -> None:
    """
    Force reload of the global classifier (e.g., after model update).

    This is useful when deploying a new model version without restarting the server.
    """
    global _classifier
    _classifier = None
    # Next call to get_global_classifier() will load the new model
