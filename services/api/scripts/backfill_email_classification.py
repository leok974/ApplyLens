"""
Backfill email classification for historical emails.

Usage (from services/api/):

    # Dry run - see what would be updated
    python -m scripts.backfill_email_classification --limit 1000 --dry-run

    # Real backfill
    python -m scripts.backfill_email_classification --limit 1000

    # Backfill for specific user
    python -m scripts.backfill_email_classification --user-id leo@applylens.app --limit 500

This script:
    - Finds emails with is_real_opportunity IS NULL (unclassified)
    - Processes oldest first (by received_at) for gradual historical coverage
    - Uses the production classifier (classify_and_persist_email)
    - Tracks counters: total processed, updated, skipped, errors
    - Supports dry-run mode (no database commit)
"""

from __future__ import annotations

import argparse
import logging
from typing import Optional

from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Email
from app.services.classification import classify_and_persist_email

logger = logging.getLogger(__name__)


def run_backfill(
    db: Session,
    limit: int,
    dry_run: bool,
    user_id: Optional[str] = None,
) -> dict[str, int]:
    """
    Run classification backfill for unclassified emails.

    Args:
        db: Database session
        limit: Maximum number of emails to process
        dry_run: If True, don't commit changes
        user_id: Optional user email to filter by (only backfill that user's emails)

    Returns:
        Dict with counters: total, classified_ok, skipped, errors
    """
    counters = {
        "total": 0,
        "classified_ok": 0,
        "skipped": 0,
        "errors": 0,
    }

    # Build query for unclassified emails
    q = db.query(Email).filter(Email.is_real_opportunity.is_(None))

    # Optional user filter
    if user_id:
        q = q.filter(Email.owner_email == user_id)

    # Process oldest first for gradual historical coverage
    q = q.order_by(asc(Email.received_at)).limit(limit)

    emails = q.all()

    if not emails:
        logger.info("No unclassified emails found to backfill")
        return counters

    logger.info(
        f"Found {len(emails)} unclassified emails to process "
        f"(limit={limit}, user_id={user_id or 'all'})"
    )

    for email in emails:
        counters["total"] += 1

        try:
            # Skip if email has no id (should never happen in practice)
            if email.id is None:
                logger.warning(f"Email has no ID, skipping: {email}")
                counters["skipped"] += 1
                continue

            # Classify and persist
            result = classify_and_persist_email(db, email)

            counters["classified_ok"] += 1

            # Log every 100 emails
            if counters["classified_ok"] % 100 == 0:
                logger.info(
                    f"Progress: {counters['classified_ok']}/{len(emails)} emails classified"
                )

            # Log details for first few emails
            if counters["total"] <= 5:
                logger.info(
                    f"Email {email.id}: {result.category}, "
                    f"is_opp={result.is_real_opportunity}, "
                    f"conf={result.confidence:.3f}, "
                    f"source={result.source}"
                )

        except Exception as e:
            logger.error(
                f"Error classifying email {email.id}: {e}",
                exc_info=True,
            )
            counters["errors"] += 1

    # Commit or rollback based on dry_run flag
    if dry_run:
        logger.info("DRY RUN: Rolling back changes (no database commit)")
        db.rollback()
    else:
        logger.info("Committing classification updates to database")
        db.commit()

    return counters


def main() -> None:
    """CLI entry point for backfill script."""
    parser = argparse.ArgumentParser(
        description="Backfill email classification for historical emails."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of emails to process (default: 1000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mode - don't commit changes to database",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        help="Only backfill emails for specific user (email address)",
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("=" * 60)
    logger.info("Email Classification Backfill")
    logger.info("=" * 60)
    logger.info(f"Limit: {args.limit}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"User filter: {args.user_id or 'none (all users)'}")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        counters = run_backfill(
            db=db,
            limit=args.limit,
            dry_run=args.dry_run,
            user_id=args.user_id,
        )

        # Print summary
        logger.info("=" * 60)
        logger.info("Backfill Summary")
        logger.info("=" * 60)
        logger.info(f"Total processed:    {counters['total']}")
        logger.info(f"Classified OK:      {counters['classified_ok']}")
        logger.info(f"Skipped:            {counters['skipped']}")
        logger.info(f"Errors:             {counters['errors']}")
        logger.info("=" * 60)

        if args.dry_run:
            logger.info("DRY RUN: No changes committed")
        else:
            logger.info("Changes committed to database")

    finally:
        db.close()


if __name__ == "__main__":
    main()
