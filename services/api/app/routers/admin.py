"""Admin endpoints for system maintenance."""
from fastapi import APIRouter, Depends, HTTPException
from app.auth.deps import current_user
from app.models import User
from app.scripts.demo_reset import run as demo_reset_run
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/demo/reset")
async def reset_demo(user: User = Depends(current_user)):
    """
    Reset demo user data with fresh seed.
    
    Requires authentication. Only allowed for specific admin users.
    
    Returns:
        Success message
    """
    # TODO: Add proper admin check (e.g., check if user email is in ADMIN_EMAILS env var)
    # For now, allow any authenticated user to reset demo
    # In production, restrict to: user.email in ["leoklemet.pa@gmail.com", ...]
    
    logger.info(f"Demo reset triggered by user: {user.email}")
    
    try:
        demo_reset_run()
        return {
            "ok": True,
            "message": "Demo data reset successfully",
            "triggered_by": user.email
        }
    except Exception as e:
        logger.error(f"Demo reset failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Demo reset failed: {str(e)}"
        )


@router.get("/health")
async def admin_health():
    """
    Health check for admin endpoints.
    
    Returns:
        Status information
    """
    return {
        "ok": True,
        "service": "admin",
        "endpoints": [
            "POST /admin/demo/reset - Reset demo user data"
        ]
    }
