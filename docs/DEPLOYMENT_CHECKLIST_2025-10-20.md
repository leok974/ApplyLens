# Production Deployment Checklist - Security Features

**Date**: October 20, 2025  
**Status**: Ready for Production Deployment

## ✅ Pre-Deployment Checklist

### 1. Generate Production AES Key

```powershell
# Generate secure key
python scripts/generate_aes_key.py

# Output example:
# sh0RoRrKrGbKX-z4WusVSOc0CsY2mtnE7vyiq2CCqXY=
```

**Status**: ⚠️ Key generated, needs to be stored

### 2. Store Key in Secrets Manager

#### Option A: GCP Secret Manager

```bash
# Create secret
echo 'sh0RoRrKrGbKX-z4WusVSOc0CsY2mtnE7vyiq2CCqXY=' | \
  gcloud secrets create APPLYLENS_AES_KEY_BASE64 \
  --project=YOUR_PROJECT_ID \
  --data-file=- \
  --replication-policy="automatic"

# Grant access to service account
gcloud secrets add-iam-policy-binding APPLYLENS_AES_KEY_BASE64 \
  --project=YOUR_PROJECT_ID \
  --member="serviceAccount:applylens-api@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Verify
gcloud secrets versions access latest \
  --secret="APPLYLENS_AES_KEY_BASE64" \
  --project=YOUR_PROJECT_ID
```

#### Option B: AWS Secrets Manager

```bash
# Create secret
aws secretsmanager create-secret \
  --name APPLYLENS_AES_KEY_BASE64 \
  --description "ApplyLens AES-256 encryption key" \
  --secret-string 'sh0RoRrKrGbKX-z4WusVSOc0CsY2mtnE7vyiq2CCqXY=' \
  --region us-east-1

# Grant access via IAM policy
aws secretsmanager put-resource-policy \
  --secret-id APPLYLENS_AES_KEY_BASE64 \
  --resource-policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::ACCOUNT_ID:role/applylens-api"},
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "*"
    }]
  }' \
  --region us-east-1

# Verify
aws secretsmanager get-secret-value \
  --secret-id APPLYLENS_AES_KEY_BASE64 \
  --region us-east-1 \
  --query 'SecretString' \
  --output text
```

**Status**: ⚠️ Pending - Choose GCP or AWS

### 3. Update Environment Configuration

Create `.env.production` file:

```bash
# Security
APPLYLENS_AES_KEY_BASE64=sh0RoRrKrGbKX-z4WusVSOc0CsY2mtnE7vyiq2CCqXY=

# Or fetch from secrets manager on startup:
# APPLYLENS_AES_KEY_BASE64=$(gcloud secrets versions access latest --secret=APPLYLENS_AES_KEY_BASE64)

# reCAPTCHA (optional - currently disabled)
RECAPTCHA_ENABLED=false
RECAPTCHA_SITE_KEY=your_site_key_here
RECAPTCHA_SECRET_KEY=your_secret_key_here
RECAPTCHA_MIN_SCORE=0.5

# CSRF
CSRF_SECRET_KEY=<generate_with_secrets.token_urlsafe(32)>

# Monitoring
PROMETHEUS_ENABLED=true
```

**Status**: ⚠️ Pending - Update docker-compose.prod.yml

### 4. Update Docker Compose Configuration

Add to `docker-compose.prod.yml` API service environment:

```yaml
api:
  environment:
    # ... existing vars ...
    
    # Security - Token Encryption
    APPLYLENS_AES_KEY_BASE64: ${APPLYLENS_AES_KEY_BASE64}
    
    # Security - CSRF Protection
    CSRF_SECRET_KEY: ${CSRF_SECRET_KEY}
    
    # Security - reCAPTCHA
    RECAPTCHA_ENABLED: ${RECAPTCHA_ENABLED:-false}
    RECAPTCHA_SITE_KEY: ${RECAPTCHA_SITE_KEY:-}
    RECAPTCHA_SECRET_KEY: ${RECAPTCHA_SECRET_KEY:-}
    RECAPTCHA_MIN_SCORE: ${RECAPTCHA_MIN_SCORE:-0.5}
    
    # Monitoring
    PROMETHEUS_ENABLED: ${PROMETHEUS_ENABLED:-true}
```

**Status**: ⚠️ Pending - Manual edit required

### 5. Verify Prometheus Configuration

Check `infra/prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: applylens-api
    metrics_path: /metrics
    static_configs:
      - targets: ["api:8003"]
    scrape_interval: 15s
```

**Status**: ✅ Already configured

### 6. Verify Alertmanager Rules

Check `infra/prometheus/alerts.yml`:

- ✅ CSRF failure alerts
- ✅ Token decryption error alerts
- ✅ Rate limiting alerts
- ✅ reCAPTCHA alerts
- ✅ Authentication alerts

**Status**: ✅ Updated with security alerts

### 7. Import Grafana Dashboard

Dashboard location: `infra/grafana/dashboards/security.json`

Panels include:
- CSRF failures/successes
- Token decryption errors
- Crypto operation duration (p95)
- Rate limiting (allowed vs exceeded)
- reCAPTCHA status distribution
- reCAPTCHA score median
- Total crypto operations

**Status**: ✅ Dashboard created

## 🚀 Deployment Steps

### Step 1: Backup Current Database

```powershell
# Export current database
docker exec applylens-db-prod pg_dump -U postgres -d applylens > backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql

# Or with compression
docker exec applylens-db-prod pg_dump -U postgres -d applylens | gzip > backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql.gz
```

**Status**: ⚠️ Execute before deployment

### Step 2: Store Production AES Key

```powershell
# For local development, add to .env file:
Add-Content -Path "infra\.env" -Value "`nAPPLYLENS_AES_KEY_BASE64=sh0RoRrKrGbKX-z4WusVSOc0CsY2mtnE7vyiq2CCqXY="

# For production, use secrets manager (see step 2 above)
```

**Status**: ⚠️ Pending

### Step 3: Rebuild API Container

```powershell
# Stop current API
docker-compose -f docker-compose.prod.yml stop api

# Rebuild with new environment
docker-compose -f docker-compose.prod.yml build api

# Start API
docker-compose -f docker-compose.prod.yml up -d api

# Wait for health check
Start-Sleep -Seconds 10
```

**Status**: ⚠️ Pending

### Step 4: Verify No Ephemeral Key Warning

```powershell
# Check logs for ephemeral key warning
docker logs applylens-api-prod 2>&1 | Select-String -Pattern "ephemeral|EPHEMERAL"

# Expected: No output (warning should be gone)
```

**Status**: ⚠️ Pending verification

### Step 5: Run Smoke Tests

```powershell
# Run comprehensive smoke tests
.\scripts\ci-smoke-test.ps1 -Base "http://localhost:5175"

# Expected output:
# Testing http://localhost:5175...
# Getting CSRF cookie... ✅
# Testing CSRF block... ✅
# Testing CSRF allow... ✅
# Testing metrics... ✅
# Testing health... ✅
# Testing crypto metrics... ✅
# Testing rate limit metrics... ✅
# 🎉 All smoke tests passed!
```

**Status**: ✅ Script ready (last run: all passed)

### Step 6: Verify Metrics in Prometheus

```powershell
# Check Prometheus targets
Start-Process "http://localhost:9090/targets"

# Check metrics are being scraped
Start-Process "http://localhost:9090/graph?g0.expr=applylens_csrf_fail_total"
```

**Status**: ⚠️ Pending verification

### Step 7: Import Grafana Dashboard

1. Open Grafana: http://localhost:3000
2. Login with admin credentials
3. Navigate to: Dashboards → Import
4. Upload: `infra/grafana/dashboards/security.json`
5. Select Prometheus datasource
6. Click "Import"

**Status**: ⚠️ Manual import required

### Step 8: Test Alert Rules

```powershell
# Generate CSRF failures to test alert
for ($i=0; $i -lt 20; $i++) {
    Invoke-WebRequest -Uri "http://localhost:5175/api/auth/logout" -Method POST -ErrorAction SilentlyContinue
}

# Check Prometheus alerts (should see HighCSRFFailureRate pending/firing)
Start-Process "http://localhost:9090/alerts"
```

**Status**: ⚠️ Pending testing

## 📊 Post-Deployment Verification

### Health Checks

```powershell
# API health
curl http://localhost:5175/api/healthz

# Metrics endpoint
curl http://localhost:5175/api/metrics | Select-String "applylens_"

# Prometheus targets
curl http://localhost:9090/api/v1/targets | ConvertFrom-Json | Select-Object -ExpandProperty data
```

### Security Feature Verification

```powershell
# 1. CSRF Protection
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-WebRequest -Uri "http://localhost:5175/api/auth/status" -WebSession $session
$token = ($session.Cookies.GetCookies("http://localhost:5175") | Where-Object {$_.Name -eq "csrf_token"}).Value

# Should fail (403)
Invoke-WebRequest -Uri "http://localhost:5175/api/auth/logout" -Method POST -ErrorAction SilentlyContinue

# Should succeed (200/400)
Invoke-WebRequest -Uri "http://localhost:5175/api/auth/demo/start" -Method POST -Headers @{"X-CSRF-Token"=$token} -WebSession $session

# 2. Token Encryption (check no ephemeral warning)
docker logs applylens-api-prod --tail 100 | Select-String "ephemeral"
# Expected: No output

# 3. Metrics Collection
curl http://localhost:5175/api/metrics | Select-String "applylens_csrf_fail_total"
# Expected: applylens_csrf_fail_total{path="/api/auth/logout",method="POST"} 1.0
```

### Monitoring Verification

```powershell
# Check Grafana dashboard
Start-Process "http://localhost:3000/d/applylens-security"

# Check Prometheus alerts
Start-Process "http://localhost:9090/alerts"

# Check Prometheus metrics
Start-Process "http://localhost:9090/graph?g0.expr=applylens_csrf_fail_total&g0.tab=0&g0.stacked=0&g0.show_exemplars=0&g0.range_input=1h"
```

## 🔄 Optional: Envelope Encryption Setup

### Apply Migration

```powershell
# Run Alembic migration
docker exec applylens-api-prod alembic upgrade head

# Verify table created
docker exec applylens-api-prod psql -U postgres -d applylens -c "\d encryption_keys"
```

### Set Up Cloud KMS

#### GCP Cloud KMS

```bash
# Enable API
gcloud services enable cloudkms.googleapis.com --project=YOUR_PROJECT_ID

# Create keyring
gcloud kms keyrings create applylens-keyring \
  --location=us-central1 \
  --project=YOUR_PROJECT_ID

# Create key
gcloud kms keys create applylens-master-key \
  --location=us-central1 \
  --keyring=applylens-keyring \
  --purpose=encryption \
  --project=YOUR_PROJECT_ID

# Grant service account access
gcloud kms keys add-iam-policy-binding applylens-master-key \
  --location=us-central1 \
  --keyring=applylens-keyring \
  --member="serviceAccount:applylens-api@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudkms.cryptoKeyEncrypterDecrypter" \
  --project=YOUR_PROJECT_ID
```

#### AWS KMS

```bash
# Create KMS key
aws kms create-key \
  --description "ApplyLens master encryption key" \
  --key-usage ENCRYPT_DECRYPT \
  --origin AWS_KMS \
  --region us-east-1

# Create alias
aws kms create-alias \
  --alias-name alias/applylens-master-key \
  --target-key-id <key-id-from-above> \
  --region us-east-1

# Grant IAM role access
aws kms create-grant \
  --key-id alias/applylens-master-key \
  --grantee-principal arn:aws:iam::ACCOUNT_ID:role/applylens-api \
  --operations Encrypt Decrypt \
  --region us-east-1
```

### Rotate to Envelope Encryption

```powershell
# Install dependencies (if not already)
pip install google-cloud-kms boto3

# Rotate key with KMS
python scripts/keys.py rotate --kms gcp --key-id "projects/YOUR_PROJECT/locations/us-central1/keyRings/applylens-keyring/cryptoKeys/applylens-master-key"

# Or for AWS
python scripts/keys.py rotate --kms aws --key-id "alias/applylens-master-key"

# List keys
python scripts/keys.py list

# Re-encrypt existing tokens (background job)
python scripts/keys.py re-encrypt --from-version 1 --to-version 2
```

## 📝 Documentation Updates

- ✅ `docs/SECURITY_KEYS_AND_CSRF.md` - Comprehensive security guide
- ✅ `docs/VERIFICATION_MONITORING_CHEATSHEET.md` - Operations runbook
- ✅ `docs/SMOKE_TEST_RESULTS.md` - Test results and CI integration
- ✅ `docs/IMPLEMENTATION_COMPLETE_2025-10-20.md` - Implementation summary
- ✅ `docs/DEPLOYMENT_CHECKLIST_2025-10-20.md` - This document

## ⚠️ Rollback Plan

If issues occur after deployment:

### Quick Rollback

```powershell
# Stop new API
docker-compose -f docker-compose.prod.yml stop api

# Restore previous image
docker tag applylens-api:latest applylens-api:backup-$(Get-Date -Format 'yyyyMMdd')
docker pull applylens-api:previous  # Or your previous tag
docker tag applylens-api:previous applylens-api:latest

# Restart
docker-compose -f docker-compose.prod.yml up -d api
```

### Database Rollback

```powershell
# Restore database backup
docker exec -i applylens-db-prod psql -U postgres -d applylens < backup_20251020_120000.sql
```

### Emergency: Disable CSRF

```powershell
# Only if absolutely necessary
docker-compose -f docker-compose.prod.yml stop api
# Add CSRF_EXEMPT=true to environment
# Restart
docker-compose -f docker-compose.prod.yml up -d api
```

## 📞 Support Contacts

- **Security Issues**: [Your security team contact]
- **On-Call Engineer**: [Your on-call rotation]
- **Monitoring**: Grafana (http://localhost:3000), Prometheus (http://localhost:9090)

## ✅ Sign-Off

- [ ] **AES Key Generated**: `python scripts/generate_aes_key.py`
- [ ] **Key Stored in Secrets Manager**: GCP or AWS
- [ ] **Environment Updated**: docker-compose.prod.yml with APPLYLENS_AES_KEY_BASE64
- [ ] **API Rebuilt**: `docker-compose -f docker-compose.prod.yml build api`
- [ ] **No Ephemeral Key Warning**: Verified in logs
- [ ] **Smoke Tests Pass**: All 7 tests ✅
- [ ] **Prometheus Scraping**: Verified at http://localhost:9090/targets
- [ ] **Grafana Dashboard Imported**: Security dashboard visible
- [ ] **Alerts Configured**: Verified in Prometheus alerts page
- [ ] **Backup Taken**: Database backup before deployment
- [ ] **Documentation Updated**: All docs complete

**Deployment Date**: _______________  
**Deployed By**: _______________  
**Verified By**: _______________  

---

**Next Review Date**: {{ 90 days from deployment }}  
**Key Rotation Schedule**: Every 90 days (envelope encryption with KMS)
