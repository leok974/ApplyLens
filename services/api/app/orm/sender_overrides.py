"""ORM helpers for user_sender_overrides table."""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import UserSenderOverride


def list_overrides_db(db: Session, user_id: str) -> list[dict]:
    """
    List all sender overrides for a user.
    
    Args:
        db: SQLAlchemy session
        user_id: User email or ID
        
    Returns:
        List of override dictionaries with id, sender, muted, safe fields
    """
    stmt = select(UserSenderOverride).where(UserSenderOverride.user_id == user_id)
    results = db.execute(stmt).scalars().all()
    
    return [
        {
            "id": row.id,
            "sender": row.sender,
            "muted": row.muted,
            "safe": row.safe,
        }
        for row in results
    ]


def upsert_override_db(
    db: Session,
    user_id: str,
    sender: str,
    *,
    muted: bool = False,
    safe: bool = False,
) -> dict:
    """
    Create or update a sender override with OR semantics.
    
    Once a sender is marked safe OR muted, it stays that way.
    This preserves the adaptive classification behavior.
    
    Args:
        db: SQLAlchemy session
        user_id: User email or ID
        sender: Email address being overridden
        muted: Mark sender as muted
        safe: Mark sender as safe
        
    Returns:
        The upserted override dictionary
    """
    stmt = select(UserSenderOverride).where(
        UserSenderOverride.user_id == user_id,
        UserSenderOverride.sender == sender
    )
    existing = db.execute(stmt).scalar_one_or_none()
    
    if existing:
        # OR semantics: once safe/muted, stays that way
        existing.muted = existing.muted or muted
        existing.safe = existing.safe or safe
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "sender": existing.sender,
            "muted": existing.muted,
            "safe": existing.safe,
        }
    else:
        # Create new override
        new_override = UserSenderOverride(
            id=str(uuid.uuid4()),
            user_id=user_id,
            sender=sender,
            muted=muted,
            safe=safe,
        )
        db.add(new_override)
        db.commit()
        db.refresh(new_override)
        return {
            "id": new_override.id,
            "sender": new_override.sender,
            "muted": new_override.muted,
            "safe": new_override.safe,
        }


def delete_override_db(db: Session, user_id: str, override_id: str) -> bool:
    """
    Delete a sender override by ID.
    
    Args:
        db: SQLAlchemy session
        user_id: User email or ID (for ownership check)
        override_id: Override UUID to delete
        
    Returns:
        True if deleted, False if not found or not owned by user
    """
    stmt = select(UserSenderOverride).where(
        UserSenderOverride.id == override_id,
        UserSenderOverride.user_id == user_id
    )
    existing = db.execute(stmt).scalar_one_or_none()
    
    if not existing:
        return False
    
    db.delete(existing)
    db.commit()
    return True
