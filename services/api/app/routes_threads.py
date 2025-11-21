"""
Thread Detail API Routes

GET /api/threads/{thread_id} - Returns detailed thread information with messages
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .db import get_db
from .models import Email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/threads", tags=["threads"])


class MailMessage(BaseModel):
    id: str
    sentAt: str  # ISO 8601
    from_: str  # Renamed to avoid Python keyword
    to: str
    subject: str
    bodyHtml: Optional[str] = None
    bodyText: Optional[str] = None
    isImportant: Optional[bool] = False

    class Config:
        # Allow 'from' to map to 'from_'
        fields = {"from_": "from"}


class MailThreadDetail(BaseModel):
    threadId: str
    subject: str
    from_: str  # Sender of first message
    to: Optional[str] = None
    lastMessageAt: str  # ISO 8601
    unreadCount: Optional[int] = 0
    riskScore: Optional[float] = None
    labels: List[str] = []
    snippet: str
    gmailUrl: str
    messages: List[MailMessage] = []

    class Config:
        fields = {"from_": "from"}


@router.get("/{thread_id}", response_model=MailThreadDetail)
async def get_thread_detail(
    thread_id: str, db: Session = Depends(get_db)
) -> MailThreadDetail:
    """
    Get detailed thread information including all messages.

    Returns:
        - MailThreadDetail with messages sorted by sentAt desc (most recent first)

    Raises:
        - 404 if thread not found
    """
    # Query all emails in this thread, ordered by received_at desc
    emails = (
        db.query(Email)
        .filter(Email.thread_id == thread_id)
        .order_by(desc(Email.received_at))
        .all()
    )

    if not emails:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

    # First email (most recent) provides the summary info
    first_email = emails[0]

    # Build messages list
    messages = []
    for email in emails:
        messages.append(
            MailMessage(
                id=str(email.id),
                sentAt=email.received_at.isoformat() if email.received_at else "",
                from_=email.sender or "Unknown",
                to=email.recipient or "Unknown",
                subject=email.subject or "No Subject",
                bodyHtml=email.body_html if hasattr(email, "body_html") else None,
                bodyText=email.body_text or email.body_preview or "",
                isImportant=email.risk_score and email.risk_score > 0.7
                if hasattr(email, "risk_score")
                else False,
            )
        )

    # Construct Gmail URL
    gmail_url = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"
    if hasattr(first_email, "gmail_thread_id") and first_email.gmail_thread_id:
        gmail_url = (
            f"https://mail.google.com/mail/u/0/#inbox/{first_email.gmail_thread_id}"
        )

    # Parse labels if available
    labels = []
    if hasattr(first_email, "labels") and first_email.labels:
        if isinstance(first_email.labels, str):
            labels = first_email.labels.split(",")
        elif isinstance(first_email.labels, list):
            labels = first_email.labels

    # Build snippet
    snippet = first_email.body_preview or first_email.subject or ""
    if len(snippet) > 200:
        snippet = snippet[:200] + "..."

    return MailThreadDetail(
        threadId=thread_id,
        subject=first_email.subject or "No Subject",
        from_=first_email.sender or "Unknown",
        to=first_email.recipient,
        lastMessageAt=first_email.received_at.isoformat()
        if first_email.received_at
        else "",
        unreadCount=sum(1 for e in emails if hasattr(e, "is_read") and not e.is_read),
        riskScore=first_email.risk_score
        if hasattr(first_email, "risk_score")
        else None,
        labels=labels,
        snippet=snippet,
        gmailUrl=gmail_url,
        messages=messages,
    )
