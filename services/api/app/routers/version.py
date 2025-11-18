"""Version endpoint for build metadata and health checks."""

from fastapi import APIRouter

from app.config import APP_VERSION, APP_BUILD_SHA, APP_BUILD_TIME, APP_ENV

router = APIRouter(tags=["ops"])


@router.get("/version")
async def get_version():
    """Return build metadata for the API.

    Returns version, git SHA, build timestamp, and environment
    for debugging and deployment verification.
    """
    return {
        "app_name": "applylens-api",
        "version": APP_VERSION,
        "commit_sha": APP_BUILD_SHA,
        "build_time": APP_BUILD_TIME,
        "env": APP_ENV,
        "git_ref": None,
    }
