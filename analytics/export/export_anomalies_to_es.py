#!/usr/bin/env python3
"""Export detected anomalies from BigQuery to Elasticsearch."""

import json
import os
from datetime import datetime

from elasticsearch import Elasticsearch, helpers
from google.cloud import bigquery


def main():
    """Query anomalies from BigQuery and bulk index to Elasticsearch."""
    # Initialize clients
    bq_client = bigquery.Client(project=os.environ["BQ_PROJECT"])
    es_client = Elasticsearch([os.environ["ES_URL"]])
    
    # Query high/low severity anomalies
    query = f"""
    SELECT
      d,
      metric,
      actual_value,
      predicted_value,
      lower_bound,
      upper_bound,
      severity,
      residual
    FROM `{os.environ['BQ_PROJECT']}.ml.anomaly_detection`
    WHERE severity IN ('high', 'low')
    ORDER BY d DESC, metric
    """
    
    query_job = bq_client.query(query)
    results = query_job.result()
    
    # Prepare bulk index actions
    actions = []
    for row in results:
        doc = {
            "_index": "analytics_applylens_anomalies",
            "_id": f"{row.metric}:{row.d.isoformat()}",
            "_source": {
                "date": row.d.isoformat(),
                "metric": row.metric,
                "actual_value": float(row.actual_value) if row.actual_value is not None else None,
                "predicted_value": float(row.predicted_value) if row.predicted_value is not None else None,
                "lower_bound": float(row.lower_bound) if row.lower_bound is not None else None,
                "upper_bound": float(row.upper_bound) if row.upper_bound is not None else None,
                "severity": row.severity,
                "residual": float(row.residual) if row.residual is not None else None,
                "exported_at": datetime.utcnow().isoformat() + "Z"
            }
        }
        actions.append(doc)
    
    # Bulk index
    if actions:
        success, failed = helpers.bulk(es_client, actions, raise_on_error=False)
        print(json.dumps({
            "total_anomalies": len(actions),
            "indexed": success,
            "failed": len(failed)
        }))
    else:
        print(json.dumps({"total_anomalies": 0, "indexed": 0, "failed": 0}))


if __name__ == "__main__":
    main()
