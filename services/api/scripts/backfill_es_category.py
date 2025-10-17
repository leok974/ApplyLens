#!/usr/bin/env python3
"""
Backfill Elasticsearch category field from Gmail labels.

This script updates Elasticsearch documents to populate the category field
based on Gmail CATEGORY_* labels, similar to the database migration backfill.

Usage:
    ES_URL=http://localhost:9200 ES_EMAIL_INDEX=gmail_emails_v2 \\
        python scripts/backfill_es_category.py
"""

import os
import sys

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from elasticsearch import Elasticsearch

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
ES_INDEX = os.getenv("ES_EMAIL_INDEX", "gmail_emails_v2")


def es_client():
    """Create Elasticsearch client."""
    api_key = os.getenv("ES_API_KEY")
    if api_key:
        return Elasticsearch(ES_URL, api_key=api_key)
    return Elasticsearch(ES_URL)


def backfill_category():
    """
    Backfill category field in Elasticsearch from Gmail labels.

    Maps Gmail CATEGORY_* labels to category values:
    - CATEGORY_PROMOTIONS → promotions
    - CATEGORY_SOCIAL → social
    - CATEGORY_UPDATES → updates
    - CATEGORY_FORUMS → forums
    - CATEGORY_PERSONAL → personal
    """
    client = es_client()

    print(f"Backfilling category field in {ES_INDEX}...")
    print(f"ES URL: {ES_URL}")
    print("-" * 60)

    # Use Painless script to set category from labels
    # This is the same logic as the database migration
    script = """
        if (ctx._source.category == null || ctx._source.category == '') {
            def labels = ctx._source.containsKey('labels') ? ctx._source.labels : [];
            if (labels != null && labels.size() > 0) {
                if (labels.contains('CATEGORY_PROMOTIONS')) {
                    ctx._source.category = 'promotions';
                } else if (labels.contains('CATEGORY_SOCIAL')) {
                    ctx._source.category = 'social';
                } else if (labels.contains('CATEGORY_UPDATES')) {
                    ctx._source.category = 'updates';
                } else if (labels.contains('CATEGORY_FORUMS')) {
                    ctx._source.category = 'forums';
                } else if (labels.contains('CATEGORY_PERSONAL')) {
                    ctx._source.category = 'personal';
                }
            }
        }
    """

    # Update all documents that don't have a category
    body = {
        "script": {"lang": "painless", "source": script},
        "query": {"bool": {"must_not": {"exists": {"field": "category"}}}},
    }

    try:
        response = client.update_by_query(
            index=ES_INDEX,
            body=body,
            conflicts="proceed",
            wait_for_completion=True,
            refresh=True,
        )

        print("✓ Update complete:")
        print(f"  Total documents: {response.get('total', 0)}")
        print(f"  Updated: {response.get('updated', 0)}")
        print(f"  Failed: {response.get('failures', [])}")
        print(f"  Version conflicts: {response.get('version_conflicts', 0)}")

        if response.get("failures"):
            print("\n⚠ Some updates failed:")
            for failure in response.get("failures", [])[:5]:  # Show first 5
                print(f"  - {failure}")

        return response.get("updated", 0)

    except Exception as e:
        print(f"✗ Error updating documents: {e}")
        import traceback

        traceback.print_exc()
        return 0


def verify_backfill():
    """Verify category backfill by counting documents with category."""
    client = es_client()

    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    # Count documents with category field
    response = client.count(
        index=ES_INDEX, body={"query": {"exists": {"field": "category"}}}
    )
    with_category = response["count"]

    # Count total documents
    total_response = client.count(index=ES_INDEX)
    total = total_response["count"]

    print(f"Documents with category: {with_category} / {total}")

    if with_category > 0:
        # Show category breakdown
        # Try keyword field first, fallback to text field if needed
        try:
            agg_response = client.search(
                index=ES_INDEX,
                body={
                    "size": 0,
                    "aggs": {
                        "categories": {
                            "terms": {
                                "field": "category.keyword",  # Try keyword subfield first
                                "size": 10,
                            }
                        }
                    },
                },
            )

            buckets = agg_response["aggregations"]["categories"]["buckets"]
            if buckets:
                print("\nCategory breakdown:")
                for bucket in buckets:
                    print(f"  - {bucket['key']}: {bucket['doc_count']} documents")
        except Exception as e:
            print(f"\n⚠ Could not aggregate by category: {str(e)[:100]}")
            print(
                "  (category field may need to be mapped as keyword for aggregations)"
            )


def main():
    """Run backfill and verification."""
    print("\n" + "=" * 60)
    print("Elasticsearch Category Backfill")
    print("=" * 60)

    updated = backfill_category()

    if updated > 0:
        print(f"\n✓ Successfully backfilled category for {updated} documents")
    else:
        print("\n⚠ No documents were updated (may already have category)")

    verify_backfill()

    print("\n" + "=" * 60)
    print("Backfill complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
