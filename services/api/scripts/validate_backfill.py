#!/usr/bin/env python3
"""
Validate backfill results for bill due dates.

Queries Elasticsearch to verify:
1. Bills missing dates[] field
2. Bills with dates[] populated
3. Bills with expires_at field set

Usage:
    python validate_backfill.py --pretty       # Human-readable output
    python validate_backfill.py --json         # Machine-readable JSON

Environment variables:
    ES_URL          - Elasticsearch URL (default: http://localhost:9200)
    ES_EMAIL_INDEX  - Email index name (default: gmail_emails_v2)
    ES_API_KEY      - Optional API key for authentication
"""

import os
import json
import argparse
from datetime import datetime, timezone
from elasticsearch import Elasticsearch

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
INDEX = os.getenv("ES_EMAIL_INDEX", "gmail_emails_v2")


def es():
    """Create Elasticsearch client."""
    api_key = os.getenv("ES_API_KEY")
    if api_key:
        return Elasticsearch(ES_URL, api_key=api_key)
    return Elasticsearch(ES_URL)


def count_missing_dates(client) -> int:
    """Count bills that don't have dates[] field."""
    query = {
        "bool": {
            "filter": [{"term": {"category": "bills"}}],
            "must_not": [{"exists": {"field": "dates"}}],
        }
    }
    res = client.count(index=INDEX, body={"query": query})
    return int(res.get("count", 0))


def counts_with_expiry(client) -> tuple[int, int]:
    """
    Count bills with dates[] and expires_at.

    Returns:
        (total_with_dates, total_with_expires_at)
    """
    # Total bills with any dates[]
    query_total = {
        "bool": {
            "filter": [{"term": {"category": "bills"}}, {"exists": {"field": "dates"}}]
        }
    }

    # Subset where expires_at exists
    query_expiry = {
        "bool": {
            "filter": [
                {"term": {"category": "bills"}},
                {"exists": {"field": "dates"}},
                {"exists": {"field": "expires_at"}},
            ]
        }
    }

    total = client.count(index=INDEX, body={"query": query_total}).get("count", 0)
    with_exp = client.count(index=INDEX, body={"query": query_expiry}).get("count", 0)

    return int(total), int(with_exp)


def main():
    """Run validation and output results."""
    parser = argparse.ArgumentParser(description="Validate backfill results")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    parser.add_argument("--pretty", action="store_true", help="Pretty print summary")
    args = parser.parse_args()

    client = es()
    missing = count_missing_dates(client)
    total_with_dates, with_exp = counts_with_expiry(client)

    # Determine verdict: OK if no missing dates, and expiry count is reasonable
    verdict = "OK" if missing == 0 and 0 <= with_exp <= total_with_dates else "CHECK"

    result = {
        "index": INDEX,
        "missing_dates_count": missing,
        "bills_with_dates": total_with_dates,
        "bills_with_expires_at": with_exp,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": verdict,
    }

    if args.json and not args.pretty:
        # Pure JSON output (machine-readable)
        print(json.dumps(result))
        return

    # Human-readable output (default or --pretty)
    print(f"Index: {result['index']}")
    print(f"Missing dates[] (bills): {missing}")
    print(f"Bills with dates[]:      {total_with_dates}")
    print(f"Bills with expires_at:   {with_exp}")
    print(f"Verdict: {result['verdict']}  @ {result['timestamp']}")


if __name__ == "__main__":
    main()
