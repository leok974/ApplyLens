#!/usr/bin/env python3
"""
Create Elasticsearch mapping for actions_audit_v1 index.

This index stores the audit trail for all email actions (proposed, approved, rejected, executed).
Used for Kibana dashboards and policy analytics.

Usage:
    python -m app.scripts.create_audit_index
    
Or with Docker:
    docker-compose exec api python -m app.scripts.create_audit_index
"""

import os
import sys
from elasticsearch import Elasticsearch


def create_audit_index():
    """Create actions_audit_v1 index with proper mapping."""
    # ES connection
    es_url = os.getenv("ES_URL", "http://localhost:9200")
    api_key = os.getenv("ES_API_KEY")
    
    if api_key:
        es = Elasticsearch(es_url, api_key=api_key)
    else:
        es = Elasticsearch(es_url)
    
    index_name = os.getenv("ES_AUDIT_INDEX", "actions_audit_v1")
    
    # Check if index exists
    if es.indices.exists(index=index_name):
        print(f"✅ Index '{index_name}' already exists")
        return
    
    # Mapping definition
    mapping = {
        "mappings": {
            "properties": {
                "email_id": {
                    "type": "keyword",
                    "doc_values": True
                },
                "action": {
                    "type": "keyword",
                    "doc_values": True
                },
                "actor": {
                    "type": "keyword",
                    "doc_values": True,
                    "meta": {
                        "description": "Who initiated the action: agent, user, or system"
                    }
                },
                "policy_id": {
                    "type": "keyword",
                    "doc_values": True
                },
                "confidence": {
                    "type": "float",
                    "doc_values": True
                },
                "rationale": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "status": {
                    "type": "keyword",
                    "doc_values": True,
                    "meta": {
                        "description": "Status: proposed, approved, rejected, executed"
                    }
                },
                "created_at": {
                    "type": "date",
                    "format": "strict_date_optional_time||epoch_millis"
                },
                "payload": {
                    "type": "flattened",
                    "doc_values": True,
                    "meta": {
                        "description": "Additional context (params, headers, etc.)"
                    }
                }
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "refresh_interval": "5s"
        }
    }
    
    # Create index
    try:
        es.indices.create(index=index_name, body=mapping)
        print(f"✅ Created index '{index_name}' with mapping:")
        print("   - email_id (keyword)")
        print("   - action (keyword)")
        print("   - actor (keyword) - agent|user|system")
        print("   - policy_id (keyword)")
        print("   - confidence (float)")
        print("   - rationale (text)")
        print("   - status (keyword) - proposed|approved|rejected|executed")
        print("   - created_at (date)")
        print("   - payload (flattened)")
    except Exception as e:
        print(f"❌ Error creating index: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    create_audit_index()
