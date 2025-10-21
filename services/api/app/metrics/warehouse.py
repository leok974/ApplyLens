"""BigQuery warehouse reader module.

Provides functions to query BigQuery mart tables for analytics and metrics.
Feature-flagged via USE_WAREHOUSE environment variable.

Usage:
    from app.metrics.warehouse import mq_top_senders_30d, mq_activity_daily
    
    # Get top senders
    senders = await mq_top_senders_30d(limit=10)
    
    # Get daily activity
    activity = await mq_activity_daily(days=14)
"""

import os
from typing import Any

from google.cloud import bigquery

# BigQuery configuration from environment
PROJECT = os.getenv("GCP_PROJECT", os.getenv("BQ_PROJECT", "applylens-app"))
LOCATION = os.getenv("GCP_BQ_LOCATION", "US")


def _client() -> bigquery.Client:
    """Get BigQuery client instance.
    
    Uses Application Default Credentials (ADC) or service account key
    if GCP_CREDENTIALS_PATH is set.
    
    Returns:
        Configured BigQuery client
    """
    credentials_path = os.getenv("GCP_CREDENTIALS_PATH")
    if credentials_path:
        return bigquery.Client.from_service_account_json(
            credentials_path, project=PROJECT, location=LOCATION
        )
    return bigquery.Client(project=PROJECT, location=LOCATION)


async def mq_top_senders_30d(limit: int = 10) -> list[dict[str, Any]]:
    """Query top email senders in last 30 days from BigQuery warehouse.
    
    Args:
        limit: Maximum number of senders to return (default: 10)
        
    Returns:
        List of dicts with keys: from_email, messages_30d, total_size_mb,
        first_message_at, last_message_at, active_days
        
    Example:
        >>> senders = await mq_top_senders_30d(limit=5)
        >>> senders[0]
        {
            'from_email': 'jobs-noreply@linkedin.com',
            'messages_30d': 42,
            'total_size_mb': 1.5,
            'first_message_at': '2025-09-18T10:00:00Z',
            'last_message_at': '2025-10-18T15:30:00Z',
            'active_days': 30
        }
    """
    sql = f"""
    SELECT 
        from_email, 
        messages_30d,
        total_size_mb,
        first_message_at,
        last_message_at,
        active_days
    FROM `{PROJECT}.gmail_marts.mart_top_senders_30d`
    ORDER BY messages_30d DESC
    LIMIT @limit
    """
    
    client = _client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("limit", "INT64", limit)
        ]
    )
    
    query_job = client.query(sql, job_config=job_config)
    results = query_job.result()
    
    return [dict(row) for row in results]


async def mq_activity_daily(days: int = 14) -> list[dict[str, Any]]:
    """Query daily email activity from BigQuery warehouse.
    
    Args:
        days: Number of days to retrieve (default: 14)
        
    Returns:
        List of dicts with keys: day (date string), messages_count,
        unique_senders, avg_size_kb, total_size_mb
        
    Example:
        >>> activity = await mq_activity_daily(days=7)
        >>> activity[0]
        {
            'day': '2025-10-18',
            'messages_count': 35,
            'unique_senders': 12,
            'avg_size_kb': 45.2,
            'total_size_mb': 1.5
        }
    """
    sql = f"""
    SELECT 
        FORMAT_DATE('%Y-%m-%d', day) as day,
        messages_count,
        unique_senders,
        avg_size_kb,
        total_size_mb
    FROM `{PROJECT}.gmail_marts.mart_email_activity_daily`
    WHERE day >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
    ORDER BY day ASC
    """
    
    client = _client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("days", "INT64", days)
        ]
    )
    
    query_job = client.query(sql, job_config=job_config)
    results = query_job.result()
    
    return [dict(row) for row in results]


async def mq_categories_30d(limit: int = 10) -> list[dict[str, Any]]:
    """Query email category distribution in last 30 days from BigQuery warehouse.
    
    Args:
        limit: Maximum number of categories to return (default: 10)
        
    Returns:
        List of dicts with keys: category, messages_30d, pct_of_total, total_size_mb
        
    Example:
        >>> categories = await mq_categories_30d(limit=5)
        >>> categories[0]
        {
            'category': 'promotions',
            'messages_30d': 150,
            'pct_of_total': 45.5,
            'total_size_mb': 12.3
        }
    """
    sql = f"""
    SELECT 
        category,
        messages_30d,
        pct_of_total,
        total_size_mb
    FROM `{PROJECT}.gmail_marts.mart_categories_30d`
    ORDER BY messages_30d DESC
    LIMIT @limit
    """
    
    client = _client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("limit", "INT64", limit)
        ]
    )
    
    query_job = client.query(sql, job_config=job_config)
    results = query_job.result()
    
    return [dict(row) for row in results]


async def mq_messages_last_24h() -> int:
    """Query count of messages synced in last 24 hours.
    
    Used for divergence monitoring (compare ES vs BQ).
    
    Returns:
        Count of messages synced in last 24 hours
        
    Example:
        >>> count = await mq_messages_last_24h()
        >>> count
        42
    """
    sql = f"""
    SELECT COUNT(*) as count
    FROM `{PROJECT}.gmail_raw.message`
    WHERE _fivetran_synced >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
      AND _fivetran_deleted = FALSE
    """
    
    client = _client()
    query_job = client.query(sql)
    results = query_job.result()
    
    row = next(results, None)
    return row["count"] if row else 0
