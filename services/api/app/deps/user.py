"""User authentication and identification dependencies."""

import os
from typing import Optional

from fastapi import HTTPException, Request, status

DEFAULT_USER_EMAIL = os.getenv("DEFAULT_USER_EMAIL")


def get_current_user_email(request: Request) -> str:
    """
    Resolve the current user's email from:
    1. X-User-Email header (for admin/testing)
    2. Session/cookie (OAuth flow)
    3. Request state (set by OAuth middleware)
    4. DEFAULT_USER_EMAIL env var (fallback for single-user mode)

    Raises 401 if no email can be determined.
    """
    # Try header first (allows admin override or testing)
    email = request.headers.get("X-User-Email")

    # Try session/cookie (OAuth)
    if not email:
        email = request.cookies.get("user_email")

    # Try state or session data if using OAuth
    if not email and hasattr(request.state, "user_email"):
        email = request.state.user_email

    # Fallback to environment default (single-user mode)
    if not email:
        email = DEFAULT_USER_EMAIL

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User email not available. Please log in or set DEFAULT_USER_EMAIL.",
        )

    return email


def get_optional_user_email(request: Request) -> Optional[str]:
    """
    Optional version that returns None instead of raising 401.
    Use for endpoints that can work with or without a user context.
    """
    try:
        return get_current_user_email(request)
    except HTTPException:
        return None
