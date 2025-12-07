"""Resume upload and management endpoints.

Handles resume file uploads (PDF, DOCX, TXT), parsing, and activation.
No resume generation - upload only.

API DESIGN RULE (Dec 2024):
    All FastAPI routes using SessionLocal (sync SQLAlchemy) MUST be `def`, not `async def`.
    Do NOT convert these handlers to async def unless we fully migrate to async SQLAlchemy.

    Why: FastAPI cannot properly serialize responses from async handlers that contain
    only synchronous operations (no await). This causes silent 500 errors in production.
    See test_routes_resume_opportunities.py for regression tests.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps.user import get_current_user_email
from ..db import get_db
from ..models import ResumeProfile
from ..services.resume_parser import (
    extract_text_from_resume,
    parse_resume_text,
    extract_profile_from_resume_llm,
)
from ..services.resume_profile_parser import parse_contact_from_resume
from ..services.profile_updater import merge_resume_contact_into_profile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resume", tags=["resume"])


# ===== Schemas =====


class ResumeProfileResponse(BaseModel):
    """Resume profile response schema."""

    id: int
    owner_email: str
    source: str  # Always "upload"
    is_active: bool

    # Contact information
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    linkedin: Optional[str]
    experience_years: Optional[int]

    # Parsed content
    headline: Optional[str]
    summary: Optional[str]
    skills: Optional[list[str]]
    experiences: Optional[list[dict]]
    projects: Optional[list[dict]]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ===== Endpoints =====


@router.post(
    "/upload", response_model=ResumeProfileResponse, status_code=status.HTTP_201_CREATED
)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    """Upload and parse a resume file (PDF, DOCX, or TXT).

    - **file**: Resume file to upload (PDF, DOCX, or TXT)

    Returns the parsed resume profile.
    """

    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    allowed_extensions = {".pdf", ".docx", ".txt"}
    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file_ext}'. For now we only support PDF and DOCX.",
        )

    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read uploaded file",
        )

    # Extract text from file
    try:
        raw_text = extract_text_from_resume(file.filename, content)
        if not raw_text or not raw_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file appears to be empty or unreadable.",
            )
    except ValueError as e:
        # User error - bad file content
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ImportError as e:
        # Server configuration error - missing dependencies
        logger.error(f"Missing dependency for file parsing: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF/DOCX parsing is temporarily unavailable. Server is missing required dependencies (PyPDF2 or python-docx). Please try uploading a .txt file or contact support.",
        )
    except Exception as e:
        # Generic server error
        logger.error(f"Failed to extract text from resume: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process resume on the server. Please try another file or contact support.",
        )

    # Parse resume text (heuristic for now, LLM integration later)
    try:
        parsed_data = await parse_resume_text(raw_text, llm_callable=None)
    except Exception as e:
        logger.error(f"Failed to parse resume text: {e}")
        # Continue with empty parsed data - we still save raw text
        parsed_data = {
            "headline": None,
            "summary": None,
            "skills": [],
            "experiences": [],
            "projects": [],
        }

    # LLM-powered profile extraction (if enabled)
    llm_enabled = os.getenv("COMPANION_LLM_ENABLED", "0") == "1"
    extracted_profile = None
    if llm_enabled:
        try:
            logger.info("Attempting LLM-powered profile extraction from resume")
            extracted_profile = await extract_profile_from_resume_llm(raw_text)
            logger.info(
                f"LLM extracted: name={extracted_profile.full_name}, "
                f"skills={len(extracted_profile.skills)}, "
                f"roles={len(extracted_profile.top_roles)}"
            )
        except Exception as e:
            logger.warning(f"LLM profile extraction failed, continuing without it: {e}")
            extracted_profile = None

    # Parse contact information from resume
    parsed_contact = parse_contact_from_resume(raw_text)
    logger.info(
        f"Parsed contact from resume: name={parsed_contact.full_name}, "
        f"email={parsed_contact.email}, phone={parsed_contact.phone}, "
        f"linkedin={parsed_contact.linkedin}, years_experience={parsed_contact.years_experience}"
    )

    # Deactivate previous active resume
    db.query(ResumeProfile).filter(
        ResumeProfile.owner_email == user_email,
        ResumeProfile.is_active == True,  # noqa: E712
    ).update({"is_active": False})

    # Create new resume profile (active by default)
    resume = ResumeProfile(
        owner_email=user_email,
        source="upload",
        is_active=True,
        raw_text=raw_text,
        headline=parsed_data.get("headline"),
        summary=parsed_data.get("summary"),
        skills=parsed_data.get("skills"),
        experiences=parsed_data.get("experiences"),
        projects=parsed_data.get("projects"),
    )

    # Merge LLM-extracted profile data (if available)
    if extracted_profile:
        # Override with LLM data if better quality
        if extracted_profile.headline:
            resume.headline = extracted_profile.headline
        if extracted_profile.summary:
            resume.summary = extracted_profile.summary

        # Merge skills (LLM extraction is usually more comprehensive)
        if extracted_profile.skills:
            existing_skills = set(resume.skills or [])
            llm_skills = set(extracted_profile.skills)
            resume.skills = sorted(existing_skills.union(llm_skills))

        # Store years of experience if available
        if extracted_profile.years_experience is not None:
            resume.experience_years = extracted_profile.years_experience

        logger.info(
            f"Merged LLM data: {len(resume.skills or [])} total skills, "
            f"years_exp={resume.experience_years}"
        )

    # Merge contact info into profile
    merge_resume_contact_into_profile(resume, parsed_contact, overwrite_existing=False)

    db.add(resume)
    db.commit()
    db.refresh(resume)

    logger.info(
        f"Resume uploaded and parsed for user {user_email}, profile ID {resume.id}"
    )

    return ResumeProfileResponse(
        id=resume.id,
        owner_email=resume.owner_email,
        source=resume.source,
        is_active=resume.is_active,
        name=resume.name,
        email=resume.email,
        phone=resume.phone,
        linkedin=resume.linkedin,
        experience_years=resume.experience_years,
        headline=resume.headline,
        summary=resume.summary,
        skills=resume.skills,
        experiences=resume.experiences,
        projects=resume.projects,
        created_at=resume.created_at.isoformat(),
        updated_at=resume.updated_at.isoformat(),
    )


@router.get("/current", response_model=Optional[ResumeProfileResponse])
def get_current_resume(
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    """Get the currently active resume profile for the authenticated user.

    Returns null if no active resume.
    """

    resume = (
        db.query(ResumeProfile)
        .filter(
            ResumeProfile.owner_email == user_email,
            ResumeProfile.is_active == True,  # noqa: E712
        )
        .first()
    )

    if not resume:
        return None

    return ResumeProfileResponse(
        id=resume.id,
        owner_email=resume.owner_email,
        source=resume.source,
        is_active=resume.is_active,
        name=resume.name,
        email=resume.email,
        phone=resume.phone,
        linkedin=resume.linkedin,
        experience_years=resume.experience_years,
        headline=resume.headline,
        summary=resume.summary,
        skills=resume.skills,
        experiences=resume.experiences,
        projects=resume.projects,
        created_at=resume.created_at.isoformat(),
        updated_at=resume.updated_at.isoformat(),
    )


@router.post("/activate/{profile_id}", response_model=ResumeProfileResponse)
async def activate_resume(
    profile_id: int,
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    """Activate a specific resume profile, deactivating others.

    - **profile_id**: Resume profile ID to activate
    """

    # Verify profile belongs to user
    resume = (
        db.query(ResumeProfile)
        .filter(
            ResumeProfile.id == profile_id,
            ResumeProfile.owner_email == user_email,
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume profile not found",
        )

    # Deactivate all other resumes
    db.query(ResumeProfile).filter(
        ResumeProfile.owner_email == user_email,
        ResumeProfile.id != profile_id,
    ).update({"is_active": False})

    # Activate this resume
    resume.is_active = True
    db.commit()
    db.refresh(resume)

    logger.info(f"Activated resume profile {profile_id} for user {user_email}")

    return ResumeProfileResponse(
        id=resume.id,
        owner_email=resume.owner_email,
        source=resume.source,
        is_active=resume.is_active,
        name=resume.name,
        email=resume.email,
        phone=resume.phone,
        linkedin=resume.linkedin,
        experience_years=resume.experience_years,
        headline=resume.headline,
        summary=resume.summary,
        skills=resume.skills,
        experiences=resume.experiences,
        projects=resume.projects,
        created_at=resume.created_at.isoformat(),
        updated_at=resume.updated_at.isoformat(),
    )


@router.get("/all", response_model=list[ResumeProfileResponse])
async def list_all_resumes(
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    """List all resume profiles for the authenticated user."""

    resumes = (
        db.query(ResumeProfile)
        .filter(ResumeProfile.owner_email == user_email)
        .order_by(ResumeProfile.created_at.desc())
        .all()
    )

    return [
        ResumeProfileResponse(
            id=r.id,
            owner_email=r.owner_email,
            source=r.source,
            is_active=r.is_active,
            name=r.name,
            email=r.email,
            phone=r.phone,
            linkedin=r.linkedin,
            experience_years=r.experience_years,
            headline=r.headline,
            summary=r.summary,
            skills=r.skills,
            experiences=r.experiences,
            projects=r.projects,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in resumes
    ]
