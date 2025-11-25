"""Job opportunities listing and management endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth_google import get_current_user
from ..db import get_db
from ..models import JobOpportunity, OpportunityMatch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


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

    class Config:
        from_attributes = True


# ===== Endpoints =====


@router.get("", response_model=list[OpportunityResponse])
async def list_opportunities(
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
    current_user: dict = Depends(get_current_user),
):
    """List job opportunities for the authenticated user.

    - **source**: Optional filter by aggregator source (indeed, linkedin, etc.)
    - **company**: Optional filter by company name (case-insensitive partial match)
    - **match_bucket**: Optional filter by match quality (perfect, strong, possible, skip)
    - **limit**: Maximum number of results (default: 100, max: 500)
    - **offset**: Number of results to skip for pagination (default: 0)

    Returns opportunities sorted by created_at (newest first), with match data if available.
    """
    user_email = current_user["email"]

    # Build query
    query = db.query(JobOpportunity).filter(JobOpportunity.owner_email == user_email)

    # Apply filters
    if source:
        query = query.filter(JobOpportunity.source == source)

    if company:
        query = query.filter(JobOpportunity.company.ilike(f"%{company}%"))

    # Apply match bucket filter via join
    if match_bucket:
        query = query.join(
            OpportunityMatch,
            OpportunityMatch.opportunity_id == JobOpportunity.id,
        ).filter(OpportunityMatch.match_bucket == match_bucket)

    # Order by newest first
    query = query.order_by(JobOpportunity.created_at.desc())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    opportunities = query.all()

    # Load match data for each opportunity
    results = []
    for opp in opportunities:
        # Get match data if exists
        match = (
            db.query(OpportunityMatch)
            .filter(OpportunityMatch.opportunity_id == opp.id)
            .first()
        )

        results.append(
            OpportunityResponse(
                id=opp.id,
                owner_email=opp.owner_email,
                source=opp.source,
                title=opp.title,
                company=opp.company,
                location=opp.location,
                remote_flag=opp.remote_flag,
                salary_text=opp.salary_text,
                level=opp.level,
                tech_stack=opp.tech_stack,
                apply_url=opp.apply_url,
                posted_at=opp.posted_at.isoformat() if opp.posted_at else None,
                created_at=opp.created_at.isoformat(),
                match_bucket=match.match_bucket if match else None,
                match_score=match.match_score if match else None,
            )
        )

    logger.info(
        f"Listed {len(results)} opportunities for user {user_email} (source={source}, company={company}, match_bucket={match_bucket})"
    )

    return results


@router.get("/{opportunity_id}", response_model=dict)
async def get_opportunity_detail(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get detailed information for a specific opportunity including match data.

    Returns opportunity details with full match analysis (reasons, missing_skills, resume_tweaks).
    """
    user_email = current_user["email"]

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
