# services/api/app/routers/extension.py
"""
Browser extension endpoints for ApplyLens Companion.
Provides profile data, form generation, and application tracking.

Security: Dev-only mode via APPLYLENS_DEV=1 env var.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from prometheus_client import Counter
from sqlalchemy.orm import Session as DBSession

from ..db import get_db
from ..models import ExtensionApplication, ExtensionOutreach
from ..llm import (
    generate_form_answers_llm,
    CompanionLLMError,
    sanitize_answers,
    validate_answers,
)

logger = logging.getLogger(__name__)

DEV_MODE = os.getenv("APPLYLENS_DEV", "1") == "1"

# Prometheus metrics for extension activity
extension_applications_total = Counter(
    "applylens_extension_applications_total",
    "Total job applications logged via browser extension",
    ["source"],
)

extension_outreach_total = Counter(
    "applylens_extension_outreach_total",
    "Total recruiter outreach logged via browser extension",
    ["source"],
)

extension_form_generations_total = Counter(
    "applylens_extension_form_generations_total",
    "Total form answer generations requested",
)

extension_dm_generations_total = Counter(
    "applylens_extension_dm_generations_total",
    "Total recruiter DM generations requested",
)


def dev_only():
    """Guard for dev-only endpoints."""
    if not DEV_MODE:
        raise HTTPException(status_code=403, detail="Dev-only endpoint")
    return True


router = APIRouter(prefix="/api", tags=["extension"])


# ---------- Phase 0: Profile "brain" ----------
class ProjectLink(BaseModel):
    demo: Optional[HttpUrl] = None
    repo: Optional[HttpUrl] = None


class Project(BaseModel):
    name: str
    one_liner: str
    bullets: List[str]
    links: ProjectLink


class Profile(BaseModel):
    name: str
    headline: str
    locations: List[str]
    target_roles: List[str]
    tech_stack: List[str]
    projects: List[Project]
    preferences: Dict[str, Any]


PROFILE = Profile(
    name="Leo Klemet",
    headline="AI/ML Engineer · Agentic systems · Full-stack",
    locations=["Remote", "Washington, DC"],
    target_roles=[
        "AI Engineer",
        "Machine Learning Engineer",
        "Full-Stack AI Engineer",
    ],
    tech_stack=[
        "Python",
        "FastAPI",
        "React",
        "TypeScript",
        "PostgreSQL",
        "Elasticsearch",
        "Docker",
        "Kubernetes",
        "LLMs",
        "LangChain/LangGraph",
    ],
    projects=[
        Project(
            name="ApplyLens",
            one_liner="Agentic job-inbox that ingests Gmail, tracks applications, and adds security risk scoring.",
            bullets=[
                "FastAPI backend with Gmail OAuth ingest and Elasticsearch search + synonym/recency boosts.",
                "Application tracker with status chips, filters, and CRUD UI in React.",
                "Prometheus/Grafana metrics + alerting for ingest errors and system health.",
            ],
            links=ProjectLink(
                demo="https://applylens.app",
                repo="https://github.com/leok974/ApplyLens",
            ),
        ),
        Project(
            name="SiteAgent",
            one_liner="Self-updating portfolio & SEO agent that ships diff-based approvals.",
            bullets=[
                "Agent tasks for SEO tuning, OG image generation, and link validation.",
                "Dev Overlay with artifacts, SSE events, and per-run diagnostics.",
                "JSON-LD + nightly SEO/analytics loops via GitHub Actions.",
            ],
            links=ProjectLink(
                demo="https://www.leoklemet.com",
                repo="https://github.com/leok974/siteagent",
            ),
        ),
    ],
    preferences={
        "domains": [
            "Agentic platforms",
            "ML infrastructure",
            "Dev tools",
            "Productivity",
        ],
        "work_setup": ["Remote", "Hybrid DC"],
        "note": "Wants roles where agents/LLMs are core to the product.",
    },
)


@router.get("/profile/me", response_model=Profile, dependencies=[Depends(dev_only)])
def get_profile():
    """Get user profile for context in form generation."""
    return PROFILE


# ---------- Phase 1: Minimal logging ----------
class AppLogIn(BaseModel):
    company: str
    role: str
    job_url: Optional[HttpUrl] = None
    source: str = "browser_extension"
    applied_at: Optional[datetime] = None
    notes: Optional[str] = None


@router.post("/extension/applications", dependencies=[Depends(dev_only)])
def log_application(payload: AppLogIn, db: DBSession = Depends(get_db)):
    """Log a job application from the browser extension."""
    rec = ExtensionApplication(
        company=payload.company,
        role=payload.role,
        job_url=str(payload.job_url) if payload.job_url else None,
        source=payload.source,
        applied_at=payload.applied_at or datetime.utcnow(),
        notes=payload.notes,
        user_email="leo@applylens.dev",  # single-user dev
    )
    db.add(rec)
    db.commit()

    # Track metric
    extension_applications_total.labels(source=payload.source).inc()

    return {"ok": True, "id": rec.id}


class OutreachIn(BaseModel):
    company: str
    role: str
    recruiter_name: Optional[str] = None
    recruiter_profile_url: Optional[HttpUrl] = None
    message_preview: Optional[str] = None
    sent_at: Optional[datetime] = None
    source: str = "browser_extension"


@router.post("/extension/outreach", dependencies=[Depends(dev_only)])
def log_outreach(payload: OutreachIn, db: DBSession = Depends(get_db)):
    """Log recruiter outreach from the browser extension."""
    rec = ExtensionOutreach(
        company=payload.company,
        role=payload.role,
        recruiter_name=payload.recruiter_name,
        recruiter_profile_url=(
            str(payload.recruiter_profile_url)
            if payload.recruiter_profile_url
            else None
        ),
        message_preview=payload.message_preview,
        sent_at=payload.sent_at or datetime.utcnow(),
        source=payload.source,
        user_email="leo@applylens.dev",
    )
    db.add(rec)
    db.commit()

    # Track metric
    extension_outreach_total.labels(source=payload.source).inc()

    return {"ok": True, "id": rec.id}


# ---------- Phase 3/4: Generators (stubbed now) ----------
class FormField(BaseModel):
    field_id: str
    label: Optional[str] = None
    type: Optional[str] = None


class FormProfileContext(BaseModel):
    """LLM-safe profile context for form generation.

    Intentionally excludes PII like email/phone/LinkedIn URLs.
    These should be filled from profile directly, not generated.
    """

    name: Optional[str] = None
    headline: Optional[str] = None
    experience_years: Optional[int] = None

    locations: List[str] = []
    target_roles: List[str] = []
    tech_stack: List[str] = []
    domains: List[str] = []

    work_setup: Optional[str] = None
    note: Optional[str] = None


class StylePrefs(BaseModel):
    """User style preferences for answer generation."""

    tone: Optional[str] = "confident"  # concise | confident | friendly | detailed
    length: Optional[str] = "medium"  # short | medium | long


class GenerateFormAnswersIn(BaseModel):
    job: Dict[str, Any]
    fields: List[FormField]
    profile_context: Optional[FormProfileContext] = None
    style_prefs: Optional[StylePrefs] = None


@router.post("/extension/generate-form-answers", dependencies=[Depends(dev_only)])
def generate_form_answers(payload: GenerateFormAnswersIn):
    """
    Generate form answers based on job context and profile using LLM.
    Phase 4.0: Now uses profile_context for personalized, grounded answers.
    """
    try:
        # Convert profile_context to dict (if provided)
        profile_ctx_dict = None
        if payload.profile_context:
            profile_ctx_dict = {
                "name": payload.profile_context.name,
                "headline": payload.profile_context.headline,
                "experience_years": payload.profile_context.experience_years,
                "target_roles": payload.profile_context.target_roles,
                "tech_stack": payload.profile_context.tech_stack,
                "domains": payload.profile_context.domains,
                "work_setup": payload.profile_context.work_setup,
                "locations": payload.profile_context.locations,
                "note": payload.profile_context.note,
            }
            logger.info(
                f"Using profile context: {payload.profile_context.name}, "
                f"{payload.profile_context.experience_years} years, "
                f"{len(payload.profile_context.tech_stack)} skills"
            )

        # Convert style_prefs to dict (if provided)
        style_dict = None
        if payload.style_prefs:
            style_dict = {
                "tone": payload.style_prefs.tone,
                "length": payload.style_prefs.length,
            }
            logger.info(
                f"Using style preferences: tone={payload.style_prefs.tone}, "
                f"length={payload.style_prefs.length}"
            )

        # Convert profile to dict format (legacy support)
        profile_dict = {
            "first_name": PROFILE.name.split()[0] if PROFILE.name else "",
            "last_name": PROFILE.name.split()[-1] if PROFILE.name else "",
            "headline": PROFILE.headline,
            "summary": PROFILE.headline,
            "tech_stack": PROFILE.tech_stack,
            "projects": [
                {
                    "name": p.name,
                    "description": p.one_liner,
                    "bullets": p.bullets,
                }
                for p in PROFILE.projects
            ],
        }

        # Convert fields to format expected by LLM client
        fields_list = [
            {
                "selector": f"field_{f.field_id}",
                "semantic_key": f.field_id,
                "label": f.label or f.field_id,
                "type": "text",
            }
            for f in payload.fields
        ]

        # Generate answers using LLM with profile context
        raw_answers = generate_form_answers_llm(
            fields=fields_list,
            profile=profile_dict,
            job_context=payload.job,
            style=style_dict or {"tone": "confident", "length": "medium"},
            profile_context=profile_ctx_dict,  # NEW: Pass profile context
        )

        # Apply safety guardrails
        safe_answers = sanitize_answers(raw_answers)

        # Validate required fields (currently all fields are optional)
        required_fields = [
            f.field_id for f in payload.fields if hasattr(f, "required") and f.required
        ]
        is_valid, missing = validate_answers(safe_answers, required_fields)

        if not is_valid:
            logger.warning(f"Missing required fields: {missing}")

        # Convert back to response format
        answers = []
        for f in payload.fields:
            answer_text = safe_answers.get(f.field_id, "")
            if answer_text:
                answers.append({"field_id": f.field_id, "answer": answer_text})
            else:
                # Fallback to template if no answer generated
                template_text = (
                    f"Answer for '{f.label or f.field_id}' based on {payload.job.get('title', 'the role')} "
                    f"and my projects (e.g., ApplyLens, SiteAgent)."
                )
                answers.append({"field_id": f.field_id, "answer": template_text})

        # Track metric
        extension_form_generations_total.inc()

        logger.info(f"Generated {len(answers)} answers with guardrails applied")

        return {"job": payload.job, "answers": answers}

    except CompanionLLMError as exc:
        logger.error(f"LLM generation failed: {exc}")
        # Fallback to template answers
        answers = []
        for f in payload.fields:
            text = (
                f"Answer for '{f.label or f.field_id}' based on {payload.job.get('title', 'the role')} "
                f"and my projects (e.g., ApplyLens, SiteAgent)."
            )
            answers.append({"field_id": f.field_id, "answer": text})

        extension_form_generations_total.inc()
        return {"job": payload.job, "answers": answers}

    except Exception as exc:
        logger.error(f"Unexpected error in generate_form_answers: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Answer generation failed")


class RecruiterProfile(BaseModel):
    name: str
    headline: Optional[str] = None
    company: Optional[str] = None
    profile_url: Optional[HttpUrl] = None


class GenerateDMIn(BaseModel):
    profile: RecruiterProfile
    job: Optional[Dict[str, Any]] = None


@router.post("/extension/generate-recruiter-dm", dependencies=[Depends(dev_only)])
def generate_recruiter_dm(payload: GenerateDMIn):
    """
    Generate a recruiter DM based on their profile and the job.
    TODO: Replace with LLM call later.
    """
    name = payload.profile.name.split()[0]
    role = (payload.job or {}).get("title", "the role")
    msg = (
        f"Hi {name}, I just applied to {role}. I build agentic systems (ApplyLens, SiteAgent) "
        f"with FastAPI/React/Elasticsearch—happy to share a quick demo if helpful!"
    )

    # Track metric
    extension_dm_generations_total.inc()

    return {"message": msg}


# ---------- List endpoints for dev UI ----------
class ApplicationOut(BaseModel):
    id: int
    company: Optional[str] = None
    role: Optional[str] = None
    job_url: Optional[str] = None
    source: Optional[str] = None
    applied_at: Optional[str] = None
    created_at: str


class OutreachOut(BaseModel):
    id: int
    company: Optional[str] = None
    role: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_profile_url: Optional[str] = None
    message_preview: Optional[str] = None
    sent_at: Optional[str] = None
    source: Optional[str] = None
    created_at: str


@router.get(
    "/extension/applications",
    response_model=List[ApplicationOut],
    dependencies=[Depends(dev_only)],
)
async def list_extension_applications(
    limit: int = 10,
    db: DBSession = Depends(get_db),
):
    """List recent applications logged via the browser extension."""
    q = (
        db.query(ExtensionApplication)
        .order_by(ExtensionApplication.created_at.desc())
        .limit(max(1, min(limit, 100)))
    )
    return [
        ApplicationOut(
            id=r.id,
            company=r.company,
            role=r.role,
            job_url=r.job_url,
            source=r.source,
            applied_at=r.applied_at.isoformat() if r.applied_at else None,
            created_at=r.created_at.isoformat(),
        )
        for r in q.all()
    ]


@router.get(
    "/extension/outreach",
    response_model=List[OutreachOut],
    dependencies=[Depends(dev_only)],
)
async def list_extension_outreach(
    limit: int = 10,
    db: DBSession = Depends(get_db),
):
    """List recent outreach logged via the browser extension."""
    q = (
        db.query(ExtensionOutreach)
        .order_by(ExtensionOutreach.created_at.desc())
        .limit(max(1, min(limit, 100)))
    )
    return [
        OutreachOut(
            id=r.id,
            company=r.company,
            role=r.role,
            recruiter_name=r.recruiter_name,
            recruiter_profile_url=r.recruiter_profile_url,
            message_preview=r.message_preview,
            sent_at=r.sent_at.isoformat() if r.sent_at else None,
            source=r.source,
            created_at=r.created_at.isoformat(),
        )
        for r in q.all()
    ]
