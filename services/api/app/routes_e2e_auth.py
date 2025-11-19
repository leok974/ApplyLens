"""
E2E test authentication endpoint

Only enabled when E2E_PROD environment variable is set.
Provides programmatic login for Playwright E2E tests.
"""

from fastapi import APIRouter, Response, HTTPException, Header
from typing import Optional
import os

from app.db import get_session
from app.models import User
from app.auth.session import new_session, set_cookie
from app.config import agent_settings
from app.core.csrf import issue_csrf_cookie
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/e2e", tags=["e2e-auth"])

# Only enable this router when E2E_PROD is set
E2E_ENABLED = os.getenv("E2E_PROD") == "1"
E2E_SHARED_SECRET = os.getenv("E2E_SHARED_SECRET", "")
E2E_TEST_USER = "leoklemet.pa@gmail.com"  # Your actual test account


@router.post("/login")
async def e2e_login(
    response: Response,
    x_e2e_secret: Optional[str] = Header(None),
):
    """
    Test-only login endpoint for E2E tests.

    Creates an authenticated session for the E2E test user.

    Guards:
    - Only enabled when E2E_PROD=1
    - Requires matching E2E_SHARED_SECRET in X-E2E-Secret header

    Returns session cookie for test user
    """

    # Guard 1: Feature must be explicitly enabled
    if not E2E_ENABLED:
        raise HTTPException(status_code=404, detail="E2E auth endpoint not enabled")

    # Guard 2: Shared secret must match
    if not E2E_SHARED_SECRET or x_e2e_secret != E2E_SHARED_SECRET:
        logger.warning(
            f"E2E login attempt with invalid secret from header: {x_e2e_secret is not None}"
        )
        raise HTTPException(status_code=403, detail="Invalid or missing E2E secret")

    try:
        # Get or verify the E2E test user exists
        db = next(get_session())
        result = db.execute(select(User).where(User.email == E2E_TEST_USER))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"E2E test user {E2E_TEST_USER} not found in database",
            )

        # Create session using existing session utilities
        sid = new_session(user_id=user.id, user_email=user.email)

        # Set session cookie using existing helper
        set_cookie(
            response,
            sid,
            domain=agent_settings.COOKIE_DOMAIN,
            secure=agent_settings.COOKIE_SECURE,
            samesite=agent_settings.COOKIE_SAMESITE,
        )

        # Issue CSRF token
        issue_csrf_cookie(response)

        logger.info(
            f"✓ E2E session created for {user.email} (session_id: {sid[:16]}...)"
        )

        return {
            "ok": True,
            "user": E2E_TEST_USER,
            "session_id": sid[:16] + "...",  # Partial ID for logging
            "expires_in": 3600,
            "message": "E2E session created",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create E2E session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create E2E session: {str(e)}"
        )
