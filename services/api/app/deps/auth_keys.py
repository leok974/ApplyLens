"""API key authentication for machine-to-machine requests.

Provides simple API key validation for automation endpoints like Gmail backfill.
"""

import os
from fastapi import Header, HTTPException

# API key for Gmail backfill automation (set via BACKFILL_API_KEY env var)
BACKFILL_API_KEY = os.getenv("BACKFILL_API_KEY", "")


async def require_backfill_key(x_api_key: str | None = Header(default=None)):
    """Require valid API key for Gmail backfill automation.

    Validates X-API-Key header against BACKFILL_API_KEY environment variable.
    If BACKFILL_API_KEY is not set (dev mode), authentication is disabled.

    Args:
        x_api_key: API key from X-API-Key header

    Raises:
        HTTPException: 401 if API key is invalid or missing (when enabled)

    Returns:
        True if authentication passed
    """
    if not BACKFILL_API_KEY:
        # API key not configured - accept all requests (dev mode)
        return True

    if x_api_key != BACKFILL_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include X-API-Key header with valid key.",
        )

    return True
