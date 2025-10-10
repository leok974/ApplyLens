#!/usr/bin/env python3
"""
Emit backfill health metrics to Elasticsearch for Kibana trending.

Indexes a single document per run into backfill_health_v1 with counts
and timestamp. This enables Kibana Lens to show trends over time.

Usage:
    python emit_backfill_health.py
    
Environment variables:
    ES_URL          - Elasticsearch URL (default: http://localhost:9200)
    ES_EMAIL_INDEX  - Email index to check (default: gmail_emails_v2)
    ES_HEALTH_INDEX - Health metrics index (default: backfill_health_v1)
    ES_API_KEY      - Optional API key for authentication

Prerequisites:
    The health index should exist. Create it with:
    
    PUT backfill_health_v1
    {
      "mappings": {
        "properties": {
          "index": { "type": "keyword" },
          "missing": { "type": "integer" },
          "with_dates": { "type": "integer" },
          "with_expires_at": { "type": "integer" },
          "ts": { "type": "date" }
        }
      }
    }
"""

import os
from datetime import datetime, timezone
from validate_backfill import es, count_missing_dates, counts_with_expiry

ES_HEALTH_INDEX = os.getenv("ES_HEALTH_INDEX", "backfill_health_v1")
ES_EMAIL_INDEX = os.getenv("ES_EMAIL_INDEX", "gmail_emails_v2")


def main():
    """
    Collect backfill health metrics and index them into Elasticsearch.
    
    This creates a time-series record that can be visualized in Kibana
    to track backfill health over time.
    """
    # Use the same ES client from validate_backfill
    client = es()
    
    # Collect current health metrics
    missing = count_missing_dates(client)
    total, with_exp = counts_with_expiry(client)
    
    # Create health document
    doc = {
        "index": ES_EMAIL_INDEX,
        "missing": missing,
        "with_dates": total,
        "with_expires_at": with_exp,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    
    # Index the document (using the same client)
    client.index(index=ES_HEALTH_INDEX, document=doc)
    
    print(f"Emitted backfill health: {doc}")


if __name__ == "__main__":
    main()
