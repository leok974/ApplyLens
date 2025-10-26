"""
Tracker API - Job application tracking

Endpoints:
- GET /api/tracker - List all applications for the current user

Note: Applications table currently lacks user_id column.
This is a skeleton implementation that returns empty list until migration is added.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps.user import get_current_user_email

router = APIRouter(prefix="/tracker", tags=["tracker"])
logger = logging.getLogger(__name__)


# ===== Models =====


class ApplicationRow(BaseModel):
    """Single application in tracker view."""

    id: str  # Changed from int to str to match frontend expectations
    company: str
    role: str
    stage: str  # e.g. "applied", "interview", "offer", "rejected", "ghosted"
    source: Optional[str]
    last_activity_at: Optional[str]  # ISO 8601 datetime string


class TrackerListResponse(BaseModel):
    """List of applications."""

    applications: List[ApplicationRow]


# ===== Endpoints =====


@router.get("", response_model=TrackerListResponse)
def get_tracker(
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> TrackerListResponse:
    """
    List all job applications for the current user.

    Returns applications sorted by most recent activity first.
    This is the stable public contract for the UI - frontend should call /api/tracker.

    NOTE: Currently returns demo data. Will query real applications table
    after migration adds user_id column.
    """
    try:
        # TODO: Uncomment after applications table gets user_id column
        # from ..models.application import Application
        #
        # applications = (
        #     db.query(Application)
        #     .filter(Application.user_id == user_email)
        #     .order_by(Application.updated_at.desc())
        #     .all()
        # )
        #
        # rows = [
        #     ApplicationRow(
        #         id=str(app.id),  # Convert int to str for frontend
        #         company=app.company,
        #         role=app.role,
        #         stage=app.status,
        #         source=app.source,
        #         last_activity_at=app.updated_at.isoformat() if app.updated_at else None,
        #     )
        #     for app in applications
        # ]

        # Demo data for now (sorted by most recent activity)
        logger.info(f"Tracker requested by {user_email} (returning demo data)")
        rows = [
            ApplicationRow(
                id="app_1",
                company="TechCorp",
                role="Senior Backend Engineer",
                stage="offer",
                source="LinkedIn",
                last_activity_at="2025-10-05T00:00:00",
            ),
            ApplicationRow(
                id="app_2",
                company="Acme Corp",
                role="Full-Stack Developer",
                stage="interview",
                source="Lever",
                last_activity_at="2025-10-01T00:00:00",
            ),
            ApplicationRow(
                id="app_3",
                company="OpenAI",
                role="ML Engineer",
                stage="applied",
                source="Greenhouse",
                last_activity_at="2025-09-20T00:00:00",
            ),
            ApplicationRow(
                id="app_4",
                company="StartupXYZ",
                role="DevOps Engineer",
                stage="rejected",
                source="Indeed",
                last_activity_at="2025-09-01T00:00:00",
            ),
        ]

        return TrackerListResponse(applications=rows)

    except Exception as e:
        logger.exception(f"Failed to get tracker applications: {e}")
        # Graceful degradation - return empty list
        return TrackerListResponse(applications=[])
