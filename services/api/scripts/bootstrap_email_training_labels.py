"""
Bootstrap high-confidence training labels for the email classifier.

Usage (from services/api/):

    python -m scripts.bootstrap_email_training_labels --limit 5000

This script:
    - Scans recent emails (up to --limit)
    - Applies a few conservative rules to assign labels
    - Inserts rows into email_training_labels with confidence scores
"""

from __future__ import annotations

import argparse
from typing import Optional, Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Email, EmailTrainingLabel


# --- Label helpers ---------------------------------------------------------


def _norm(s: Optional[str]) -> str:
    return (s or "").lower()


def infer_label_for_email(email: Email) -> Optional[Tuple[str, bool, str, float]]:
    """
    Return (category, is_real_opportunity, label_source, confidence)
    or None if we don't have a high-confidence guess.

    This is intentionally conservative: we only emit labels when extremely confident.
    """
    subject = _norm(getattr(email, "subject", None))
    snippet = _norm(getattr(email, "body_text", None))

    text = subject + " " + snippet

    # 1) Security / auth codes
    if any(
        k in text
        for k in [
            "verification code",
            "one-time code",
            "one time code",
            "2-step verification",
            "two-step verification",
            "security code",
        ]
    ):
        return (
            "security_auth",
            False,
            "bootstrap_rule_security_auth",
            0.99,
        )

    # 2) Receipts / invoices
    if any(
        k in text
        for k in [
            "your receipt",
            "payment receipt",
            "payment confirmation",
            "invoice",
            "order confirmation",
            "thank you for your purchase",
        ]
    ):
        return (
            "receipt_invoice",
            False,
            "bootstrap_rule_receipt_invoice",
            0.97,
        )

    # 3) Application confirmation / ATS emails
    if any(
        k in text
        for k in [
            "we received your application",
            "your application to",
            "thank you for applying",
            "application received",
            "has been submitted",
        ]
    ):
        return (
            "application_confirmation",
            True,
            "bootstrap_rule_application_confirmation",
            0.92,
        )

    # 4) Interview invites
    if any(
        k in text
        for k in [
            "would like to schedule an interview",
            "interview with",
            "phone screen",
            "phone interview",
            "technical interview",
            "onsite interview",
        ]
    ):
        return (
            "interview_invite",
            True,
            "bootstrap_rule_interview_invite",
            0.94,
        )

    # 5) Obvious job alert digests / newsletters
    if any(
        k in text
        for k in [
            "daily job alert",
            "job alerts for",
            "jobs we found for you",
            "weekly job round-up",
            "weekly job roundup",
            "weekly newsletter",
            "our latest newsletter",
            "this week in",
        ]
    ):
        return (
            "job_alert_digest",
            False,
            "bootstrap_rule_job_alert_digest",
            0.9,
        )

    # 6) Generic marketing newsletter
    if any(
        k in text
        for k in [
            "our latest blog posts",
            "new features we released",
            "this month we",
            "our latest update",
        ]
    ):
        return (
            "newsletter_marketing",
            False,
            "bootstrap_rule_newsletter_marketing",
            0.88,
        )

    # No confident label
    return None


def email_already_labeled(db: Session, email_id: int) -> bool:
    return (
        db.query(EmailTrainingLabel.id)
        .filter(EmailTrainingLabel.email_id == email_id)
        .limit(1)
        .scalar()
        is not None
    )


# --- Main script -----------------------------------------------------------


def bootstrap_labels(limit: int) -> int:
    """
    Bootstrap labels for up to `limit` emails.
    Returns the number of EmailTrainingLabel rows inserted.
    """
    db: Session = SessionLocal()
    inserted = 0

    try:
        # Process most recent emails first (more relevant content)
        q = db.query(Email).order_by(desc(Email.received_at)).limit(limit)

        for email in q:
            if email_already_labeled(db, email.id):
                continue

            inferred = infer_label_for_email(email)
            if inferred is None:
                continue

            category, is_real_opp, source, confidence = inferred

            tl = EmailTrainingLabel(
                email_id=email.id,
                thread_id=email.thread_id,
                label_category=category,
                label_is_real_opportunity=is_real_opp,
                label_source=source,
                confidence=confidence,
            )
            db.add(tl)
            inserted += 1

        if inserted:
            db.commit()
        else:
            db.rollback()

    finally:
        db.close()

    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap high-confidence training labels for the email classifier."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5000,
        help="Max number of emails to scan (default: 5000).",
    )
    args = parser.parse_args()

    inserted = bootstrap_labels(limit=args.limit)
    print(f"Inserted {inserted} training labels")


if __name__ == "__main__":
    main()
