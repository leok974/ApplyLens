# Dev-only backfill endpoints for E2E testing
from fastapi import APIRouter, Depends, HTTPException, Response
import os
import uuid
from app.deps.auth_keys import require_backfill_key
from app.core.metrics import backfill_runs_total, backfill_emails_synced

router = APIRouter(tags=["gmail", "dev"])


def require_dev():
    """Ensure dev routes are only accessible when ALLOW_DEV_ROUTES=1"""
    if os.getenv("ALLOW_DEV_ROUTES") != "1":
        raise HTTPException(status_code=403, detail="Dev routes disabled")


@router.post(
    "/gmail/backfill/start",
    operation_id="gmail_backfill_start",
    dependencies=[Depends(require_dev), Depends(require_backfill_key)],
    status_code=202,
)
def start_backfill(days: int = 7, response: Response = None):
    """Start a Gmail backfill job (dev stub)

    Accessible via:
    - /gmail/backfill/start (production path)
    - /api/gmail/backfill/start (canonical API path)

    Requires:
    - ALLOW_DEV_ROUTES=1 environment variable
    - Valid X-API-Key header (if BACKFILL_API_KEY is set)

    Returns:
    - 202 Accepted with job details
    - X-RateLimit-Limit header for rate limit info
    - Retry-After header if rate limited
    """
    try:
        job_id = str(uuid.uuid4())

        # Simulate email sync count
        emails_synced = 42
        backfill_emails_synced.inc(emails_synced)

        # Track successful run
        backfill_runs_total.labels(status="ok").inc()

        # Add rate limit headers
        if response:
            response.headers["X-RateLimit-Limit"] = "2/30m"
            response.headers["X-RateLimit-Remaining"] = "1"

        return {
            "job_id": job_id,
            "status": "accepted",
            "days": days,
            "message": f"Backfill job {job_id} started (dev stub)",
            "emails_synced": emails_synced,
            "version": "dev-stub",
        }
    except Exception as e:
        # Track failed run
        backfill_runs_total.labels(status="err").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/gmail/backfill/start",
    operation_id="gmail_backfill_start_api",
    dependencies=[Depends(require_dev), Depends(require_backfill_key)],
    status_code=202,
)
def start_backfill_api(days: int = 7, response: Response = None):
    """Start a Gmail backfill job - API path alias

    This is an alias for /gmail/backfill/start to support both paths.
    The /api/ prefix is the canonical path going forward.
    """
    return start_backfill(days, response)


@router.get(
    "/gmail/backfill/status",
    operation_id="gmail_backfill_status",
    dependencies=[Depends(require_dev)],
)
def get_backfill_status(job_id: str):
    """Get backfill job status (query param)

    Accessible via:
    - /gmail/backfill/status?job_id=...
    - /api/gmail/backfill/status?job_id=...
    """
    return {
        "job_id": job_id,
        "state": "done",  # Match expected field name
        "status": "completed",
        "progress": 100,
        "processed": 42,
        "total": 42,
        "emails_synced": 42,
        "version": "dev-stub",
    }


@router.get(
    "/api/gmail/backfill/status",
    operation_id="gmail_backfill_status_api",
    dependencies=[Depends(require_dev)],
)
def get_backfill_status_api(job_id: str):
    """Get backfill job status - API path alias"""
    return get_backfill_status(job_id)
