# ApplyLens — Post-Implementation Verification & Monitoring Cheatsheet

**Quick Reference for Security Features**  
**Date:** October 20, 2025

One-stop quick checks for everything deployed: AES-GCM, CSRF, rate limiting, reCAPTCHA, and Elasticsearch — plus Prometheus panels & alerts.

---

## 1) Health & Versions

### Quick Health Check
```bash
# API health
curl -sSf http://localhost:5175/api/healthz || curl -sSf http://localhost:8003/api/healthz

# Metrics endpoint
curl -s http://localhost:5175/api/metrics | head -n 20

# Or from API container directly
docker exec applylens-api-prod curl -s http://localhost:8003/metrics | head -n 20
```

### Version Information
```bash
# Check API container
docker exec applylens-api-prod python -c "from app.config import agent_settings; print(f'Encryption: {agent_settings.ENCRYPTION_ENABLED}'); print(f'CSRF: {agent_settings.CSRF_ENABLED}'); print(f'Rate Limit: {agent_settings.RATE_LIMIT_ENABLED}')"

# Check logs for initialization
docker logs applylens-api-prod | grep -E "Token encryption|Rate limiter|CSRF"
```

---

## 2) CSRF — Block & Allow

### PowerShell Commands

**Block Test (no header):**
```powershell
# Should return 403
Invoke-WebRequest -Uri "http://localhost:5175/auth/logout" -Method POST -UseBasicParsing
```

**Allow Test (cookie + matching header):**
```powershell
# Get CSRF cookie
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-WebRequest -Uri "http://localhost:5175/auth/status" -WebSession $session -UseBasicParsing | Out-Null

# Extract CSRF token
$csrfCookie = $session.Cookies.GetCookies("http://localhost:5175") | Where-Object { $_.Name -eq "csrftoken" }
$token = $csrfCookie.Value

# Make request with token
$headers = @{ "X-CSRF-Token" = $token }
Invoke-WebRequest -Uri "http://localhost:5175/auth/demo/start" -Method POST -Headers $headers -WebSession $session -UseBasicParsing
```

### Bash Commands

**Block (no header):**
```bash
curl -i -X POST http://localhost:5175/auth/logout | sed -n '1,10p'
```

**Allow (cookie + matching header):**
```bash
curl -s -c /tmp/c.txt http://localhost:5175/auth/status >/dev/null
TOK=$(awk '$6=="csrf_token"{print $7}' /tmp/c.txt)
curl -i -b /tmp/c.txt -H "X-CSRF-Token: $TOK" -X POST http://localhost:5175/auth/demo/start | sed -n '1,12p'
```

### PromQL (Grafana Panels)
```promql
# CSRF failure rate
sum(rate(applylens_csrf_fail_total[5m]))

# CSRF success rate
sum(rate(applylens_csrf_success_total[5m]))

# By path
sum(rate(applylens_csrf_fail_total[5m])) by (path, method)
```

### Alertmanager Alert
```yaml
groups:
  - name: applylens_csrf
    rules:
      - alert: CSRFSpike
        expr: sum(rate(applylens_csrf_fail_total[5m])) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "CSRF failures spiking"
          description: "{{ $value }} CSRF failures/sec (possible attack or misconfiguration)"
```

---

## 3) Crypto — Encryption/Decryption

### Verify Production Key (Not Ephemeral)
```bash
# Log should NOT show ephemeral key in prod
docker logs applylens-api-prod | grep -i ephemeral | head -n1 || echo "✅ Using production key"

# Should show persistent key loaded
docker logs applylens-api-prod | grep "Loaded AES" | head -n1
```

### Test Encryption Flow
```bash
# Create demo session (triggers encryption)
curl -X POST http://localhost:5175/auth/demo/start -H "Content-Type: application/json" -d '{}'

# Check encrypt counter increased
docker exec applylens-api-prod curl -s http://localhost:8003/metrics | grep applylens_crypto_encrypt_total
```

### PromQL (Grafana Panels)
```promql
# Decryption errors by type
sum(rate(applylens_crypto_decrypt_error_total[5m])) by (error_type)

# Encryption rate
sum(rate(applylens_crypto_encrypt_total[5m]))

# Decryption rate
sum(rate(applylens_crypto_decrypt_total[5m]))

# Operation duration
histogram_quantile(0.99, sum(rate(applylens_crypto_operation_duration_seconds_bucket[5m])) by (le, operation))
```

### Alertmanager Alert
```yaml
- alert: CryptoDecryptErrors
  expr: sum(rate(applylens_crypto_decrypt_error_total[5m])) > 0.1
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Decrypt errors detected"
    description: "{{ $value }} decrypt errors/sec (check AES key / rotation)"

- alert: InvalidTagErrors
  expr: sum(rate(applylens_crypto_decrypt_error_total{error_type="invalid_tag"}[5m])) > 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Token tampering detected"
    description: "Invalid authentication tags (possible security breach)"
```

---

## 4) Rate Limiting — Burst Test

### PowerShell Burst Test
```powershell
# 80 concurrent requests (should see some 429s)
$uri = "http://localhost:5175/auth/status"
1..80 | ForEach-Object -Parallel {
    try {
        $r = Invoke-WebRequest -Uri $using:uri -UseBasicParsing -ErrorAction Stop
        $r.StatusCode
    } catch {
        $_.Exception.Response.StatusCode.value__
    }
} -ThrottleLimit 80 | Group-Object | ForEach-Object {
    "$($_.Name): $($_.Count)"
}
```

### Bash + GNU Parallel
```bash
URL=http://localhost:5175/auth/status
seq 1 80 | parallel -j80 curl -s -o /dev/null -w "%{http_code}\n" "$URL" | sort | uniq -c
# Expected: Some 200s and some 429s
```

### Sequential Test (Won't Trigger Limit)
```bash
# This is too slow to hit rate limit
for i in {1..80}; do
  curl -s -o /dev/null -w "%{http_code} " http://localhost:5175/auth/status
done
echo ""
```

### PromQL (Grafana Panels)
```promql
# Rate limit exceeded rate
sum(rate(applylens_rate_limit_exceeded_total[5m]))

# Requests allowed rate
sum(rate(applylens_rate_limit_allowed_total[5m]))

# By path
sum(rate(applylens_rate_limit_exceeded_total[5m])) by (path, ip_prefix)
```

### Alertmanager Alert
```yaml
- alert: RateLimitFlood
  expr: sum(rate(applylens_rate_limit_exceeded_total[1m])) > 100
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Rate limiting flood detected"
    description: "{{ $value }} rate limit events/sec (possible attack)"
```

### Behind Proxy Configuration
```nginx
# nginx.conf - Pass real client IP
location /auth/ {
    proxy_pass http://api:8003/auth/;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

## 5) reCAPTCHA — Backend Gate

### Test Without Token (Should Fail When Enabled)
```bash
# With RECAPTCHA_ENABLED=1 and no token -> should fail
curl -i -X POST http://localhost:5175/auth/demo/start -H "Content-Type: application/json" -d '{}' | sed -n '1,10p'

# Should return 400 if enabled, 200 if disabled
```

### Check reCAPTCHA Status
```bash
docker exec applylens-api-prod python -c "from app.config import agent_settings; print(f'reCAPTCHA enabled: {agent_settings.RECAPTCHA_ENABLED}'); print(f'Min score: {agent_settings.RECAPTCHA_MIN_SCORE}')"
```

### PromQL (Grafana Panels)
```promql
# Verification failures
sum(rate(applylens_recaptcha_verify_total{status="failure"}[5m]))

# Low score rate
sum(rate(applylens_recaptcha_verify_total{status="low_score"}[5m]))

# Success rate
sum(rate(applylens_recaptcha_verify_total{status="success"}[5m]))

# Score distribution
histogram_quantile(0.5, sum(rate(applylens_recaptcha_score_bucket[5m])) by (le))
```

### Alertmanager Alert
```yaml
- alert: CaptchaFailures
  expr: sum(rate(applylens_recaptcha_verify_total{status="failure"}[5m])) > 10
  for: 10m
  labels:
    severity: info
  annotations:
    summary: "High captcha failure rate"
    description: "{{ $value }} captcha failures/sec (check bot traffic)"

- alert: LowCaptchaScores
  expr: sum(rate(applylens_recaptcha_verify_total{status="low_score"}[5m])) > 5
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Many low reCAPTCHA scores"
    description: "Possible bot traffic detected"
```

---

## 6) Elasticsearch — Connectivity & Hygiene

### Cluster Health
```bash
# From ES container
curl -s http://localhost:9200/_cluster/health?pretty

# Expected: status "yellow" (single node) or "green" (multi-node)
```

### Indices Check
```bash
curl -s http://localhost:9200/_cat/indices?v

# Look for gmail_emails-000001 index
```

### API Container Connection
```bash
# Ping test
docker exec applylens-api-prod python -c "from app.es import es; print('ES connected:', bool(es and es.ping()))"

# Index stats
docker exec applylens-api-prod curl -s http://elasticsearch:9200/_cat/indices?v | grep gmail_emails
```

### Query Test
```bash
# Search applications
curl -s "http://localhost:5175/api/search/applications?q=software+engineer" | head -n 50
```

### Security Checks
- ✅ Queries filter by `user_id` (tenant isolation)
- ✅ Default search excludes `archived_at != null`
- ✅ Index mappings include security analyzers

### Single-Node Dev Optimization
```bash
# Set replicas to 0 on single-node
curl -X PUT "http://localhost:9200/gmail_emails-000001/_settings" -H 'Content-Type: application/json' -d '{
  "index": {
    "number_of_replicas": 0
  }
}'
```

---

## 7) AES Key — Secrets & Rotation

### Generate AES-256 Key (PowerShell)
```powershell
python -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

### Generate AES-256 Key (Bash)
```bash
python - <<'PY'
import os, base64
print(base64.urlsafe_b64encode(os.urandom(32)).decode())
PY
```

### GCP Secret Manager (Store & Read)
```bash
PROJECT_ID=<your-project>
SECRET_ID=APPLYLENS_AES_KEY_BASE64

# Create secret
gcloud secrets create $SECRET_ID --replication-policy=automatic --project $PROJECT_ID

# Add version
AES_KEY=$(python -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())")
printf "%s" "$AES_KEY" | gcloud secrets versions add $SECRET_ID --data-file=- --project $PROJECT_ID

# Read latest
gcloud secrets versions access latest --secret=$SECRET_ID --project $PROJECT_ID
```

### AWS Secrets Manager (Store & Read)
```bash
REGION=us-west-2
SECRET_NAME=APPLYLENS_AES_KEY_BASE64

# Create secret
AES_KEY=$(python -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())")
aws secretsmanager create-secret \
  --name $SECRET_NAME \
  --secret-string "$AES_KEY" \
  --region $REGION

# Read
aws secretsmanager get-secret-value \
  --secret-id $SECRET_NAME \
  --query SecretString \
  --output text \
  --region $REGION
```

### Envelope Encryption (Future)
**Migration:** `alembic/versions/0032_encryption_keys.py`

**Workflow:**
1. Add `encryption_keys` table
2. Add `oauth_tokens.key_version` column
3. Load active wrapped key at startup
4. Store new tokens with latest version
5. Old tokens still decryptable with their version

**Key Rotation:**
```bash
# Generate and wrap with KMS
python scripts/keys.py rotate --kms-key projects/my-project/locations/global/keyRings/applylens/cryptoKeys/token-key

# List versions
python scripts/keys.py list

# Activate specific version
python scripts/keys.py activate --version 2
```

---

## 8) Grafana Panels — Quick PromQL Cards

### Security Dashboard

**CSRF Failures (5m):**
```promql
sum(rate(applylens_csrf_fail_total[5m]))
```

**Decrypt Errors by Type:**
```promql
sum(rate(applylens_crypto_decrypt_error_total[5m])) by (error_type)
```

**Rate Limit 429s (1m):**
```promql
sum(rate(applylens_rate_limit_exceeded_total[1m]))
```

**Captcha Fail Rate (5m):**
```promql
sum(rate(applylens_recaptcha_verify_total{status="failure"}[5m]))
```

**Crypto Operation Duration (p99):**
```promql
histogram_quantile(0.99, sum(rate(applylens_crypto_operation_duration_seconds_bucket[5m])) by (le, operation))
```

**Auth Success Rate:**
```promql
sum(rate(applylens_auth_attempt_total{status="success"}[5m])) 
/ 
sum(rate(applylens_auth_attempt_total[5m]))
```

### Example Grafana JSON (Simple Panel)
```json
{
  "targets": [
    {
      "expr": "sum(rate(applylens_csrf_fail_total[5m]))",
      "legendFormat": "CSRF Failures"
    },
    {
      "expr": "sum(rate(applylens_crypto_decrypt_error_total[5m]))",
      "legendFormat": "Decrypt Errors"
    }
  ],
  "title": "Security Events",
  "type": "graph"
}
```

---

## 9) Rollback & Fast Fixes

### CSRF Stuck
```bash
# Temporarily disable (dev/staging only)
docker exec applylens-api-prod python -c "from app.config import agent_settings; agent_settings.CSRF_ENABLED = 0"
docker compose -f docker-compose.prod.yml restart api

# Re-enable after root cause analysis
```

### Decrypt Errors
```bash
# Confirm key matches
docker exec applylens-api-prod python -c "from app.config import agent_settings; print(agent_settings.AES_KEY_BASE64[:20] + '...')"

# Compare with secret
gcloud secrets versions access latest --secret=APPLYLENS_AES_KEY_BASE64 --project=$PROJECT_ID | cut -c1-20

# If lost, force re-auth
docker exec applylens-api-prod psql -U postgres -d applylens -c "DELETE FROM oauth_tokens;"
```

### 429s Too Frequent
```bash
# Raise limits temporarily
docker exec applylens-api-prod python -c "from app.config import agent_settings; print(f'Current: {agent_settings.RATE_LIMIT_MAX_REQ}/{agent_settings.RATE_LIMIT_WINDOW_SEC}s')"

# Update and redeploy
# APPLYLENS_RATE_LIMIT_MAX_REQ=120
# APPLYLENS_RATE_LIMIT_WINDOW_SEC=60
```

### Captcha Too Strict
```bash
# Lower threshold
# APPLYLENS_RECAPTCHA_MIN_SCORE=0.3

# Or disable temporarily
# APPLYLENS_RECAPTCHA_ENABLED=0
```

### Emergency: Disable All Security
```bash
# ONLY FOR EMERGENCY DEBUGGING
docker exec applylens-api-prod sh -c 'cat > /tmp/emergency_disable.py << EOF
from app.config import agent_settings
agent_settings.CSRF_ENABLED = 0
agent_settings.RATE_LIMIT_ENABLED = 0
agent_settings.RECAPTCHA_ENABLED = 0
print("Security disabled - FOR DEBUGGING ONLY")
EOF'

# DO NOT USE IN PRODUCTION
```

---

## 10) CI Smoke Test Script

### Bash Version
```bash
#!/usr/bin/env bash
# ci-smoke-test.sh
set -euo pipefail

base="${1:-http://localhost:5175}"
echo "Testing $base..."

# 1. CSRF cookie
echo -n "Getting CSRF cookie... "
curl -s -c /tmp/c.txt "$base/auth/status" >/dev/null || { echo "❌ Failed"; exit 1; }
TOK=$(awk '$6=="csrftoken"{print $7}' /tmp/c.txt)
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
echo "✅"

# 4. Metrics endpoint
echo -n "Testing metrics... "
curl -s "$base/api/metrics" | grep -q "applylens_csrf_fail_total" || { echo "❌ No metrics"; exit 1; }
echo "✅"

# 5. Health check
echo -n "Testing health... "
curl -sSf "$base/api/healthz" >/dev/null || { echo "❌ Health check failed"; exit 1; }
echo "✅"

echo ""
echo "🎉 All smoke tests passed!"
```

### PowerShell Version
```powershell
# ci-smoke-test.ps1
param(
    [string]$Base = "http://localhost:5175"
)

$ErrorActionPreference = "Stop"
Write-Host "Testing $Base..." -ForegroundColor Cyan

# 1. CSRF cookie
Write-Host -NoNewline "Getting CSRF cookie... "
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-WebRequest -Uri "$Base/auth/status" -WebSession $session -UseBasicParsing | Out-Null
$csrfCookie = $session.Cookies.GetCookies($Base) | Where-Object { $_.Name -eq "csrf_token" }
if (-not $csrfCookie) { Write-Host "❌ No token" -ForegroundColor Red; exit 1 }
$token = $csrfCookie.Value
Write-Host "✅" -ForegroundColor Green

# 2. CSRF blocked
Write-Host -NoNewline "Testing CSRF block... "
try {
    Invoke-WebRequest -Uri "$Base/auth/logout" -Method POST -UseBasicParsing -ErrorAction Stop | Out-Null
    Write-Host "❌ Should have blocked" -ForegroundColor Red
    exit 1
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 403) {
        Write-Host "✅" -ForegroundColor Green
    } else {
        Write-Host "❌ Expected 403, got $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
        exit 1
    }
}

# 3. CSRF allowed
Write-Host -NoNewline "Testing CSRF allow... "
$headers = @{ "X-CSRF-Token" = $token; "Content-Type" = "application/json" }
$body = "{}"
try {
    $response = Invoke-WebRequest -Uri "$Base/auth/demo/start" -Method POST -Headers $headers -Body $body -WebSession $session -UseBasicParsing
    if ($response.StatusCode -in @(200, 400)) {
        Write-Host "✅" -ForegroundColor Green
    } else {
        Write-Host "❌ Unexpected status: $($response.StatusCode)" -ForegroundColor Red
        exit 1
    }
} catch {
    # 400 is OK (captcha might be required)
    if ($_.Exception.Response.StatusCode.value__ -in @(200, 400)) {
        Write-Host "✅" -ForegroundColor Green
    } else {
        Write-Host "❌ Expected 200/400, got $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
        exit 1
    }
}

# 4. Metrics endpoint
Write-Host -NoNewline "Testing metrics... "
$metrics = Invoke-WebRequest -Uri "$Base/api/metrics" -UseBasicParsing
if ($metrics.Content -match "applylens_csrf_fail_total") {
    Write-Host "✅" -ForegroundColor Green
} else {
    Write-Host "❌ No metrics" -ForegroundColor Red
    exit 1
}

# 5. Health check
Write-Host -NoNewline "Testing health... "
Invoke-WebRequest -Uri "$Base/api/healthz" -UseBasicParsing | Out-Null
Write-Host "✅" -ForegroundColor Green

Write-Host ""
Write-Host "🎉 All smoke tests passed!" -ForegroundColor Green
```

### Run CI Tests
```bash
# Bash
chmod +x ci-smoke-test.sh
./ci-smoke-test.sh http://localhost:5175

# PowerShell
.\ci-smoke-test.ps1 -Base "http://localhost:5175"
```

---

## Complete Verification Checklist

- [ ] **Health**: `/api/healthz` returns 200
- [ ] **Metrics**: `/api/metrics` exposes all `applylens_*` metrics
- [ ] **CSRF Block**: POST without token returns 403
- [ ] **CSRF Allow**: POST with valid token succeeds
- [ ] **Crypto**: No ephemeral key in logs (production)
- [ ] **Decrypt**: No `crypto_decrypt_error_total` spikes
- [ ] **Rate Limit**: Concurrent burst triggers 429s
- [ ] **reCAPTCHA**: Returns 400 without token (if enabled)
- [ ] **Elasticsearch**: Cluster health yellow/green
- [ ] **ES Ping**: API can connect to ES
- [ ] **AES Key**: Stored in GCP/AWS Secret Manager
- [ ] **Prometheus**: Scraping `/metrics` successfully
- [ ] **Grafana**: Security dashboard populated
- [ ] **Alerts**: Configured in Alertmanager

---

## Quick Reference Commands

```bash
# Full verification suite
./ci-smoke-test.sh

# Check all features enabled
docker exec applylens-api-prod python -c "
from app.config import agent_settings
print('Encryption:', agent_settings.ENCRYPTION_ENABLED)
print('CSRF:', agent_settings.CSRF_ENABLED)
print('Rate Limit:', agent_settings.RATE_LIMIT_ENABLED)
print('reCAPTCHA:', agent_settings.RECAPTCHA_ENABLED)
"

# Watch metrics in real-time
watch -n 2 'docker exec applylens-api-prod curl -s http://localhost:8003/metrics | grep applylens_csrf'

# Tail security logs
docker logs -f applylens-api-prod | grep -E "CSRF|crypto|Rate limit|reCAPTCHA"
```

---

**Last Updated:** October 20, 2025  
**Related Docs:**
- `TOKEN_ENCRYPTION_CSRF_2025-10-20.md`
- `RATE_LIMITING_ES_CONFIG_2025-10-20.md`
- `SECURITY_KEYS_AND_CSRF.md`
- `IMPLEMENTATION_COMPLETE_2025-10-20.md`
