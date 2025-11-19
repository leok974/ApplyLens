from datetime import datetime, timedelta
from elasticsearch import Elasticsearch

es = Elasticsearch("http://es:9200")

USER_ID = "leoklemet.pa@gmail.com"


def run_basic_search(days: int | None = None, query_text: str = ""):
    must = []
    filters = [{"match": {"user_id": USER_ID}}]

    # Same as tool: no query => match all
    if query_text and query_text != "*":
        must.append(
            {
                "multi_match": {
                    "query": query_text,
                    "fields": ["subject^3", "body_text"],
                }
            }
        )
    else:
        must.append({"match_all": {}})

    if days is not None:
        now = datetime.utcnow()
        gte = (now - timedelta(days=days)).isoformat()
        filters.append({"range": {"received_at": {"gte": gte}}})

    body = {
        "query": {"bool": {"must": must, "filter": filters}},
        "sort": [{"received_at": "desc"}],
        "size": 5,
    }

    print("ES query:", body)
    res = es.search(index="gmail_emails", body=body)
    total = res["hits"]["total"]["value"]
    print(f"total hits: {total}")

    for h in res["hits"]["hits"]:
        src = h["_source"]
        print(
            "-",
            src.get("received_at"),
            "|",
            src.get("sender"),
            "→",
            src.get("subject"),
        )
    return total


if __name__ == "__main__":
    print("=== All emails for user ===")
    run_basic_search(days=None)

    print("\n=== Last 7 days ===")
    count_7d = run_basic_search(days=7)

    print("\n=== Last 30 days ===")
    count_30d = run_basic_search(days=30)

    print("\n=== Latest email timestamp ===")
    latest = es.search(
        index="gmail_emails",
        body={
            "query": {"match": {"user_id": USER_ID}},
            "sort": [{"received_at": {"order": "desc"}}],
            "size": 1,
        },
    )
    if latest["hits"]["hits"]:
        latest_date = latest["hits"]["hits"][0]["_source"]["received_at"]
        print(f"Most recent email: {latest_date}")
