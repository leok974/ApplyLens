"""Session management for cookie-based authentication."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Response, Request
from sqlalchemy.orm import Session as DbSession
from app.models import Session, User

SESSION_COOKIE = "session_id"
SESSION_TTL_HOURS = 24 * 7  # 7 days


def new_session(db: DbSession, user_id: str) -> Session:
    """Create a new session for the user."""
    sid = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    sess = Session(
        id=sid,
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(hours=SESSION_TTL_HOURS),
    )
    db.add(sess)
    db.commit()
    return sess


def set_cookie(
    response: Response, sid: str, domain: str, secure: bool, samesite: str = "lax"
):
    """Set session cookie on response."""
    response.set_cookie(
        key=SESSION_COOKIE,
        value=sid,
        httponly=True,
        secure=bool(int(secure)) if isinstance(secure, str) else secure,
        samesite=samesite,
        domain=domain if domain and domain != "localhost" else None,
        max_age=SESSION_TTL_HOURS * 3600,
        path="/",
    )


def clear_cookie(response: Response, domain: str):
    """Clear session cookie from response."""
    response.delete_cookie(
        SESSION_COOKIE,
        domain=domain if domain and domain != "localhost" else None,
        path="/",
    )


def get_session(db: DbSession, sid: str) -> Optional[Session]:
    """Get session by ID."""
    if not sid:
        return None
    return db.query(Session).filter(Session.id == sid).first()


def verify_session(db: DbSession, request: Request) -> Optional[User]:
    """Verify session cookie and return user if valid."""
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        return None

    sess = get_session(db, sid)
    if not sess or (sess.expires_at and sess.expires_at < datetime.now(timezone.utc)):
        return None

    return db.query(User).filter(User.id == sess.user_id).first()
