"""Version endpoint for build metadata and health checks."""

from fastapi import APIRouter

from app.config import APP_VERSION, APP_BUILD_SHA, APP_BUILD_TIME

router = APIRouter(tags=["ops"])


@router.get("/version")
async def get_version():
    """Return build metadata for the API.

    Returns version, git SHA, and build timestamp for debugging
    and deployment verification.
    """
    return {
        "app": "applylens-api",
        "version": APP_VERSION,
        "sha": APP_BUILD_SHA,
        "built_at": APP_BUILD_TIME,
    }
