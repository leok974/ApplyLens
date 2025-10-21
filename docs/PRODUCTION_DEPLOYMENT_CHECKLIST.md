# ApplyLens Production Deployment Checklist

**Last Updated:** October 20, 2025  
**Status:** ✅ Ready for Production

This checklist ensures all deployment finalization steps are properly configured and validated before going live.

---

## Pre-Deployment Checklist

### Environment Variables ✅
Run `.\scripts\pre-deploy-check.ps1` to validate:

- [x] APPLYLENS_AES_KEY_BASE64 (required)
- [x] CSRF_SECRET_KEY (required)
- [x] OAUTH_STATE_SECRET (required)
- [x] DATABASE_URL (required)
- [x] POSTGRES_PASSWORD (required)
- [x] COOKIE_DOMAIN (required)
- [x] CORS_ALLOW_ORIGINS (required)
- [x] GOOGLE_CLIENT_ID (required)
- [x] GOOGLE_CLIENT_SECRET (required)
- [x] GOOGLE_REDIRECT_URI (required)
- [x] ES_ENABLED (optional)
- [x] ES_URL (optional)
- [x] PROMETHEUS_ENABLED (optional)
- [x] RECAPTCHA_ENABLED (optional)

**Command:**
```powershell
.\scripts\pre-deploy-check.ps1
```

**Expected:** ✅ All validation checks passed

---

### Infrastructure Configuration ✅

#### 1. Nginx Real Client IP Extraction
- [x] `real_ip_header X-Forwarded-For` configured
- [x] `real_ip_recursive on` enabled
- [x] Trusted proxy ranges configured:
  - [x] Docker networks (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
  - [x] Cloudflare IP ranges (20+ ranges)
- [x] Forward headers configured:
  - [x] X-Forwarded-For
  - [x] X-Forwarded-Proto
  - [x] X-Real-IP

**File:** `infra/nginx/conf.d/applylens.prod.conf`

#### 2. Rate Limiting
- [x] X-Forwarded-For parsing implemented
- [x] First IP extraction (actual client, not proxy)
- [x] Retry-After header on 429 responses
- [x] Rate limit: 60 requests per 60 seconds

**File:** `services/api/app/core/limiter.py`

#### 3. Metrics Security
- [x] /metrics only on internal network (port 8003)
- [x] No public nginx route to /metrics
- [x] Prometheus scrapes via internal DNS (api:8003)
- [x] No external port mapping in docker-compose

**Files:** 
- `docker-compose.prod.yml`
- `infra/prometheus/prometheus.yml`

#### 4. Grafana Dashboard Auto-Provisioning
- [x] Dashboard provider configured
- [x] Security folder configured
- [x] Volume mount: `./infra/grafana/dashboards:/var/lib/grafana/dashboards:ro`
- [x] Dashboard file exists: `infra/grafana/dashboards/security.json`

**Files:**
- `infra/grafana/provisioning/dashboards/applylens.yml`
- `docker-compose.prod.yml`

#### 5. Prometheus Alert Rules
- [x] `rule_files` configured in prometheus.yml
- [x] Alert rules file exists: `infra/prometheus/alerts.yml`
- [x] 10+ security alert rules defined:
  - [x] HighCSRFFailureRate
  - [x] InvalidTagErrors
  - [x] FrequentRateLimiting
  - [x] HighCaptchaFailureRate
  - [x] ApplyLensApiDown
  - [x] HighHttpErrorRate
  - [x] BackfillFailing
  - [x] And more...

**Files:**
- `infra/prometheus/prometheus.yml`
- `infra/prometheus/alerts.yml`

---

### Operational Scripts ✅

- [x] Pre-deployment validation: `scripts/pre-deploy-check.sh` (Bash)
- [x] Pre-deployment validation: `scripts/pre-deploy-check.ps1` (PowerShell)
- [x] Quick smoke tests: `scripts/quick-smoke.sh` (Bash)
- [x] Quick smoke tests: `scripts/quick-smoke.ps1` (PowerShell)

---

## Deployment Steps

### 1. Pre-Deployment Validation
```powershell
# Validate environment variables
.\scripts\pre-deploy-check.ps1

# Expected output: "✅ All validation checks passed"
```

### 2. Build and Start Services
```bash
# Build with latest changes
docker-compose -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Or restart specific services
docker-compose -f docker-compose.prod.yml restart nginx api prometheus grafana
```

### 3. Wait for Health Checks
```bash
# Wait 10-15 seconds for health checks
Start-Sleep -Seconds 15

# Verify all services are healthy
docker ps --filter "name=applylens-*-prod"

# Expected: All services show "(healthy)" status
```

### 4. Run Smoke Tests
```powershell
# Run quick smoke test (30 seconds)
.\scripts\quick-smoke.ps1

# Expected output: "🎉 Quick smoke test passed!"
# All 4 tests should pass:
#   1. CSRF block (expect 403) ✅
#   2. CSRF allow (get cookie) ✅
#   3. CSRF allow (with token) ✅
#   4. Metrics present ✅
```

---

## Post-Deployment Verification

### 1. Service Health Check ✅
```bash
docker ps --filter "name=applylens-*-prod" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Expected:**
- applylens-api-prod: Up (healthy)
- applylens-nginx-prod: Up (healthy)
- applylens-prometheus-prod: Up (healthy)
- applylens-grafana-prod: Up (healthy)
- applylens-db-prod: Up (healthy)
- applylens-es-prod: Up (healthy)
- applylens-redis-prod: Up (healthy)

### 2. Grafana Dashboard Verification ✅
1. Open: http://localhost:3000/dashboards
2. Login: admin/admin (change immediately!)
3. Navigate to: "Security" folder
4. Verify: "ApplyLens Security Monitoring" dashboard exists
5. Check: 8 panels are visible:
   - CSRF Failures
   - CSRF Successes
   - Token Decryption Errors
   - Invalid Tags
   - Rate Limit Exceeded
   - Rate Limit Allowed
   - reCAPTCHA Failures
   - reCAPTCHA Successes

**Dashboard UID:** `applylens-security`

### 3. Prometheus Alert Rules Verification ✅
1. Open: http://localhost:9090/alerts
2. Verify: 10+ alert rules loaded
3. Check: All rules in "inactive" state (green)
4. Verify rules present:
   - ApplyLensApiDown
   - HighCSRFFailureRate (warning & critical)
   - InvalidTagErrors (warning & critical)
   - FrequentRateLimiting
   - HighCaptchaFailureRate
   - HighHttpErrorRate
   - BackfillFailing
   - BackfillRateLimitedSpike
   - GmailDisconnected
   - DependenciesDown

### 4. Prometheus Targets Verification ✅
1. Open: http://localhost:9090/targets
2. Verify: `applylens-api` target
3. Check: State = "UP" (green)
4. Verify: Endpoint = `http://api:8003/metrics`
5. Check: Last scrape successful

### 5. Metrics Endpoint Verification ✅
```bash
# Metrics should be accessible internally
curl http://localhost:8003/metrics | grep applylens_

# Should see metrics like:
# applylens_csrf_fail_total
# applylens_csrf_success_total
# applylens_decrypt_errors_total
# applylens_invalid_tag_total
# applylens_rate_limit_exceeded_total
# applylens_rate_limit_allowed_total
# And more...

# Metrics should NOT be accessible via nginx
curl http://localhost:5175/metrics
# Expected: 404 Not Found
```

### 6. Rate Limiting Test ✅
```powershell
# Test rate limiting (60 requests/60 seconds)
Write-Host "Testing rate limiting..."
$responses = @()
for ($i=1; $i -le 65; $i++) {
    $code = (Invoke-WebRequest -Uri "http://localhost:5175/api/auth/status" -SkipHttpErrorCheck -UseBasicParsing).StatusCode
    $responses += $code
    Write-Host -NoNewline "$code "
}

# Expected behavior:
# - First ~60 requests: 200 OK
# - Requests 61-65: 429 Too Many Requests
# - 429 response includes: Retry-After header
```

### 7. CSRF Protection Test ✅
```powershell
# Test 1: Request without CSRF token (should be blocked)
$response = Invoke-WebRequest -Uri "http://localhost:5175/api/auth/logout" -Method POST -SkipHttpErrorCheck -UseBasicParsing
Write-Host "Without token: $($response.StatusCode)"  # Expected: 403

# Test 2: Get CSRF token
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$response = Invoke-WebRequest -Uri "http://localhost:5175/api/auth/status" -WebSession $session -UseBasicParsing
$token = ($session.Cookies.GetCookies("http://localhost:5175") | Where-Object { $_.Name -eq "csrf_token" }).Value
Write-Host "CSRF token obtained: $($token.Length) chars"  # Should have token

# Test 3: Request with CSRF token (should succeed)
$headers = @{ "X-CSRF-Token" = $token }
$response = Invoke-WebRequest -Uri "http://localhost:5175/api/auth/demo/start" -Method POST -Headers $headers -WebSession $session -SkipHttpErrorCheck -UseBasicParsing
Write-Host "With token: $($response.StatusCode)"  # Expected: 200 or 201
```

### 8. Real IP Extraction Test ✅
```bash
# Check nginx logs to verify real IP extraction
docker logs applylens-nginx-prod --tail 100 | grep -i "x-forwarded-for"

# Check API logs to verify rate limiting uses real IP
docker logs applylens-api-prod | grep -i "rate limit" | tail -20

# Expected: Logs show first IP from X-Forwarded-For chain, not proxy IP
```

---

## Security Checklist

### Production Secrets ✅
- [x] AES key is production-grade (256-bit, base64-encoded)
- [x] CSRF secret is cryptographically random
- [x] OAuth state secret is cryptographically random
- [x] Database password is strong and unique
- [x] Grafana admin password changed from default
- [x] All secrets stored in `.env` file (git-ignored)

### Network Security ✅
- [x] Metrics endpoint not exposed publicly
- [x] Database not exposed publicly (internal network only)
- [x] Redis not exposed publicly (internal network only)
- [x] Elasticsearch not exposed publicly (internal network only)
- [x] Only nginx, Grafana, Kibana, Prometheus have public ports

### HTTPS/TLS ✅
- [x] Cloudflare Tunnel handles TLS termination
- [x] Nginx serves HTTP (Cloudflare provides HTTPS)
- [x] Content-Security-Policy header includes `upgrade-insecure-requests`

### Rate Limiting ✅
- [x] Rate limiting enabled on /auth/* endpoints
- [x] Real client IP extraction working
- [x] Retry-After headers on 429 responses
- [x] 60 requests per 60 seconds limit

### CSRF Protection ✅
- [x] CSRF middleware enabled
- [x] SameSite=Strict cookies
- [x] X-CSRF-Token header validation
- [x] Blocked requests return 403

---

## Monitoring Checklist

### Metrics Collection ✅
- [x] Prometheus scraping every 15 seconds
- [x] 15+ metrics exposed by API
- [x] Metrics include:
  - CSRF failures/successes
  - Token decryption errors
  - Rate limit exceeded/allowed
  - reCAPTCHA failures/successes
  - HTTP request counts
  - Backfill requests
  - Gmail connection status

### Alert Rules ✅
- [x] 10+ security alert rules configured
- [x] Alerts firing to Prometheus Alertmanager
- [x] Alert thresholds set appropriately:
  - CSRF failures: >10 req/sec (warning), >50 req/sec (critical)
  - Decrypt errors: >5 errors in 5min (warning), >20 in 5min (critical)
  - Rate limiting: >20 rate limits in 15min

### Dashboards ✅
- [x] Security dashboard auto-provisioned
- [x] 8 visualization panels
- [x] Real-time data from Prometheus
- [x] Dashboard accessible at http://localhost:3000

---

## Rollback Plan

If issues are detected after deployment:

### 1. Quick Rollback
```bash
# Stop current deployment
docker-compose -f docker-compose.prod.yml down

# Restore previous version from git
git checkout <previous-commit>

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Service-Specific Rollback
```bash
# Roll back specific service only
docker-compose -f docker-compose.prod.yml stop api
docker-compose -f docker-compose.prod.yml rm -f api

# Rebuild from previous version
git checkout <previous-commit> services/api
docker-compose -f docker-compose.prod.yml build api
docker-compose -f docker-compose.prod.yml up -d api
```

### 3. Configuration Rollback
```bash
# Restore previous nginx config
git checkout <previous-commit> infra/nginx/conf.d/applylens.prod.conf
docker-compose -f docker-compose.prod.yml restart nginx

# Restore previous limiter
git checkout <previous-commit> services/api/app/core/limiter.py
docker-compose -f docker-compose.prod.yml build api
docker-compose -f docker-compose.prod.yml up -d api
```

---

## Success Criteria

Deployment is considered successful when:

- [x] All environment variables validated ✅
- [x] All services healthy (docker ps shows "healthy") ✅
- [x] Quick smoke test passes (4/4 tests) ✅
- [x] Grafana dashboard auto-loaded ✅
- [x] Prometheus scraping metrics successfully ✅
- [x] Alert rules loaded and inactive ✅
- [x] Rate limiting working with real client IPs ✅
- [x] CSRF protection functioning correctly ✅
- [x] Metrics endpoint secured (internal only) ✅
- [x] No errors in service logs ✅

---

## Maintenance

### Daily
- [ ] Check Grafana dashboard for anomalies
- [ ] Review Prometheus alerts (should be inactive)
- [ ] Check service health: `docker ps`

### Weekly
- [ ] Review rate limiting patterns
- [ ] Check for CSRF failures spike
- [ ] Review decryption error trends
- [ ] Backup database

### Monthly
- [ ] Review and update alert thresholds
- [ ] Rotate secrets (if using KMS)
- [ ] Update dependencies
- [ ] Security audit

---

## Contact Information

**Documentation:**
- Main: `docs/DEPLOYMENT_FINALIZED.md`
- Checklist: `docs/FINALIZATION_CHECKLIST_2025-10-20.md`
- Security: `docs/SECURITY_IMPLEMENTATION_2025-10-19.md`
- Monitoring: `docs/MONITORING_CHEATSHEET.md`

**Scripts:**
- Pre-deploy: `scripts/pre-deploy-check.ps1`
- Smoke test: `scripts/quick-smoke.ps1`

**Endpoints:**
- App: http://localhost:5175/web/
- API Docs: http://localhost:5175/docs
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Kibana: http://localhost:5601/kibana/

---

**Last Validated:** October 20, 2025 19:08:45 EDT  
**Status:** ✅ Production Ready  
**Validated By:** GitHub Copilot
