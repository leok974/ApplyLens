from elasticsearch import Elasticsearch

es = Elasticsearch("http://es:9200")

total = es.count(index="gmail_emails")["count"]
print("Total emails:", total)

if total == 0:
    raise SystemExit("No emails in gmail_emails index")

resp = es.search(
    index="gmail_emails",
    body={
        "size": 0,
        "aggs": {"users": {"terms": {"field": "user_id.keyword", "size": 20}}},
    },
)

print("\nuser_id → doc_count:")
for bucket in resp["aggregations"]["users"]["buckets"]:
    print(f"- {bucket['key']}: {bucket['doc_count']}")
