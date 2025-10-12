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
