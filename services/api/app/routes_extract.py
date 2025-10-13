"""
Applications extraction routes - Extract company/role/source from emails.

Endpoints:
- POST /applications/extract - Extract fields from email (no DB changes)
- POST /applications/backfill-from-email - Extract and create/update application
"""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from .db import SessionLocal
from .models import Application, AppStatus, GmailToken
from .settings import settings
from .email_extractor import extract_from_email as extract_service, ExtractInput
from .gmail_providers import (
    db_backed_provider,
    mock_provider,
    GmailProvider,
)

router = APIRouter(prefix="/applications", tags=["applications"])


def _get_gmail_provider() -> Optional[GmailProvider]:
    """
    Get Gmail provider based on configuration.

    Priority:
    1. Mock provider (if USE_MOCK_GMAIL=True)
    2. DB-backed provider (if CLIENT_ID+SECRET set)
    3. Single-user provider (if all 4 env vars set)
    4. None (no Gmail support)
    """
    if settings.USE_MOCK_GMAIL:
        # Return mock provider with empty seed
        return mock_provider({})

    if settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET:
        # DB-backed provider for multi-user
        async def get_token_by_email(email: str) -> Optional[Dict[str, Any]]:
            db = SessionLocal()
            try:
                token = (
                    db.query(GmailToken).filter(GmailToken.user_email == email).first()
                )
                if not token:
                    return None
                return {
                    "access_token": token.access_token,
                    "refresh_token": token.refresh_token,
                    "expiry_date": token.expiry_date,
                    "scope": token.scope,
                }
            finally:
                db.close()

        return db_backed_provider(get_token_by_email)

    # No Gmail support
    return None


# ---- Request/Response Models ----


class ExtractPayload(BaseModel):
    """Request payload for /extract endpoint."""

    gmail_thread_id: Optional[str] = None
    user_email: Optional[str] = None
    subject: Optional[str] = None
    from_: Optional[str] = Field(None, alias="from")
    headers: Optional[Dict[str, str]] = None
    text: Optional[str] = None
    html: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class ExtractResponse(BaseModel):
    """Response from /extract endpoint."""

    company: Optional[str] = None
    role: Optional[str] = None
    source: Optional[str] = None
    source_confidence: float = 0.5
    debug: Dict[str, Any] = {}


class BackfillPayload(ExtractPayload):
    """Request payload for /backfill-from-email endpoint."""

    defaults: Optional[Dict[str, Any]] = None
    company: Optional[str] = None
    role: Optional[str] = None
    source: Optional[str] = None


class ApplicationResponse(BaseModel):
    """Application model for responses."""

    id: int
    company: str
    role: Optional[str] = None
    source: Optional[str] = None
    source_confidence: float = 0.5
    status: str
    notes: Optional[str] = None
    thread_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class BackfillResponse(BaseModel):
    """Response from /backfill-from-email endpoint."""

    saved: ApplicationResponse
    extracted: ExtractResponse
    updated: bool = False


# ---- Endpoints ----


@router.post("/extract", response_model=ExtractResponse)
async def extract_endpoint(
    body: ExtractPayload,
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
):
    """
    Extract company, role, and source from email content.

    If gmail_thread_id is provided, attempts to fetch email from Gmail.
    Otherwise, uses provided email fields (subject, from, text, etc.).

    Supports multi-user OAuth via X-User-Email header or user_email in body.
    """
    # Get Gmail provider
    gmail_provider = _get_gmail_provider()

    # Start with body fields
    email_data = body.model_dump()

    # Try to fetch from Gmail if thread_id provided
    if body.gmail_thread_id and gmail_provider:
        user_email = body.user_email or x_user_email
        pulled = await gmail_provider.fetch_thread_latest(
            body.gmail_thread_id, user_email
        )

        if pulled:
            # Merge Gmail content with body (body wins for non-empty fields)
            email_data = {**pulled, **email_data}

    # Extract using service
    result = extract_service(
        ExtractInput(
            subject=email_data.get("subject"),
            from_=email_data.get("from") or email_data.get("from_"),
            headers=email_data.get("headers"),
            text=email_data.get("text"),
            html=email_data.get("html"),
            attachments=email_data.get("attachments"),
            pdf_text=email_data.get("_pdfText"),  # From PDF parsing
        )
    )

    # Add debug info
    result.debug["used_gmail"] = bool(body.gmail_thread_id and gmail_provider)
    result.debug["user_email"] = body.user_email or x_user_email

    return ExtractResponse(
        company=result.company,
        role=result.role,
        source=result.source,
        source_confidence=result.source_confidence,
        debug=result.debug,
    )


@router.post("/backfill-from-email", response_model=BackfillResponse)
async def backfill_endpoint(
    body: BackfillPayload,
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
):
    """
    Extract fields from email and create/update application.

    If gmail_thread_id is provided, fetches from Gmail.
    Otherwise, uses provided email fields.

    Logic:
    1. Fetch email content (Gmail or body)
    2. Extract company/role/source
    3. Find existing application (by thread_id or company+role)
    4. Update existing or create new
    """
    # Get Gmail provider
    gmail_provider = _get_gmail_provider()

    # Start with body fields
    email_data = body.model_dump()

    # Try to fetch from Gmail
    if body.gmail_thread_id and gmail_provider:
        user_email = body.user_email or x_user_email
        pulled = await gmail_provider.fetch_thread_latest(
            body.gmail_thread_id, user_email
        )

        if pulled:
            email_data = {**pulled, **email_data}

    # Extract
    result = extract_service(
        ExtractInput(
            subject=email_data.get("subject"),
            from_=email_data.get("from") or email_data.get("from_"),
            headers=email_data.get("headers"),
            text=email_data.get("text"),
            html=email_data.get("html"),
            attachments=email_data.get("attachments"),
            pdf_text=email_data.get("_pdfText"),
        )
    )

    # Use extracted values or explicit overrides
    company = body.company or result.company or ""
    role = body.role or result.role or ""
    source = (
        (body.defaults or {}).get("source") or body.source or result.source or "Email"
    )
    source_conf = result.source_confidence
    thread_id = body.gmail_thread_id

    # Validation
    if not (company.strip() or role.strip()):
        raise HTTPException(
            status_code=422,
            detail="insufficient_fields: provide at least company or role",
        )

    # Database operations
    db = SessionLocal()
    try:
        existing = None
        updated = False

        # Try to find by thread_id
        if thread_id:
            existing = (
                db.query(Application)
                .filter(
                    (Application.gmail_thread_id == thread_id)
                    | (Application.thread_id == thread_id)
                )
                .first()
            )

        # Try to find by company+role
        if not existing and company and role:
            existing = (
                db.query(Application)
                .filter(Application.company == company, Application.role == role)
                .order_by(Application.id.desc())
                .first()
            )

        if existing:
            # Update existing application
            if company:
                existing.company = company
            if role:
                existing.role = role
            if not existing.gmail_thread_id and thread_id:
                existing.gmail_thread_id = thread_id
            if not existing.thread_id and thread_id:
                existing.thread_id = thread_id
            if not existing.source or existing.source_confidence < source_conf:
                existing.source = source
                existing.source_confidence = source_conf

            db.commit()
            db.refresh(existing)
            updated = True
            app = existing
        else:
            # Create new application
            app = Application(
                company=company or "(Unknown)",
                role=role or "(Unknown Role)",
                source=source,
                source_confidence=source_conf,
                gmail_thread_id=thread_id,
                thread_id=thread_id,
                status=AppStatus.applied,
            )
            db.add(app)
            db.commit()
            db.refresh(app)

        return BackfillResponse(
            saved=ApplicationResponse(
                id=app.id,
                company=app.company,
                role=app.role,
                source=app.source,
                source_confidence=app.source_confidence,
                status=app.status.value,
                notes=app.notes,
                thread_id=app.thread_id,
                gmail_thread_id=app.gmail_thread_id,
                created_at=app.created_at.isoformat() if app.created_at else "",
                updated_at=app.updated_at.isoformat() if app.updated_at else None,
            ),
            extracted=ExtractResponse(
                company=result.company,
                role=result.role,
                source=result.source,
                source_confidence=result.source_confidence,
                debug=result.debug,
            ),
            updated=updated,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        db.close()
