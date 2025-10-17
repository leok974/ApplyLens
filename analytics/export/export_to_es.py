#!/usr/bin/env python3
"""
Export dbt aggregates from BigQuery to Elasticsearch for Kibana dashboards.

This script fetches mart tables from BigQuery and pushes them to Elasticsearch
indices, allowing Ops team to visualize risk trends, parity drift, and SLO
metrics in Kibana without switching tools.

Usage:
    python export_to_es.py

Environment Variables:
    BQ_PROJECT: Google Cloud project ID
    ES_URL: Elasticsearch URL (default: http://elasticsearch:9200)
    ES_ANALYTICS_INDEX: Index name prefix (default: analytics_applylens_daily)
"""

import os
import sys
import json
import logging
from datetime import datetime, date
from typing import List, Dict, Any

try:
    from google.cloud import bigquery
    from elasticsearch import Elasticsearch, helpers
except ImportError as e:
    print(f"Error: Missing required library: {e}")
    print("Install with: pip install google-cloud-bigquery elasticsearch")
    sys.exit(1)

# Configuration
BQ_PROJECT = os.environ.get("BQ_PROJECT")
BQ_DATASET = os.environ.get("BQ_DATASET", "applylens")
ES_URL = os.environ.get("ES_URL", "http://elasticsearch:9200")
ES_INDEX_PREFIX = os.environ.get("ES_ANALYTICS_INDEX", "analytics_applylens")

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def serialize_value(value: Any) -> Any:
    """Convert BigQuery types to JSON-serializable types."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    return value


def fetch_bigquery_table(
    bq_client: bigquery.Client, query: str
) -> List[Dict[str, Any]]:
    """Execute query and return results as list of dicts."""
    logger.info(f"Executing query: {query[:100]}...")
    job = bq_client.query(query)
    results = job.result()

    rows = [{k: serialize_value(v) for k, v in dict(row).items()} for row in results]

    logger.info(f"Fetched {len(rows)} rows")
    return rows


def upsert_to_elasticsearch(
    es_client: Elasticsearch, index: str, docs: List[Dict[str, Any]], id_key: str = "id"
) -> Dict[str, int]:
    """
    Upsert documents to Elasticsearch index.

    Args:
        es_client: Elasticsearch client
        index: Index name
        docs: List of documents to index
        id_key: Field to use as document ID

    Returns:
        Dict with success and error counts
    """
    if not docs:
        logger.warning("No documents to index")
        return {"success": 0, "errors": 0}

    actions = []
    for doc in docs:
        doc_id = str(doc.get(id_key, doc.get("d", "unknown")))
        actions.append({"_op_type": "index", "_index": index, "_id": doc_id, **doc})

    logger.info(f"Indexing {len(actions)} documents to {index}")

    success_count = 0
    error_count = 0

    for ok, response in helpers.streaming_bulk(
        es_client, actions, raise_on_error=False, raise_on_exception=False
    ):
        if ok:
            success_count += 1
        else:
            error_count += 1
            logger.error(f"Indexing error: {response}")

    logger.info(f"Indexed {success_count} documents successfully, {error_count} errors")

    return {"success": success_count, "errors": error_count}


def export_risk_daily(
    bq_client: bigquery.Client, es_client: Elasticsearch
) -> Dict[str, int]:
    """Export mrt_risk_daily to Elasticsearch."""
    logger.info("Exporting mrt_risk_daily...")

    query = f"""
    SELECT 
        FORMAT_DATE('%Y-%m-%d', d) as id,
        d,
        emails,
        emails_scored,
        avg_risk,
        min_risk,
        max_risk,
        low_risk_count,
        medium_risk_count,
        high_risk_count,
        critical_risk_count,
        unscored_count,
        recruiter_count,
        interview_count,
        offer_count,
        rejection_count,
        coverage_pct,
        high_risk_pct,
        critical_risk_pct
    FROM `{BQ_PROJECT}.{BQ_DATASET}.mrt_risk_daily`
    WHERE d >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    ORDER BY d DESC
    """

    docs = fetch_bigquery_table(bq_client, query)
    index = f"{ES_INDEX_PREFIX}_risk_daily"

    return upsert_to_elasticsearch(es_client, index, docs, id_key="id")


def export_parity_drift(
    bq_client: bigquery.Client, es_client: Elasticsearch
) -> Dict[str, int]:
    """Export mrt_parity_drift to Elasticsearch."""
    logger.info("Exporting mrt_parity_drift...")

    query = f"""
    SELECT 
        FORMAT_DATE('%Y-%m-%d', d) as id,
        d,
        total_checked,
        total_mismatches,
        mismatch_ratio,
        risk_score_mismatches,
        expires_at_mismatches,
        category_mismatches,
        last_check_at,
        slo_status
    FROM `{BQ_PROJECT}.{BQ_DATASET}.mrt_parity_drift`
    WHERE d >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    ORDER BY d DESC
    """

    docs = fetch_bigquery_table(bq_client, query)
    index = f"{ES_INDEX_PREFIX}_parity_drift"

    return upsert_to_elasticsearch(es_client, index, docs, id_key="id")


def export_backfill_slo(
    bq_client: bigquery.Client, es_client: Elasticsearch
) -> Dict[str, int]:
    """Export mrt_backfill_slo to Elasticsearch."""
    logger.info("Exporting mrt_backfill_slo...")

    query = f"""
    SELECT 
        FORMAT_DATE('%Y-%m-%d', d) as id,
        d,
        backfill_count,
        avg_duration_seconds,
        p50_duration_seconds,
        p95_duration_seconds,
        p99_duration_seconds,
        total_emails_processed,
        failed_count,
        slo_status,
        success_rate_pct
    FROM `{BQ_PROJECT}.{BQ_DATASET}.mrt_backfill_slo`
    WHERE d >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    ORDER BY d DESC
    """

    docs = fetch_bigquery_table(bq_client, query)
    index = f"{ES_INDEX_PREFIX}_backfill_slo"

    return upsert_to_elasticsearch(es_client, index, docs, id_key="id")


def main():
    """Main export function."""
    # Validate environment
    if not BQ_PROJECT:
        logger.error("BQ_PROJECT environment variable not set")
        sys.exit(1)

    logger.info("Starting export from BigQuery to Elasticsearch")
    logger.info(f"BigQuery project: {BQ_PROJECT}")
    logger.info(f"BigQuery dataset: {BQ_DATASET}")
    logger.info(f"Elasticsearch URL: {ES_URL}")
    logger.info(f"Index prefix: {ES_INDEX_PREFIX}")

    # Initialize clients
    try:
        bq_client = bigquery.Client(project=BQ_PROJECT)
        es_client = Elasticsearch(ES_URL)

        # Test connections
        logger.info("Testing BigQuery connection...")
        bq_client.query("SELECT 1").result()

        logger.info("Testing Elasticsearch connection...")
        if not es_client.ping():
            raise ConnectionError("Elasticsearch ping failed")

        logger.info("✓ Connections successful")

    except Exception as e:
        logger.error(f"Connection failed: {e}")
        sys.exit(1)

    # Export all mart tables
    results = {}

    try:
        results["risk_daily"] = export_risk_daily(bq_client, es_client)
        results["parity_drift"] = export_parity_drift(bq_client, es_client)
        results["backfill_slo"] = export_backfill_slo(bq_client, es_client)

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        sys.exit(1)

    # Summary
    logger.info("=" * 60)
    logger.info("Export Summary:")

    total_success = sum(r["success"] for r in results.values())
    total_errors = sum(r["errors"] for r in results.values())

    for table, result in results.items():
        logger.info(f"  {table}: {result['success']} docs, {result['errors']} errors")

    logger.info(f"Total: {total_success} docs indexed, {total_errors} errors")
    logger.info("=" * 60)

    # Output JSON for CI/CD parsing
    output = {
        "timestamp": datetime.utcnow().isoformat(),
        "bq_project": BQ_PROJECT,
        "es_url": ES_URL,
        "results": results,
        "total_success": total_success,
        "total_errors": total_errors,
    }

    print(json.dumps(output, indent=2))

    # Exit with error if any failures
    if total_errors > 0:
        logger.warning(f"Export completed with {total_errors} errors")
        sys.exit(1)

    logger.info("✓ Export completed successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
