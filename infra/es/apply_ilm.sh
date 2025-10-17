#!/usr/bin/env bash
set -euo pipefail
: "${ES_URL:?Set ES_URL, e.g. export ES_URL=http://elasticsearch:9200}"

echo "Applying ILM policy..."
curl -sf -X PUT "$ES_URL/_ilm/policy/emails-rolling-90d" \
  -H 'Content-Type: application/json' \
  --data-binary @infra/es/ilm_emails_rolling_90d.json
echo -e "\n✅ ILM policy applied"

echo "Applying index template..."
curl -sf -X PUT "$ES_URL/_index_template/gmail-emails-template" \
  -H 'Content-Type: application/json' \
  --data-binary @infra/es/index_template_gmail_emails.json
echo -e "\n✅ Index template applied"

echo "Bootstrapping write index (if needed)..."
set +e
curl -sf -X PUT "$ES_URL/gmail_emails-000001" \
  -H 'Content-Type: application/json' \
  -d '{"aliases":{"gmail_emails":{"is_write_index":true}}}'
if [ $? -eq 0 ]; then
  echo "✅ Bootstrapped gmail_emails-000001 as write index"
else
  echo "ℹ️ Write index may already exist; skipping"
fi
set -e

echo "Verifying ILM assignment..."
curl -sf "$ES_URL/gmail_emails/_ilm/explain?human" | jq '.indices | to_entries | .[0].value.managed'
echo -e "✅ Done"
