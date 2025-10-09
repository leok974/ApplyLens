"""
Backfill first/last user reply and reply count for existing emails.
Requires:
  - DATABASE_URL (SQLAlchemy URL)
  - ES_URL (defaults http://localhost:9200)
  - ES_ALIAS (defaults gmail_emails)
  - GMAIL_PRIMARY_ADDRESS (user's email address)
  
Usage:
  python -m services.api.scripts.backfill_reply_metrics
"""
import os
import sys
from collections import defaultdict
from datetime import datetime
from sqlalchemy import create_engine, text
from elasticsearch import Elasticsearch

# Import the metrics computation module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.ingest.gmail_metrics import compute_thread_reply_metrics

DB_URL = os.getenv("DATABASE_URL")
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
ES_ALIAS = os.getenv("ES_ALIAS", "gmail_emails")
USER_EMAIL = (os.getenv("GMAIL_PRIMARY_ADDRESS") or os.getenv("DEFAULT_USER_EMAIL") or "").lower()

def main():
    if not DB_URL:
        raise SystemExit("DATABASE_URL not set")
    if not USER_EMAIL:
        raise SystemExit("GMAIL_PRIMARY_ADDRESS or DEFAULT_USER_EMAIL not set")
    
    print(f"Backfilling reply metrics for user: {USER_EMAIL}")
    print(f"Database: {DB_URL}")
    print(f"Elasticsearch: {ES_URL}/{ES_ALIAS}")
    
    eng = create_engine(DB_URL)
    es = Elasticsearch(ES_URL)

    # Pull minimal fields needed: id, thread_id, gmail_id, raw
    print("\n1. Loading emails from database...")
    rows = []
    with eng.connect() as c:
        res = c.execute(text("SELECT id, thread_id, gmail_id, raw FROM emails WHERE raw IS NOT NULL"))
        for r in res:
            rows.append({
                "id": r.id, 
                "thread_id": r.thread_id, 
                "gmail_id": r.gmail_id, 
                "raw": r.raw
            })
    
    print(f"   Loaded {len(rows)} emails")

    # Group by thread
    print("\n2. Grouping by thread...")
    by_thread = defaultdict(list)
    row_by_thread = defaultdict(list)
    for r in rows:
        by_thread[r["thread_id"]].append(r["raw"])
        row_by_thread[r["thread_id"]].append(r)
    
    print(f"   Found {len(by_thread)} unique threads")

    # Compute metrics per thread
    print("\n3. Computing reply metrics per thread...")
    updates = []
    thread_metrics = {}
    for thread_id, msgs in by_thread.items():
        metrics = compute_thread_reply_metrics(msgs, USER_EMAIL)
        thread_metrics[thread_id] = metrics
        
        # Update all rows within thread (denormalized)
        for r in row_by_thread[thread_id]:
            updates.append({
                "id": r["id"],
                "first": metrics["first_user_reply_at"],
                "last": metrics["last_user_reply_at"],
                "cnt": metrics["user_reply_count"],
            })
    
    print(f"   Computed metrics for {len(thread_metrics)} threads")
    print(f"   Will update {len(updates)} email records")

    # DB apply
    print("\n4. Updating database...")
    with eng.begin() as c:
        for i, u in enumerate(updates):
            c.execute(
                text(
                    """
                    UPDATE emails
                    SET first_user_reply_at = :first,
                        last_user_reply_at  = :last,
                        user_reply_count    = :cnt
                    WHERE id=:id
                    """
                ),
                u,
            )
            if (i + 1) % 100 == 0:
                print(f"   Updated {i + 1}/{len(updates)} records...")
    
    print(f"   ✓ Database updated")

    # ES apply (update by query per thread)
    print("\n5. Updating Elasticsearch...")
    es_updated = 0
    for i, (thread_id, metrics) in enumerate(thread_metrics.items()):
        try:
            result = es.update_by_query(
                index=ES_ALIAS,
                body={
                    "script": {
                        "source": """
                          ctx._source.first_user_reply_at = params.first;
                          ctx._source.last_user_reply_at  = params.last;
                          ctx._source.user_reply_count    = params.cnt;
                          ctx._source.replied             = (params.cnt != null && params.cnt > 0);
                        """,
                        "params": {
                            "first": metrics["first_user_reply_at"],
                            "last": metrics["last_user_reply_at"],
                            "cnt": metrics["user_reply_count"],
                        },
                    },
                    "query": {"term": {"thread_id": thread_id}},
                },
                refresh=False,
            )
            es_updated += result.get("updated", 0)
            
            if (i + 1) % 100 == 0:
                print(f"   Processed {i + 1}/{len(thread_metrics)} threads...")
        except Exception as e:
            print(f"   Warning: Failed to update thread {thread_id}: {e}")
            continue
    
    # Final refresh
    es.indices.refresh(index=ES_ALIAS)
    print(f"   ✓ Elasticsearch updated ({es_updated} documents)")

    print("\n✅ Backfill complete!")
    print(f"\nSummary:")
    print(f"  - {len(rows)} emails processed")
    print(f"  - {len(thread_metrics)} threads analyzed")
    print(f"  - {len(updates)} database records updated")
    print(f"  - {es_updated} Elasticsearch documents updated")

if __name__ == "__main__":
    main()
