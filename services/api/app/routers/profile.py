"""FastAPI router for user email profile and analytics.

This router provides insights about user's email patterns:
- Category distribution (how many promos, newsletters, etc.)
- Top senders by volume
- Sender breakdown by category
- Time-based patterns

These endpoints power the Profile UI and help users understand
their email composition and manage subscriptions.
"""

from fastapi import APIRouter, Query, HTTPException
import httpx
import os
from typing import Optional

router = APIRouter(prefix="/profile", tags=["profile"])

# Elasticsearch configuration
ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200")
INDEX = os.getenv("ES_EMAIL_INDEX", "emails_v1-000001")


@router.get("/summary")
async def profile_summary(days: int = Query(60, ge=1, le=365)) -> dict:
    """Get summary of user's email profile over time window.
    
    Returns aggregated stats:
    - Total email count
    - Breakdown by category
    - Top senders by volume
    - Average emails per day
    
    Args:
        days: Time window in days (default: 60, max: 365)
        
    Returns:
        {
            "total": 1234,
            "days": 60,
            "avg_per_day": 20.5,
            "by_category": [
                {"category": "newsletter", "count": 456, "percent": 37.0},
                {"category": "promo", "count": 321, "percent": 26.0},
                ...
            ],
            "top_senders": [
                {"sender_domain": "example.com", "count": 42},
                ...
            ]
        }
    """
    # Build aggregation query
    query = {
        "size": 0,
        "query": {
            "range": {
                "received_at": {
                    "gte": f"now-{days}d"
                }
            }
        },
        "aggs": {
            "by_category": {
                "terms": {
                    "field": "category",
                    "size": 20,
                    "missing": "uncategorized"
                }
            },
            "top_senders": {
                "terms": {
                    "field": "sender_domain",
                    "size": 20
                }
            }
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{ES_URL}/{INDEX}/_search",
                json=query
            )
            response.raise_for_status()
            
            data = response.json()
            total = data["hits"]["total"]["value"]
            aggs = data["aggregations"]
            
            # Calculate category breakdown with percentages
            categories = []
            for bucket in aggs["by_category"]["buckets"]:
                categories.append({
                    "category": bucket["key"],
                    "count": bucket["doc_count"],
                    "percent": round((bucket["doc_count"] / total * 100), 1) if total > 0 else 0
                })
            
            # Top senders
            senders = [
                {
                    "sender_domain": bucket["key"],
                    "count": bucket["doc_count"]
                }
                for bucket in aggs["top_senders"]["buckets"]
            ]
            
            return {
                "total": total,
                "days": days,
                "avg_per_day": round(total / days, 1) if days > 0 else 0,
                "by_category": categories,
                "top_senders": senders
            }
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {str(e)}")


@router.get("/senders")
async def profile_senders(
    category: Optional[str] = Query(None, description="Filter by category"),
    days: int = Query(60, ge=1, le=365),
    size: int = Query(100, ge=1, le=500),
) -> dict:
    """Get detailed sender breakdown with optional category filter.
    
    Useful for:
    - Finding all newsletter senders
    - Identifying promotional email sources
    - Analyzing recruiting email patterns
    
    Args:
        category: Filter by specific category (e.g., "newsletter", "promo")
        days: Time window in days (default: 60)
        size: Max senders to return (default: 100)
        
    Returns:
        {
            "category": "newsletter",  # or null if no filter
            "days": 60,
            "senders": [
                {
                    "sender_domain": "example.com",
                    "count": 42,
                    "latest": "2024-12-15T10:00:00Z"
                },
                ...
            ]
        }
    """
    # Build query with optional category filter
    query = {
        "range": {
            "received_at": {
                "gte": f"now-{days}d"
            }
        }
    }
    
    if category:
        query = {
            "bool": {
                "must": [
                    {"term": {"category": category}},
                    query
                ]
            }
        }
    
    # Aggregation with latest email timestamp
    aggs = {
        "senders": {
            "terms": {
                "field": "sender_domain",
                "size": size,
                "order": {"_count": "desc"}
            },
            "aggs": {
                "latest_email": {
                    "max": {"field": "received_at"}
                }
            }
        }
    }
    
    body = {
        "size": 0,
        "query": query,
        "aggs": aggs
    }
    
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{ES_URL}/{INDEX}/_search",
                json=body
            )
            response.raise_for_status()
            
            data = response.json()
            buckets = data["aggregations"]["senders"]["buckets"]
            
            senders = [
                {
                    "sender_domain": bucket["key"],
                    "count": bucket["doc_count"],
                    "latest": bucket["latest_email"]["value_as_string"]
                }
                for bucket in buckets
            ]
            
            return {
                "category": category,
                "days": days,
                "senders": senders
            }
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch senders: {str(e)}")


@router.get("/categories/{category}")
async def category_details(
    category: str,
    days: int = Query(60, ge=1, le=365),
) -> dict:
    """Get detailed breakdown for a specific category.
    
    Args:
        category: Category name (e.g., "newsletter", "promo", "recruiting")
        days: Time window in days (default: 60)
        
    Returns:
        {
            "category": "newsletter",
            "total": 456,
            "days": 60,
            "avg_per_day": 7.6,
            "top_senders": [...],
            "recent_subjects": [...]
        }
    """
    query = {
        "bool": {
            "must": [
                {"term": {"category": category}},
                {"range": {"received_at": {"gte": f"now-{days}d"}}}
            ]
        }
    }
    
    body = {
        "size": 5,
        "query": query,
        "sort": [{"received_at": {"order": "desc"}}],
        "_source": ["subject", "sender_domain", "received_at"],
        "aggs": {
            "top_senders": {
                "terms": {
                    "field": "sender_domain",
                    "size": 10
                }
            }
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{ES_URL}/{INDEX}/_search",
                json=body
            )
            response.raise_for_status()
            
            data = response.json()
            total = data["hits"]["total"]["value"]
            hits = data["hits"]["hits"]
            aggs = data["aggregations"]
            
            # Extract recent subjects
            recent_subjects = [
                {
                    "subject": hit["_source"]["subject"],
                    "sender": hit["_source"]["sender_domain"],
                    "received_at": hit["_source"]["received_at"]
                }
                for hit in hits
            ]
            
            # Top senders
            top_senders = [
                {"sender_domain": b["key"], "count": b["doc_count"]}
                for b in aggs["top_senders"]["buckets"]
            ]
            
            return {
                "category": category,
                "total": total,
                "days": days,
                "avg_per_day": round(total / days, 1) if days > 0 else 0,
                "top_senders": top_senders,
                "recent_subjects": recent_subjects
            }
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch category details: {str(e)}")


@router.get("/time-series")
async def time_series(
    days: int = Query(30, ge=1, le=90),
    interval: str = Query("1d", regex="^(1h|6h|12h|1d|1w)$"),
) -> dict:
    """Get email volume over time (time series data).
    
    Useful for visualizing email patterns and trends.
    
    Args:
        days: Time window in days (default: 30, max: 90)
        interval: Bucket interval (1h, 6h, 12h, 1d, 1w)
        
    Returns:
        {
            "interval": "1d",
            "buckets": [
                {
                    "timestamp": "2024-12-01T00:00:00Z",
                    "count": 42,
                    "by_category": {"newsletter": 20, "promo": 15, ...}
                },
                ...
            ]
        }
    """
    query = {
        "range": {
            "received_at": {
                "gte": f"now-{days}d"
            }
        }
    }
    
    body = {
        "size": 0,
        "query": query,
        "aggs": {
            "over_time": {
                "date_histogram": {
                    "field": "received_at",
                    "calendar_interval": interval,
                    "min_doc_count": 0
                },
                "aggs": {
                    "by_category": {
                        "terms": {
                            "field": "category",
                            "size": 10
                        }
                    }
                }
            }
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{ES_URL}/{INDEX}/_search",
                json=body
            )
            response.raise_for_status()
            
            data = response.json()
            buckets_raw = data["aggregations"]["over_time"]["buckets"]
            
            # Format buckets
            buckets = []
            for bucket in buckets_raw:
                by_cat = {
                    b["key"]: b["doc_count"]
                    for b in bucket["by_category"]["buckets"]
                }
                
                buckets.append({
                    "timestamp": bucket["key_as_string"],
                    "count": bucket["doc_count"],
                    "by_category": by_cat
                })
            
            return {
                "interval": interval,
                "buckets": buckets
            }
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch time series: {str(e)}")


# ============================================================================
# Phase 2: Database-backed Profile Analytics (ML labeling system)
# ============================================================================

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime, timedelta
import logging
import re
from collections import Counter

from app.db import get_db
from app.models import Email, ProfileSenderStats, ProfileCategoryStats, ProfileInterests


logger = logging.getLogger(__name__)


@router.post("/rebuild")
def profile_rebuild_v2(
    user_email: str = Query(..., description="User email to rebuild profile for"),
    lookback_days: int = Query(90, description="Days of email history to analyze"),
    db: Session = Depends(get_db)
):
    """
    Rebuild user profile from email history (database-backed).
    
    Aggregates:
    - Sender statistics (volume, categories, open rate)
    - Category statistics (volume per category)
    - Interests (extracted keywords with scores)
    
    Args:
        user_email: User email address
        lookback_days: Days of history to analyze (default 90)
        
    Returns:
        Dict with rebuild stats
    """
    logger.info(f"Rebuilding profile for {user_email} (lookback={lookback_days} days)")
    
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    
    # Fetch user's emails
    emails = (
        db.query(Email)
        .filter(
            and_(
                Email.recipient == user_email,
                Email.received_at >= cutoff
            )
        )
        .all()
    )
    
    if not emails:
        return {"message": "No emails found for user", "user_email": user_email}
    
    logger.info(f"Processing {len(emails)} emails...")
    
    # Clear existing profile data
    db.query(ProfileSenderStats).filter(ProfileSenderStats.user_email == user_email).delete()
    db.query(ProfileCategoryStats).filter(ProfileCategoryStats.user_email == user_email).delete()
    db.query(ProfileInterests).filter(ProfileInterests.user_email == user_email).delete()
    db.commit()
    
    # Aggregate sender stats
    sender_stats = {}
    for email in emails:
        sender_domain = (email.sender or "").split("@")[-1]
        if not sender_domain:
            continue
        
        if sender_domain not in sender_stats:
            sender_stats[sender_domain] = {
                "total": 0,
                "last_received_at": None,
                "categories": {},
                "opened": 0,
            }
        
        sender_stats[sender_domain]["total"] += 1
        
        if email.received_at:
            if not sender_stats[sender_domain]["last_received_at"]:
                sender_stats[sender_domain]["last_received_at"] = email.received_at
            else:
                sender_stats[sender_domain]["last_received_at"] = max(
                    sender_stats[sender_domain]["last_received_at"],
                    email.received_at
                )
        
        if email.category:
            sender_stats[sender_domain]["categories"][email.category] = (
                sender_stats[sender_domain]["categories"].get(email.category, 0) + 1
            )
    
    # Insert sender stats
    for domain, stats in sender_stats.items():
        # Note: open_rate would require tracking email read status
        open_rate = 0.0
        
        db.add(ProfileSenderStats(
            user_email=user_email,
            sender_domain=domain,
            total=stats["total"],
            last_received_at=stats["last_received_at"],
            categories=stats["categories"],
            open_rate=open_rate,
        ))
    
    # Aggregate category stats
    category_stats = {}
    for email in emails:
        if not email.category:
            continue
        
        if email.category not in category_stats:
            category_stats[email.category] = {
                "total": 0,
                "last_received_at": None,
            }
        
        category_stats[email.category]["total"] += 1
        
        if email.received_at:
            if not category_stats[email.category]["last_received_at"]:
                category_stats[email.category]["last_received_at"] = email.received_at
            else:
                category_stats[email.category]["last_received_at"] = max(
                    category_stats[email.category]["last_received_at"],
                    email.received_at
                )
    
    # Insert category stats
    for category, stats in category_stats.items():
        db.add(ProfileCategoryStats(
            user_email=user_email,
            category=category,
            total=stats["total"],
            last_received_at=stats["last_received_at"],
        ))
    
    # Extract interests from subjects and bodies
    interest_keywords = Counter()
    
    for email in emails:
        text = f"{email.subject or ''} {email.body_text or ''}"[:1000]  # First 1000 chars
        
        # Extract capitalized phrases (likely topics/companies)
        phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        for phrase in phrases:
            if len(phrase) >= 3:  # Skip short words
                interest_keywords[phrase.lower()] += 1
        
        # Extract hashtags
        hashtags = re.findall(r'#(\w+)', text)
        for tag in hashtags:
            interest_keywords[tag.lower()] += 1
    
    # Filter and insert top interests
    min_mentions = 3
    top_interests = [
        (keyword, count)
        for keyword, count in interest_keywords.most_common(100)
        if count >= min_mentions
    ]
    
    for keyword, score in top_interests:
        db.add(ProfileInterests(
            user_email=user_email,
            interest=keyword,
            score=float(score),
            updated_at=datetime.utcnow(),
        ))
    
    db.commit()
    
    logger.info(f"Profile rebuild complete: {len(sender_stats)} senders, {len(category_stats)} categories, {len(top_interests)} interests")
    
    return {
        "user_email": user_email,
        "emails_processed": len(emails),
        "senders": len(sender_stats),
        "categories": len(category_stats),
        "interests": len(top_interests),
        "lookback_days": lookback_days,
    }


@router.get("/db-summary")
def profile_summary_v2(
    user_email: str = Query(..., description="User email to get summary for"),
    db: Session = Depends(get_db)
):
    """
    Get profile summary for user (database-backed).
    
    Args:
        user_email: User email address
        
    Returns:
        Dict with top senders, categories, and interests
    """
    # Top senders
    top_senders = (
        db.query(ProfileSenderStats)
        .filter(ProfileSenderStats.user_email == user_email)
        .order_by(desc(ProfileSenderStats.total))
        .limit(10)
        .all()
    )
    
    # Top categories
    top_categories = (
        db.query(ProfileCategoryStats)
        .filter(ProfileCategoryStats.user_email == user_email)
        .order_by(desc(ProfileCategoryStats.total))
        .all()
    )
    
    # Top interests
    top_interests = (
        db.query(ProfileInterests)
        .filter(ProfileInterests.user_email == user_email)
        .order_by(desc(ProfileInterests.score))
        .limit(20)
        .all()
    )
    
    return {
        "user_email": user_email,
        "top_senders": [
            {
                "domain": s.sender_domain,
                "total": s.total,
                "categories": s.categories,
                "open_rate": round(s.open_rate * 100, 2) if s.open_rate else 0,
                "last_received": s.last_received_at.isoformat() if s.last_received_at else None,
            }
            for s in top_senders
        ],
        "categories": [
            {
                "category": c.category,
                "total": c.total,
                "last_received": c.last_received_at.isoformat() if c.last_received_at else None,
            }
            for c in top_categories
        ],
        "interests": [
            {
                "keyword": i.interest,
                "score": i.score,
            }
            for i in top_interests
        ],
    }


@router.get("/db-interests")
def get_interests_v2(
    user_email: str = Query(..., description="User email"),
    limit: int = Query(50, description="Max interests to return"),
    db: Session = Depends(get_db)
):
    """
    Get user interests with scores (database-backed).
    
    Args:
        user_email: User email address
        limit: Max number of interests (default 50)
        
    Returns:
        List of interests with scores
    """
    interests = (
        db.query(ProfileInterests)
        .filter(ProfileInterests.user_email == user_email)
        .order_by(desc(ProfileInterests.score))
        .limit(limit)
        .all()
    )
    
    return [
        {
            "interest": i.interest,
            "score": i.score,
            "updated_at": i.updated_at.isoformat() if i.updated_at else None,
        }
        for i in interests
    ]


@router.get("/db-senders")
def get_top_senders_v2(
    user_email: str = Query(..., description="User email"),
    limit: int = Query(20, description="Max senders to return"),
    db: Session = Depends(get_db)
):
    """
    Get top senders by volume (database-backed).
    
    Args:
        user_email: User email address
        limit: Max number of senders (default 20)
        
    Returns:
        List of sender domains with stats
    """
    senders = (
        db.query(ProfileSenderStats)
        .filter(ProfileSenderStats.user_email == user_email)
        .order_by(desc(ProfileSenderStats.total))
        .limit(limit)
        .all()
    )
    
    return [
        {
            "domain": s.sender_domain,
            "total": s.total,
            "categories": s.categories,
            "open_rate": round(s.open_rate * 100, 2) if s.open_rate else 0,
            "last_received": s.last_received_at.isoformat() if s.last_received_at else None,
        }
        for s in senders
    ]


@router.get("/db-categories")
def get_categories_v2(
    user_email: str = Query(..., description="User email"),
    db: Session = Depends(get_db)
):
    """
    Get category breakdown for user (database-backed).
    
    Args:
        user_email: User email address
        
    Returns:
        List of categories with counts
    """
    categories = (
        db.query(ProfileCategoryStats)
        .filter(ProfileCategoryStats.user_email == user_email)
        .order_by(desc(ProfileCategoryStats.total))
        .all()
    )
    
    total = sum(c.total for c in categories)
    
    return {
        "total_emails": total,
        "categories": [
            {
                "category": c.category,
                "total": c.total,
                "percentage": round(c.total / total * 100, 2) if total > 0 else 0,
                "last_received": c.last_received_at.isoformat() if c.last_received_at else None,
            }
            for c in categories
        ],
    }
