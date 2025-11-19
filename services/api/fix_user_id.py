from elasticsearch import Elasticsearch

es = Elasticsearch("http://es:9200")

# Add user_id to all documents that don't have it
resp = es.update_by_query(
    index="gmail_emails",
    body={
        "script": {
            "source": "ctx._source.user_id = params.user_id",
            "lang": "painless",
            "params": {"user_id": "leoklemet.pa@gmail.com"},
        },
        "query": {"bool": {"must_not": {"exists": {"field": "user_id"}}}},
    },
    conflicts="proceed",
    refresh=True,
)

print(f"Updated {resp.get('updated', 0)} documents")
print(f"Total: {resp.get('total', 0)}")

# Verify
count = es.count(
    index="gmail_emails",
    body={"query": {"term": {"user_id": "leoklemet.pa@gmail.com"}}},
)["count"]
print(f"\nVerification: {count} emails now have user_id=leoklemet.pa@gmail.com")
