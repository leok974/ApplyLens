#!/usr/bin/env bash
# ci-smoke-test.sh
# ApplyLens Security Features Smoke Test
# Tests: CSRF, Metrics, Health

set -euo pipefail

base="${1:-http://localhost:5175}"
echo "Testing $base..."

# 1. CSRF cookie
echo -n "Getting CSRF cookie... "
curl -s -c /tmp/c.txt "$base/auth/status" >/dev/null || { echo "❌ Failed"; exit 1; }
TOK=$(awk '$6=="csrf_token"{print $7}' /tmp/c.txt)
[[ -n "$TOK" ]] || { echo "❌ No token"; exit 1; }
echo "✅"

# 2. CSRF blocked
echo -n "Testing CSRF block... "
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$base/auth/logout")
[[ "$code" == "403" ]] || { echo "❌ Expected 403, got $code"; exit 1; }
echo "✅"

# 3. CSRF allowed
echo -n "Testing CSRF allow... "
code=$(curl -s -o /dev/null -w "%{http_code}" -b /tmp/c.txt -H "X-CSRF-Token: $TOK" -X POST "$base/auth/demo/start" -H "Content-Type: application/json" -d '{}')
[[ "$code" == "200" || "$code" == "400" ]] || { echo "❌ Expected 200/400, got $code"; exit 1; }
echo "✅ (got $code)"

# 4. Metrics endpoint
echo -n "Testing metrics... "
curl -s "$base/api/metrics" | grep -q "applylens_csrf_fail_total" || { echo "❌ No metrics"; exit 1; }
echo "✅"

# 5. Health check
echo -n "Testing health... "
curl -sSf "$base/api/healthz" >/dev/null || { echo "❌ Health check failed"; exit 1; }
echo "✅"

# 6. Crypto metrics present
echo -n "Testing crypto metrics... "
curl -s "$base/api/metrics" | grep -q "applylens_crypto_encrypt_total" || { echo "❌ No crypto metrics"; exit 1; }
echo "✅"

# 7. Rate limit metrics present
echo -n "Testing rate limit metrics... "
curl -s "$base/api/metrics" | grep -q "applylens_rate_limit_allowed_total" || { echo "❌ No rate limit metrics"; exit 1; }
echo "✅"

# Cleanup
rm -f /tmp/c.txt

echo ""
echo "🎉 All smoke tests passed!"
echo ""
echo "Summary:"
echo "  ✅ CSRF protection working"
echo "  ✅ Metrics exposed"
echo "  ✅ Health check passing"
echo "  ✅ All security features initialized"
