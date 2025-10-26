"""
Sender Overrides Router - Manage muted and safe sender preferences

Endpoints for managing user-level sender overrides:
- GET /api/settings/senders - List all overrides
- POST /api/settings/senders/mute - Mute a sender
- POST /api/settings/senders/safe - Mark sender as safe
- DELETE /api/settings/senders/:id - Remove an override

Now using Postgres storage for durability and multi-user support.
"""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps.user import get_current_user_email
from ..orm.sender_overrides import (
    list_overrides_db,
    upsert_override_db,
    delete_override_db,
)

router = APIRouter(prefix="/settings/senders", tags=["sender_overrides"])
logger = logging.getLogger(__name__)


# ===== Models =====


class SenderOverride(BaseModel):
    """Sender override preference."""

    id: str
    sender: str
    muted: bool
    safe: bool
    created_at: datetime
    updated_at: datetime


class SenderOverrideListResponse(BaseModel):
    """List response wrapper."""

    overrides: List[SenderOverride]


class SenderOverrideCreateRequest(BaseModel):
    """Request to create/update a sender override."""

    sender: str  # Can be full email or domain-like string (@example.com)


class SenderOverrideDeleteResponse(BaseModel):
    """Delete response."""

    ok: bool
    deleted_id: str


# ===== Endpoints =====


@router.get("", response_model=SenderOverrideListResponse)
def list_overrides(
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> SenderOverrideListResponse:
    """
    List all sender overrides for current user.

    Returns both muted and safe senders from Postgres.
    """
    rows = list_overrides_db(db, user_email)

    # Don't leak user_id in response
    clean = [
        {
            "id": r["id"],
            "sender": r["sender"],
            "muted": r["muted"],
            "safe": r["safe"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]

    return SenderOverrideListResponse(overrides=clean)


@router.post("/mute", response_model=SenderOverride)
def mute_sender(
    body: SenderOverrideCreateRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> SenderOverride:
    """
    Mute a sender (auto-archive future emails).

    Creates or updates an override with muted=true in Postgres.
    """
    if not body.sender:
        raise HTTPException(status_code=400, detail="Sender is required")

    row = upsert_override_db(db, user_email, body.sender, muted=True, safe=False)

    logger.info(f"Muted sender {body.sender} for {user_email}")

    return SenderOverride(
        id=row["id"],
        sender=row["sender"],
        muted=row["muted"],
        safe=row["safe"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/safe", response_model=SenderOverride)
def safe_sender(
    body: SenderOverrideCreateRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> SenderOverride:
    """
    Mark a sender as safe (trusted, not spammy).

    Creates or updates an override with safe=true in Postgres.
    """
    if not body.sender:
        raise HTTPException(status_code=400, detail="Sender is required")

    row = upsert_override_db(db, user_email, body.sender, muted=False, safe=True)

    logger.info(f"Marked sender {body.sender} as safe for {user_email}")

    return SenderOverride(
        id=row["id"],
        sender=row["sender"],
        muted=row["muted"],
        safe=row["safe"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.delete("/{override_id}", response_model=SenderOverrideDeleteResponse)
def delete_override(
    override_id: str,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> SenderOverrideDeleteResponse:
    """
    Remove a sender override.

    Returns 404 if override not found for this user.
    """
    ok = delete_override_db(db, user_email, override_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Override not found")

    logger.info(f"Deleted sender override {override_id} for {user_email}")

    return SenderOverrideDeleteResponse(ok=True, deleted_id=override_id)


# ===== Helpers for other routers =====


def upsert_sender_override_safe(db: Session, user_id: str, sender: str):
    """
    Helper for mark_safe in inbox_actions to record sender-level override.

    This is how adaptive classification works - mark one email safe,
    and future emails from that sender won't be flagged.
    """
    upsert_override_db(db, user_id, sender, muted=False, safe=True)
    logger.info(f"Recorded safe override for {sender} (user: {user_id})")


def get_overrides_for_user(db: Session, user_id: str) -> list[dict]:
    """
    Helper for metrics endpoint to count overrides.

    Returns raw list of override dicts (not Pydantic, not cleaned).
    Used by inbox_actions.py for metrics/summary endpoint.
    """
    return list_overrides_db(db, user_id)
