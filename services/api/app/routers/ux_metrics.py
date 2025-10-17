"""
UX metrics router for client-side observability.

Provides lightweight endpoints for tracking user engagement
and connection health without impacting core functionality.
"""

from fastapi import APIRouter
from prometheus_client import Counter

router = APIRouter(prefix="/ux", tags=["ux"])

# Metrics
ux_heartbeat_total = Counter(
    "ux_heartbeat_total",
    "Client heartbeat pings (indicates active sessions)",
    ["user_agent_type"]
)

ux_chat_opened_total = Counter(
    "ux_chat_opened_total",
    "Chat interface opened events",
)


@router.post("/heartbeat")
async def heartbeat():
    """
    Client heartbeat ping.
    
    Frontend calls this every 30s while user is active on the chat page.
    Helps distinguish "no activity" from "no users connected".
    
    Returns minimal response to keep overhead low.
    """
    # Simple user agent detection
    # In production, you'd extract from request headers
    user_agent_type = "web"  # Could be "mobile", "desktop", etc.
    
    ux_heartbeat_total.labels(user_agent_type=user_agent_type).inc()
    
    return {"ok": True}


@router.post("/chat/opened")
async def chat_opened():
    """
    Track when users open the chat interface.
    
    Useful for funnel analysis and engagement metrics.
    """
    ux_chat_opened_total.inc()
    
    return {"ok": True}
