#!/bin/bash
# Elasticsearch ILM Setup for ApplyLens
# 90-day retention with monthly rollover

set -e

ES_URL="${ES_URL:-http://localhost:9200}"

echo "=== Elasticsearch ILM Policy Setup ==="
echo ""
echo "Target: $ES_URL"
echo ""

# A. Create ILM policy emails-rolling-90d
echo "1. Creating ILM policy 'emails-rolling-90d'..."
curl -s -X PUT "$ES_URL/_ilm/policy/emails-rolling-90d" -H 'Content-Type: application/json' -d '{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0d",
        "actions": {
          "rollover": { 
            "max_age": "30d", 
            "max_size": "20gb" 
          },
          "set_priority": { "priority": 100 }
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": { "delete": {} }
      }
    }
  }
}' | jq

echo ""
echo "✓ ILM policy created"
echo ""

# B. Create index template for alias gmail_emails
echo "2. Creating index template 'gmail-emails-template'..."
curl -s -X PUT "$ES_URL/_index_template/gmail-emails-template" -H 'Content-Type: application/json' -d '{
  "index_patterns": ["gmail_emails-*"],
  "template": {
    "settings": {
      "index.lifecycle.name": "emails-rolling-90d",
      "index.lifecycle.rollover_alias": "gmail_emails",
      "index.refresh_interval": "1s",
      "index.number_of_shards": 1,
      "index.number_of_replicas": 1
    },
    "mappings": {
      "properties": {
        "owner_email": { "type": "keyword" },
        "received_at": { "type": "date" },
        "sender": { "type": "keyword" },
        "sender_domain": { "type": "keyword" },
        "subject": { "type": "text" },
        "body": { "type": "text" },
        "labels": { "type": "keyword" },
        "thread_id": { "type": "keyword" },
        "message_id": { "type": "keyword" }
      }
    },
    "aliases": {
      "gmail_emails": { "is_write_index": false }
    }
  },
  "priority": 500,
  "composed_of": []
}' | jq

echo ""
echo "✓ Index template created"
echo ""

# C. Check if we need to bootstrap the first rollover index
echo "3. Checking existing indices..."
EXISTING_INDEX=$(curl -s "$ES_URL/_cat/indices/gmail_emails?h=index" | head -1)

if [[ "$EXISTING_INDEX" == "gmail_emails" ]]; then
  echo "   Found concrete 'gmail_emails' index"
  echo "   Migration required:"
  echo ""
  echo "   ⚠️  MANUAL STEPS REQUIRED:"
  echo "   1. Stop API ingestion temporarily"
  echo "   2. Create first write index:"
  echo "      curl -X PUT '$ES_URL/gmail_emails-000001' -H 'Content-Type: application/json' -d '{\"aliases\":{\"gmail_emails\":{\"is_write_index\":true}}}'"
  echo "   3. Reindex data (optional):"
  echo "      curl -X POST '$ES_URL/_reindex' -H 'Content-Type: application/json' -d '{\"source\":{\"index\":\"gmail_emails\"},\"dest\":{\"index\":\"gmail_emails-000001\"}}'"
  echo "   4. Delete old index:"
  echo "      curl -X DELETE '$ES_URL/gmail_emails'"
  echo "   5. Restart API ingestion"
  echo ""
elif [[ "$EXISTING_INDEX" == gmail_emails-* ]]; then
  echo "   ✓ Rollover index already exists: $EXISTING_INDEX"
  echo ""
else
  echo "   No existing index found. Creating first write index..."
  curl -s -X PUT "$ES_URL/gmail_emails-000001" -H 'Content-Type: application/json' -d '{
    "aliases": { "gmail_emails": { "is_write_index": true } }
  }' | jq
  echo ""
  echo "   ✓ First write index created: gmail_emails-000001"
  echo ""
fi

# D. Verify setup
echo "4. Verifying ILM setup..."
echo ""
echo "   Policy status:"
curl -s "$ES_URL/_ilm/policy/emails-rolling-90d" | jq -r '.["emails-rolling-90d"].policy.phases | keys[]'

echo ""
echo "   Index status:"
curl -s "$ES_URL/gmail_emails/_ilm/explain?human" | jq -c '.indices | to_entries[] | {index: .key, phase: .value.phase, action: .value.action}'

echo ""
echo ""
echo "=== Setup Complete ==="
echo ""
echo "To manually test rollover:"
echo "  curl -X POST '$ES_URL/gmail_emails/_rollover'"
echo ""
echo "To monitor ILM status:"
echo "  curl '$ES_URL/gmail_emails/_ilm/explain?human' | jq"
echo ""
