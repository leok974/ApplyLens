"""
Money Router - Phase 6: Receipt tracking and export

Endpoints:
- GET /money/receipts.csv - Export receipts as CSV
- GET /money/duplicates - Find duplicate charges
- GET /money/summary - Spending summary
"""

import os
from datetime import datetime
from typing import Any, Dict

from elasticsearch import Elasticsearch
from fastapi import APIRouter, Depends, HTTPException, Response

from ..core.money import (build_receipts_csv, detect_duplicates,
                          summarize_spending)

router = APIRouter(prefix="/money", tags=["money"])

# Elasticsearch connection
ES_URL = os.getenv("ES_URL", "http://localhost:9200")


def get_es():
    """Get Elasticsearch client."""
    try:
        return Elasticsearch(ES_URL)
    except Exception as e:
        raise HTTPException(503, f"Elasticsearch not available: {e}")


def get_current_user():
    """Get current user (stub - replace with actual auth)."""
    return type("User", (), {"email": "user@example.com"})()


@router.get("/receipts.csv")
def receipts_csv(es=Depends(get_es), user=Depends(get_current_user)):
    """
    Export all receipt emails as CSV.

    Finds emails that match receipt heuristics:
    - Subject contains: receipt, invoice, order, payment
    - Category is finance
    - Sender is known payment processor

    Returns:
        CSV file with columns: date, merchant, amount, email_id, subject, category
    """
    # Build query for receipt emails
    query = {
        "bool": {
            "should": [
                {"match_phrase": {"subject": "receipt"}},
                {"match_phrase": {"subject": "invoice"}},
                {"match_phrase": {"subject": "order"}},
                {"match_phrase": {"subject": "payment"}},
                {"match_phrase": {"subject": "purchase"}},
                {"term": {"category": "finance"}},
            ],
            "minimum_should_match": 1,
        }
    }

    try:
        # Fetch receipts (limit to 2000 for CSV export)
        res = es.search(
            index="emails",
            body={"size": 2000, "query": query},
            _source=[
                "id",
                "subject",
                "sender",
                "sender_domain",
                "received_at",
                "category",
                "body_text",
            ],
        )

        # Extract documents
        docs = []
        for hit in res["hits"]["hits"]:
            doc = {"id": hit["_id"], **hit["_source"]}
            docs.append(doc)

        # Build CSV
        csv_data = build_receipts_csv(docs)

        # Return as downloadable file
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=receipts_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            },
        )

    except Exception as e:
        raise HTTPException(500, f"Failed to export receipts: {str(e)}")


@router.get("/duplicates")
def find_duplicates(
    window_days: int = 7, es=Depends(get_es), user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Find potential duplicate charges.

    A duplicate is defined as:
    - Same merchant (sender_domain)
    - Same amount
    - Within N days of each other

    Args:
        window_days: Time window for duplicate detection (default 7 days)

    Returns:
        {
            "duplicates": [
                {
                    "merchant": "amazon.com",
                    "amount": 49.99,
                    "earlier": {...},
                    "later": {...},
                    "days_apart": 2
                }
            ],
            "count": 5
        }
    """
    # Build query for receipt emails
    query = {
        "bool": {
            "should": [
                {"match_phrase": {"subject": "receipt"}},
                {"match_phrase": {"subject": "invoice"}},
                {"term": {"category": "finance"}},
            ],
            "minimum_should_match": 1,
        }
    }

    try:
        # Fetch receipts
        res = es.search(
            index="emails",
            body={"size": 1000, "query": query, "sort": [{"received_at": "desc"}]},
            _source=["id", "subject", "sender_domain", "received_at", "body_text"],
        )

        # Extract documents and parse
        docs = []
        for hit in res["hits"]["hits"]:
            doc = {"id": hit["_id"], **hit["_source"]}
            docs.append(doc)

        # Detect duplicates
        dup_pairs = detect_duplicates(docs, window_days=window_days)

        # Format response
        duplicates = []
        for earlier, later in dup_pairs:
            date1 = earlier.get("received_at") or ""
            date2 = later.get("received_at") or ""

            if isinstance(date1, str):
                date1 = datetime.fromisoformat(date1.replace("Z", "+00:00"))
            if isinstance(date2, str):
                date2 = datetime.fromisoformat(date2.replace("Z", "+00:00"))

            days_apart = abs((date2 - date1).days) if date1 and date2 else 0

            duplicates.append(
                {
                    "merchant": earlier.get("sender_domain") or earlier.get("sender"),
                    "amount": earlier.get("amount"),
                    "earlier": {
                        "id": earlier.get("id"),
                        "subject": earlier.get("subject"),
                        "date": earlier.get("received_at"),
                    },
                    "later": {
                        "id": later.get("id"),
                        "subject": later.get("subject"),
                        "date": later.get("received_at"),
                    },
                    "days_apart": days_apart,
                }
            )

        return {
            "duplicates": duplicates,
            "count": len(duplicates),
            "window_days": window_days,
        }

    except Exception as e:
        raise HTTPException(500, f"Failed to find duplicates: {str(e)}")


@router.get("/summary")
def spending_summary(
    es=Depends(get_es), user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get spending summary from receipt emails.

    Returns:
        {
            "total_amount": 1234.56,
            "count": 42,
            "by_merchant": {"amazon.com": 500.0, "uber.com": 234.56},
            "by_month": {"2025-10": 800.0, "2025-09": 434.56},
            "avg_amount": 29.39
        }
    """
    # Build query for receipt emails
    query = {
        "bool": {
            "should": [
                {"match_phrase": {"subject": "receipt"}},
                {"match_phrase": {"subject": "invoice"}},
                {"term": {"category": "finance"}},
            ],
            "minimum_should_match": 1,
        }
    }

    try:
        # Fetch receipts
        res = es.search(
            index="emails",
            body={"size": 2000, "query": query},
            _source=["id", "sender_domain", "received_at", "body_text"],
        )

        # Extract documents
        docs = []
        for hit in res["hits"]["hits"]:
            doc = {"id": hit["_id"], **hit["_source"]}
            docs.append(doc)

        # Generate summary
        summary = summarize_spending(docs)

        return summary

    except Exception as e:
        raise HTTPException(500, f"Failed to generate summary: {str(e)}")
