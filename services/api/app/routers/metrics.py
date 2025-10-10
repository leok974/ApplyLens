"""
Prometheus metrics router for backfill health monitoring.

Exposes /metrics endpoint that Prometheus can scrape to monitor
the health of bill backfill operations.
"""
from fastapi import APIRouter, Response
from prometheus_client import CollectorRegistry, Gauge, generate_latest, CONTENT_TYPE_LATEST
import os
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import validate_backfill as V

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Custom registry for backfill health metrics
REG = CollectorRegistry()

# Backfill health gauges
G_MISSING = Gauge(
    "bills_missing_dates",
    "Bills missing dates[] field",
    registry=REG
)

G_WITH_DATES = Gauge(
    "bills_with_dates",
    "Bills with dates[] populated",
    registry=REG
)

G_WITH_EXP = Gauge(
    "bills_with_expires_at",
    "Bills with expires_at field set",
    registry=REG
)

G_LAST_TS = Gauge(
    "backfill_health_last_run_timestamp",
    "Last refresh timestamp (unix seconds)",
    registry=REG
)

G_INDEX_INFO = Gauge(
    "backfill_health_index_info",
    "Index info (labels only)",
    registry=REG,
    labelnames=["index"]
)


def refresh_metrics():
    """
    Query Elasticsearch and update Prometheus gauges with current backfill health.
    
    This function is called on every scrape to ensure metrics are fresh.
    For high-traffic scenarios, consider caching or using the /refresh endpoint.
    """
    client = V.es()
    missing = V.count_missing_dates(client)
    total, with_exp = V.counts_with_expiry(client)
    
    # Set gauges
    G_MISSING.set(missing)
    G_WITH_DATES.set(total)
    G_WITH_EXP.set(with_exp)
    G_LAST_TS.set(datetime.now(timezone.utc).timestamp())
    
    # Set index info label
    index_name = os.getenv("ES_EMAIL_INDEX", "gmail_emails_v2")
    G_INDEX_INFO.labels(index=index_name).set(1)


@router.get("")
def metrics():
    """
    Prometheus metrics endpoint for backfill health.
    
    Returns metrics in Prometheus exposition format.
    Refreshes metrics on every scrape (lazy refresh).
    
    Example response:
        # HELP bills_missing_dates Bills missing dates[] field
        # TYPE bills_missing_dates gauge
        bills_missing_dates 0.0
        # HELP bills_with_dates Bills with dates[] populated
        # TYPE bills_with_dates gauge
        bills_with_dates 1243.0
        ...
    """
    # Lazy refresh on scrape
    refresh_metrics()
    output = generate_latest(REG)
    return Response(content=output, media_type=CONTENT_TYPE_LATEST)


@router.post("/refresh")
def metrics_refresh():
    """
    Manually trigger metrics refresh.
    
    Useful for precomputing metrics on a schedule instead of
    refreshing on every scrape.
    
    Returns:
        {"ok": True} on success
    """
    refresh_metrics()
    return {"ok": True}
