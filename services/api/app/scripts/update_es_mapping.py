"""
Elasticsearch mapping update for email automation system

This script adds new fields to the emails_v1 index to support:
- Email classification (category, risk_score)
- Automation (expires_at for time-based actions)
- Personalization (profile_tags, features_json)
- Semantic search (subject_vector, body_vector for embeddings)

Run this after creating a new index or use reindex API for existing data.
"""

EMAILS_V1_MAPPING_UPDATE = {
    "settings": {
        "analysis": {
            "analyzer": {
                "html_text": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "char_filter": ["html_strip"],
                    "filter": ["lowercase"]
                }
            },
            "normalizer": {
                "lowercase_norm": {
                    "type": "custom",
                    "filter": ["lowercase"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            # Existing fields
            "id": {"type": "keyword"},
            "thread_id": {"type": "keyword"},
            "received_at": {"type": "date"},
            "subject": {"type": "text", "analyzer": "standard"},
            "body_text": {"type": "text", "analyzer": "html_text"},
            "sender": {"type": "keyword", "normalizer": "lowercase_norm"},
            "sender_domain": {"type": "keyword", "normalizer": "lowercase_norm"},
            "list_id": {"type": "keyword"},
            "labels": {"type": "keyword"},
            "urls": {"type": "keyword"},
            "has_unsubscribe": {"type": "boolean"},
            "money_amounts": {"type": "float"},
            "dates": {"type": "date"},
            
            # NEW: Classification & Automation fields
            "category": {
                "type": "keyword",
                "fields": {
                    "text": {"type": "text"}
                }
            },
            "risk_score": {
                "type": "float",
                "index": True
            },
            "expires_at": {
                "type": "date",
                "index": True,
                "null_value": None
            },
            "profile_tags": {
                "type": "keyword"
            },
            "features_json": {
                "type": "flattened",
                "doc_values": True
            },
            
            # NEW: Vector embeddings for semantic search
            "subject_vector": {
                "type": "dense_vector",
                "dims": 768,
                "index": True,
                "similarity": "cosine"
            },
            "body_vector": {
                "type": "dense_vector",
                "dims": 768,
                "index": True,
                "similarity": "cosine"
            },
            
            # Reply metrics (from previous migration)
            "first_user_reply_at": {"type": "date"},
            "last_user_reply_at": {"type": "date"},
            "user_reply_count": {"type": "integer"},
            "replied": {"type": "boolean"}
        }
    }
}


def create_emails_v1_index(es_client):
    """
    Create the emails_v1 index with full mapping.
    
    Usage:
        from app.es import get_es_client
        from app.scripts.update_es_mapping import create_emails_v1_index
        
        es = get_es_client()
        create_emails_v1_index(es)
    """
    index_name = "emails_v1"
    
    if es_client.indices.exists(index=index_name):
        print(f"⚠️  Index '{index_name}' already exists. Use reindex_with_new_fields() instead.")
        return False
    
    es_client.indices.create(index=index_name, body=EMAILS_V1_MAPPING_UPDATE)
    print(f"✅ Created index '{index_name}' with automation fields")
    return True


def update_existing_index_mapping(es_client, index_name="emails_v1"):
    """
    Update mapping on existing index (only adds new fields, doesn't modify existing).
    
    Note: Some field type changes require reindexing.
    """
    new_properties = EMAILS_V1_MAPPING_UPDATE["mappings"]["properties"]
    
    # Extract only the new fields (automation-related)
    new_fields = {
        "category": new_properties["category"],
        "risk_score": new_properties["risk_score"],
        "expires_at": new_properties["expires_at"],
        "profile_tags": new_properties["profile_tags"],
        "features_json": new_properties["features_json"],
        "subject_vector": new_properties["subject_vector"],
        "body_vector": new_properties["body_vector"],
    }
    
    try:
        es_client.indices.put_mapping(
            index=index_name,
            body={"properties": new_fields}
        )
        print(f"✅ Updated mapping for '{index_name}' with new fields:")
        for field in new_fields:
            print(f"   - {field}")
        return True
    except Exception as e:
        print(f"❌ Failed to update mapping: {e}")
        print("💡 Tip: Some changes require reindexing. Use reindex_with_new_fields()")
        return False


def reindex_with_new_fields(es_client, source_index="emails_v1", dest_index="emails_v2"):
    """
    Reindex data from source to destination with new mapping.
    
    Workflow:
    1. Create new index with updated mapping
    2. Reindex all data from source to dest
    3. (Manual) Update aliases to point to new index
    4. (Manual) Delete old index after verification
    """
    # Create new index with full mapping
    if es_client.indices.exists(index=dest_index):
        print(f"❌ Destination index '{dest_index}' already exists!")
        return False
    
    es_client.indices.create(index=dest_index, body=EMAILS_V1_MAPPING_UPDATE)
    print(f"✅ Created new index: {dest_index}")
    
    # Reindex
    print(f"🔄 Reindexing from {source_index} to {dest_index}...")
    result = es_client.reindex(
        body={
            "source": {"index": source_index},
            "dest": {"index": dest_index}
        },
        wait_for_completion=False
    )
    
    task_id = result['task']
    print(f"📋 Reindex task started: {task_id}")
    print(f"💡 Check status: GET _tasks/{task_id}")
    
    return task_id


if __name__ == "__main__":
    """
    Run directly to update your local Elasticsearch:
    
        python -m app.scripts.update_es_mapping
    """
    import sys
    sys.path.insert(0, ".")
    
    from app.es import get_es_client
    
    es = get_es_client()
    
    # Try to update existing index first
    print("🚀 Updating Elasticsearch mapping for email automation...")
    success = update_existing_index_mapping(es)
    
    if not success:
        print("\n💡 Consider creating a new index and reindexing:")
        print("   reindex_with_new_fields(es, 'emails_v1', 'emails_v2')")
