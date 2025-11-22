from elasticsearch import Elasticsearch

es = Elasticsearch("http://es:9200")

# Get a sample document
hit = es.search(index="gmail_emails", body={"size": 1})["hits"]["hits"][0]
doc = hit["_source"]

print("Sample document fields:")
print(f"- _id: {hit['_id']}")
print(f"- user_id: {doc.get('user_id', 'NOT FOUND')}")
print(f"- from: {doc.get('from', doc.get('sender', 'NOT FOUND'))}")
print(f"- to: {doc.get('to', 'NOT FOUND')}")
print(f"- subject: {doc.get('subject', 'NOT FOUND')}")
print(f"- received_at: {doc.get('received_at', 'NOT FOUND')}")

print("\nAll fields in doc:")
for k, v in doc.items():
    print(f"- {k}: {type(v).__name__}")
