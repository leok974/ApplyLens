import time
from datetime import datetime, timedelta, timezone
from elasticsearch import Elasticsearch
import os

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
INDEX = os.getenv("ES_ALIAS", "gmail_emails")

def seed_doc(es, subject, labels=None, days_ago=0, body="Body", sender="hr@company.com"):
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    return es.index(
        index=INDEX,
        document={
            "subject": subject,
            "body_text": body,
            "sender": sender,
            "to": "leo@example.com",
            "labels": labels or [],
            "received_at": ts,
            "thread_id": f"t-{subject}",
            "message_id": f"m-{subject}-{ts}",
        },
        refresh=True,
    )

def test_label_boost_and_recency(client):
    es = Elasticsearch(ES_URL)

    # Seed: same subject tokens so text relevance ties, label and recency decide
    seed_doc(es, "Interview schedule", labels=["interview"], days_ago=10)
    seed_doc(es, "Offer package details", labels=["offer"], days_ago=14)
    seed_doc(es, "Application update", labels=["rejection"], days_ago=1)
    seed_doc(es, "Application update", labels=[], days_ago=0)  # recent neutral

    r = client.get("/search", params={"q": "application update"})
    assert r.status_code == 200
    data = r.json()["hits"]
    # Expect recent neutral to outrank rejection; offer/interview may not match query text
    ids_by_label = [(h["labels"], h["score"]) for h in data]
    # sanity: rejection shouldn't beat the fresh neutral for same text
    scores = {tuple(h["labels"]): h["score"] for h in data}
    assert scores.get(("rejection",), -1) <= scores.get((), 0)
