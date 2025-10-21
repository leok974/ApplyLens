#!/usr/bin/env bash
set -euo pipefail
ES="${ES_URL:-http://localhost:9200}"
ALIAS="gmail_emails"
ID="test-$RANDOM"
now=$(date -u +%FT%TZ)
curl -s -X POST "$ES/$ALIAS/_doc/$ID?pipeline=applylens_emails_v2" \
  -H 'Content-Type: application/json' \
  -d "{\"from\":\"recruiter@acme.com\",\"to\":\"you@applylens.app\",\"subject\":\"Interview Invite\",\"body_html\":\"<p>calendar invite attached</p>\",\"received_at\":\"$now\"}" > /dev/null
sleep 1
resp=$(curl -s "$ES/$ALIAS/_search" -H 'Content-Type: application/json' \
  -d "{\"query\":{\"ids\":{\"values\":[\"$ID\"]}},\"_source\":[\"is_recruiter\",\"is_interview\",\"has_calendar_invite\",\"company_guess\"]}")
echo "$resp"
echo "$resp" | grep -q '"is_recruiter":true'
echo "$resp" | grep -q '"is_interview":true'
echo "$resp" | grep -q '"has_calendar_invite":true'
echo "$resp" | grep -q '"company_guess":"acme"'
echo "OK: flags present"
