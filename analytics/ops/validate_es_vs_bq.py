#!/usr/bin/env python3
"""
Elasticsearch vs BigQuery data validation script.

Compares document counts between ES and BQ to ensure data consistency.
Pushes metrics to Prometheus Pushgateway for alerting.

Environment Variables:
- ES_URL: Elasticsearch endpoint (default: http://elasticsearch:9200)
- GCP_PROJECT: Google Cloud project ID
- BQ_MARTS_DATASET: BigQuery dataset (default: gmail_marts)
- PUSHGATEWAY: Prometheus Pushgateway URL (default: http://prometheus-pushgateway:9091)
- GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON
- VALIDATION_THRESHOLD_PCT: Alert threshold % (default: 2.0)

Exit Codes:
- 0: Validation passed (delta < threshold)
- 2: Validation failed (delta >= threshold)

Usage:
    python validate_es_vs_bq.py
"""

import os
import sys
import requests
from google.cloud import bigquery
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200")
BQ_PROJECT = os.getenv("GCP_PROJECT")
DS_MARTS = os.getenv("BQ_MARTS_DATASET", "gmail_marts")
PUSHGATEWAY = os.getenv("PUSHGATEWAY", "http://prometheus-pushgateway:9091")
THRESHOLD_PCT = float(os.getenv("VALIDATION_THRESHOLD_PCT", "2.0"))


def get_es_count_7d() -> int:
    """Get document count from Elasticsearch for last 7 days."""
    try:
        query = {"query": {"range": {"received_at": {"gte": "now-7d/d"}}}}

        response = requests.get(f"{ES_URL}/gmail_emails/_count", json=query, timeout=30)
        response.raise_for_status()

        count = response.json()["count"]
        logger.info(f"Elasticsearch 7d count: {count}")
        return count

    except Exception as e:
        logger.error(f"Failed to get ES count: {e}")
        raise


def get_bq_count_7d() -> int:
    """Get document count from BigQuery for last 7 days."""
    try:
        if not BQ_PROJECT:
            raise ValueError("GCP_PROJECT environment variable not set")

        client = bigquery.Client(project=BQ_PROJECT)

        sql = f"""
            SELECT SUM(messages_count) as total_count
            FROM `{BQ_PROJECT}.{DS_MARTS}.mart_email_activity_daily`
            WHERE day >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
        """

        query_job = client.query(sql)
        result = list(query_job.result())

        if not result or result[0].total_count is None:
            logger.warning("No data found in BigQuery")
            return 0

        count = int(result[0].total_count)
        logger.info(f"BigQuery 7d count: {count}")
        return count

    except Exception as e:
        logger.error(f"Failed to get BQ count: {e}")
        raise


def calculate_delta_pct(es_count: int, bq_count: int) -> float:
    """Calculate percentage difference between ES and BQ counts."""
    if es_count == 0:
        return 100.0 if bq_count > 0 else 0.0

    delta = abs(es_count - bq_count)
    pct = (delta / es_count) * 100
    return round(pct, 2)


def push_metrics(es_count: int, bq_count: int, delta_pct: float):
    """Push validation metrics to Prometheus Pushgateway."""
    try:
        registry = CollectorRegistry()

        # Delta percentage metric
        gauge_delta = Gauge(
            "applylens_gmail_7d_delta_pct",
            "ES vs BQ 7d count delta percentage",
            registry=registry,
        )
        gauge_delta.set(delta_pct)

        # Absolute counts
        gauge_es = Gauge(
            "applylens_gmail_7d_es_count",
            "Elasticsearch 7d document count",
            registry=registry,
        )
        gauge_es.set(es_count)

        gauge_bq = Gauge(
            "applylens_gmail_7d_bq_count",
            "BigQuery 7d document count",
            registry=registry,
        )
        gauge_bq.set(bq_count)

        # Validation status (1 = passed, 0 = failed)
        gauge_status = Gauge(
            "applylens_gmail_validation_passed",
            "Validation status (1=passed, 0=failed)",
            registry=registry,
        )
        gauge_status.set(1 if delta_pct <= THRESHOLD_PCT else 0)

        # Push to gateway
        push_to_gateway(PUSHGATEWAY, job="validate_es_vs_bq", registry=registry)

        logger.info(f"Pushed metrics to Pushgateway: {PUSHGATEWAY}")

    except Exception as e:
        logger.warning(f"Failed to push metrics to Pushgateway: {e}")
        # Don't fail validation due to pushgateway issues


def main():
    """Main validation logic."""
    logger.info("=" * 60)
    logger.info("Starting ES vs BQ validation")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"Threshold: {THRESHOLD_PCT}%")
    logger.info("=" * 60)

    try:
        # Get counts
        es_count = get_es_count_7d()
        bq_count = get_bq_count_7d()
        delta_pct = calculate_delta_pct(es_count, bq_count)

        # Log results
        logger.info("")
        logger.info("Validation Results:")
        logger.info(f"  Elasticsearch: {es_count:,} documents")
        logger.info(f"  BigQuery:      {bq_count:,} documents")
        logger.info(
            f"  Delta:         {abs(es_count - bq_count):,} documents ({delta_pct}%)"
        )
        logger.info(f"  Threshold:     {THRESHOLD_PCT}%")
        logger.info("")

        # Push metrics
        push_metrics(es_count, bq_count, delta_pct)

        # Determine pass/fail
        if delta_pct <= THRESHOLD_PCT:
            logger.info(
                f"✅ VALIDATION PASSED (delta {delta_pct}% <= {THRESHOLD_PCT}%)"
            )
            return 0
        else:
            logger.error(
                f"❌ VALIDATION FAILED (delta {delta_pct}% > {THRESHOLD_PCT}%)"
            )
            return 2

    except Exception as e:
        logger.error(f"❌ VALIDATION ERROR: {e}")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
