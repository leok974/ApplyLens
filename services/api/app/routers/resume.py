"""Resume upload and management endpoints.

Handles resume file uploads (PDF, DOCX, TXT), parsing, and activation.
No resume generation - upload only.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps.user import get_current_user_email
from ..db import get_db
from ..models import ResumeProfile
from ..services.resume_parser import extract_text_from_resume, parse_resume_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resume", tags=["resume"])


# ===== Schemas =====


class ResumeProfileResponse(BaseModel):
    """Resume profile response schema."""

    id: int
    owner_email: str
    source: str  # Always "upload"
    is_active: bool
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}",
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ImportError as e:
        logger.error(f"Missing dependency for file parsing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server is missing required dependencies for this file format",
        )
    except Exception as e:
        logger.error(f"Failed to extract text from resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract text from resume file",
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
        headline=resume.headline,
        summary=resume.summary,
        skills=resume.skills,
        experiences=resume.experiences,
        projects=resume.projects,
        created_at=resume.created_at.isoformat(),
        updated_at=resume.updated_at.isoformat(),
    )


@router.get("/current", response_model=Optional[ResumeProfileResponse])
async def get_current_resume(
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
