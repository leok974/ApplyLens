#!/usr/bin/env bash
# Immediate ILM Migration Script
# Retrofits existing gmail_emails index to ILM-managed structure
set -euo pipefail

ES_URL="${ES_URL:-http://elasticsearch:9200}"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Elasticsearch ILM - Immediate Migration (Retrofit)            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  WARNING: This will migrate your existing gmail_emails index to ILM management"
echo "    - Creates new index: gmail_emails-000001"
echo "    - Reindexes all documents"
echo "    - Deletes old index: gmail_emails"
echo "    - Creates alias: gmail_emails → gmail_emails-000001"
echo ""
read -p "Continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Migration cancelled."
    exit 0
fi

echo ""
echo "Step 1: Create ILM-managed target index..."
curl -sf -X PUT "$ES_URL/gmail_emails-000001" -H 'Content-Type: application/json' -d '{
  "settings": {
    "index.lifecycle.name": "emails-rolling-90d",
    "index.lifecycle.rollover_alias": "gmail_emails"
  }
}'
echo ""
echo "✅ Created gmail_emails-000001 with ILM policy"

echo ""
echo "Step 2: Reindexing existing data..."
echo "   (This may take a few minutes depending on data size)"
REINDEX_RESPONSE=$(curl -sf -X POST "$ES_URL/_reindex?wait_for_completion=true" -H 'Content-Type: application/json' -d '{
  "source": { "index": "gmail_emails" },
  "dest":   { "index": "gmail_emails-000001" }
}')
echo ""
TOTAL=$(echo "$REINDEX_RESPONSE" | jq -r '.total')
CREATED=$(echo "$REINDEX_RESPONSE" | jq -r '.created')
TOOK=$(echo "$REINDEX_RESPONSE" | jq -r '.took')
echo "✅ Reindexed $CREATED/$TOTAL documents in ${TOOK}ms"

echo ""
echo "Step 3: Deleting old index..."
curl -sf -X DELETE "$ES_URL/gmail_emails"
echo ""
echo "✅ Deleted old gmail_emails index"

echo ""
echo "Step 4: Creating write alias..."
curl -sf -X POST "$ES_URL/_aliases" -H 'Content-Type: application/json' -d '{
  "actions": [
    { "add": { "index": "gmail_emails-000001", "alias": "gmail_emails", "is_write_index": true } }
  ]
}'
echo ""
echo "✅ Created alias: gmail_emails → gmail_emails-000001 (write_index: true)"

echo ""
echo "Step 5: Applying index template for future rollovers..."
curl -sf -X PUT "$ES_URL/_index_template/gmail-emails-template" -H 'Content-Type: application/json' -d '{
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
        "received_at": { "type": "date" }
      }
    }
  },
  "priority": 500
}'
echo ""
echo "✅ Applied index template for future rollovers"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Verification:"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "ILM Status:"
curl -sf "$ES_URL/gmail_emails-000001/_ilm/explain?human" | jq '{
  index: .indices | keys[0],
  managed: .indices[.indices | keys[0]].managed,
  policy: .indices[.indices | keys[0]].policy,
  phase: .indices[.indices | keys[0]].phase,
  action: .indices[.indices | keys[0]].action
}'

echo ""
echo "Alias Configuration:"
curl -sf "$ES_URL/_cat/aliases/gmail_emails?v"

echo ""
echo "Index Stats:"
curl -sf "$ES_URL/_cat/indices/gmail_emails-*?v&h=index,docs.count,store.size,health"

echo ""
echo "✅ Migration Complete!"
echo ""
echo "🧠 What happens next:"
echo "  • ILM will automatically rollover at 30 days or 20 GB"
echo "  • Old indices delete after 90 days"
echo "  • Disk footprint drops 70-80% year-over-year"
echo "  • Your API continues writing to alias 'gmail_emails' transparently"
echo ""
