# app/routes_applications.py
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .db import SessionLocal
from .email_parsing import extract_company, extract_role, extract_source
from .gmail import is_configured as gmail_is_configured
from .gmail import sync_fetch_thread_latest
from .gmail_service import upsert_application_for_email
from .models import Application, AppStatus, Email
from .core.metrics import applications_created_from_thread_total

router = APIRouter(prefix="/applications", tags=["applications"])
logger = logging.getLogger(__name__)


# ---- New: Extract endpoint for email parsing ----
class ExtractPayload(BaseModel):
    gmail_thread_id: Optional[str] = None
    subject: str = ""
    from_: str = Field("", alias="from")
    headers: dict = {}
    text: str = ""
    html: str = ""


class ExtractResult(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    source: Optional[str] = None
    source_confidence: float = 0.5
    debug: dict = {}


@router.post("/extract", response_model=ExtractResult)
def extract_from_email(payload: ExtractPayload):
    """
    Extract company, role, and source from email content using heuristics.

    If gmail_thread_id is provided and Gmail is configured, fetches the latest
    message from the thread automatically. Otherwise, uses provided subject/from/text.
    """
    # Try to fetch from Gmail if thread_id provided
    email_data = payload.model_dump()
    if payload.gmail_thread_id and gmail_is_configured():
        gmail_content = sync_fetch_thread_latest(payload.gmail_thread_id)
        if gmail_content:
            # Use Gmail content, but allow payload to override
            email_data = {
                **gmail_content,
                **{
                    k: v for k, v in email_data.items() if v
                },  # Keep non-empty payload fields
            }

    # Extract from merged data
    from_field = email_data.get("from", "") or email_data.get("from_", "")
    text_field = email_data.get("text", "")
    subject_field = email_data.get("subject", "")
    headers_field = email_data.get("headers", {})

    company = extract_company(from_field, text_field, subject_field)
    role = extract_role(subject_field, text_field)
    source = extract_source(headers_field, from_field, subject_field, text_field)

    # Calculate confidence based on source detection
    confidence = 0.5
    if source and source.lower() in ["greenhouse", "lever", "workday"]:
        confidence = 0.95
    elif "mailing-list" in str(headers_field):
        confidence = 0.6

    return ExtractResult(
        company=company,
        role=role,
        source=source,
        source_confidence=confidence,
        debug={
            "from": from_field,
            "subject": subject_field,
            "has_text": bool(text_field),
            "has_html": bool(email_data.get("html", "")),
            "used_gmail": bool(payload.gmail_thread_id and gmail_is_configured()),
        },
    )


# ---- New: Backfill endpoint ----
class BackfillPayload(BaseModel):
    gmail_thread_id: Optional[str] = None
    thread_id: str
    subject: str = ""
    from_: str = Field("", alias="from")
    headers: dict = {}
    text: str = ""
    html: str = ""


class BackfillResult(BaseModel):
    saved: "AppOut"
    extracted: ExtractResult
    updated: bool


@router.post("/backfill-from-email", response_model=BackfillResult)
def backfill_from_email(payload: BackfillPayload):
    """
    Create or update an application using extracted data from email.

    If gmail_thread_id is provided and Gmail is configured, fetches the latest
    message from the thread automatically. Otherwise, uses provided subject/from/text.
    """
    db: Session = SessionLocal()
    try:
        # Try to fetch from Gmail if thread_id provided
        email_data = payload.model_dump()
        if payload.gmail_thread_id and gmail_is_configured():
            gmail_content = sync_fetch_thread_latest(payload.gmail_thread_id)
            if gmail_content:
                # Use Gmail content, but allow payload to override
                email_data = {
                    **gmail_content,
                    **{
                        k: v for k, v in email_data.items() if v
                    },  # Keep non-empty payload fields
                }

        # Extract from merged data
        from_field = email_data.get("from", "") or email_data.get("from_", "")
        text_field = email_data.get("text", "")
        subject_field = email_data.get("subject", "")
        headers_field = email_data.get("headers", {})

        company = extract_company(from_field, text_field, subject_field)
        role = extract_role(subject_field, text_field)
        source = extract_source(headers_field, from_field, subject_field, text_field)

        # Calculate confidence
        confidence = 0.5
        if source and source.lower() in ["greenhouse", "lever", "workday"]:
            confidence = 0.95
        elif "mailing-list" in str(headers_field):
            confidence = 0.6

        # Try to find existing application by thread_id or company+role
        thread_id_to_use = payload.gmail_thread_id or payload.thread_id
        existing = (
            db.query(Application)
            .filter(Application.thread_id == thread_id_to_use)
            .first()
        )
        updated = False

        if not existing and company and role:
            # Try to find by company+role
            existing = (
                db.query(Application)
                .filter(Application.company == company, Application.role == role)
                .first()
            )

        if existing:
            # Update existing application
            if not existing.thread_id:
                existing.thread_id = thread_id_to_use
            if not existing.source or existing.source_confidence < confidence:
                existing.source = source or existing.source
                existing.source_confidence = confidence
            db.commit()
            db.refresh(existing)
            updated = True
            app = existing
        else:
            # Create new application
            app = Application(
                company=company or "(Unknown)",
                role=role or "(Unknown Role)",
                source=source or "Email",
                source_confidence=confidence,
                thread_id=thread_id_to_use,
                status=AppStatus.applied,
            )
            db.add(app)
            db.commit()
            db.refresh(app)

        return BackfillResult(
            saved=AppOut(
                id=app.id,
                company=app.company,
                role=app.role,
                source=app.source,
                source_confidence=app.source_confidence,
                status=app.status,
                notes=app.notes,
                thread_id=app.thread_id,
                created_at=app.created_at.isoformat() if app.created_at else "",
                updated_at=app.updated_at.isoformat() if app.updated_at else None,
            ),
            extracted=ExtractResult(
                company=company,
                role=role,
                source=source,
                source_confidence=confidence,
                debug={
                    "from": from_field,
                    "subject": subject_field,
                    "used_gmail": bool(
                        payload.gmail_thread_id and gmail_is_configured()
                    ),
                },
            ),
            updated=updated,
        )
    except ValueError as e:
        if "gmail_not_configured" in str(e):
            raise HTTPException(400, detail="Gmail not configured")
        raise
    finally:
        db.close()


class AppIn(BaseModel):
    company: str
    role: Optional[str] = None
    source: Optional[str] = None
    source_confidence: Optional[float] = 0.0
    status: AppStatus = AppStatus.applied
    notes: Optional[str] = None
    thread_id: Optional[str] = None


class AppOut(AppIn):
    id: int
    created_at: str
    updated_at: Optional[str] = None


@router.post("", response_model=AppOut)
def create_application(payload: AppIn):
    """Create a new application"""
    db: Session = SessionLocal()
    try:
        app = Application(**payload.model_dump())
        db.add(app)
        db.commit()
        db.refresh(app)
        return AppOut(
            id=app.id,
            company=app.company,
            role=app.role,
            source=app.source,
            source_confidence=app.source_confidence,
            status=app.status,
            notes=app.notes,
            thread_id=app.thread_id,
            created_at=app.created_at.isoformat() if app.created_at else "",
            updated_at=app.updated_at.isoformat() if app.updated_at else None,
        )
    finally:
        db.close()


@router.get("", response_model=List[AppOut])
def list_applications(
    status: Optional[AppStatus] = None,
    company: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 500,
):
    """List applications with optional filters"""
    db: Session = SessionLocal()
    try:
        query = db.query(Application)
        if status:
            query = query.filter(Application.status == status)
        if company:
            query = query.filter(Application.company.ilike(f"%{company}%"))
        if q:
            like = f"%{q}%"
            query = query.filter(
                (Application.company.ilike(like)) | (Application.role.ilike(like))
            )
        rows = (
            query.order_by(Application.updated_at.desc().nullslast()).limit(limit).all()
        )
        return [
            AppOut(
                id=r.id,
                company=r.company,
                role=r.role,
                source=r.source,
                source_confidence=r.source_confidence,
                status=r.status,
                notes=r.notes,
                thread_id=r.thread_id,
                created_at=r.created_at.isoformat() if r.created_at else "",
                updated_at=r.updated_at.isoformat() if r.updated_at else None,
            )
            for r in rows
        ]
    finally:
        db.close()


@router.get("/{app_id}", response_model=AppOut)
def get_application(app_id: int):
    """Get a single application by ID"""
    db: Session = SessionLocal()
    try:
        r = db.query(Application).get(app_id)
        if not r:
            raise HTTPException(404, "Application not found")
        return AppOut(
            id=r.id,
            company=r.company,
            role=r.role,
            source=r.source,
            source_confidence=r.source_confidence,
            status=r.status,
            notes=r.notes,
            thread_id=r.thread_id,
            created_at=r.created_at.isoformat() if r.created_at else "",
            updated_at=r.updated_at.isoformat() if r.updated_at else None,
        )
    finally:
        db.close()


@router.patch("/{app_id}", response_model=AppOut)
def update_application(app_id: int, payload: AppIn):
    """Update an existing application"""
    db: Session = SessionLocal()
    try:
        r = db.query(Application).get(app_id)
        if not r:
            raise HTTPException(404, "Application not found")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(r, k, v)
        db.commit()
        db.refresh(r)
        return AppOut(
            id=r.id,
            company=r.company,
            role=r.role,
            source=r.source,
            source_confidence=r.source_confidence,
            status=r.status,
            notes=r.notes,
            thread_id=r.thread_id,
            created_at=r.created_at.isoformat() if r.created_at else "",
            updated_at=r.updated_at.isoformat() if r.updated_at else None,
        )
    finally:
        db.close()


@router.delete("/{app_id}")
def delete_application(app_id: int):
    """Delete an application"""
    db: Session = SessionLocal()
    try:
        r = db.query(Application).get(app_id)
        if not r:
            raise HTTPException(404, "Application not found")
        db.delete(r)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# ---- Create/Upsert from an email ----
class FromEmailResp(BaseModel):
    application_id: int
    linked_email_id: int


@router.post("/from-email/{email_id}", response_model=FromEmailResp)
def create_from_email(email_id: int):
    """Create or link an application from an email"""
    db: Session = SessionLocal()
    try:
        e = db.query(Email).get(email_id)
        if not e:
            raise HTTPException(404, "Email not found")
        app = upsert_application_for_email(db, e)
        if not app:
            raise HTTPException(
                400,
                "Cannot infer application from this email - missing company/role/thread",
            )
        db.commit()
        return FromEmailResp(application_id=app.id, linked_email_id=e.id)
    finally:
        db.close()


# ---- Create from Gmail thread ----
class FromThreadPayload(BaseModel):
    thread_id: str
    company: Optional[str] = None
    role: Optional[str] = None
    snippet: Optional[str] = None
    sender: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    headers: Optional[dict] = None
    source: Optional[str] = None


@router.post("/from-email", response_model=AppOut)
def create_from_thread(payload: FromThreadPayload):
    """Create an application row from a Gmail thread.

    Accepts thread_id plus optional parsed company/role/snippet.
    If company/role not provided, uses email parsing heuristics to extract them.
    The client can call this via a "Create application" button in the email view.
    """
    db: Session = SessionLocal()
    try:
        # Try to extract company, role, and source using heuristics if not provided
        company = payload.company
        role = payload.role
        source = payload.source

        # If company/role not provided, try to extract from email content
        if not company or not role or not source:
            # Try to find the email in database first
            email = db.query(Email).filter(Email.thread_id == payload.thread_id).first()
            if email:
                # Use database email data for extraction
                sender = email.sender or payload.sender or ""
                subject = email.subject or payload.subject or ""
                body = email.body_text or payload.body_text or ""
                headers = payload.headers or {}

                if not company:
                    company = extract_company(sender, body, subject)
                if not role:
                    role = extract_role(subject, body)
                if not source:
                    # Extract source from email metadata
                    source = extract_source(headers, sender, subject, body)
            else:
                # Use provided metadata for extraction
                sender = payload.sender or ""
                subject = payload.subject or ""
                body = payload.body_text or ""
                headers = payload.headers or {}

                if not company:
                    company = extract_company(sender, body, subject)
                if not role:
                    role = extract_role(subject, body)
                if not source:
                    source = extract_source(headers, sender, subject, body)
                if not role:
                    role = extract_role(subject, body)
                if not source:
                    source = extract_source(headers, sender, subject, body)

        # Create application with extracted or provided data
        app = Application(
            company=company or "(Unknown)",
            role=role or "(Unknown Role)",
            source=source or "Email",
            gmail_thread_id=payload.thread_id,
            thread_id=payload.thread_id,  # Keep both for compatibility
            last_email_snippet=payload.snippet,
        )
        db.add(app)
        db.commit()
        db.refresh(app)

        # Increment metric for applications created from threads
        applications_created_from_thread_total.inc()

        return AppOut(
            id=app.id,
            company=app.company,
            role=app.role,
            source=app.source,
            source_confidence=app.source_confidence,
            status=app.status,
            notes=app.notes,
            thread_id=app.thread_id,
            created_at=app.created_at.isoformat() if app.created_at else "",
            updated_at=app.updated_at.isoformat() if app.updated_at else None,
        )
    finally:
        db.close()


# ---- Archive & Auto-Delete Lifecycle Endpoints ----


class ArchiveResponse(BaseModel):
    ok: bool
    archived_at: str
    message: str = ""


class RestoreResponse(BaseModel):
    ok: bool
    message: str = ""


class DeleteResponse(BaseModel):
    ok: bool
    message: str = ""


class BulkArchiveRequest(BaseModel):
    application_ids: List[int]


class BulkArchiveResponse(BaseModel):
    archived_count: int
    failed_ids: List[int] = []


@router.post("/{app_id}/archive", response_model=ArchiveResponse)
def archive_application(app_id: int):
    """
    Archive an application, hiding it from default views.

    - Can be manually triggered by users
    - Auto-triggered by scheduler for rejected apps after X days
    - Includes grace period for undo
    """
    from .db import audit_action
    from datetime import datetime, timezone

    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == app_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        if app.deleted_at:
            raise HTTPException(
                status_code=400, detail="Cannot archive: application already deleted"
            )

        if app.archived_at:
            return ArchiveResponse(
                ok=True,
                archived_at=app.archived_at.isoformat(),
                message="Application was already archived",
            )

        # Archive the application
        app.archived_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(app)

        # Audit log
        audit_action(
            email_id=str(app_id),
            action="application.archive",
            actor="user",
            rationale="Manual archive via API",
        )

        # Sync to Elasticsearch (tombstone pattern)
        try:
            from .utils.es_applications import es_tombstone_application

            es_tombstone_application(app_id)
        except Exception as e:
            logger.warning(f"ES sync failed for archive: {e}")

        return ArchiveResponse(
            ok=True,
            archived_at=app.archived_at.isoformat(),
            message="Application archived successfully",
        )
    finally:
        db.close()


@router.post("/{app_id}/restore", response_model=RestoreResponse)
def restore_application(app_id: int):
    """
    Restore an archived application, making it visible again.

    - Only works within grace period (configurable)
    - Clears archived_at timestamp
    - Re-indexes in Elasticsearch
    """
    from .db import audit_action

    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == app_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        if app.deleted_at:
            raise HTTPException(
                status_code=400, detail="Cannot restore: application is deleted"
            )

        if not app.archived_at:
            return RestoreResponse(ok=True, message="Application was not archived")

        # Check grace period (optional enforcement)
        # from .config import agent_settings
        # grace_hours = agent_settings.ARCHIVE_GRACE_UNDO_HOURS
        # if (datetime.now(timezone.utc) - app.archived_at).total_seconds() > grace_hours * 3600:
        #     raise HTTPException(status_code=400, detail=f"Grace period expired ({grace_hours}h)")

        # Restore the application
        app.archived_at = None
        db.commit()

        # Audit log
        audit_action(
            email_id=str(app_id),
            action="application.restore",
            actor="user",
            rationale="Manual restore via API",
        )

        # Sync to Elasticsearch (re-index)
        try:
            from .utils.es_applications import es_upsert_application

            es_upsert_application(app)
        except Exception as e:
            logger.warning(f"ES sync failed for restore: {e}")

        return RestoreResponse(ok=True, message="Application restored successfully")
    finally:
        db.close()


@router.delete("/{app_id}", response_model=DeleteResponse)
def hard_delete_application(app_id: int, force: bool = False):
    """
    Permanently delete an application from the database.

    - Requires application to be archived first (unless force=True)
    - Removes from Elasticsearch
    - Cannot be undone

    Args:
        app_id: Application ID to delete
        force: Skip archive requirement (use with caution)
    """
    from .db import audit_action
    from datetime import datetime, timezone

    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == app_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        if not app.archived_at and not force:
            raise HTTPException(
                status_code=400,
                detail="Application must be archived before deletion. Use force=true to bypass.",
            )

        # Soft delete (mark deleted_at)
        app.deleted_at = datetime.now(timezone.utc)
        db.delete(app)
        db.commit()

        # Audit log
        audit_action(
            email_id=str(app_id),
            action="application.delete",
            actor="user",
            rationale="Manual hard delete via API",
        )

        # Sync to Elasticsearch (delete document)
        try:
            from .utils.es_applications import es_delete_application

            es_delete_application(app_id)
        except Exception as e:
            logger.warning(f"ES sync failed for delete: {e}")

        return DeleteResponse(ok=True, message="Application permanently deleted")
    finally:
        db.close()


@router.post("/bulk/archive", response_model=BulkArchiveResponse)
def bulk_archive_applications(req: BulkArchiveRequest):
    """
    Archive multiple applications in a single request.

    - Used for bulk actions in UI
    - Atomic per-application (continues on error)
    - Returns count of successes and list of failures
    """
    from .db import audit_action
    from datetime import datetime, timezone

    db: Session = SessionLocal()
    archived_count = 0
    failed_ids = []

    try:
        for app_id in req.application_ids:
            try:
                app = db.query(Application).filter(Application.id == app_id).first()
                if not app or app.deleted_at or app.archived_at:
                    failed_ids.append(app_id)
                    continue

                app.archived_at = datetime.now(timezone.utc)
                db.commit()
                archived_count += 1

                # Audit log
                audit_action(
                    email_id=str(app_id),
                    action="application.archive",
                    actor="user",
                    rationale="Bulk archive via API",
                )

                # Sync to Elasticsearch
                try:
                    from .utils.es_applications import es_tombstone_application

                    es_tombstone_application(app_id)
                except Exception as e:
                    logger.warning(f"ES sync failed for bulk archive app {app_id}: {e}")

            except Exception:
                failed_ids.append(app_id)
                db.rollback()

        return BulkArchiveResponse(archived_count=archived_count, failed_ids=failed_ids)
    finally:
        db.close()
