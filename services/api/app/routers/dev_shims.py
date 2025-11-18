"""Dev-only shim endpoints to keep the web UI happy.

These routes exist only when APPLYLENS_DEV=1 to avoid 404 noise in
the web console while developing against a lightweight dev API.
They intentionally provide minimal, non-sensitive mock data.
"""

import os
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException


DEV_MODE = os.getenv("APPLYLENS_DEV", "0") == "1"

router = APIRouter(prefix="/api", tags=["dev-shims"])


def _ensure_dev_mode() -> None:
    """Guard to ensure these routes are only active in dev.

    In practice, main.py should only include this router when
    APPLYLENS_DEV=1, but this extra check keeps behavior explicit.
    """

    if not DEV_MODE:
        raise HTTPException(status_code=404, detail="Not Found")


@router.get("/auth/csrf")
def get_csrf(_: None = Depends(_ensure_dev_mode)) -> Dict[str, str]:
    """Return a fake CSRF token for dev.

    The real auth flow isn't used in dev (LoginGuard bypasses auth),
    but the web client still calls this endpoint by default.
    """

    return {"csrfToken": "dev-csrf-token"}


@router.get("/auth/me")
def get_me(_: None = Depends(_ensure_dev_mode)) -> Dict[str, Any]:
    """Return a mock user profile for dev.

    Mirrors the shape expected by the web header so that initials,
    email, and display name render correctly without hitting real auth.
    """

    return {
        "email": "dev.user@example.com",
        "name": "Dev User",
        "picture": None,
        "roles": ["dev"],
    }


@router.get("/actions/tray")
def get_actions_tray(_: None = Depends(_ensure_dev_mode)) -> Dict[str, List[Any]]:
    """Return an empty actions tray for dev.

    The header polls this endpoint to show pending actions. In dev we
    just return an empty list to avoid 404s and noisy error logs.
    """

    return {"items": []}
