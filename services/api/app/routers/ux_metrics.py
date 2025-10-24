"""
UX metrics router for client-side observability.

Provides lightweight endpoints for tracking user engagement
and connection health without impacting core functionality.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from prometheus_client import Counter

router = APIRouter(prefix="/ux", tags=["ux"])


class Heartbeat(BaseModel):
    """Heartbeat payload from client."""

    page: str
    ts: float
    meta: dict | None = None


# Metrics
ux_heartbeat_total = Counter(
    "ux_heartbeat_total",
    "Client heartbeat pings (indicates active sessions)",
    ["page", "user_agent_type"],
)

ux_chat_opened_total = Counter(
    "ux_chat_opened_total",
    "Chat interface opened events",
)


@router.post("/heartbeat")
async def heartbeat(payload: Heartbeat, request: Request):
    """
    Client heartbeat ping.

    Frontend calls this every 30s while user is active on a page.
    Helps distinguish "no activity" from "no users connected".

    CSRF-exempt: This is a non-sensitive UX metric endpoint.

    Returns minimal response to keep overhead low.
    """
    # Simple user agent detection
    user_agent = request.headers.get("user-agent", "")
    if "mobile" in user_agent.lower():
        user_agent_type = "mobile"
    else:
        user_agent_type = "web"

    ux_heartbeat_total.labels(page=payload.page, user_agent_type=user_agent_type).inc()

    # Log or enqueue for analytics if needed
    # For now, just increment the metric

    return {"ok": True}


@router.post("/chat/opened")
async def chat_opened():
    """
    Track when users open the chat interface.

    Useful for funnel analysis and engagement metrics.
    """
    ux_chat_opened_total.inc()

    return {"ok": True}
