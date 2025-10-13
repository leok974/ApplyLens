"""
Export weakly-labeled training data from Elasticsearch.

It streams docs from ES (by received_at), applies high-precision rules
(from rules.py) to produce a weak_label, computes a few lightweight features,
and writes JSONL suitable for train_ml.py.

Usage:
    # Export 60 days of data with balanced classes
    python services/api/app/labeling/export_weak_labels.py \\
        --days 60 --limit 40000 --limit-per-cat 8000 \\
        --out /tmp/weak_labels.jsonl

    # Export all data (no time filter)
    python services/api/app/labeling/export_weak_labels.py \\
        --days 0 --out /tmp/all_weak_labels.jsonl

    # Include unlabeled emails (for "other" category)
    python services/api/app/labeling/export_weak_labels.py \\
        --days 60 --include-unlabeled --out /tmp/weak_with_other.jsonl
"""

from __future__ import annotations
import os
import sys
import json
import argparse
import re
from typing import Dict, Any, Iterable, Optional

import requests

# Local rules module
from .rules import rule_labels  # returns (category|None, reason)

DEFAULT_ES_URL = os.getenv("ES_URL", "http://localhost:9200")
DEFAULT_ES_INDEX = os.getenv("ES_EMAIL_INDEX", "emails_v1-000001")


def build_query(days: Optional[int]) -> Dict[str, Any]:
    """Build Elasticsearch query with optional time filter.

    Args:
        days: Lookback window in days, or None for all emails

    Returns:
        Elasticsearch query dict
    """
    if not days:
        return {"match_all": {}}
    return {"range": {"received_at": {"gte": f"now-{days}d"}}}


def open_jsonl(path: str):
    """Open JSONL file for writing with UTF-8 encoding."""
    return open(path, "w", encoding="utf-8")


def features_for(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Extract features from email document for ML model.

    Args:
        doc: Email document from Elasticsearch

    Returns:
        Dict with text and numeric features
    """
    subj = doc.get("subject", "") or ""
    body = doc.get("body_text", "") or ""
    text = f"{subj}\n{body}"

    urls = doc.get("urls") or []
    money_hits = 1 if any(x in text for x in ["$", "€", "£"]) else 0
    due_date_hit = 1 if re.search(r"\bdue\b", text, re.I) else 0
    sender_tf = 1  # placeholder; later compute true per-sender frequency

    return {
        "text": text,
        "url_count": len(urls),
        "money_hits": money_hits,
        "due_date_hit": due_date_hit,
        "sender_tf": sender_tf,
    }


def iter_es(
    es_url: str,
    index: str,
    query: Dict[str, Any],
    batch: int = 500,
) -> Iterable[Dict[str, Any]]:
    """
    Scroll through ES results yielding _source docs.

    Args:
        es_url: Elasticsearch base URL
        index: Index name
        query: Elasticsearch query
        batch: Batch size for scrolling

    Yields:
        Email documents from _source
    """
    search_body = {
        "size": batch,
        "query": query,
        "sort": [{"received_at": {"order": "desc"}}],
        "_source": True,
    }

    # Initial search with scroll
    response = requests.post(
        f"{es_url}/{index}/_search?scroll=2m", json=search_body, timeout=60
    )
    response.raise_for_status()

    data = response.json()
    scroll_id = data.get("_scroll_id")
    hits = data["hits"]["hits"]

    # Yield initial batch
    while hits:
        for hit in hits:
            yield hit["_source"]

        # Continue scrolling
        response = requests.post(
            f"{es_url}/_search/scroll",
            json={"scroll": "2m", "scroll_id": scroll_id},
            timeout=60,
        )
        response.raise_for_status()

        data = response.json()
        scroll_id = data.get("_scroll_id")
        hits = data["hits"]["hits"]


def export(
    es_url: str,
    index: str,
    out_path: str,
    days: Optional[int],
    limit: Optional[int],
    limit_per_cat: Optional[int],
    include_unlabeled: bool,
) -> Dict[str, Any]:
    """Export weakly-labeled training data from Elasticsearch.

    Args:
        es_url: Elasticsearch base URL
        index: Index name
        out_path: Output JSONL file path
        days: Lookback window in days (None = all)
        limit: Hard cap on total rows (None = no cap)
        limit_per_cat: Cap per category (None = no cap)
        include_unlabeled: Keep rows without rule-derived label

    Returns:
        Dict with export statistics
    """
    query = build_query(days)
    cat_counts = {}
    total_written = 0
    total_seen = 0

    print(f"🚀 Starting export from {index}")
    print(f"   Time window: {days} days" if days else "   Time window: all")
    print(f"   Output: {out_path}")
    print()

    with open_jsonl(out_path) as f:
        for doc in iter_es(es_url, index, query):
            total_seen += 1

            # Apply high-precision rules to get weak label
            category, reason = rule_labels(doc)

            # Optionally skip unlabeled examples
            if not include_unlabeled and not category:
                continue

            # Enforce per-category cap for class balance
            if category and limit_per_cat:
                if cat_counts.get(category, 0) >= limit_per_cat:
                    continue

            # Extract features
            features = features_for(doc)

            # Build training row
            row = {
                # Text for vectorizer
                "subject": doc.get("subject", ""),
                "body_text": doc.get("body_text", ""),
                # Identifiers + metadata
                "id": doc.get("id"),
                "sender_domain": doc.get("sender_domain"),
                "received_at": doc.get("received_at"),
                # Features used by train_ml.py
                "features": {
                    "url_count": features["url_count"],
                    "money_hits": features["money_hits"],
                    "due_date_hit": features["due_date_hit"],
                    "sender_tf": features["sender_tf"],
                },
                # Labels
                "weak_label": category or "other",
                "weak_reason": reason,
            }

            # Write to JSONL
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            total_written += 1

            if category:
                cat_counts[category] = cat_counts.get(category, 0) + 1

            # Progress indicator
            if total_written % 500 == 0:
                print(f"   Processed {total_written} documents...")

            # Hard limit check
            if limit and total_written >= limit:
                break

    print()
    print("✅ Export complete!")
    print(f"   Seen: {total_seen} documents")
    print(f"   Written: {total_written} documents")
    print()

    return {
        "seen": total_seen,
        "written": total_written,
        "by_category": cat_counts,
        "out": out_path,
        "days": days,
        "limit": limit,
        "limit_per_cat": limit_per_cat,
        "include_unlabeled": include_unlabeled,
    }


def main():
    """CLI entry point for weak label export."""
    parser = argparse.ArgumentParser(
        description="Export weakly-labeled JSONL from Elasticsearch.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export 60 days with balanced classes
  python export_weak_labels.py --days 60 --limit 40000 --limit-per-cat 8000

  # Export all data
  python export_weak_labels.py --days 0 --out all_labels.jsonl

  # Include unlabeled emails
  python export_weak_labels.py --days 60 --include-unlabeled
        """,
    )

    parser.add_argument(
        "--es-url",
        default=DEFAULT_ES_URL,
        help="Elasticsearch URL (default: %(default)s)",
    )
    parser.add_argument(
        "--index",
        default=DEFAULT_ES_INDEX,
        help="Elasticsearch index (default: %(default)s)",
    )
    parser.add_argument(
        "--out",
        default="weak_labels.jsonl",
        help="Output JSONL file path (default: %(default)s)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="Lookback window in days (0 = all) (default: %(default)s)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Hard cap on total rows (0 = no cap) (default: %(default)s)",
    )
    parser.add_argument(
        "--limit-per-cat",
        type=int,
        default=2000,
        help="Cap per category for balance (0 = no cap) (default: %(default)s)",
    )
    parser.add_argument(
        "--include-unlabeled",
        action="store_true",
        help="Keep rows without rule-derived label (weak_label=other)",
    )

    args = parser.parse_args()

    # Normalize arguments
    limit = args.limit if args.limit and args.limit > 0 else None
    limit_per_cat = (
        args.limit_per_cat if args.limit_per_cat and args.limit_per_cat > 0 else None
    )
    days = args.days if args.days and args.days > 0 else None

    # Run export
    try:
        stats = export(
            es_url=args.es_url,
            index=args.index,
            out_path=args.out,
            days=days,
            limit=limit,
            limit_per_cat=limit_per_cat,
            include_unlabeled=args.include_unlabeled,
        )

        # Print final statistics
        print("📊 Export Statistics:")
        print(json.dumps(stats, indent=2))

    except Exception as e:
        print(f"\n❌ Export failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
