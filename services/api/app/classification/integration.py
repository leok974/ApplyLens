"""
Helper functions for integrating email classification into ingest pipeline.

Usage in your Gmail worker:
    from app.classification.integration import classify_and_persist

    # After creating Email object:
    classify_and_persist(db, email)
    db.commit()
"""

from sqlalchemy.orm import Session

from app.classification.email_classifier import get_classifier, ClassificationResult
from app.models import Email, EmailClassificationEvent


def classify_and_persist(
    db: Session, email: Email, shadow_mode: bool = False
) -> ClassificationResult:
    """
    Classify an email and persist the results.

    Args:
        db: Database session
        email: Email object to classify
        shadow_mode: If True, log classification but don't update email fields

    Returns:
        ClassificationResult

    Example:
        email = Email(subject="Interview invitation", ...)
        db.add(email)
        db.flush()  # Get email.id

        result = classify_and_persist(db, email)
        db.commit()
    """
    classifier = get_classifier()
    result: ClassificationResult = classifier.classify(email)

    # Update email fields (unless in shadow mode)
    if not shadow_mode:
        email.category = result.category
        email.is_real_opportunity = result.is_real_opportunity
        email.category_confidence = result.confidence
        email.classifier_version = result.model_version

    # Log classification event
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

    return result


def log_category_correction(
    db: Session,
    email: Email,
    new_category: str,
    new_is_real_opportunity: bool,
    user_id: int | None = None,
) -> None:
    """
    Log a user's category correction.

    This should be called when a user manually changes an email's category
    or marks it as not an opportunity.

    Args:
        db: Database session
        email: Email being corrected
        new_category: User's corrected category
        new_is_real_opportunity: User's corrected opportunity flag
        user_id: Optional user ID making the correction
    """
    from app.models import EmailCategoryCorrection

    correction = EmailCategoryCorrection(
        email_id=email.id,
        thread_id=email.thread_id,
        old_category=email.category,
        new_category=new_category,
        old_is_real_opportunity=email.is_real_opportunity,
        new_is_real_opportunity=new_is_real_opportunity,
        user_id=user_id,
    )
    db.add(correction)

    # Update email with corrected values
    email.category = new_category
    email.is_real_opportunity = new_is_real_opportunity
    # Optionally reset confidence to indicate manual override
    email.category_confidence = 1.0
    email.classifier_version = "user_corrected"
