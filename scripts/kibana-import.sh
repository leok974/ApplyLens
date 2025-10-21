#!/usr/bin/env bash
set -euo pipefail
KBN_URL=${KBN_URL:-http://localhost:5601}
KBN_AUTH=${KBN_AUTH:-elastic:changeme}

imp(){
  local f=$1
  curl -s -X POST "$KBN_URL/api/saved_objects/_import?createNewCopies=true" \
    -H 'kbn-xsrf: true' \
    -H "Authorization: Basic $(printf "$KBN_AUTH" | base64)" \
    -F file=@"$f" | jq '.success,.errors'
}

imp infra/kibana/emails_index_pattern.ndjson
imp infra/kibana/emails_saved_search.ndjson
