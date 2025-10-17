#!/usr/bin/env bash
set -euo pipefail
: "${ES_URL:?Set ES_URL}"
echo "Deleting template gmail-emails-template..."
curl -sf -X DELETE "$ES_URL/_index_template/gmail-emails-template" || true
echo -e "\nDeleting ILM policy emails-rolling-90d..."
curl -sf -X DELETE "$ES_URL/_ilm/policy/emails-rolling-90d" || true
echo -e "\n(Templates removed. Existing indices keep their current settings until recreated.)"
