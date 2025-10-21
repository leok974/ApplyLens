# Security Keys and CSRF Protection

**Date:** October 20, 2025  
**Author:** GitHub Copilot  
**Status:** Production-Ready with Future Enhancements

---

## Table of Contents

1. [Overview](#overview)
2. [Token Encryption](#token-encryption)
3. [CSRF Protection](#csrf-protection)
4. [Development vs Production](#development-vs-production)
5. [Key Management](#key-management)
6. [Envelope Encryption & Rotation](#envelope-encryption--rotation)
7. [Monitoring & Metrics](#monitoring--metrics)
8. [Deployment Guide](#deployment-guide)
9. [Troubleshooting](#troubleshooting)

---

## Overview

ApplyLens implements multiple layers of security to protect OAuth tokens and prevent Cross-Site Request Forgery (CSRF) attacks:

1. **AES-GCM Encryption** - OAuth tokens encrypted at rest in database
2. **CSRF Middleware** - Validates CSRF tokens on all state-changing requests
3. **Rate Limiting** - Protects auth endpoints from brute force attacks
4. **reCAPTCHA Support** - Optional bot protection (disabled by default)
5. **Envelope Encryption** - KMS-backed key rotation (future enhancement)

### Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    HTTP Request                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Rate Limiter        │ ← 60 req/60sec on /auth/*
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  CSRF Middleware     │ ← Validate token on POST/PUT/DELETE
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Session Middleware  │ ← OAuth state management
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Request Handler     │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Crypto Module       │ ← Encrypt/decrypt tokens
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  PostgreSQL          │ ← LargeBinary encrypted tokens
          └──────────────────────┘
```

---

## Token Encryption

### How It Works

**Encryption Flow:**
```python
# Login → Store token
plaintext = b"ya29.a0AfH6SMB..."
nonce = os.urandom(12)  # 96-bit random nonce
ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
blob = base64.urlsafe_b64encode(nonce + ciphertext)
db.execute("INSERT INTO oauth_tokens (access_token) VALUES (%s)", blob)

# API call → Retrieve token
blob = db.query(OAuthToken).first().access_token
raw = base64.urlsafe_b64decode(blob)
nonce, ciphertext = raw[:12], raw[12:]
plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
# Use plaintext to call Gmail API
```

**Algorithm:** AES-256-GCM (Authenticated Encryption with Associated Data)

**Key Properties:**
- 256-bit key (32 bytes)
- 96-bit nonce (12 bytes) - unique per encryption
- Authentication tag prevents tampering
- FIPS 140-2 compliant

### Configuration

**Environment Variables:**
```bash
# Enable/disable encryption
APPLYLENS_ENCRYPTION_ENABLED=1

# Production key (base64url-encoded 32 bytes)
APPLYLENS_AES_KEY_BASE64=<generated-key>

# Future: KMS key for envelope encryption
APPLYLENS_KMS_KEY_ID=projects/my-project/locations/global/keyRings/applylens/cryptoKeys/token-key
```

**Generate Production Key:**
```bash
# Using Python
python scripts/generate_aes_key.py

# Or directly
python -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"

# Output example:
# xQ7vK9mN2pL8wR5tY6uE3oA1sD4fG7hJ9kZ0cX1vB2n=
```

### Database Schema

```sql
-- oauth_tokens table
CREATE TABLE oauth_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    access_token BYTEA NOT NULL,  -- Encrypted with AES-GCM
    refresh_token BYTEA,           -- Encrypted with AES-GCM
    key_version INTEGER,           -- Which key version was used
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## CSRF Protection

### How It Works

**CSRF Token Flow:**
```
1. User visits site → CSRFMiddleware generates token → Set-Cookie: csrftoken=abc123
2. Frontend reads cookie → Stores in memory
3. User submits form → Adds X-CSRF-Token: abc123 header
4. Server validates: request.headers['X-CSRF-Token'] == request.cookies['csrftoken']
5. If match → Process request (200)
   If mismatch → Reject (403)
```

**Protected Methods:** POST, PUT, PATCH, DELETE

**Safe Methods (No CSRF check):** GET, HEAD, OPTIONS

### Configuration

**Environment Variables:**
```bash
# Enable/disable CSRF protection
APPLYLENS_CSRF_ENABLED=1

# Cookie name
APPLYLENS_CSRF_COOKIE_NAME=csrftoken

# Header name
APPLYLENS_CSRF_HEADER_NAME=X-CSRF-Token

# Cookie security
APPLYLENS_COOKIE_SECURE=1  # HTTPS only (production)
```

**Cookie Properties:**
- `httponly=False` - JavaScript can read (required for AJAX)
- `secure=True` - HTTPS only (production)
- `samesite=lax` - Prevents cross-site sends
- `path=/` - Available on all routes

### Frontend Integration

**Fetch Wrapper (`apps/web/src/api/fetcher.ts`):**
```typescript
function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? match[2] : null;
}

export async function api(path: string, init?: RequestInit) {
  const headers = new Headers(init?.headers);
  
  // Add CSRF token for non-GET requests
  if (init?.method && init.method !== 'GET') {
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) {
      headers.set('X-CSRF-Token', csrfToken);
    }
  }
  
  return fetch(`/api${path}`, {
    ...init,
    headers,
    credentials: 'include'  // Send cookies
  });
}
```

**Usage:**
```typescript
// All API calls use the wrapper
await api('/auth/demo/start', { method: 'POST' });  // CSRF token added automatically
await api('/auth/logout', { method: 'POST' });
```

---

## Development vs Production

### Development Mode

**Characteristics:**
- Ephemeral AES key (random on startup)
- Tokens **invalid after container restart**
- CSRF can be disabled for debugging
- Rate limiting disabled or lenient

**Configuration:**
```bash
# .env.local
APPLYLENS_ENCRYPTION_ENABLED=1
# AES_KEY_BASE64 not set → ephemeral key
APPLYLENS_CSRF_ENABLED=1
APPLYLENS_RATE_LIMIT_ENABLED=0
```

**⚠️ WARNING:**
- Users must re-login after every API restart
- Tokens stored during dev cannot be decrypted later
- Never use ephemeral keys in production

### Production Mode

**Characteristics:**
- Persistent AES key from Secret Manager
- Tokens survive container restarts
- CSRF **must** be enabled
- Rate limiting **must** be enabled

**Configuration:**
```bash
# Production environment variables
APPLYLENS_ENCRYPTION_ENABLED=1
APPLYLENS_AES_KEY_BASE64=<key-from-secret-manager>
APPLYLENS_CSRF_ENABLED=1
APPLYLENS_RATE_LIMIT_ENABLED=1
APPLYLENS_COOKIE_SECURE=1  # HTTPS only
```

**Key Source:**
```bash
# GCP Secret Manager
export APPLYLENS_AES_KEY_BASE64=$(gcloud secrets versions access latest \
  --secret=APPLYLENS_AES_KEY_BASE64 \
  --project=my-project)

# AWS Secrets Manager
export APPLYLENS_AES_KEY_BASE64=$(aws secretsmanager get-secret-value \
  --secret-id APPLYLENS_AES_KEY_BASE64 \
  --query SecretString \
  --output text \
  --region us-west-2)
```

**Container Deployment:**
```yaml
# Docker Compose
services:
  api:
    environment:
      APPLYLENS_AES_KEY_BASE64: ${APPLYLENS_AES_KEY_BASE64}

# Kubernetes
env:
  - name: APPLYLENS_AES_KEY_BASE64
    valueFrom:
      secretKeyRef:
        name: applylens-secrets
        key: aes-key
```

---

## Key Management

### Secret Manager Setup

**GCP Secret Manager:**
```bash
# Create secret
./scripts/gcp_secrets.sh create my-project api@my-project.iam.gserviceaccount.com

# Retrieve for deployment
export APPLYLENS_AES_KEY_BASE64=$(./scripts/gcp_secrets.sh retrieve my-project)

# Rotate key
./scripts/gcp_secrets.sh rotate my-project

# Grant access to another service account
./scripts/gcp_secrets.sh grant my-project worker@my-project.iam.gserviceaccount.com
```

**AWS Secrets Manager:**
```bash
# Create secret
./scripts/aws_secrets.sh create us-west-2

# Retrieve for deployment
export APPLYLENS_AES_KEY_BASE64=$(./scripts/aws_secrets.sh retrieve us-west-2)

# Rotate key
./scripts/aws_secrets.sh rotate us-west-2

# Grant access to ECS task role
./scripts/aws_secrets.sh grant us-west-2 arn:aws:iam::123456789012:role/applylens-api-task-role
```

### Key Storage Best Practices

**✅ DO:**
- Store production keys in GCP/AWS Secret Manager
- Rotate keys every 90 days
- Use separate keys for dev/staging/prod
- Enable audit logging for secret access
- Use IAM roles, not service account keys

**❌ DON'T:**
- Commit keys to version control
- Email/Slack keys to team members
- Store keys in .env files in production
- Use the same key across environments
- Share keys between applications

---

## Envelope Encryption & Rotation

### Why Envelope Encryption?

**Problem:** Rotating AES keys requires re-encrypting all tokens (expensive)

**Solution:** Wrap AES data keys with KMS, rotate wrapper key only

**Benefits:**
- Fast rotation (no token re-encryption needed)
- Multiple key versions coexist
- Old tokens still decryptable with their version
- Background re-encryption optional

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  KMS Master Key                          │
│         (GCP Cloud KMS / AWS KMS)                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Wrap/Unwrap
                     ▼
┌─────────────────────────────────────────────────────────┐
│          encryption_keys Table                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Version 1: KMS-wrapped AES key (inactive)        │   │
│  │ Version 2: KMS-wrapped AES key (inactive)        │   │
│  │ Version 3: KMS-wrapped AES key (ACTIVE)          │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Unwrap on startup → Get plaintext AES key
                     ▼
┌─────────────────────────────────────────────────────────┐
│              In-Memory AES Keys                          │
│  {                                                       │
│    1: <unwrapped-key-v1>,                                │
│    2: <unwrapped-key-v2>,                                │
│    3: <unwrapped-key-v3>  ← Active for new tokens        │
│  }                                                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Encrypt/Decrypt
                     ▼
┌─────────────────────────────────────────────────────────┐
│             oauth_tokens Table                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │ User A: encrypted token (key_version=1)          │   │
│  │ User B: encrypted token (key_version=2)          │   │
│  │ User C: encrypted token (key_version=3)          │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Database Schema

```sql
-- Key versions table
CREATE TABLE encryption_keys (
    id UUID PRIMARY KEY,
    version INTEGER UNIQUE NOT NULL,
    kms_wrapped_key BYTEA NOT NULL,  -- KMS-encrypted AES key
    algorithm VARCHAR(32) DEFAULT 'AES-GCM-256',
    kms_key_id VARCHAR(512),  -- GCP/AWS KMS key resource ID
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    rotated_at TIMESTAMP  -- When deactivated
);

-- Track which key version encrypted each token
ALTER TABLE oauth_tokens
ADD COLUMN key_version INTEGER REFERENCES encryption_keys(version);
```

### Migration Applied

**File:** `alembic/versions/0032_encryption_keys.py`

**Changes:**
1. Create `encryption_keys` table
2. Add `key_version` column to `oauth_tokens`
3. Backfill existing tokens with `key_version=1`

**Apply Migration:**
```bash
# Run migration
docker exec applylens-api-prod alembic upgrade head

# Verify
docker exec applylens-api-prod psql -U postgres -d applylens -c "SELECT * FROM encryption_keys;"
```

### Key Rotation Workflow

**1. Generate New Key:**
```bash
python scripts/keys.py rotate --kms-key projects/my-project/locations/global/keyRings/applylens/cryptoKeys/token-key
```

**Process:**
- Generate random 256-bit AES data key
- Wrap with GCP/AWS KMS
- Store wrapped key in `encryption_keys` table
- Mark old keys as inactive
- New tokens use new version

**2. List Key Versions:**
```bash
python scripts/keys.py list
```

**Output:**
```
Version    Status      Algorithm        Created              Rotated
--------------------------------------------------------------------------------
3          🟢 ACTIVE   AES-GCM-256      2025-10-20 15:30:00  -
2          🔴 inactive AES-GCM-256      2025-07-15 10:00:00  2025-10-20 15:30:00
1          🔴 inactive AES-GCM-256      2025-04-01 08:00:00  2025-07-15 10:00:00

TOKEN DISTRIBUTION
Version    Token Count
--------------------------------------------------------------------------------
1          2,450
2          8,123
3          1,205
```

**3. Restart API:**
```bash
# API loads all key versions on startup
docker compose up -d --force-recreate api

# Check logs
docker logs applylens-api-prod | grep "encryption"
# Expected: "Loaded 3 encryption key versions (active: v3)"
```

**4. Optional Re-encryption:**
```bash
# Migrate old tokens to new key (background job)
python scripts/keys.py re-encrypt --from-version 1 --to-version 3
```

**Note:** Re-encryption is **optional**. Old tokens work fine with old keys.

---

## Monitoring & Metrics

### Prometheus Metrics

**Exposed at:** `http://localhost:8003/metrics`

**Crypto Metrics:**
```prometheus
# Encryption operations
applylens_crypto_encrypt_total 1234

# Decryption operations
applylens_crypto_decrypt_total 1230

# Decryption errors by type
applylens_crypto_decrypt_error_total{error_type="invalid_tag"} 2
applylens_crypto_decrypt_error_total{error_type="decode_error"} 1
applylens_crypto_decrypt_error_total{error_type="decrypt_error"} 0

# Operation duration
applylens_crypto_operation_duration_seconds_bucket{operation="encrypt",le="0.001"} 1200
applylens_crypto_operation_duration_seconds_bucket{operation="decrypt",le="0.001"} 1180
```

**CSRF Metrics:**
```prometheus
# Successful validations
applylens_csrf_success_total{path="/auth/demo/start",method="POST"} 45

# Validation failures
applylens_csrf_fail_total{path="/auth/logout",method="POST"} 3
```

**Rate Limiting Metrics:**
```prometheus
# Requests allowed
applylens_rate_limit_allowed_total{path="/auth/status"} 5234

# Requests rate limited
applylens_rate_limit_exceeded_total{path="/auth/demo/start",ip_prefix="192.168.*.*"} 12
```

**reCAPTCHA Metrics:**
```prometheus
# Verification attempts
applylens_recaptcha_verify_total{status="success"} 89
applylens_recaptcha_verify_total{status="low_score"} 5
applylens_recaptcha_verify_total{status="failure"} 2
applylens_recaptcha_verify_total{status="disabled"} 1024

# Score distribution
applylens_recaptcha_score_bucket{le="0.5"} 7
applylens_recaptcha_score_bucket{le="0.9"} 85
applylens_recaptcha_score_bucket{le="1.0"} 94
```

### Alerts

**Recommended Alertmanager Rules:**
```yaml
groups:
  - name: applylens_security
    rules:
      # High rate of decryption errors
      - alert: HighTokenDecryptionErrors
        expr: rate(applylens_crypto_decrypt_error_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High token decryption error rate"
          description: "{{ $value }} decryption errors/sec (possible key mismatch or tampering)"

      # High CSRF failure rate
      - alert: HighCSRFFailureRate
        expr: rate(applylens_csrf_fail_total[5m]) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CSRF validation failure rate"
          description: "{{ $value }} CSRF failures/sec on {{ $labels.path }}"

      # Rate limiting triggered frequently
      - alert: FrequentRateLimiting
        expr: rate(applylens_rate_limit_exceeded_total[5m]) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Frequent rate limiting events"
          description: "{{ $value }} rate limit events/sec (possible attack or misconfiguration)"

      # Low reCAPTCHA scores
      - alert: LowCaptchaScores
        expr: rate(applylens_recaptcha_verify_total{status="low_score"}[15m]) > 0.5
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High rate of low reCAPTCHA scores"
          description: "{{ $value }} low-score captchas/sec (possible bot traffic)"
```

### Logging

**Log Levels:**
- `INFO`: Normal operations (key loaded, CSRF validated, token encrypted)
- `WARNING`: Security events (CSRF failure, rate limit exceeded, low captcha score)
- `ERROR`: Failures (decryption error, missing key, KMS unavailable)

**Key Log Messages:**
```
INFO:app.core.crypto:Loaded AES-256 key from environment
INFO:app.core.crypto:Token encryption initialized successfully
INFO:app.core.csrf:CSRF validated for POST /auth/demo/start
WARNING:app.core.csrf:CSRF failure: Token mismatch for POST /auth/logout
WARNING:app.core.crypto:Decryption failed - authentication tag invalid (tampering detected)
ERROR:app.core.crypto:Failed to load AES key: Invalid AES_KEY_BASE64
```

**Search Logs:**
```bash
# All security events
docker logs applylens-api-prod | grep -E "CSRF|crypto|Rate limit|reCAPTCHA"

# CSRF failures only
docker logs applylens-api-prod | grep "CSRF failure"

# Decryption errors
docker logs applylens-api-prod | grep "Decryption failed"

# Rate limiting
docker logs applylens-api-prod | grep "Rate limit exceeded"
```

---

## Deployment Guide

### Initial Setup

**1. Generate Production Key:**
```bash
python scripts/generate_aes_key.py
# Save output to Secret Manager
```

**2. Store in GCP/AWS:**
```bash
# GCP
./scripts/gcp_secrets.sh create my-project api@my-project.iam.gserviceaccount.com

# AWS
./scripts/aws_secrets.sh create us-west-2
```

**3. Set Environment Variables:**
```bash
# docker-compose.prod.yml
services:
  api:
    environment:
      APPLYLENS_AES_KEY_BASE64: ${APPLYLENS_AES_KEY_BASE64}
      APPLYLENS_ENCRYPTION_ENABLED: 1
      APPLYLENS_CSRF_ENABLED: 1
      APPLYLENS_RATE_LIMIT_ENABLED: 1
      APPLYLENS_COOKIE_SECURE: 1
```

**4. Run Migration:**
```bash
docker exec applylens-api-prod alembic upgrade head
```

**5. Restart Services:**
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

**6. Verify:**
```bash
# Check encryption initialized
docker logs applylens-api-prod | grep "Token encryption initialized"

# Check CSRF middleware
docker logs applylens-api-prod | grep "CSRF"

# Check metrics
curl http://localhost:8003/metrics | grep applylens_crypto
```

### Kubernetes Deployment

**1. Create Secret:**
```bash
kubectl create secret generic applylens-aes-key \
  --from-literal=APPLYLENS_AES_KEY_BASE64="$(./scripts/gcp_secrets.sh retrieve my-project)"
```

**2. Update Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: applylens-api
spec:
  template:
    spec:
      containers:
        - name: api
          env:
            - name: APPLYLENS_AES_KEY_BASE64
              valueFrom:
                secretKeyRef:
                  name: applylens-aes-key
                  key: APPLYLENS_AES_KEY_BASE64
            - name: APPLYLENS_ENCRYPTION_ENABLED
              value: "1"
            - name: APPLYLENS_CSRF_ENABLED
              value: "1"
```

**3. Apply:**
```bash
kubectl apply -f k8s/deployment.yaml
kubectl rollout status deployment/applylens-api
```

### Key Rotation in Production

**1. Generate New Key:**
```bash
# Rotate in Secret Manager
./scripts/gcp_secrets.sh rotate my-project

# Or for envelope encryption
python scripts/keys.py rotate --kms-key projects/my-project/locations/global/keyRings/applylens/cryptoKeys/token-key
```

**2. Update Environment:**
```bash
# Docker Compose
export APPLYLENS_AES_KEY_BASE64=$(./scripts/gcp_secrets.sh retrieve my-project)
docker compose up -d --force-recreate api

# Kubernetes
kubectl delete secret applylens-aes-key
kubectl create secret generic applylens-aes-key \
  --from-literal=APPLYLENS_AES_KEY_BASE64="$(./scripts/gcp_secrets.sh retrieve my-project)"
kubectl rollout restart deployment/applylens-api
```

**3. Force Re-login (if not using envelope encryption):**
```bash
# Invalidate all tokens (users must re-authenticate)
docker exec applylens-api-prod psql -U postgres -d applylens -c "DELETE FROM oauth_tokens;"
```

**Note:** With envelope encryption, old tokens remain valid.

---

## Troubleshooting

### "Token encryption initialized" not in logs

**Cause:** `APPLYLENS_ENCRYPTION_ENABLED=0` or import error

**Fix:**
```bash
docker exec applylens-api-prod python -c "from app.config import agent_settings; print(f'Encryption enabled: {agent_settings.ENCRYPTION_ENABLED}')"
# If 0, set to 1 and restart
```

### "Failed to decrypt token"

**Cause:** Key mismatch (wrong `AES_KEY_BASE64`)

**Fix:**
```bash
# Check if key changed
./scripts/gcp_secrets.sh retrieve my-project
# Compare with current container env

# If using ephemeral key, must re-login after restart
```

### "CSRF token invalid"

**Cause:** Frontend not sending `X-CSRF-Token` header

**Fix:**
```typescript
// Ensure using api() wrapper
import { api } from './api/fetcher';
await api('/auth/logout', { method: 'POST' });  // ✅ Correct

// Not this:
fetch('/api/auth/logout', { method: 'POST' });  // ❌ Missing CSRF
```

### CSRF errors in production with nginx

**Cause:** Nginx not passing cookies or headers

**Fix:**
```nginx
location /api/ {
    proxy_pass http://api:8003/;
    proxy_set_header Cookie $http_cookie;
    proxy_set_header X-CSRF-Token $http_x_csrf_token;
    proxy_pass_request_headers on;
}
```

### High decryption error rate

**Possible Causes:**
1. **Key rotation without migration** - Old tokens encrypted with old key
2. **Database corruption** - Partial writes
3. **Tampering** - Authentication tag validation failing

**Investigation:**
```bash
# Check error types
docker logs applylens-api-prod | grep "crypto_decrypt_error"

# Query metrics
curl http://localhost:8003/metrics | grep crypto_decrypt_error_total

# If error_type=invalid_tag → Possible tampering or key mismatch
# If error_type=decode_error → Database corruption
```

**Fix:**
```bash
# For key mismatch: Load correct key
# For tampering: Investigate access logs
# For corruption: Force re-authentication
docker exec applylens-api-prod psql -U postgres -d applylens -c "DELETE FROM oauth_tokens WHERE id = '<corrupted-token-id>';"
```

### Rate limiting not working

**Cause:** See `docs/RATE_LIMITING_ES_CONFIG_2025-10-20.md`

**Quick Fix:**
```bash
# Check if enabled
docker exec applylens-api-prod python -c "from app.config import agent_settings; print(f'Rate limit enabled: {agent_settings.RATE_LIMIT_ENABLED}')"

# Check logs
docker logs applylens-api-prod | grep "Rate limit"
```

---

## References

- **Token Encryption Documentation:** `docs/TOKEN_ENCRYPTION_CSRF_2025-10-20.md`
- **Rate Limiting Documentation:** `docs/RATE_LIMITING_ES_CONFIG_2025-10-20.md`
- **Key Generation Script:** `scripts/generate_aes_key.py`
- **GCP Secret Manager Script:** `scripts/gcp_secrets.sh`
- **AWS Secret Manager Script:** `scripts/aws_secrets.sh`
- **Key Rotation Script:** `scripts/keys.py`
- **Migration:** `alembic/versions/0032_encryption_keys.py`

---

**Last Updated:** October 20, 2025  
**Version:** 1.0
