"""
Async Gmail backfill API - Returns immediately with job ID, tracks progress.

Endpoints:
- POST /gmail/backfill/start - Start async backfill, returns job_id
- GET /gmail/backfill/status - Check job status and progress
- POST /gmail/backfill/cancel - Cancel running job

TODO: Replace in-memory JOBS dict with Redis for production multi-instance support
"""

import logging
import os
import time
import uuid
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from ..db import SessionLocal
from ..metrics import BACKFILL_INSERTED, BACKFILL_REQUESTS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail/backfill", tags=["gmail"])

# In-memory job store (replace with Redis in production)
JOBS: Dict[str, Dict] = {}

# Rate limiting per user
_BACKFILL_COOLDOWN_SECONDS = int(os.getenv("BACKFILL_COOLDOWN_SECONDS", "300"))
_LAST_BACKFILL_TS = {}


class StartResp(BaseModel):
    job_id: str
    started: bool


class StatusResp(BaseModel):
    job_id: str
    state: str  # queued | running | done | error | canceled
    processed: int = 0
    total: Optional[int] = None
    error: Optional[str] = None
    inserted: Optional[int] = None  # Final count when done
    started_at: Optional[float] = None  # Unix timestamp
    completed_at: Optional[float] = None  # Unix timestamp


class CancelResp(BaseModel):
    ok: bool
    error: Optional[str] = None


def _run_backfill(job_id: str, days: int, user_email: str):
    """Background task to run Gmail backfill with progress tracking"""
    logger.info(f"[Job {job_id}] Starting backfill for {user_email}, days={days}")

    try:
        # Update state to running
        if job_id not in JOBS:
            logger.warning(f"[Job {job_id}] Job not found in JOBS dict")
            return

        JOBS[job_id]["state"] = "running"
        JOBS[job_id]["started_at"] = time.time()

        # Run the actual backfill with progress tracking
        db = SessionLocal()
        try:
            # Import here to avoid circular dependency
            from ..gmail_service import gmail_backfill_with_progress

            def progress_callback(processed: int, total: int):
                """Update job progress"""
                if job_id in JOBS:
                    JOBS[job_id]["processed"] = processed
                    JOBS[job_id]["total"] = total

                    # Check if job was canceled
                    if JOBS[job_id]["state"] == "canceled":
                        raise InterruptedError("Job canceled by user")

            count = gmail_backfill_with_progress(
                db,
                user_email=user_email,
                days=days,
                progress_callback=progress_callback,
            )

            # Force ES refresh to make documents immediately searchable
            try:
                from ..gmail_service import es_client

                es = es_client()
                index_name = os.getenv("ELASTICSEARCH_INDEX", "gmail_emails")
                es.indices.refresh(index=index_name)
                logger.info(f"[Job {job_id}] Refreshed ES index: {index_name}")
            except Exception as e:
                logger.warning(f"[Job {job_id}] ES refresh failed: {e}")

            # Mark as done
            JOBS[job_id]["state"] = "done"
            JOBS[job_id]["processed"] = count
            JOBS[job_id]["inserted"] = count
            JOBS[job_id]["completed_at"] = time.time()

            # Metrics
            BACKFILL_REQUESTS.labels(result="ok").inc()
            BACKFILL_INSERTED.inc(count)

            logger.info(f"[Job {job_id}] Completed successfully, inserted={count}")

        except InterruptedError:
            logger.info(f"[Job {job_id}] Canceled by user")
            JOBS[job_id]["state"] = "canceled"
            BACKFILL_REQUESTS.labels(result="canceled").inc()
        except Exception as e:
            logger.error(
                f"[Job {job_id}] Error during backfill: {str(e)}", exc_info=True
            )
            JOBS[job_id]["state"] = "error"
            JOBS[job_id]["error"] = str(e)
            BACKFILL_REQUESTS.labels(result="error").inc()
        finally:
            db.close()

    except Exception as e:
        logger.error(f"[Job {job_id}] Fatal error: {str(e)}", exc_info=True)
        if job_id in JOBS:
            JOBS[job_id]["state"] = "error"
            JOBS[job_id]["error"] = f"Fatal error: {str(e)}"


@router.post("/start", response_model=StartResp, status_code=202)
def start_backfill(
    days: int = Query(60, ge=1, le=365),
    user_email: Optional[str] = Query(None),
    bt: BackgroundTasks = None,
):
    """
    Start async Gmail backfill job.

    Returns immediately with job_id. Use /status to poll for completion.
    """
    global _LAST_BACKFILL_TS
    now = time.time()

    # Get user email
    email = user_email or os.getenv("DEFAULT_USER_EMAIL")
    if not email:
        BACKFILL_REQUESTS.labels(result="bad_request").inc()
        raise HTTPException(400, "user_email required (or set DEFAULT_USER_EMAIL)")

    # Per-user rate limit
    last_ts = _LAST_BACKFILL_TS.get(email, 0)
    if now - last_ts < _BACKFILL_COOLDOWN_SECONDS:
        remaining = int(_BACKFILL_COOLDOWN_SECONDS - (now - last_ts))
        BACKFILL_REQUESTS.labels(result="rate_limited").inc()
        raise HTTPException(
            status_code=429,
            detail=f"Backfill too frequent; try again in {remaining} seconds.",
        )

    # Create job
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {
        "state": "queued",
        "processed": 0,
        "total": None,
        "user_email": email,
        "days": days,
        "created_at": now,
    }

    # Update rate limit timestamp
    _LAST_BACKFILL_TS[email] = now

    # Enqueue background task
    bt.add_task(_run_backfill, job_id, days, email)

    logger.info(f"[Job {job_id}] Queued backfill for {email}, days={days}")

    return StartResp(job_id=job_id, started=True)


@router.get("/status", response_model=StatusResp)
def get_status(job_id: str = Query(..., description="Job ID from /start")):
    """
    Get job status and progress.

    States:
    - queued: Job is waiting to start
    - running: Job is currently executing
    - done: Job completed successfully
    - error: Job failed with error
    - canceled: Job was canceled by user
    """
    j = JOBS.get(job_id)

    if not j:
        return StatusResp(
            job_id=job_id,
            state="error",
            error="Job not found. It may have expired or never existed.",
        )

    return StatusResp(
        job_id=job_id,
        state=j["state"],
        processed=j.get("processed", 0),
        total=j.get("total"),
        error=j.get("error"),
        inserted=j.get("inserted"),
        started_at=j.get("started_at"),
        completed_at=j.get("completed_at"),
    )


@router.post("/cancel", response_model=CancelResp)
def cancel_job(job_id: str = Query(..., description="Job ID to cancel")):
    """
    Cancel a running or queued job.

    Note: This sets a flag but may not stop immediately if already running.
    """
    j = JOBS.get(job_id)

    if not j:
        return CancelResp(ok=False, error="Job not found")

    if j["state"] in ["done", "error"]:
        return CancelResp(ok=False, error=f"Job already {j['state']}")

    # Set canceled flag
    j["state"] = "canceled"

    logger.info(f"[Job {job_id}] Canceled by user")

    return CancelResp(ok=True)


@router.get("/jobs", response_model=Dict[str, StatusResp])
def list_jobs(user_email: Optional[str] = Query(None)):
    """
    List all jobs (optionally filtered by user_email).

    Useful for debugging and monitoring.
    """
    filtered_jobs = {}

    for job_id, job_data in JOBS.items():
        # Filter by user if provided
        if user_email and job_data.get("user_email") != user_email:
            continue

        filtered_jobs[job_id] = StatusResp(
            job_id=job_id,
            state=job_data["state"],
            processed=job_data.get("processed", 0),
            total=job_data.get("total"),
            error=job_data.get("error"),
            inserted=job_data.get("inserted"),
        )

    return filtered_jobs
