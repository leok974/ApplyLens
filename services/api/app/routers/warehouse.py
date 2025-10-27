"""Warehouse profile metrics API routes.

Feature-flagged endpoints for BigQuery warehouse metrics.
Requires USE_WAREHOUSE=1 environment variable to enable.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.config import get_agent_settings
from app.metrics import warehouse
from app.metrics.divergence import compute_divergence_24h
from app.utils.cache import cache_json

router = APIRouter(prefix="/warehouse/profile", tags=["warehouse", "analytics"])

settings = get_agent_settings()


def _guard():
    """Guard function to check if warehouse is enabled.

    Raises:
        HTTPException: 412 Precondition Failed if USE_WAREHOUSE is not enabled
    """
    if not settings.USE_WAREHOUSE:
        raise HTTPException(
            status_code=412,
            detail="Warehouse disabled. Set USE_WAREHOUSE=1 to enable BigQuery metrics.",
        )


@router.get("/top-senders", summary="Top email senders (30 days)")
async def top_senders(limit: int = 10) -> list[dict[str, Any]]:
    """Get top email senders in the last 30 days from BigQuery warehouse.

    Requires USE_WAREHOUSE=1 environment variable.
    Results are cached for 60 seconds.

    Args:
        limit: Maximum number of senders to return (default: 10, max: 100)

    Returns:
        List of sender metrics with keys:
        - from_email: Sender email address
        - messages_30d: Number of messages in last 30 days
        - total_size_mb: Total size in MB
        - first_message_at: Timestamp of first message
        - last_message_at: Timestamp of last message
        - active_days: Number of days between first and last message

    Example:
        ```
        GET /api/warehouse/profile/top-senders?limit=5

        [
            {
                "from_email": "jobs-noreply@linkedin.com",
                "messages_30d": 42,
                "total_size_mb": 1.5,
                "first_message_at": "2025-09-18T10:00:00+00:00",
                "last_message_at": "2025-10-18T15:30:00+00:00",
                "active_days": 30
            },
            ...
        ]
        ```
    """
    _guard()

    # Clamp limit to reasonable range
    limit = max(1, min(limit, 100))

    cache_key = f"warehouse:top_senders:{limit}"
    return await cache_json(
        cache_key, ttl=60, fn=lambda: warehouse.mq_top_senders_30d(limit)
    )


@router.get("/activity-daily", summary="Daily email activity")
async def activity_daily(days: int = 14) -> list[dict[str, Any]]:
    """Get daily email activity from BigQuery warehouse.

    Requires USE_WAREHOUSE=1 environment variable.
    Results are cached for 60 seconds.

    Args:
        days: Number of days to retrieve (default: 14, max: 90)

    Returns:
        List of daily metrics with keys:
        - day: Date string (YYYY-MM-DD)
        - messages_count: Number of messages received
        - unique_senders: Number of unique senders
        - avg_size_kb: Average message size in KB
        - total_size_mb: Total size in MB

    Example:
        ```
        GET /api/warehouse/profile/activity-daily?days=7

        [
            {
                "day": "2025-10-18",
                "messages_count": 35,
                "unique_senders": 12,
                "avg_size_kb": 45.2,
                "total_size_mb": 1.5
            },
            ...
        ]
        ```
    """
    _guard()

    # Clamp days to reasonable range
    days = max(1, min(days, 90))

    cache_key = f"warehouse:activity_daily:{days}"
    return await cache_json(
        cache_key, ttl=60, fn=lambda: warehouse.mq_activity_daily(days)
    )


@router.get("/categories-30d", summary="Email category distribution (30 days)")
async def categories_30d(limit: int = 10) -> list[dict[str, Any]]:
    """Get email category distribution in last 30 days from BigQuery warehouse.

    Requires USE_WAREHOUSE=1 environment variable.
    Results are cached for 60 seconds.

    Args:
        limit: Maximum number of categories to return (default: 10)

    Returns:
        List of category metrics with keys:
        - category: Category name (primary, promotions, updates, social, forums)
        - messages_30d: Number of messages in last 30 days
        - pct_of_total: Percentage of total messages
        - total_size_mb: Total size in MB

    Example:
        ```
        GET /api/warehouse/profile/categories-30d?limit=5

        [
            {
                "category": "promotions",
                "messages_30d": 150,
                "pct_of_total": 45.5,
                "total_size_mb": 12.3
            },
            ...
        ]
        ```
    """
    _guard()

    # Clamp limit to reasonable range
    limit = max(1, min(limit, 50))

    cache_key = f"warehouse:categories:{limit}"
    return await cache_json(
        cache_key, ttl=60, fn=lambda: warehouse.mq_categories_30d(limit)
    )


@router.get("/divergence-24h", summary="Data divergence between ES and BQ")
async def divergence_24h() -> dict[str, Any]:
    """Check data consistency between Elasticsearch and BigQuery for last 24 hours.

    Requires USE_WAREHOUSE=1 environment variable.
    Results are cached for 300 seconds (5 minutes).

    Returns:
        Dict with divergence metrics:
        - es_count: Count from Elasticsearch
        - bq_count: Count from BigQuery warehouse
        - divergence: Absolute divergence ratio
        - divergence_pct: Divergence as percentage
        - slo_met: Boolean, True if divergence < 2% (SLO)
        - status: "healthy" | "warning" | "critical"
        - message: Human-readable status message

    Example:
        ```
        GET /api/warehouse/profile/divergence-24h

        {
            "es_count": 100,
            "bq_count": 98,
            "divergence": 0.02,
            "divergence_pct": 2.0,
            "slo_met": True,
            "status": "healthy",
            "message": "Divergence: 2.00% (within SLO)"
        }
        ```

    SLO Thresholds:
        - < 2%: healthy (green)
        - 2-5%: warning (amber)
        - > 5%: critical (red)
    """
    _guard()

    cache_key = "warehouse:divergence_24h"
    return await cache_json(cache_key, ttl=300, fn=compute_divergence_24h)
