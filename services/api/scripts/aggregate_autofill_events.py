#!/usr/bin/env python3
"""
Companion Learning Aggregator - Nightly Job

Aggregates AutofillEvent rows into FormProfile statistics:
- Canonical field mappings (most common selector→semantic pairs)
- Success rate (% of events with status='ok')
- Average edit distance (chars added/deleted)
- Average completion time
- Style performance tracking and preferred_style_id selection

Run via cron or manually:
    python scripts/aggregate_autofill_events.py --days 30
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.autofill_aggregator import aggregate_autofill_profiles

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate autofill events into form profiles"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Look back N days (0 = all events, default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without committing to database",
    )

    args = parser.parse_args()

    logger.info(f"Starting autofill aggregation (lookback: {args.days} days)")

    if args.dry_run:
        logger.info("DRY RUN MODE - no database changes will be made")

    db = SessionLocal()

    try:
        profiles_updated = aggregate_autofill_profiles(db, days=args.days)

        if args.dry_run:
            db.rollback()
            logger.info(f"DRY RUN: Would have updated {profiles_updated} profiles")
        else:
            db.commit()
            logger.info(f"✓ Successfully updated {profiles_updated} form profiles")

        return 0

    except Exception as e:
        db.rollback()
        logger.error(f"✗ Aggregation failed: {e}", exc_info=True)
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
