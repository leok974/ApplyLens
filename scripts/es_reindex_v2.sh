#!/usr/bin/env bash
set -euo pipefail
ES="${ES_URL:-http://localhost:9200}"
SRC_INDEX="${SRC_INDEX:-gmail_emails-000001}"
DST_INDEX="${DST_INDEX:-gmail_emails-reindexed-$(date +%Y%m%d)}"
ALIAS="${ALIAS:-gmail_emails}"
DRY_RUN="${DRY_RUN:-true}"

json(){ echo "$1" | jq -c .; }

# Create empty destination
curl -fsS -X PUT "$ES/$DST_INDEX" -H 'Content-Type: application/json' -d '{"aliases":{}}' >/dev/null

# Reindex via v2 pipeline
curl -fsS -X POST "$ES/_reindex" -H 'Content-Type: application/json' -d @- <<JSON
{
  "source": { "index": "$SRC_INDEX" },
  "dest":   { "index": "$DST_INDEX", "pipeline": "applylens_emails_v2" }
}
JSON

# Verify counts (simple)
SRC_COUNT=$(curl -fsS "$ES/$SRC_INDEX/_count" | jq -r .count)
DST_COUNT=$(curl -fsS "$ES/$DST_INDEX/_count" | jq -r .count)
echo "SRC=$SRC_COUNT DST=$DST_COUNT"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "DRY_RUN=true → skipping alias swap"; exit 0
fi

# Atomic alias swap
curl -fsS -X POST "$ES/_aliases" -H 'Content-Type: application/json' -d @- <<JSON
{
  "actions": [
    {"remove":{"index":"$SRC_INDEX","alias":"$ALIAS","is_write_index":true}},
    {"add":{"index":"$DST_INDEX","alias":"$ALIAS","is_write_index":true}}
  ]
}
JSON

echo "Alias $ALIAS now points to $DST_INDEX"
