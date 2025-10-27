"""
Warehouse metrics API endpoints.

Serves analytics data from BigQuery mart tables created by dbt.
Uses Fivetran-synced Gmail data for dashboard and profile insights.

Environment Variables:
- GCP_PROJECT: Google Cloud project ID
- BQ_MARTS_DATASET: BigQuery dataset for mart tables (default: gmail_marts)
- USE_WAREHOUSE_METRICS: Enable/disable warehouse endpoints (default: 0)
- GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON
"""

from fastapi import APIRouter, HTTPException, Query
from google.cloud import bigquery
from app.utils.cache import cache_get, cache_set
import os
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics/profile", tags=["metrics", "warehouse"])

# Configuration
BQ_PROJECT = os.getenv("GCP_PROJECT")
DS_MARTS = os.getenv("BQ_MARTS_DATASET", "gmail_marts")
DS_STAGING = os.getenv("BQ_STAGING_DATASET", "gmail_raw_stg_gmail_raw_stg")
USE_WAREHOUSE = os.getenv("USE_WAREHOUSE_METRICS", "0") == "1"
CACHE_TTL_SECONDS = 300  # 5 minutes
SUMMARY_CACHE_TTL = 60  # 1 minute for summary endpoint

# Active account email (TODO: Get from auth context)
DEFAULT_ACCOUNT = "leoklemet.pa@gmail.com"

# Initialize BigQuery client (lazy)
_bq_client = None


def get_bq_client():
    """Get or create BigQuery client."""
    global _bq_client
    if _bq_client is None:
        if not BQ_PROJECT:
            raise HTTPException(
                status_code=500, detail="GCP_PROJECT environment variable not set"
            )
        _bq_client = bigquery.Client(project=BQ_PROJECT)
    return _bq_client


def query_bq(sql: str) -> List[Dict[str, Any]]:
    """Execute BigQuery SQL and return results as list of dicts."""
    try:
        client = get_bq_client()
        query_job = client.query(sql)
        result = query_job.result()

        # Convert to list of dicts
        cols = [field.name for field in result.schema]
        rows = []
        for row in result:
            row_dict = {}
            for i, col in enumerate(cols):
                val = row[i]
                # Convert dates/timestamps to ISO strings
                if isinstance(val, datetime):
                    val = val.isoformat()
                row_dict[col] = val
            rows.append(row_dict)

        return rows
    except Exception as e:
        logger.error(f"BigQuery query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/activity_daily")
def get_activity_daily(days: int = Query(default=90, ge=1, le=365)):
    """
    Get daily email activity metrics.

    Returns:
    - day: Date
    - messages_count: Total messages
    - unique_senders: Count of unique senders
    - avg_size_kb: Average message size in KB
    - total_size_mb: Total size in MB

    Cache: 5 minutes
    Source: mart_email_activity_daily (dbt model)
    """
    if not USE_WAREHOUSE:
        raise HTTPException(
            status_code=412,
            detail="Warehouse metrics disabled. Set USE_WAREHOUSE_METRICS=1",
        )

    cache_key = f"metrics:activity_daily:{days}"
    cached = cache_get(cache_key)
    if cached:
        return cached  # Already deserialized by cache_get

    sql = f"""
        SELECT
            day,
            messages_count,
            unique_senders,
            avg_size_kb,
            total_size_mb
        FROM `{BQ_PROJECT}.{DS_MARTS}.mart_email_activity_daily`
        ORDER BY day DESC
        LIMIT {days}
    """

    rows = query_bq(sql)
    payload = {
        "rows": rows,
        "count": len(rows),
        "source": "bigquery",
        "dataset": f"{BQ_PROJECT}.{DS_MARTS}.mart_email_activity_daily",
    }

    cache_set(cache_key, payload, CACHE_TTL_SECONDS)
    return payload


@router.get("/top_senders_30d")
def get_top_senders_30d(limit: int = Query(default=20, ge=1, le=100)):
    """
    Get top email senders in the last 30 days.

    Returns:
    - from_email: Sender email
    - messages_30d: Message count
    - total_size_mb: Total size
    - first_message_at: First message timestamp
    - last_message_at: Last message timestamp
    - active_days: Days between first and last message

    Cache: 5 minutes
    Source: mart_top_senders_30d (dbt model)
    """
    if not USE_WAREHOUSE:
        raise HTTPException(
            status_code=412,
            detail="Warehouse metrics disabled. Set USE_WAREHOUSE_METRICS=1",
        )

    cache_key = f"metrics:top_senders_30d:{limit}"
    cached = cache_get(cache_key)
    if cached:
        return cached  # Already deserialized by cache_get

    sql = f"""
        SELECT
            from_email,
            messages_30d,
            total_size_mb,
            first_message_at,
            last_message_at,
            active_days
        FROM `{BQ_PROJECT}.{DS_MARTS}.mart_top_senders_30d`
        ORDER BY messages_30d DESC
        LIMIT {limit}
    """

    rows = query_bq(sql)
    payload = {
        "rows": rows,
        "count": len(rows),
        "source": "bigquery",
        "dataset": f"{BQ_PROJECT}.{DS_MARTS}.mart_top_senders_30d",
    }

    cache_set(cache_key, payload, CACHE_TTL_SECONDS)
    return payload


@router.get("/categories_30d")
def get_categories_30d():
    """
    Get email category distribution in the last 30 days.

    Returns:
    - category: Gmail category (promotions, updates, social, forums, primary)
    - messages_30d: Message count
    - pct_of_total: Percentage of total
    - total_size_mb: Total size

    Cache: 5 minutes
    Source: mart_categories_30d (dbt model)
    """
    if not USE_WAREHOUSE:
        raise HTTPException(
            status_code=412,
            detail="Warehouse metrics disabled. Set USE_WAREHOUSE_METRICS=1",
        )

    cache_key = "metrics:categories_30d"
    cached = cache_get(cache_key)
    if cached:
        return cached  # Already deserialized by cache_get

    sql = f"""
        SELECT
            category,
            messages_30d,
            pct_of_total,
            total_size_mb
        FROM `{BQ_PROJECT}.{DS_MARTS}.mart_categories_30d`
        ORDER BY messages_30d DESC
    """

    rows = query_bq(sql)
    payload = {
        "rows": rows,
        "count": len(rows),
        "source": "bigquery",
        "dataset": f"{BQ_PROJECT}.{DS_MARTS}.mart_categories_30d",
    }

    cache_set(cache_key, payload, CACHE_TTL_SECONDS)
    return payload


@router.get("/freshness")
def get_data_freshness():
    """
    Get data freshness metrics from Fivetran sync.

    Returns:
    - last_sync_at: Last Fivetran sync timestamp
    - minutes_since_sync: Minutes since last sync
    - is_fresh: True if synced within 30 minutes (SLO)

    Cache: 1 minute
    """
    if not USE_WAREHOUSE:
        raise HTTPException(
            status_code=412,
            detail="Warehouse metrics disabled. Set USE_WAREHOUSE_METRICS=1",
        )

    cache_key = "metrics:freshness"
    cached = cache_get(cache_key)
    if cached:
        return cached  # Already deserialized by cache_get

    sql = f"""
        SELECT
            MAX(synced_at) as last_sync_at,
            TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(synced_at), MINUTE) as minutes_since_sync
        FROM `{BQ_PROJECT}.{DS_STAGING}.stg_gmail__messages`
    """

    rows = query_bq(sql)
    if not rows:
        raise HTTPException(status_code=404, detail="No sync data found")

    row = rows[0]
    payload = {
        "last_sync_at": row["last_sync_at"],
        "minutes_since_sync": row["minutes_since_sync"],
        "is_fresh": row["minutes_since_sync"] <= 30,  # SLO: 30 minutes
        "source": "bigquery",
    }

    cache_set(cache_key, payload, 60)  # Cache for 1 minute
    return payload


@router.get("/summary")
def get_profile_summary():
    """
    Unified profile summary aggregating warehouse mart data.

    Returns:
    - account: User email address
    - last_sync_at: ISO8601 timestamp of most recent warehouse sync (from BigQuery data)
    - dataset: Dataset/table prefix being queried for debugging
    - totals: all_time_emails, last_30d_emails
    - top_senders_30d: Top 3 senders (sender, email, count)
    - top_categories_30d: Top 3 categories (category, count)
    - top_interests: Top 3 interests/keywords (keyword, count)

    Cache: 60 seconds
    Error handling: Returns 200 with empty arrays on failure (graceful degradation)
    """
    if not USE_WAREHOUSE:
        return {
            "account": "leoklemet.pa@gmail.com",
            "last_sync_at": None,
            "dataset": f"{BQ_PROJECT}.{DS_MARTS}",
            "totals": {"all_time_emails": 0, "last_30d_emails": 0},
            "top_senders_30d": [],
            "top_categories_30d": [],
            "top_interests": [],
        }

    cache_key = "metrics:profile_summary"
    cached = cache_get(cache_key)
    if cached:
        return cached

    result = {
        "account": "leoklemet.pa@gmail.com",  # TODO: Get from auth context
        "last_sync_at": None,
        "dataset": f"{BQ_PROJECT}.{DS_MARTS}",
        "totals": {"all_time_emails": 0, "last_30d_emails": 0},
        "top_senders_30d": [],
        "top_categories_30d": [],
        "top_interests": [],
    }

    # Fetch last_sync_at from warehouse (most recent data timestamp)
    try:
        sync_sql = f"""
        SELECT MAX(synced_at) as last_sync_at
        FROM `{BQ_PROJECT}.{DS_STAGING}.stg_gmail__messages`
        """
        sync_rows = query_bq(sync_sql)
        if sync_rows and sync_rows[0] and sync_rows[0].get("last_sync_at"):
            result["last_sync_at"] = sync_rows[0]["last_sync_at"]
    except Exception as e:
        logger.warning(f"Error fetching last_sync_at: {e}")

    # Fetch totals from mart_email_activity_daily
    try:
        totals_sql = f"""
        SELECT
            SUM(message_count) as all_time_emails,
            SUM(CASE WHEN activity_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                THEN message_count ELSE 0 END) as last_30d_emails
        FROM `{BQ_PROJECT}.{DS_MARTS}.mart_email_activity_daily`
        """
        totals_rows = query_bq(totals_sql)
        if totals_rows and totals_rows[0]:
            result["totals"]["all_time_emails"] = int(
                totals_rows[0].get("all_time_emails") or 0
            )
            result["totals"]["last_30d_emails"] = int(
                totals_rows[0].get("last_30d_emails") or 0
            )
    except Exception as e:
        logger.warning(f"Error fetching totals: {e}")

    # Fetch top 3 senders from mart_top_senders_30d
    try:
        senders_sql = f"""
        SELECT
            from_name as sender,
            from_email as email,
            messages_30d as count
        FROM `{BQ_PROJECT}.{DS_MARTS}.mart_top_senders_30d`
        ORDER BY messages_30d DESC
        LIMIT 3
        """
        senders_rows = query_bq(senders_sql)
        result["top_senders_30d"] = [
            {
                "sender": row.get("sender") or row.get("email", "Unknown"),
                "email": row.get("email", ""),
                "count": int(row.get("count") or 0),
            }
            for row in senders_rows
        ]
    except Exception as e:
        logger.warning(f"Error fetching top senders: {e}")

    # Fetch top 3 categories from mart_categories_30d
    try:
        categories_sql = f"""
        SELECT
            category,
            messages_30d as count
        FROM `{BQ_PROJECT}.{DS_MARTS}.mart_categories_30d`
        WHERE category IS NOT NULL
        ORDER BY messages_30d DESC
        LIMIT 3
        """
        categories_rows = query_bq(categories_sql)
        result["top_categories_30d"] = [
            {
                "category": row.get("category", "Unknown"),
                "count": int(row.get("count") or 0),
            }
            for row in categories_rows
        ]
    except Exception as e:
        logger.warning(f"Error fetching top categories: {e}")

    # Fetch top 3 interests/keywords
    # TODO: Create mart_interests_30d in dbt for better performance
    try:
        interests_sql = f"""
        SELECT
            keyword,
            COUNT(*) as count
        FROM (
            SELECT
                LOWER(SPLIT(subject, ' ')[SAFE_OFFSET(0)]) as keyword
            FROM `{BQ_PROJECT}.{DS_STAGING}.stg_gmail__messages`
            WHERE received_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
                AND subject IS NOT NULL
                AND LENGTH(subject) > 3
        )
        WHERE keyword IS NOT NULL
            AND LENGTH(keyword) > 3
            AND keyword NOT IN ('re:', 'fwd:', 'the', 'your', 'new', 'update', 'from')
        GROUP BY keyword
        ORDER BY count DESC
        LIMIT 3
        """
        interests_rows = query_bq(interests_sql)
        result["top_interests"] = [
            {"keyword": row.get("keyword", ""), "count": int(row.get("count") or 0)}
            for row in interests_rows
        ]
    except Exception as e:
        logger.warning(f"Error fetching top interests: {e}")

    # Cache for 60 seconds
    cache_set(cache_key, result, SUMMARY_CACHE_TTL)
    return result
