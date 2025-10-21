#!/usr/bin/env bash
# Quick 30-second Smoke Test
# Copy-paste friendly version for rapid verification

set -e

BASE_URL="${1:-http://localhost:5175}"
echo "Testing $BASE_URL..."

# CSRF block test
echo -n "1. CSRF block (expect 403)... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/auth/logout")
if [ "$STATUS" = "403" ]; then
    echo "✅"
else
    echo "❌ Got $STATUS"
    exit 1
fi

# CSRF allow test
echo -n "2. CSRF allow (get cookie)... "
curl -s -c /tmp/c.txt "$BASE_URL/api/auth/status" >/dev/null
TOK=$(awk '$6=="csrf_token"{print $7}' /tmp/c.txt)
if [ -n "$TOK" ]; then
    echo "✅"
else
    echo "❌ No token"
    exit 1
fi

echo -n "3. CSRF allow (with token)... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -b /tmp/c.txt -H "X-CSRF-Token: $TOK" -X POST "$BASE_URL/api/auth/demo/start")
if [ "$STATUS" = "200" ] || [ "$STATUS" = "400" ]; then
    echo "✅ ($STATUS)"
else
    echo "❌ Got $STATUS"
    exit 1
fi

# Metrics present
echo -n "4. Metrics present... "
if curl -s "$BASE_URL/api/metrics" | grep -qE "applylens_(csrf|crypto|rate_limit|recaptcha)"; then
    echo "✅"
else
    echo "❌ No metrics"
    exit 1
fi

echo ""
echo "🎉 Quick smoke test passed!"
echo ""

# Show sample metrics
echo "Sample metrics:"
curl -s "$BASE_URL/api/metrics" | grep -E "applylens_(csrf|crypto|rate_limit)" | head -5
