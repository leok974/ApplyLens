import os
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import desc

from .db import SessionLocal
from .gmail_service import gmail_backfill
from .metrics import BACKFILL_INSERTED, BACKFILL_REQUESTS, GMAIL_CONNECTED
from .models import Email, OAuthToken

# Copilot: POST /gmail/backfill?days=60 enqueues backfill task and returns inserted count.
# Copilot: Rate limiting enforced per user with configurable cooldown (default 300s).
# Copilot: Metrics increments (BACKFILL_REQUESTS, BACKFILL_INSERTED) for observability.
router = APIRouter(prefix="/gmail", tags=["gmail"])

# Simple rate limiter for backfill (configurable cooldown in seconds)
_BACKFILL_COOLDOWN_SECONDS = int(
    os.getenv("BACKFILL_COOLDOWN_SECONDS", "300")
)  # 5 minutes default
_LAST_BACKFILL_TS = {}


class BackfillResp(BaseModel):
    inserted: int
    days: int
    user_email: str


class ConnectionStatus(BaseModel):
    connected: bool
    user_email: Optional[str] = None
    provider: str = "google"
    has_refresh_token: bool = False
    total: Optional[int] = None  # Total emails in DB


class EmailItem(BaseModel):
    id: int
    gmail_id: Optional[str]
    thread_id: Optional[str]
    subject: Optional[str]
    body_preview: Optional[str]  # First 250 chars
    sender: Optional[str]
    recipient: Optional[str]
    received_at: Optional[str]
    labels: Optional[List[str]]
    label_heuristics: Optional[List[str]]
    company: Optional[str] = None
    role: Optional[str] = None
    source: Optional[str] = None
    application_id: Optional[int] = None


class InboxResponse(BaseModel):
    emails: List[EmailItem]
    total: int
    page: int
    limit: int


# For now, use the email that owns the OAuth token (single-user)
# If you manage multi-user, pass user_email in header or session.
DEFAULT_USER_EMAIL_ENV = os.getenv("DEFAULT_USER_EMAIL", "user@example.com")


@router.get("/status", response_model=ConnectionStatus)
def get_connection_status(user_email: str = Query(DEFAULT_USER_EMAIL_ENV)):
    """Check if user has connected their Gmail account"""
    db = SessionLocal()
    try:
        token = (
            db.query(OAuthToken)
            .filter_by(provider="google", user_email=user_email)
            .first()
        )
        if not token:
            # Set gauge: disconnected
            GMAIL_CONNECTED.labels(user_email=user_email).set(0)
            return ConnectionStatus(connected=False)

        # Count total emails for this user
        total = db.query(Email).filter(Email.gmail_id.isnot(None)).count()

        # Set gauge: connected
        GMAIL_CONNECTED.labels(user_email=token.user_email).set(1)

        return ConnectionStatus(
            connected=True,
            user_email=token.user_email,
            provider=token.provider,
            has_refresh_token=bool(token.refresh_token),
            total=total,
        )
    finally:
        db.close()


@router.get("/inbox", response_model=InboxResponse)
def get_inbox(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    label_filter: Optional[str] = Query(None, description="Filter by label_heuristics"),
    user_email: str = Query(DEFAULT_USER_EMAIL_ENV),
):
    """Get paginated list of Gmail emails from database"""
    db = SessionLocal()
    try:
        # Check if user is connected
        token = (
            db.query(OAuthToken)
            .filter_by(provider="google", user_email=user_email)
            .first()
        )
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Gmail not connected. Please authenticate first.",
            )

        # Build query
        query = db.query(Email).filter(Email.gmail_id.isnot(None))

        # Apply label filter if provided
        if label_filter:
            query = query.filter(Email.label_heuristics.contains([label_filter]))

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * limit
        emails = (
            query.order_by(desc(Email.received_at)).offset(offset).limit(limit).all()
        )

        # Convert to response
        email_items = [
            EmailItem(
                id=email.id,
                gmail_id=email.gmail_id,
                thread_id=email.thread_id,
                subject=email.subject,
                body_preview=(
                    email.body_text[:250] if email.body_text else None
                ),  # Server-side truncation
                sender=email.sender,
                recipient=email.recipient,
                labels=email.labels,
                label_heuristics=email.label_heuristics,
                received_at=(
                    email.received_at.isoformat() if email.received_at else None
                ),
                company=email.company,
                role=email.role,
                source=email.source,
                application_id=email.application_id,
            )
            for email in emails
        ]

        return InboxResponse(emails=email_items, total=total, page=page, limit=limit)
    finally:
        db.close()


@router.post("/backfill", response_model=BackfillResp)
def backfill(
    request: Request, days: int = Query(60, ge=1, le=365), user_email: str | None = None
):
    """Backfill Gmail messages from the last N days"""
    global _LAST_BACKFILL_TS
    now = time.time()

    # Get user email
    email = user_email or os.getenv("DEFAULT_USER_EMAIL")
    if not email:
        BACKFILL_REQUESTS.labels(result="bad_request").inc()
        raise HTTPException(400, "user_email required (or set DEFAULT_USER_EMAIL)")

    # Per-user rate limit
    last_ts = _LAST_BACKFILL_TS.get(email, 0)
    if now - last_ts < _BACKFILL_COOLDOWN_SECONDS:
        remaining = int(_BACKFILL_COOLDOWN_SECONDS - (now - last_ts))
        BACKFILL_REQUESTS.labels(result="rate_limited").inc()
        raise HTTPException(
            status_code=429,
            detail=f"Backfill too frequent; try again in {remaining} seconds.",
        )
    _LAST_BACKFILL_TS[email] = now

    db = SessionLocal()
    try:
        count = gmail_backfill(db, user_email=email, days=days)

        # Success metrics
        BACKFILL_REQUESTS.labels(result="ok").inc()
        BACKFILL_INSERTED.inc(count)

        return BackfillResp(inserted=count, days=days, user_email=email)
    except HTTPException:
        raise
    except Exception as e:
        BACKFILL_REQUESTS.labels(result="error").inc()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
