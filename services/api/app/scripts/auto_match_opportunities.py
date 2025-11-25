"""
CLI script for auto-matching job opportunities.

Run nightly via Docker scheduled task or cron to match all unmatched
opportunities for users with active resume profiles.

Usage:
    python -m app.scripts.auto_match_opportunities
"""

import asyncio
import logging
import sys

from app.db import SessionLocal
from app.services.opportunity_auto_match import auto_match_all_opportunities

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main entrypoint for auto-match script."""
    logger.info("Starting auto-match opportunities job")

    db = SessionLocal()
    try:
        total = await auto_match_all_opportunities(db)
        logger.info(f"✅ Auto-matched {total} opportunities")
        print(f"✅ Auto-matched {total} opportunities")
        return 0
    except Exception as e:
        logger.error(f"❌ Auto-match job failed: {e}", exc_info=True)
        print(f"❌ Auto-match job failed: {e}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
