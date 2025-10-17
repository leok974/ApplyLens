"""
Recreate index with ATS search-time synonyms, then reindex and swap the alias.
Usage:
  UVICORN or Docker not required. Just run:
     python -m services.api.scripts.es_reindex_with_ats
"""

from elasticsearch import Elasticsearch
import os

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
ALIAS = os.getenv("ES_ALIAS", "gmail_emails")
NEW_INDEX = f"{ALIAS}_v{os.getenv('ES_VERSION_TAG','2')}"
OLD_INDEX_FALLBACK = os.getenv("ES_OLD_INDEX", "gmail_emails")

SETTINGS = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "filter": {
                "ats_synonyms": {
                    "type": "synonym",
                    "lenient": True,
                    "synonyms": [
                        "lever, lever.co, hire.lever.co",
                        "workday, myworkdayjobs, wd1.myworkday, wd2.myworkday, wd3.myworkday, wd5.myworkday",
                        "smartrecruiters, smartrecruiters.com, sr.job",
                    ],
                }
            },
            "analyzer": {
                "ats_search_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "ats_synonyms"],
                }
            },
        },
    },
    "mappings": {
        "properties": {
            "subject": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "ats_search_analyzer",
            },
            "body_text": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "ats_search_analyzer",
            },
            "sender": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "ats_search_analyzer",
            },
            "to": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "ats_search_analyzer",
            },
            "labels": {"type": "keyword"},
            "received_at": {"type": "date"},
            "first_user_reply_at": {"type": "date"},
            "last_user_reply_at": {"type": "date"},
            "user_reply_count": {"type": "integer"},
            "replied": {"type": "boolean"},
            "thread_id": {"type": "keyword"},
            "message_id": {"type": "keyword"},
        }
    },
}


def main():
    es = Elasticsearch(ES_URL)

    # Resolve the current concrete index behind the alias if present.
    src_index = OLD_INDEX_FALLBACK
    try:
        a = es.indices.get_alias(name=ALIAS, ignore=[404])
        if a and isinstance(a, dict) and 404 not in a:
            src_index = list(a.keys())[0]
    except Exception:
        pass

    # Create the new index
    if es.indices.exists(index=NEW_INDEX):
        es.indices.delete(index=NEW_INDEX, ignore=[404])
    es.indices.create(index=NEW_INDEX, body=SETTINGS)

    # Reindex
    es.reindex(
        body={"source": {"index": src_index}, "dest": {"index": NEW_INDEX}},
        wait_for_completion=True,
        refresh=True,
    )

    # Swap alias atomically
    actions = []
    try:
        a = es.indices.get_alias(name=ALIAS, ignore=[404])
        if a and isinstance(a, dict) and 404 not in a:
            old = list(a.keys())[0]
            actions.append({"remove": {"index": old, "alias": ALIAS}})
    except Exception:
        pass
    actions.append({"add": {"index": NEW_INDEX, "alias": ALIAS}})
    es.indices.update_aliases(body={"actions": actions})
    print(f"Alias {ALIAS} -> {NEW_INDEX} (from {src_index})")


if __name__ == "__main__":
    main()
