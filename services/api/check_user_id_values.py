from elasticsearch import Elasticsearch

es = Elasticsearch("http://es:9200")

# Aggregate by user_id
resp = es.search(
    index="gmail_emails",
    body={
        "size": 0,
        "aggs": {"users": {"terms": {"field": "user_id", "size": 10}}},
    },
)

print("user_id values:")
for b in resp["aggregations"]["users"]["buckets"]:
    print(f"- {b['key']}: {b['doc_count']}")

# Get a sample with user_id
hit = es.search(
    index="gmail_emails", body={"size": 1, "query": {"exists": {"field": "user_id"}}}
)["hits"]["hits"][0]

print(f"\nSample user_id value: '{hit['_source']['user_id']}'")
print(f"Type: {type(hit['_source']['user_id'])}")
