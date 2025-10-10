#!/usr/bin/env bash
set -euo pipefail

ES="${ES_URL:-http://localhost:9200}"
KBN="${KIBANA_URL:-http://localhost:5601}"
API="${API_URL:-http://localhost:8003}"

echo "1) ES index exists?"
curl -s "$ES/actions_audit_v1" | jq -r '.acknowledged,.error // empty' >/dev/null && echo "  ✓ actions_audit_v1 reachable"

echo "2) Kibana saved search present?"
curl -s -H "kbn-xsrf: true" "$KBN/api/saved_objects/_find?type=search&search=policy-hits-vs-misses" \
 | jq -e '.total | select(.>=1)' >/dev/null && echo "  ✓ policy-hits-vs-misses found"

echo "3) API approvals endpoints healthy?"
curl -s "$API/docs" >/dev/null && echo "  ✓ FastAPI up"
curl -s -X POST "$API/approvals/propose" -H "Content-Type: application/json" \
 -d '{"items":[{"email_id":"healthcheck","action":"archive","policy_id":"hc","confidence":0.9}]}' \
 | jq -e '.accepted==1' >/dev/null && echo "  ✓ propose works"

echo "4) ES audit received doc?"
sleep 1
curl -s "$ES/actions_audit_v1/_search?q=email_id:healthcheck" | jq -e '.hits.hits[0]' >/dev/null \
  && echo "  ✓ audit indexed"

echo "All good ✅"
