"""
Debug LLM endpoint for hackathon monitoring.

Provides real-time visibility into LLM provider status and recent performance.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from collections import deque
from datetime import datetime

router = APIRouter(prefix="/debug", tags=["debug"])


class LLMCallSample(BaseModel):
    """Sample of a recent LLM call."""

    timestamp: str
    task_type: str  # "classify" or "extract"
    model_used: str  # "gemini" or "heuristic"
    latency_ms: int
    success: bool
    error_msg: Optional[str] = None


class LLMDebugInfo(BaseModel):
    """Debug information about LLM system."""

    provider_active: str  # "gemini" | "heuristic_only" | "disabled"
    gemini_enabled: bool
    gemini_model: str
    gemini_timeout_seconds: float
    google_cloud_project: Optional[str]
    recent_calls: List[LLMCallSample]
    stats_last_100: Dict[str, Any]


# In-memory storage for recent calls (last 100)
_recent_calls: deque = deque(maxlen=100)


def log_llm_call(
    task_type: str,
    model_used: str,
    latency_ms: int,
    success: bool = True,
    error_msg: Optional[str] = None,
):
    """Log an LLM call for debug tracking."""
    _recent_calls.append(
        LLMCallSample(
            timestamp=datetime.utcnow().isoformat() + "Z",
            task_type=task_type,
            model_used=model_used,
            latency_ms=latency_ms,
            success=success,
            error_msg=error_msg,
        )
    )


@router.get("/llm", response_model=LLMDebugInfo)
async def get_llm_debug_info():
    """
    Get debug information about LLM provider status and recent performance.

    Shows:
    - Which provider is active (Gemini vs heuristic fallback)
    - Recent call samples (last N calls)
    - Aggregated stats from recent calls
    """
    # Check environment configuration
    use_gemini_classify = bool(os.getenv("USE_GEMINI_FOR_CLASSIFY"))
    use_gemini_extract = bool(os.getenv("USE_GEMINI_FOR_EXTRACT"))
    gemini_enabled = use_gemini_classify or use_gemini_extract

    # Determine active provider
    if gemini_enabled and os.getenv("GOOGLE_CLOUD_PROJECT"):
        provider_active = "gemini"
    elif gemini_enabled:
        provider_active = "gemini_configured_but_no_project"
    else:
        provider_active = "heuristic_only"

    # Calculate stats from recent calls
    recent_list = list(_recent_calls)
    stats = {
        "total_calls": len(recent_list),
        "gemini_calls": sum(1 for c in recent_list if c.model_used == "gemini"),
        "heuristic_calls": sum(1 for c in recent_list if c.model_used == "heuristic"),
        "classify_calls": sum(1 for c in recent_list if c.task_type == "classify"),
        "extract_calls": sum(1 for c in recent_list if c.task_type == "extract"),
        "success_count": sum(1 for c in recent_list if c.success),
        "error_count": sum(1 for c in recent_list if not c.success),
        "avg_latency_ms": int(sum(c.latency_ms for c in recent_list) / len(recent_list))
        if recent_list
        else 0,
        "p95_latency_ms": int(
            sorted(c.latency_ms for c in recent_list)[int(len(recent_list) * 0.95)]
        )
        if len(recent_list) > 10
        else 0,
    }

    return LLMDebugInfo(
        provider_active=provider_active,
        gemini_enabled=gemini_enabled,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        gemini_timeout_seconds=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "5.0")),
        google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        recent_calls=recent_list[-20:],  # Last 20 for API response
        stats_last_100=stats,
    )
