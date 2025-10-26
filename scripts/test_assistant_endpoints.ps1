Write-Host "Testing /api/assistant/query (list_suspicious style)..."
$resp = curl -s `
  -X POST `
  https://applylens.app/api/assistant/query `
  -H "Content-Type: application/json" `
  --data '{
    "user_query": "show suspicious emails",
    "mode": "off",
    "time_window_days": 30,
    "memory_opt_in": false,
    "account": "test@example.com"
  }'

Write-Host $resp

# Basic shape assertions:
# 1. JSON has "summary"
# 2. JSON has "next_steps"
# 3. JSON has "followup_prompt"
# 4. JSON has "sources"

if ($resp -notmatch '"summary"') { throw "❌ missing summary" }
if ($resp -notmatch '"next_steps"') { throw "❌ missing next_steps" }
if ($resp -notmatch '"followup_prompt"') { throw "❌ missing followup_prompt" }
if ($resp -notmatch '"sources"') { throw "❌ missing sources" }

Write-Host "✅ backend contract looks good"
