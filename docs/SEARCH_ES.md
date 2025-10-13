# Search & Elasticsearch

This document covers Elasticsearch configuration, index mappings, search queries, and relevance tuning for ApplyLens.

## Elasticsearch Setup

### Version

ApplyLens uses **Elasticsearch 8.x** (currently 8.11).

### Docker Configuration

```yaml
# infra/docker-compose.yml
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
    - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
  ports:
    - "9200:9200"
  volumes:
    - es_data:/usr/share/elasticsearch/data
```

## Index Configuration

### Index Name

- **Alias:** `emails_v1`
- **Physical Index:** `emails_v1-000001`

Using aliases allows zero-downtime reindexing.

### Mapping

```json
PUT /emails_v1-000001
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "analyzer": {
        "email_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "stop", "porter_stem"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "gmail_message_id": {
        "type": "keyword"
      },
      "subject": {
        "type": "text",
        "analyzer": "email_analyzer",
        "fields": {
          "keyword": {
            "type": "keyword",
            "ignore_above": 256
          }
        }
      },
      "sender": {
        "type": "keyword"
      },
      "sender_domain": {
        "type": "keyword"
      },
      "body": {
        "type": "text",
        "analyzer": "email_analyzer"
      },
      "received_at": {
        "type": "date",
        "format": "strict_date_optional_time||epoch_millis"
      },
      "category": {
        "type": "keyword"
      },
      "risk_score": {
        "type": "float"
      },
      "is_quarantined": {
        "type": "boolean"
      },
      "user_id": {
        "type": "keyword"
      }
    }
  }
}
```

### Analyzers

**email_analyzer:**

- **Tokenizer:** `standard` (splits on whitespace and punctuation)
- **Filters:**
  - `lowercase` - Normalize case
  - `stop` - Remove common words (the, a, an)
  - `porter_stem` - Stemming (running → run)

## Search Queries

### Full-Text Search

```python
# services/api/app/services/es_service.py

def search_emails(query: str, user_id: str, filters: dict):
    body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["subject^2", "body"],  # Boost subject 2x
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    {
                        "term": {"user_id": user_id}
                    }
                ],
                "filter": []
            }
        },
        "sort": [
            {"received_at": {"order": "desc"}}
        ],
        "from": filters.get("offset", 0),
        "size": filters.get("limit", 20)
    }
    
    # Add optional filters
    if filters.get("category"):
        body["query"]["bool"]["filter"].append({
            "term": {"category": filters["category"]}
        })
    
    if filters.get("sender_domain"):
        body["query"]["bool"]["filter"].append({
            "term": {"sender_domain": filters["sender_domain"]}
        })
    
    if filters.get("date_from"):
        body["query"]["bool"]["filter"].append({
            "range": {"received_at": {"gte": filters["date_from"]}}
        })
    
    return es_client.search(index="emails_v1", body=body)
```

### Aggregations (Facets)

```python
def get_facets(user_id: str):
    body = {
        "query": {
            "term": {"user_id": user_id}
        },
        "size": 0,  # Don't return documents
        "aggs": {
            "by_category": {
                "terms": {
                    "field": "category",
                    "size": 10
                }
            },
            "by_sender_domain": {
                "terms": {
                    "field": "sender_domain",
                    "size": 20
                }
            },
            "risk_histogram": {
                "histogram": {
                    "field": "risk_score",
                    "interval": 10,
                    "min_doc_count": 0
                }
            }
        }
    }
    
    result = es_client.search(index="emails_v1", body=body)
    
    return {
        "categories": result["aggregations"]["by_category"]["buckets"],
        "sender_domains": result["aggregations"]["by_sender_domain"]["buckets"],
        "risk_distribution": result["aggregations"]["risk_histogram"]["buckets"]
    }
```

## Relevance Tuning

### Field Boosting

- **Subject:** 2x boost (more important than body)
- **Sender:** Use exact match (keyword field)
- **Body:** Full-text with stemming

### Fuzziness

```json
{
  "multi_match": {
    "query": "sofware engineer",  // typo: sofware
    "fuzziness": "AUTO",           // Will match "software engineer"
    "prefix_length": 2             // First 2 chars must match exactly
  }
}
```

### Function Score

Boost recent emails:

```python
{
    "function_score": {
        "query": { "match": {"body": query} },
        "functions": [
            {
                "exp": {
                    "received_at": {
                        "origin": "now",
                        "scale": "7d",
                        "decay": 0.5
                    }
                }
            }
        ],
        "boost_mode": "multiply"
    }
}
```

## Indexing Strategy

### Initial Bulk Index

```python
from elasticsearch import helpers

def bulk_index_emails(emails: List[dict]):
    actions = [
        {
            "_index": "emails_v1",
            "_id": email["id"],
            "_source": email
        }
        for email in emails
    ]
    
    helpers.bulk(es_client, actions, chunk_size=500)
```

### Incremental Updates

```python
def index_email(email: dict):
    es_client.index(
        index="emails_v1",
        id=email["id"],
        document=email
    )
```

### Delete by Query

```python
def delete_quarantined_emails():
    es_client.delete_by_query(
        index="emails_v1",
        body={
            "query": {
                "term": {"is_quarantined": True}
            }
        }
    )
```

## Reindexing

### Zero-Downtime Reindex

```bash
# 1. Create new index with updated mapping
PUT /emails_v2-000001
{
  "mappings": { ... }
}

# 2. Reindex from old to new
POST /_reindex
{
  "source": { "index": "emails_v1-000001" },
  "dest": { "index": "emails_v2-000001" }
}

# 3. Update alias
POST /_aliases
{
  "actions": [
    { "remove": { "index": "emails_v1-000001", "alias": "emails_v1" } },
    { "add": { "index": "emails_v2-000001", "alias": "emails_v1" } }
  ]
}

# 4. Delete old index
DELETE /emails_v1-000001
```

## Performance Optimization

### Refresh Interval

```json
PUT /emails_v1/_settings
{
  "index": {
    "refresh_interval": "30s"  // Default: 1s (reduce for faster indexing)
  }
}
```

### Bulk Requests

Use `bulk` API for batch operations (500-1000 docs per request).

### Routing

```python
# Route all emails for a user to the same shard
es_client.index(
    index="emails_v1",
    id=email["id"],
    routing=email["user_id"],  # Ensures co-location
    document=email
)
```

## Monitoring

### Cluster Health

```bash
curl http://localhost:9200/_cluster/health?pretty
```

### Index Stats

```bash
curl http://localhost:9200/emails_v1/_stats?pretty
```

### Search Performance

```python
{
    "profile": True,  # Add to query for detailed timing
    "query": { ... }
}
```

## Common Queries

### Find High-Risk Emails

```json
GET /emails_v1/_search
{
  "query": {
    "range": {
      "risk_score": {
        "gte": 80
      }
    }
  }
}
```

### Find Emails Without Applications

```json
GET /emails_v1/_search
{
  "query": {
    "bool": {
      "must": [
        { "term": { "category": "application" } }
      ],
      "must_not": [
        { "exists": { "field": "application_id" } }
      ]
    }
  }
}
```

### Top Senders by Count

```json
GET /emails_v1/_search
{
  "size": 0,
  "aggs": {
    "top_senders": {
      "terms": {
        "field": "sender",
        "size": 10,
        "order": { "_count": "desc" }
      }
    }
  }
}
```

## See Also

- [Backend Implementation](./BACKEND.md)
- [Architecture](./ARCHITECTURE.md)
- [Smart Search Features](./SMART_SEARCH.md)
