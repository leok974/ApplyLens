"""Job opportunities listing and management endpoints.

API DESIGN RULE (Dec 2024):
    All FastAPI routes using SessionLocal (sync SQLAlchemy) MUST be `def`, not `async def`.
    Do NOT convert these handlers to async def unless we fully migrate to async SQLAlchemy.

    Why: FastAPI cannot properly serialize responses from async handlers that contain
    only synchronous operations (no await). This causes silent 500 errors in production.
    See test_routes_resume_opportunities.py for regression tests.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..deps.user import get_current_user_email
from ..db import get_db
from ..models import Application, Email, JobOpportunity, OpportunityMatch
from .agent import is_newsletter_or_digest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])

OpportunityPriority = Literal["low", "medium", "high"]


# ===== Filter Helpers =====


JOB_BOARD_DOMAINS = {
    "indeed.com",
    "ziprecruiter.com",
    "glassdoor.com",
    "monster.com",
    "simplyhired.com",
    "jobcase.com",
    "careerbuilder.com",
    "noreply.linkedin.com",
    "linkedin.com",
}

JOB_ALERT_SUBJECT_PATTERNS = [
    r"new jobs for you",
    r"jobs you might like",
    r"job alerts?",
    r"top jobs",
    r"daily (job )?digest",
    r"recommended jobs",
    r"because you searched",
    r"job recommendations",
]

# Priority scoring constants
STAGE_WEIGHTS = {
    "offer": 4,
    "negotiation": 4,
    "onsite": 3,
    "final_round": 3,
    "onsite_interview": 3,
    "interview": 2,
    "hr_screen": 2,
    "phone_screen": 2,
    "applied": 1,
    "recruiter_outreach": 1,
}

CATEGORY_STAGE_HINTS = {
    "offer": 4,
    "interview_invite": 3,
    "onsite": 3,
    "phone_screen": 2,
    "recruiter_outreach": 1,
}

GOOD_CATEGORIES = {
    "offer",
    "interview_invite",
    "onsite",
    "phone_screen",
    "hr_screen",
    "recruiter_outreach",
}


def _age_bonus(last_message_at: Optional[datetime]) -> int:
    """
    Calculate recency bonus based on how old the opportunity is.

    More recent = higher bonus:
    - ≤ 3 days: +2
    - ≤ 7 days: +1
    - ≤ 21 days: 0
    - > 21 days: -1
    """
    if last_message_at is None:
        return 0

    if last_message_at.tzinfo is None:
        last_message_at = last_message_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    age_days = (now - last_message_at).total_seconds() / 86400.0

    if age_days <= 3:
        return 2
    if age_days <= 7:
        return 1
    if age_days <= 21:
        return 0
    return -1


def compute_opportunity_priority(
    *,
    application_status: Optional[str],
    email_category: Optional[str],
    email_category_confidence: Optional[float],
    last_message_at: Optional[datetime],
) -> OpportunityPriority:
    """
    Compute priority score for an opportunity based on:
    - Stage (from application status or email category)
    - Recency (age of last message)
    - Category quality
    - **NEW**: Category confidence from ML classifier

    Returns:
    - "high": score >= 5 (hot opportunities)
    - "medium": score >= 3 (warm opportunities)
    - "low": score < 3 (backlog/cold)
    """
    status = (application_status or "").lower()
    category = (email_category or "").lower()

    # Stage weight from app status, fallback to category hints
    stage_weight = STAGE_WEIGHTS.get(status)
    if stage_weight is None:
        stage_weight = CATEGORY_STAGE_HINTS.get(category, 0)

    age = _age_bonus(last_message_at)

    category_bonus = 1 if category in GOOD_CATEGORIES else 0

    # NEW: Confidence boost for high-confidence ML predictions
    # Only apply if we have both category and high confidence
    confidence_boost = 0
    if email_category_confidence is not None and email_category_confidence >= 0.9:
        confidence_boost = 1  # Extra point for very confident classifications

    score = stage_weight + age + category_bonus + confidence_boost

    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def is_job_alert_or_blast(email: Email) -> bool:
    """
    Detect job board alerts and mass mailings.

    Returns True if the email is a generic job alert/blast that should be excluded
    from the opportunities list (not a real recruiter outreach).
    """
    subject = (email.subject or "").lower()
    from_addr = (email.sender or "").lower()

    # Check sender domain against known job boards
    if any(domain in from_addr for domain in JOB_BOARD_DOMAINS):
        return True

    # Check subject for job alert patterns
    for pattern in JOB_ALERT_SUBJECT_PATTERNS:
        if re.search(pattern, subject, re.IGNORECASE):
            return True

    # Check body for bulk email markers
    # Use body_text field from Email model
    body = (email.body_text or "").lower()
    # Require both markers to avoid false positives
    has_unsubscribe = "unsubscribe" in body
    has_browser_view = (
        "view this email in your browser" in body or "view in browser" in body
    )
    if has_unsubscribe and has_browser_view:
        return True

    return False


NEEDS_ATTENTION_STATUSES = {"applied", "hr_screen", "interview", "onsite", "offer"}
CLOSED_STATUSES = {"rejected", "withdrawn", "ghosted", "closed"}


def is_real_opportunity(email: Email, application: Optional[Application]) -> bool:
    """
    Determine if an Email+Application pair represents a real opportunity.

    Returns True if this is a legitimate recruiter outreach / application thread
    that should be shown in the opportunities list.

    Filters out:
    - Newsletters and digests
    - Job board alerts and mass mailings
    - Applications with terminal/closed statuses
    - Emails with non-recruiting categories

    **NEW (Dec 2025)**: Prioritizes email.is_real_opportunity field if populated
    by the email classifier. Falls back to heuristics if field is None.
    """
    # PRIORITY 1: Use email.is_real_opportunity field if classifier has set it
    if email.is_real_opportunity is not None:
        # If classifier says it's not an opportunity, respect that
        if not email.is_real_opportunity:
            return False
        # If classifier says it IS an opportunity, still check application status
        # (classifier doesn't know about closed/withdrawn apps)
        if application:
            status = (application.status.value if application.status else "").lower()
            if status in CLOSED_STATUSES:
                return False
        return True

    # FALLBACK: Use legacy heuristics if is_real_opportunity field is None
    # (e.g., old emails before classifier was deployed)

    # 1) Filter out newsletters/digests using existing helper
    # Convert Email model to dict format expected by is_newsletter_or_digest
    thread_dict = {
        "subject": email.subject,
        "from_email": email.sender,
    }
    labels = email.labels or []
    category = email.category

    if is_newsletter_or_digest(thread_dict, labels=labels, category=category):
        return False

    # 2) Filter out job board alerts and blasts
    if is_job_alert_or_blast(email):
        return False

    # 3) If we have an application, require a "live" status
    if application:
        status = (application.status.value if application.status else "").lower()
        if status in CLOSED_STATUSES:
            return False
        if status not in NEEDS_ATTENTION_STATUSES:
            # Don't treat purely informational states as "opportunities"
            return False

    # 4) Optionally use email category if available
    category_str = (category or "").lower()
    if category_str:
        # Only allow categories that look like real recruiting leads
        allowed_categories = {
            "recruiter_outreach",
            "interview_invite",
            "phone_screen",
            "onsite",
            "offer",
            "application_update",
            "applications",  # general application category
        }
        # If there's a category but it's not in allowed list, exclude it
        if category_str not in allowed_categories:
            return False

    return True


# ===== Schemas =====


class OpportunityResponse(BaseModel):
    """Job opportunity response schema."""

    id: int
    owner_email: str
    source: str
    title: str
    company: str
    location: Optional[str]
    remote_flag: Optional[bool]
    salary_text: Optional[str]
    level: Optional[str]
    tech_stack: Optional[list[str]]
    apply_url: Optional[str]
    posted_at: Optional[str]
    created_at: str

    # Match data (if available)
    match_bucket: Optional[str] = None
    match_score: Optional[float] = None

    # Priority scoring (hot/warm/cold)
    priority: OpportunityPriority = "low"

    class Config:
        from_attributes = True


# ===== Endpoints =====


@router.get("", response_model=list[OpportunityResponse])
def list_opportunities(
    source: Optional[str] = Query(
        None, description="Filter by source (indeed, linkedin, etc.)"
    ),
    company: Optional[str] = Query(
        None, description="Filter by company name (partial match)"
    ),
    match_bucket: Optional[str] = Query(
        None, description="Filter by match bucket (perfect, strong, possible, skip)"
    ),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    """List job opportunities for the authenticated user.

    Returns filtered opportunities from real recruiter emails and applications,
    excluding newsletters, job alerts, and closed applications.

    Filters applied:
    - Removes newsletters and marketing digests
    - Removes job board alerts and mass mailings
    - Removes applications with terminal statuses (rejected, withdrawn, etc.)
    - Only includes emails with recruiting categories or active application statuses

    - **source**: Optional filter by aggregator source (indeed, linkedin, etc.)
    - **company**: Optional filter by company name (case-insensitive partial match)
    - **match_bucket**: Optional filter by match quality (perfect, strong, possible, skip)
    - **limit**: Maximum number of results (default: 100, max: 500)
    - **offset**: Number of results to skip for pagination (default: 0)

    Returns opportunities sorted by recency (most recent email first).
    """

    try:
        logger.info(f"list_opportunities called for user_email={user_email}")

        # Query emails with potential applications
        # Start with emails that have application category or are linked to applications
        email_query = (
            db.query(Email, Application)
            .outerjoin(Application, Email.application_id == Application.id)
            .filter(Email.owner_email == user_email)
            # Focus on recent emails (last 6 months) to avoid processing entire history
            .filter(Email.received_at >= func.now() - text("INTERVAL '6 months'"))
        )

        logger.info("Email query constructed successfully")
    except Exception as e:
        logger.exception(f"Error in list_opportunities for user {user_email}: {e}")
        raise HTTPException(
            status_code=500, detail="Internal error listing opportunities"
        )  # Apply company filter if provided
    if company:
        email_query = email_query.filter(
            (Email.company.ilike(f"%{company}%"))
            | (Application.company.ilike(f"%{company}%"))
        )

    # Apply source filter if provided (email source or application source)
    if source:
        email_query = email_query.filter(
            (Email.source == source) | (Application.source == source)
        )

    # Order by recency
    email_query = email_query.order_by(Email.received_at.desc())

    # Execute query (we'll filter in Python due to complex logic)
    email_app_pairs = email_query.all()

    # Filter using our opportunity detection logic
    filtered_items = []
    for email, application in email_app_pairs:
        if not is_real_opportunity(email, application):
            continue

        last_message_at = email.received_at

        # Compute priority score
        priority = compute_opportunity_priority(
            application_status=application.status.value
            if application and application.status
            else None,
            email_category=email.category,
            email_category_confidence=email.category_confidence,
            last_message_at=last_message_at,
        )

        # Build response item
        filtered_items.append(
            {
                "email": email,
                "application": application,
                "company": application.company if application else email.company,
                "role": application.role if application else email.role,
                "status": application.status.value
                if application and application.status
                else None,
                "last_message_at": last_message_at,
                "email_id": email.id,
                "thread_id": email.thread_id,
                "priority": priority,
            }
        )

    # Apply match_bucket filter if specified (for JobOpportunity integration)
    # Note: This filter applies to the old JobOpportunity model, not Email/Application
    # We keep it for backward compatibility but it won't filter Email-based opportunities
    if match_bucket:
        logger.warning(
            f"match_bucket filter ({match_bucket}) not applicable to Email-based opportunities"
        )

    # Sort by priority (high > medium > low), then by recency
    priority_rank = {"high": 2, "medium": 1, "low": 0}
    filtered_items.sort(
        key=lambda it: (
            priority_rank[it["priority"]],
            it["last_message_at"] or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )

    # Apply pagination
    total_count = len(filtered_items)
    paginated_items = filtered_items[offset : offset + limit]

    # Convert to response format
    results = []
    for item in paginated_items:
        email = item["email"]
        application = item["application"]

        # For backward compatibility, map to OpportunityResponse schema
        # Note: Some fields like tech_stack, apply_url won't be populated from Email
        try:
            results.append(
                OpportunityResponse(
                    id=email.id,  # Use email ID as opportunity ID
                    owner_email=email.owner_email or user_email,
                    source=email.source
                    or (application.source if application else "email"),
                    title=item["role"] or email.subject or "",
                    company=item["company"] or "Unknown",
                    location=None,  # Not available in Email model
                    remote_flag=None,  # Not available in Email model
                    salary_text=None,  # Not available in Email model
                    level=None,  # Not available in Email model
                    tech_stack=None,  # Not available in Email model
                    apply_url=None,  # Not available in Email model
                    posted_at=None,
                    created_at=email.received_at.isoformat()
                    if email.received_at
                    else "",
                    match_bucket=None,  # Not applicable for Email-based opportunities
                    match_score=None,  # Not applicable for Email-based opportunities
                    priority=item["priority"],
                )
            )
        except Exception as e:
            logger.exception(
                f"Error creating OpportunityResponse for email {email.id}: {e}"
            )

    logger.info(
        f"Listed {len(results)}/{total_count} opportunities for user {user_email} "
        f"(source={source}, company={company}, after filtering noise)"
    )

    return results


@router.get("/{opportunity_id}", response_model=dict)
def get_opportunity_detail(
    opportunity_id: int,
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    """Get detailed information for a specific opportunity including match data.

    Returns opportunity details with full match analysis (reasons, missing_skills, resume_tweaks).
    """

    # Load opportunity
    opportunity = (
        db.query(JobOpportunity)
        .filter(
            JobOpportunity.id == opportunity_id,
            JobOpportunity.owner_email == user_email,
        )
        .first()
    )

    if not opportunity:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found",
        )

    # Load match data
    match = (
        db.query(OpportunityMatch)
        .filter(OpportunityMatch.opportunity_id == opportunity_id)
        .first()
    )

    result = {
        "id": opportunity.id,
        "owner_email": opportunity.owner_email,
        "source": opportunity.source,
        "source_message_id": opportunity.source_message_id,
        "title": opportunity.title,
        "company": opportunity.company,
        "location": opportunity.location,
        "remote_flag": opportunity.remote_flag,
        "salary_text": opportunity.salary_text,
        "level": opportunity.level,
        "tech_stack": opportunity.tech_stack,
        "apply_url": opportunity.apply_url,
        "posted_at": opportunity.posted_at.isoformat()
        if opportunity.posted_at
        else None,
        "created_at": opportunity.created_at.isoformat(),
        "updated_at": opportunity.updated_at.isoformat(),
        "match": None,
    }

    if match:
        result["match"] = {
            "id": match.id,
            "bucket": match.match_bucket,
            "score": match.match_score,
            "reasons": match.reasons,
            "missing_skills": match.missing_skills,
            "resume_tweaks": match.resume_tweaks,
            "created_at": match.created_at.isoformat(),
            "updated_at": match.updated_at.isoformat(),
        }

    return result
