"""
Backfill script to extract due dates from existing bill emails.

Uses the robust due_dates.py parser to extract dates from bills already
indexed in Elasticsearch. Updates dates[] and expires_at fields.

NOTE: Requires elasticsearch<9.0.0 for ES 8.x compatibility.
If you have elasticsearch==9.x installed, downgrade with:
    pip install "elasticsearch>=8.0.0,<9.0.0"

Usage:
    # Dry run (show what would be updated)
    DRY_RUN=1 ES_EMAIL_INDEX=gmail_emails_v2 python services/api/scripts/backfill_bill_dates.py

    # Execute updates
    DRY_RUN=0 ES_EMAIL_INDEX=gmail_emails_v2 python services/api/scripts/backfill_bill_dates.py
"""

import os
import sys
import datetime as dt
from typing import List, Dict, Any, Iterable

from elasticsearch import helpers

# Add app to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingest.due_dates import extract_due_dates
from app.utils.schema_guard import require_min_migration

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
ES_INDEX = os.getenv("ES_EMAIL_INDEX", "gmail_emails_v2")
BATCH = int(os.getenv("BATCH", "500"))
DRY_RUN = os.getenv("DRY_RUN", "1") == "1"


def es():
    """
    Create Elasticsearch client.

    Note: If using elasticsearch>=9.0.0 with ES 8.x server, you may encounter
    compatibility issues. Either downgrade client to 8.x or upgrade server to 9.x.
    """
    from elasticsearch import Elasticsearch as ES_Client

    api_key = os.getenv("ES_API_KEY")

    # Simple client creation - works with matching versions
    if api_key:
        return ES_Client(ES_URL, api_key=api_key)
    return ES_Client(ES_URL)


def scan_bills_missing_dates(client) -> Iterable[Dict[str, Any]]:
    """
    Scan all bill emails in the index.

    Returns documents with id, subject, body_text, received_at, dates, expires_at.
    """
    query = {"bool": {"filter": [{"term": {"category": "bills"}}]}}
    return helpers.scan(
        client,
        index=ES_INDEX,
        query={
            "query": query,
            "_source": [
                "id",
                "subject",
                "body_text",
                "received_at",
                "dates",
                "expires_at",
            ],
        },
        size=BATCH,
    )


def earliest(iso_list: List[str]) -> str | None:
    """Return earliest date from list of ISO timestamps."""
    if not iso_list:
        return None
    # ISO lex order matches chronological if all Z; safe here
    filtered = [x for x in iso_list if x]
    return sorted(filtered)[0] if filtered else None


def transform(doc: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Transform a document by extracting due dates.

    Returns dict with updated fields or None if no changes needed.
    """
    src = doc.get("_source", {})
    body = src.get("body_text") or ""
    subject = src.get("subject") or ""
    combined_text = f"{subject} {body}"

    recv = src.get("received_at") or dt.datetime.utcnow().replace(
        tzinfo=dt.timezone.utc
    ).isoformat().replace("+00:00", "Z")

    # Parse received_at into datetime
    if isinstance(recv, str):
        try:
            recv_dt = dt.datetime.fromisoformat(recv.replace("Z", "+00:00"))
        except Exception:
            recv_dt = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
    else:
        recv_dt = recv

    # Extract due dates using robust parser
    due = extract_due_dates(combined_text, recv_dt)

    if not due and src.get("dates"):
        # Nothing new extracted; use existing dates to recompute expires_at
        due = src.get("dates")

    if not due:
        # No dates found
        return None

    exp_old = src.get("expires_at")
    earliest_due = earliest(due)
    exp_new = exp_old

    # Update expires_at if:
    # 1. No existing expires_at, OR
    # 2. New earliest date is earlier than existing expires_at
    if earliest_due and (not exp_old or earliest_due < exp_old):
        exp_new = earliest_due

    # Check if anything changed
    existing_dates = src.get("dates") or []
    new_dates_set = sorted(list(set(due)))
    existing_dates_set = sorted(list(set(existing_dates)))

    if exp_new == exp_old and new_dates_set == existing_dates_set:
        # No changes needed
        return None

    # Build update doc
    out = {"dates": new_dates_set}
    if exp_new:
        out["expires_at"] = exp_new

    return out


def run():
    """Run the backfill job."""
    # Schema guard: Ensure database has required columns
    print("Checking database schema...")
    try:
        require_min_migration(
            "0012_add_emails_features_json", "email automation system fields"
        )
        print("✓ Database schema validation passed\n")
    except RuntimeError as e:
        print(f"❌ Schema validation failed:\n{e}", file=sys.stderr)
        sys.exit(1)

    # Re-read DRY_RUN in case it was changed via environment
    dry_run = os.getenv("DRY_RUN", "1") == "1"
    batch = int(os.getenv("BATCH", "500"))
    es_index = os.getenv("ES_EMAIL_INDEX", "gmail_emails_v2")

    client = es()
    to_update = []
    count = 0
    scanned = 0

    print(f"Starting backfill for index: {es_index}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print(f"Batch size: {batch}")
    print("-" * 60)

    for hit in scan_bills_missing_dates(client):
        scanned += 1
        upd = transform(hit)

        if upd:
            action = {
                "_op_type": "update",
                "_index": es_index,
                "_id": hit["_id"],
                "doc": upd,
            }
            to_update.append(action)

            if dry_run and len(to_update) <= 5:
                # Show first few updates in dry run
                print(f"Would update {hit['_id']}: {upd}")

        # Bulk update when batch is full
        if len(to_update) >= batch:
            if not dry_run:
                helpers.bulk(client, to_update)
            count += len(to_update)
            print(f"Processed {scanned} docs, updated {count} docs...")
            to_update.clear()

    # Final batch
    if to_update:
        if not dry_run:
            helpers.bulk(client, to_update)
        count += len(to_update)

    print("-" * 60)
    print(f"Backfill {'(DRY RUN) ' if dry_run else ''}completed.")
    print(f"Scanned: {scanned} bills")
    print(f"Updated: {count} bills")
    print(f"Unchanged: {scanned - count} bills")


if __name__ == "__main__":
    run()
