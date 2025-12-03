"""
Bootstrap email_training_labels from existing emails with high-confidence rules.

This script applies heuristic rules to label emails that we're confident about,
creating training data for the ML classifier.

Usage:
    python -m scripts.bootstrap_email_training_labels [--limit N] [--dry-run]

Rules implemented:
    1. Application confirmations (ATS systems)
    2. Security/auth codes
    3. Job alert digests
    4. Receipts/invoices
    5. Interview invites (high-signal keywords)
"""

import argparse
import sys
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Email, EmailTrainingLabel


# Known ATS domains that send application confirmations
ATS_DOMAINS = [
    "greenhouse.io",
    "jobs.workablemail.com",
    "jobs.lever.co",
    "myworkday.com",
    "icims.com",
    "smartrecruiters.com",
    "jobvite.com",
    "brassring.com",
    "ultipro.com",
    "successfactors.com",
    "taleo.net",
]


def bootstrap_application_confirmations(
    db: Session, limit: int = 1000
) -> List[EmailTrainingLabel]:
    """
    Label emails that are clearly application confirmations from ATS systems.

    High-confidence rules:
        - Subject contains "application received" OR "we received your application"
        - OR sender domain is a known ATS
        - AND subject contains "application" or "applied"
    """
    labels = []

    # Rule 1: Subject-based application confirmations
    emails = (
        db.query(Email)
        .filter(
            Email.subject.ilike("%application received%")
            | Email.subject.ilike("%we received your application%")
            | Email.subject.ilike("%your application to%")
            | Email.subject.ilike("%application submitted%")
        )
        .filter(
            ~db.query(EmailTrainingLabel.id)
            .filter(EmailTrainingLabel.email_id == Email.id)
            .exists()
        )
        .limit(limit)
        .all()
    )

    for email in emails:
        labels.append(
            EmailTrainingLabel(
                email_id=email.id,
                thread_id=email.thread_id,
                label_category="application_confirmation",
                label_is_real_opportunity=True,
                label_source="bootstrap_rule_application_subject",
                confidence=0.95,
            )
        )

    # Rule 2: ATS domain senders
    for domain in ATS_DOMAINS:
        emails = (
            db.query(Email)
            .filter(Email.from_address.ilike(f"%@%{domain}%"))
            .filter(
                Email.subject.ilike("%application%") | Email.subject.ilike("%applied%")
            )
            .filter(
                ~db.query(EmailTrainingLabel.id)
                .filter(EmailTrainingLabel.email_id == Email.id)
                .exists()
            )
            .limit(100)
            .all()
        )

        for email in emails:
            labels.append(
                EmailTrainingLabel(
                    email_id=email.id,
                    thread_id=email.thread_id,
                    label_category="application_confirmation",
                    label_is_real_opportunity=True,
                    label_source=f"bootstrap_rule_ats_{domain.split('.')[0]}",
                    confidence=0.90,
                )
            )

    return labels


def bootstrap_security_codes(
    db: Session, limit: int = 1000
) -> List[EmailTrainingLabel]:
    """
    Label emails that are clearly security/auth codes.

    High-confidence rules:
        - Subject contains security/verification keywords
    """
    labels = []

    keywords = [
        "verification code",
        "one-time code",
        "2-step verification",
        "two-factor authentication",
        "security code",
        "authentication code",
        "2fa code",
        "confirm your email",
    ]

    for keyword in keywords:
        emails = (
            db.query(Email)
            .filter(Email.subject.ilike(f"%{keyword}%"))
            .filter(
                ~db.query(EmailTrainingLabel.id)
                .filter(EmailTrainingLabel.email_id == Email.id)
                .exists()
            )
            .limit(limit // len(keywords))
            .all()
        )

        for email in emails:
            labels.append(
                EmailTrainingLabel(
                    email_id=email.id,
                    thread_id=email.thread_id,
                    label_category="security_auth",
                    label_is_real_opportunity=False,
                    label_source="bootstrap_rule_security_code",
                    confidence=0.99,
                )
            )

    return labels


def bootstrap_job_alerts(db: Session, limit: int = 500) -> List[EmailTrainingLabel]:
    """
    Label emails that are job alert digests from known platforms.

    High-confidence rules:
        - Sender is LinkedIn, Indeed, Glassdoor, ZipRecruiter
        - Subject contains "job alert" OR "recommended jobs"
    """
    labels = []

    alert_senders = [
        ("linkedin.com", "linkedin"),
        ("indeed.com", "indeed"),
        ("glassdoor.com", "glassdoor"),
        ("ziprecruiter.com", "ziprecruiter"),
        ("monster.com", "monster"),
    ]

    for domain, platform in alert_senders:
        emails = (
            db.query(Email)
            .filter(Email.from_address.ilike(f"%@%{domain}%"))
            .filter(
                Email.subject.ilike("%job alert%")
                | Email.subject.ilike("%recommended jobs%")
                | Email.subject.ilike("%new jobs%")
                | Email.subject.ilike("%daily digest%")
            )
            .filter(
                ~db.query(EmailTrainingLabel.id)
                .filter(EmailTrainingLabel.email_id == Email.id)
                .exists()
            )
            .limit(limit // len(alert_senders))
            .all()
        )

        for email in emails:
            labels.append(
                EmailTrainingLabel(
                    email_id=email.id,
                    thread_id=email.thread_id,
                    label_category="job_alert_digest",
                    label_is_real_opportunity=False,
                    label_source=f"bootstrap_rule_job_alert_{platform}",
                    confidence=0.92,
                )
            )

    return labels


def bootstrap_receipts(db: Session, limit: int = 500) -> List[EmailTrainingLabel]:
    """
    Label emails that are clearly receipts/invoices.

    High-confidence rules:
        - Subject contains receipt/invoice keywords
    """
    labels = []

    keywords = [
        "receipt",
        "invoice",
        "payment confirmation",
        "order confirmation",
        "your order",
    ]

    for keyword in keywords:
        emails = (
            db.query(Email)
            .filter(Email.subject.ilike(f"%{keyword}%"))
            .filter(
                ~db.query(EmailTrainingLabel.id)
                .filter(EmailTrainingLabel.email_id == Email.id)
                .exists()
            )
            .limit(limit // len(keywords))
            .all()
        )

        for email in emails:
            labels.append(
                EmailTrainingLabel(
                    email_id=email.id,
                    thread_id=email.thread_id,
                    label_category="receipt_invoice",
                    label_is_real_opportunity=False,
                    label_source="bootstrap_rule_receipt",
                    confidence=0.93,
                )
            )

    return labels


def bootstrap_interview_invites(
    db: Session, limit: int = 500
) -> List[EmailTrainingLabel]:
    """
    Label emails that are likely interview invitations.

    Medium-high confidence rules:
        - Subject contains strong interview signals
    """
    labels = []

    strong_keywords = [
        "interview invitation",
        "schedule an interview",
        "phone screen",
        "video interview",
        "interview with",
        "interview for",
        "onsite interview",
    ]

    for keyword in strong_keywords:
        emails = (
            db.query(Email)
            .filter(Email.subject.ilike(f"%{keyword}%"))
            .filter(
                ~db.query(EmailTrainingLabel.id)
                .filter(EmailTrainingLabel.email_id == Email.id)
                .exists()
            )
            .limit(limit // len(strong_keywords))
            .all()
        )

        for email in emails:
            labels.append(
                EmailTrainingLabel(
                    email_id=email.id,
                    thread_id=email.thread_id,
                    label_category="interview_invite",
                    label_is_real_opportunity=True,
                    label_source="bootstrap_rule_interview_invite",
                    confidence=0.88,
                )
            )

    return labels


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap email_training_labels from high-confidence rules"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5000,
        help="Max emails to label per rule category",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stats without committing to DB",
    )
    args = parser.parse_args()

    db = SessionLocal()

    try:
        print("=== Email Training Labels Bootstrap ===\n")
        print(f"Limit per category: {args.limit}")
        print(f"Dry run: {args.dry_run}\n")

        # Check existing labels
        existing_count = db.query(func.count(EmailTrainingLabel.id)).scalar()
        print(f"Existing training labels: {existing_count}\n")

        all_labels = []

        # Run bootstrap rules
        print("Applying bootstrap rules...\n")

        print("[1/5] Application confirmations...")
        labels = bootstrap_application_confirmations(db, limit=args.limit)
        all_labels.extend(labels)
        print(f"      → {len(labels)} labels")

        print("[2/5] Security/auth codes...")
        labels = bootstrap_security_codes(db, limit=args.limit)
        all_labels.extend(labels)
        print(f"      → {len(labels)} labels")

        print("[3/5] Job alert digests...")
        labels = bootstrap_job_alerts(db, limit=args.limit // 2)
        all_labels.extend(labels)
        print(f"      → {len(labels)} labels")

        print("[4/5] Receipts/invoices...")
        labels = bootstrap_receipts(db, limit=args.limit // 2)
        all_labels.extend(labels)
        print(f"      → {len(labels)} labels")

        print("[5/5] Interview invites...")
        labels = bootstrap_interview_invites(db, limit=args.limit // 2)
        all_labels.extend(labels)
        print(f"      → {len(labels)} labels")

        print(f"\n✓ Total new labels: {len(all_labels)}")

        if args.dry_run:
            print("\n[DRY RUN] No changes committed to database")
        else:
            # Bulk insert
            db.bulk_save_objects(all_labels)
            db.commit()
            print("\n✅ Labels committed to database")

            # Show distribution
            print("\n=== Label Distribution ===")
            distribution = (
                db.query(
                    EmailTrainingLabel.label_category,
                    func.count(EmailTrainingLabel.id).label("count"),
                )
                .group_by(EmailTrainingLabel.label_category)
                .order_by(func.count(EmailTrainingLabel.id).desc())
                .all()
            )

            for category, count in distribution:
                print(f"  {category:30s} {count:>6,} labels")

            total = db.query(func.count(EmailTrainingLabel.id)).scalar()
            print(f"\n  {'TOTAL':30s} {total:>6,} labels")

            print("\n✅ Bootstrap complete!")
            print("\nNext step: python -m scripts.train_email_classifier")

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
