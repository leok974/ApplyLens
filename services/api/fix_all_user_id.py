from elasticsearch import Elasticsearch

es = Elasticsearch("http://es:9200")

# Update ALL documents, not just those missing user_id
resp = es.update_by_query(
    index="gmail_emails",
    body={
        "script": {
            "source": "ctx._source.user_id = params.user_id",
            "lang": "painless",
            "params": {"user_id": "leoklemet.pa@gmail.com"},
        },
        "query": {"match_all": {}},
    },
    conflicts="proceed",
    refresh=True,
    wait_for_completion=True,
)

print(f"Updated: {resp.get('updated', 0)}")
print(f"Total: {resp.get('total', 0)}")
print(f"Failures: {resp.get('failures', [])}")

# Verify
count = es.count(
    index="gmail_emails",
    body={"query": {"term": {"user_id": "leoklemet.pa@gmail.com"}}},
)["count"]
print(f"\nVerification: {count} emails have user_id=leoklemet.pa@gmail.com")
