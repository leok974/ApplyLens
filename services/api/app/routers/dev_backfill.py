# Dev-only backfill endpoints for E2E testing
from fastapi import APIRouter, Depends, HTTPException
import os
import uuid

router = APIRouter(prefix="/gmail/backfill", tags=["gmail", "dev"])


def require_dev():
    """Ensure dev routes are only accessible when ALLOW_DEV_ROUTES=1"""
    if os.getenv("ALLOW_DEV_ROUTES") != "1":
        raise HTTPException(status_code=403, detail="Dev routes disabled")


@router.post("/start", dependencies=[Depends(require_dev)], status_code=202)
def start_backfill(days: int = 7):
    """Dev stub for starting a Gmail backfill job"""
    job_id = str(uuid.uuid4())
    return {
        "job_id": job_id,
        "status": "accepted",
        "days": days,
        "message": f"Backfill job {job_id} started (dev stub)",
        "version": "dev-stub",
    }


@router.get("/status", dependencies=[Depends(require_dev)])
def get_backfill_status(job_id: str):
    """Dev stub for checking backfill job status (query param)"""
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
