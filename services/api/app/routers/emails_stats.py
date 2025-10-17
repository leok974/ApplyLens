"""
Email statistics and counters endpoints.

Provides aggregated statistics about user's emails with Redis caching.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps.user import get_current_user_email
from ..utils.cache import cache_get, cache_set

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("/count")
def emails_count(
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Get total email count for current user.
    
    Returns:
        {"owner_email": str, "count": int}
    """
    row = db.execute(
        text("SELECT COUNT(*) AS c FROM emails WHERE owner_email = :e"),
        {"e": user_email},
    ).first()
    
    return {
        "owner_email": user_email,
        "count": int(row.c if row and row.c else 0),
    }


@router.get("/stats")
def emails_stats(
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Get detailed email statistics for current user.
    
    Cached for 60 seconds. Returns:
    - total: Total email count
    - last_30d: Emails received in last 30 days
    - by_day: Daily counts for last 30 days
    - top_senders: Top 10 senders by email count
    - top_categories: Top 10 categories by email count
    """
    cache_key = f"emails:stats:{user_email}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    # Total counts
    totals = db.execute(
        text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE received_at >= NOW() - INTERVAL '30 days') AS last_30d
            FROM emails
            WHERE owner_email = :e
        """),
        {"e": user_email},
    ).first()

    # Daily breakdown (last 30 days)
    by_day = db.execute(
        text("""
            SELECT 
                DATE_TRUNC('day', received_at)::date AS day,
                COUNT(*) AS c
            FROM emails
            WHERE owner_email = :e 
                AND received_at >= NOW() - INTERVAL '30 days'
            GROUP BY 1
            ORDER BY 1
        """),
        {"e": user_email},
    ).mappings().all()

    # Top senders
    top_senders = db.execute(
        text("""
            SELECT 
                sender,
                COUNT(*) AS c
            FROM emails
            WHERE owner_email = :e
            GROUP BY sender
            ORDER BY c DESC
            LIMIT 10
        """),
        {"e": user_email},
    ).mappings().all()

    # Top categories
    top_categories = db.execute(
        text("""
            SELECT 
                COALESCE(category, '(uncategorized)') AS category,
                COUNT(*) AS c
            FROM emails
            WHERE owner_email = :e
            GROUP BY 1
            ORDER BY c DESC
            LIMIT 10
        """),
        {"e": user_email},
    ).mappings().all()

    out = {
        "owner_email": user_email,
        "total": int(totals.total if totals and totals.total else 0),
        "last_30d": int(totals.last_30d if totals and totals.last_30d else 0),
        "by_day": [
            {"day": str(r["day"]), "count": int(r["c"])}
            for r in by_day
        ],
        "top_senders": [
            {"sender": r["sender"], "count": int(r["c"])}
            for r in top_senders
        ],
        "top_categories": [
            {"category": r["category"], "count": int(r["c"])}
            for r in top_categories
        ],
    }
    
    # Cache for 60 seconds
    cache_set(cache_key, out, ttl=60)
    
    return out
