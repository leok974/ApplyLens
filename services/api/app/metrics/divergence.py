"""Divergence monitoring between Elasticsearch and BigQuery.

Monitors data consistency between ES (serving) and BQ (warehouse).
Alerts if divergence exceeds SLO threshold (default 2%).
"""

import datetime as dt
from typing import Any

from app.es import ES_URL, INDEX, es
from app.metrics.warehouse import mq_messages_last_24h


async def count_emails_last_24h_es() -> int:
    """Count emails in Elasticsearch indexed in last 24 hours.
    
    Returns:
        Count of emails with created_at >= 24 hours ago
    """
    if not es:
        return 0
    
    try:
        # Query emails from last 24 hours
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
        cutoff_str = cutoff.isoformat()
        
        response = es.count(
            index=INDEX,
            body={
                "query": {
                    "range": {
                        "created_at": {
                            "gte": cutoff_str
                        }
                    }
                }
            }
        )
        
        return response.get("count", 0)
    except Exception as e:
        # Log error but don't fail
        print(f"ES count error: {e}")
        return 0


async def compute_divergence_24h() -> dict[str, Any]:
    """Compute divergence between ES and BQ for last 24 hours.
    
    Divergence = |BQ_count - ES_count| / max(ES_count, 1)
    
    SLO: Divergence < 2% (0.02)
    
    Returns:
        Dict with keys:
        - es_count: Count from Elasticsearch
        - bq_count: Count from BigQuery
        - divergence: Absolute divergence ratio (0.0 = perfect match)
        - divergence_pct: Divergence as percentage
        - slo_met: Boolean, True if divergence < 2%
        - status: "healthy" | "warning" | "critical"
        
    Example:
        ```python
        result = await compute_divergence_24h()
        # {
        #     "es_count": 100,
        #     "bq_count": 98,
        #     "divergence": 0.02,
        #     "divergence_pct": 2.0,
        #     "slo_met": True,
        #     "status": "healthy"
        # }
        ```
    """
    # Get counts from both sources
    es_count = await count_emails_last_24h_es()
    bq_count = await mq_messages_last_24h()
    
    # Handle zero counts
    if es_count == 0 and bq_count == 0:
        return {
            "es_count": 0,
            "bq_count": 0,
            "divergence": 0.0,
            "divergence_pct": 0.0,
            "slo_met": True,
            "status": "healthy",
            "message": "No data in last 24h (both sources empty)"
        }
    
    # Compute divergence
    div = abs(bq_count - es_count) / max(es_count, 1)
    div_pct = div * 100
    
    # Determine status
    if div < 0.02:  # < 2%
        status = "healthy"
        slo_met = True
    elif div < 0.05:  # 2-5%
        status = "warning"
        slo_met = False
    else:  # > 5%
        status = "critical"
        slo_met = False
    
    return {
        "es_count": es_count,
        "bq_count": bq_count,
        "divergence": round(div, 4),
        "divergence_pct": round(div_pct, 2),
        "slo_met": slo_met,
        "status": status,
        "message": f"Divergence: {div_pct:.2f}% ({'within' if slo_met else 'exceeds'} SLO)"
    }
