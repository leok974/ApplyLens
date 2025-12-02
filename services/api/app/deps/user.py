"""User authentication and identification dependencies."""

import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from ..auth.deps import current_user, optional_current_user
from ..models import User

DEFAULT_USER_EMAIL = os.getenv("DEFAULT_USER_EMAIL")


def get_current_user_email(request: Request, user: User = Depends(current_user)) -> str:
    """
    Get the current authenticated user's email.

    Uses session-based authentication via current_user dependency.
    Falls back to DEFAULT_USER_EMAIL env var for single-user mode.

    Raises 401 if no user is authenticated and no default is set.
    """
    # If we have an authenticated user, use their email
    if user:
        return user.email

    # Fallback to environment default (single-user mode)
    email = DEFAULT_USER_EMAIL
    if email:
        return email

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User email not available. Please log in or set DEFAULT_USER_EMAIL.",
    )

    return email


def get_optional_user_email(
    request: Request, user: User = Depends(optional_current_user)
) -> Optional[str]:
    """
    Optional version that returns None instead of raising 401.
    Use for endpoints that can work with or without a user context.
    """
    if user:
        return user.email

    # Fallback to environment default
    return DEFAULT_USER_EMAIL
