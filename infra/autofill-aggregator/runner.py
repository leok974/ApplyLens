#!/usr/bin/env python3
"""Autofill aggregator scheduler.

Runs profile aggregation on a schedule to update companion autofill data.
Aggregates host patterns from application tracking data to improve form autofill.
"""

import os
import sys
import time
import random
from datetime import datetime

# Add API app to path
sys.path.insert(0, "/api/app")

# Configuration
ENABLED = os.getenv("COMPANION_AUTOFILL_AGG_ENABLED", "0") == "1"
HOURS = int(os.getenv("AGG_EVERY_HOURS", "6"))
DAYS = int(os.getenv("AGG_LOOKBACK_DAYS", "30"))


def log(level, msg):
    """Structured logging."""
    ts = datetime.utcnow().isoformat() + "Z"
    print(f"[autofill-agg] {ts} {level} {msg}", flush=True)


def run_aggregator_wrapper():
    """Run the autofill aggregator.

    Calls the actual aggregator function from the API codebase.
    Returns stats about what was updated.
    """
    if not ENABLED:
        log("SKIP", "aggregator disabled (COMPANION_AUTOFILL_AGG_ENABLED=0)")
        return {"profiles_updated": 0, "hosts_processed": 0, "duration_s": 0}

    start_time = time.time()

    try:
        # Import the actual aggregator function from API
        from app.autofill_aggregator import run_aggregator

        # Run aggregation
        profiles_updated = run_aggregator(days=DAYS)

        duration = time.time() - start_time

        log(
            "OK",
            f"aggregation complete: profiles={profiles_updated} duration={duration:.2f}s lookback={DAYS}d",
        )

        return {
            "profiles_updated": profiles_updated,
            "hosts_processed": 0,  # Tracked inside run_aggregator
            "duration_s": round(duration, 2),
        }

    except Exception as e:
        duration = time.time() - start_time
        log(
            "ERR",
            f"aggregation failed: {type(e).__name__}: {e} duration={duration:.2f}s",
        )
        return {
            "profiles_updated": 0,
            "hosts_processed": 0,
            "duration_s": round(duration, 2),
            "error": str(e),
        }


def main():
    """Main scheduler loop."""
    log(
        "START",
        f"autofill aggregator starting (enabled={ENABLED}, interval={HOURS}h, lookback={DAYS}d)",
    )

    # Initial jitter to avoid thundering herd on container restart
    initial_jitter = random.randint(10, 60)
    log("SLEEP", f"initial_jitter={initial_jitter}s")
    time.sleep(initial_jitter)

    while True:
        # Run aggregation
        stats = run_aggregator_wrapper()

        # Calculate next run time (with small jitter)
        sleep_seconds = HOURS * 3600 + random.randint(0, 300)  # +0-5min jitter

        log("SLEEP", f"next_run_in={sleep_seconds}s ({HOURS}h) " f"stats={stats}")

        time.sleep(sleep_seconds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("EXIT", "keyboard interrupt")
        sys.exit(0)
