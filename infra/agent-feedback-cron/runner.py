#!/usr/bin/env python3
"""
Agent Feedback Aggregation Cron Job

Periodically calls the /api/v2/agent/feedback/aggregate endpoint to:
- Aggregate user feedback from companion usage
- Update agent learning models
- Generate performance reports

Schedule: Every N hours (configurable via EVERY_HOURS env var)
"""

import os
import sys
import time
import logging
from datetime import datetime
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Configuration from environment
API_URL = os.getenv(
    "API_URL", "http://applylens-api-prod:8003/api/v2/agent/feedback/aggregate"
)
EVERY_HOURS = int(os.getenv("EVERY_HOURS", "6"))  # Default: 6 hours
TIMEOUT = int(os.getenv("TIMEOUT", "120"))  # Default: 2 minutes
BACKFILL_API_KEY = os.getenv("BACKFILL_API_KEY", "")


def aggregate_feedback():
    """Call the feedback aggregation endpoint."""
    try:
        logger.info(f"🔄 Calling {API_URL}")

        headers = {}
        if BACKFILL_API_KEY:
            headers["X-API-Key"] = BACKFILL_API_KEY

        response = requests.post(
            API_URL,
            headers=headers,
            timeout=TIMEOUT,
            json={},  # Empty payload, endpoint handles defaults
        )

        response.raise_for_status()
        data = response.json()

        logger.info("✅ Aggregation completed successfully")
        logger.info(f"   Response: {data}")

        return True

    except requests.exceptions.Timeout:
        logger.error(f"⏱️  Timeout after {TIMEOUT}s - aggregation may still be running")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"   Status: {e.response.status_code}")
            logger.error(f"   Body: {e.response.text[:500]}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return False


def main():
    """Main loop - run aggregation every N hours."""
    logger.info("🚀 Agent Feedback Aggregator starting")
    logger.info(f"   API URL: {API_URL}")
    logger.info(f"   Interval: Every {EVERY_HOURS} hour(s)")
    logger.info(f"   Timeout: {TIMEOUT} seconds")

    # Run first aggregation immediately
    logger.info("⏰ Running initial aggregation...")
    aggregate_feedback()

    # Calculate sleep interval
    interval_seconds = EVERY_HOURS * 3600

    # Main loop
    while True:
        next_run = datetime.now().replace(microsecond=0)
        next_run = next_run.replace(
            hour=(next_run.hour + EVERY_HOURS) % 24, minute=0, second=0
        )

        logger.info(f"⏰ Next run scheduled for {next_run}")
        logger.info(f"   Sleeping for {EVERY_HOURS} hour(s)...")

        time.sleep(interval_seconds)

        logger.info("⏰ Starting scheduled aggregation...")
        aggregate_feedback()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("⏹️  Shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)
