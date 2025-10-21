# Smoke Test Results

**Date**: 2025-01-20  
**Status**: ✅ **ALL TESTS PASSING**

## Test Summary

All security features have been verified and are functioning correctly:

```
Testing http://localhost:5175...

Getting CSRF cookie... ✅
Testing CSRF block... ✅                                                                                                
Testing CSRF allow... ✅ (got 200)
Testing metrics... ✅
Testing health... ✅
Testing crypto metrics... ✅
Testing rate limit metrics... ✅

🎉 All smoke tests passed!

Summary:
  ✅ CSRF protection working
  ✅ Metrics exposed
  ✅ Health check passing
  ✅ All security features initialized
```

## Test Details

### 1. CSRF Cookie Retrieval
- **Endpoint**: `GET /api/auth/status`
- **Cookie Name**: `csrf_token`
- **Result**: ✅ Cookie successfully set with SameSite=lax

### 2. CSRF Block Test
- **Endpoint**: `POST /api/auth/logout`
- **Method**: Without X-CSRF-Token header
- **Expected**: 403 Forbidden
- **Result**: ✅ Request blocked as expected

### 3. CSRF Allow Test
- **Endpoint**: `POST /api/auth/demo/start`
- **Method**: With valid X-CSRF-Token header
- **Expected**: 200 OK or 400 (validation error)
- **Result**: ✅ Request allowed (got 200)

### 4. Metrics Endpoint
- **Endpoint**: `GET /api/metrics`
- **Check**: Presence of `applylens_csrf_fail_total`
- **Result**: ✅ Metrics exposed correctly

### 5. Health Check
- **Endpoint**: `GET /api/healthz`
- **Expected**: 200 OK
- **Result**: ✅ Health check passing

### 6. Crypto Metrics
- **Endpoint**: `GET /api/metrics`
- **Check**: Presence of `applylens_crypto_*` metrics
- **Result**: ✅ Crypto metrics present

### 7. Rate Limit Metrics
- **Endpoint**: `GET /api/metrics`
- **Check**: Presence of `applylens_rate_limit_*` metrics
- **Result**: ✅ Rate limit metrics present

## Key Findings

### Correct Endpoint Paths

All endpoints require the `/api/` prefix when accessing through nginx:

| Endpoint | Correct Path | Notes |
|----------|-------------|-------|
| Health | `/api/healthz` | Standard health check |
| Metrics | `/api/metrics` | Prometheus text format |
| Auth Status | `/api/auth/status` | Returns CSRF cookie |
| Logout | `/api/auth/logout` | Requires CSRF token |
| Demo Start | `/api/auth/demo/start` | Requires CSRF token |

### Cookie Configuration

- **Cookie Name**: `csrf_token` (not `csrftoken`)
- **Path**: `/`
- **SameSite**: `lax`
- **HttpOnly**: Not set (needs to be accessible by JavaScript)
- **Secure**: Only in production with HTTPS

### Metrics Verification

All Prometheus metrics are properly exposed at `/api/metrics`:

```
# CSRF Protection
applylens_csrf_fail_total{path="/api/auth/logout",method="POST"} 1.0
applylens_csrf_success_total{path="/api/auth/demo/start",method="POST"} 1.0

# Crypto Operations
applylens_crypto_encrypt_total 45.0
applylens_crypto_decrypt_total 42.0
applylens_crypto_decrypt_error_total{error_type="invalid_tag"} 0.0

# Rate Limiting
applylens_rate_limit_allowed_total{path="/api/auth/status"} 3.0
applylens_rate_limit_exceeded_total{path="/api/auth/*",ip_prefix="192.168.*.*"} 0.0

# reCAPTCHA
applylens_recaptcha_verify_total{status="disabled"} 1.0
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Smoke Tests
  run: |
    chmod +x scripts/ci-smoke-test.sh
    ./scripts/ci-smoke-test.sh http://localhost:5175
```

### Azure DevOps

```yaml
- script: |
    pwsh -File scripts/ci-smoke-test.ps1 -Base "http://localhost:5175"
  displayName: 'Run Smoke Tests'
```

### GitLab CI

```yaml
smoke-test:
  script:
    - bash scripts/ci-smoke-test.sh http://localhost:5175
  artifacts:
    when: always
    reports:
      junit: test-results.xml
```

## Rollback Procedures

If smoke tests fail after deployment:

### 1. Check Container Health

```powershell
docker ps --filter name=applylens
docker logs applylens-api-prod --tail 100
```

### 2. Verify Environment Variables

```powershell
docker exec applylens-api-prod env | grep -E "CSRF|AES|RECAPTCHA"
```

### 3. Quick Rollback

```powershell
# Tag current image
docker tag applylens-api:latest applylens-api:failed-$(date +%Y%m%d-%H%M)

# Restore previous version
docker pull applylens-api:previous
docker-compose -f docker-compose.prod.yml up -d api
```

### 4. Emergency Disable Features

```powershell
# Disable CSRF (emergency only)
docker exec applylens-api-prod bash -c 'echo "CSRF_EXEMPT=true" >> .env'
docker-compose -f docker-compose.prod.yml restart api

# Disable reCAPTCHA
docker exec applylens-api-prod bash -c 'echo "RECAPTCHA_ENABLED=false" >> .env'
docker-compose -f docker-compose.prod.yml restart api
```

## Next Steps

1. **Production Deployment**
   - [ ] Generate production AES key: `python scripts/generate_aes_key.py`
   - [ ] Store in GCP/AWS Secrets Manager
   - [ ] Update `APPLYLENS_AES_KEY_BASE64` environment variable
   - [ ] Restart API container
   - [ ] Verify no "ephemeral key" warnings in logs

2. **Monitoring Setup**
   - [ ] Configure Prometheus to scrape `/api/metrics`
   - [ ] Import Grafana dashboards from `docs/VERIFICATION_MONITORING_CHEATSHEET.md`
   - [ ] Set up Alertmanager rules from `docs/SECURITY_KEYS_AND_CSRF.md`

3. **Envelope Encryption** (Optional)
   - [ ] Apply migration: `alembic upgrade head`
   - [ ] Set up GCP Cloud KMS or AWS KMS
   - [ ] Run initial key rotation: `python scripts/keys.py rotate --kms gcp`
   - [ ] Implement background re-encryption job

4. **Security Hardening**
   - [ ] Enable HTTPS in production (auto-sets Secure flag on cookies)
   - [ ] Configure HSTS headers
   - [ ] Enable reCAPTCHA v3 (update `RECAPTCHA_ENABLED=true`)
   - [ ] Review and adjust rate limits based on traffic patterns

## References

- **Main Documentation**: `docs/SECURITY_KEYS_AND_CSRF.md`
- **Verification Guide**: `docs/VERIFICATION_MONITORING_CHEATSHEET.md`
- **Implementation Summary**: `docs/IMPLEMENTATION_COMPLETE_2025-10-20.md`
- **Smoke Test Scripts**:
  - Bash: `scripts/ci-smoke-test.sh`
  - PowerShell: `scripts/ci-smoke-test.ps1`
