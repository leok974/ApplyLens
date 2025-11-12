# Production Deployment Checklist v0.5.0

This document provides a comprehensive checklist for deploying ApplyLens v0.5.0 to production.

## 📋 Pre-Deployment Checklist

### 1. Version & Changelog ✅

- [x] **Version bumped to 0.5.0**
  - `apps/web/package.json`: `"version": "0.5.0"`
  - `services/api/pyproject.toml`: `version = "0.5.0"`

- [x] **CHANGELOG.md created** with comprehensive release notes:
  - Critical fixes (logout 500, browser crashes, CSRF bootstrap)
  - Features (deep linking, dev routes precedence)
  - Testing improvements (E2E hardening, regression tests)
  - Documentation (E2E_GUIDE.md, DOCKER_SETUP_COMPLETE.md)
  - Migration notes and rollback instructions

### 2. Production Configuration

#### 2.1 Backend Environment Variables

**Required Changes for Production:**

```bash
# ❌ Development (current)
ALLOW_DEV_ROUTES=1
RATE_LIMIT_MAX_REQ=60
RATE_LIMIT_WINDOW_SEC=60

# ✅ Production (recommended)
ALLOW_DEV_ROUTES=0                    # Disable dev routes in production
RATE_LIMIT_MAX_REQ=100                # More permissive for real users
RATE_LIMIT_WINDOW_SEC=60              # Keep 1-minute window
```

**Configuration Review:**

```bash
# Authentication & Session
SESSION_SECRET=<generate-strong-random-secret>    # ⚠️ MUST CHANGE
COOKIE_DOMAIN=applylens.app                        # Set to apex domain
COOKIE_SECURE=1                                    # HTTPS-only cookies
COOKIE_SAMESITE=lax                                # CSRF protection
GOOGLE_CLIENT_ID=<your-oauth-client-id>
GOOGLE_CLIENT_SECRET=<your-oauth-secret>
OAUTH_REDIRECT_URI=https://applylens.app/auth/google/callback

# CSRF Protection
CSRF_ENABLED=1                                     # Keep enabled
CSRF_COOKIE_NAME=csrf_token
CSRF_HEADER_NAME=X-CSRF-Token

# Rate Limiting
RATE_LIMIT_ENABLED=1                               # Keep enabled
RATE_LIMIT_REDIS_URL=redis://redis:6379/0         # Optional: Use Redis for distributed limiting

# Database
DATABASE_URL=postgresql://user:pass@db:5432/applylens
CREATE_TABLES_ON_STARTUP=0                         # Tables already exist

# Elasticsearch
ES_HOST=http://elasticsearch:9200
ES_INDEX_EMAILS=emails

# Features (optional)
FEATURE_SUMMARIZE=false                            # Disable AI features if no LLM
FEATURE_RAG_SEARCH=false                           # Disable if no vector DB
OLLAMA_BASE=http://ollama:11434                    # If using local LLM
OLLAMA_MODEL=gpt-oss:20b

# Observability
SENTRY_DSN=<your-sentry-dsn>                       # Optional: Error tracking
LOG_LEVEL=INFO                                     # Production logging
```

#### 2.2 Frontend Environment Variables

**Production `.env.production`:**

```bash
VITE_API_BASE=/api                                 # Same-origin API (proxied by Nginx)
VITE_ENV=production
```

#### 2.3 Nginx Configuration Review

**Verify `infra/nginx/nginx.conf`:**

```nginx
server {
    listen 80 default_server;                      # ✅ Single default_server
    server_name _;

    # Frontend (React SPA)
    location / {
        proxy_pass http://web:80;                  # ✅ Correct upstream
        # ... proxy headers ...
    }

    # API Backend
    location /api/ {
        proxy_pass http://api:8003/;               # ✅ Correct upstream (note trailing slash)
        # ... proxy headers ...
    }
}
```

**Key Points:**
- ✅ Only ONE `default_server` directive
- ✅ Web upstream: `http://web:80`
- ✅ API upstream: `http://api:8003/` (with trailing slash)
- ✅ CSRF works with same-origin setup

#### 2.4 Docker Compose Production Config

**Verify `docker-compose.prod.yml` (or main compose file):**

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    # ... configuration ...

  es:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.13.4
    restart: unless-stopped
    # ... configuration ...

  api:
    image: ghcr.io/leok974/applylens/api:0.5.0     # ✅ Pin to version
    restart: unless-stopped
    environment:
      - ALLOW_DEV_ROUTES=0                          # ✅ Disabled in prod
      - RATE_LIMIT_MAX_REQ=100
      - COOKIE_SECURE=1
      - SESSION_SECRET=${SESSION_SECRET}            # From .env file
    # ... ports, volumes ...

  web:
    image: ghcr.io/leok974/applylens/web:0.5.0      # ✅ Pin to version
    restart: unless-stopped
    # ... configuration ...

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"                                    # If using HTTPS
    # ... configuration ...
```

### 3. Build & Push Docker Images

#### 3.1 Build Images

```bash
# Build API image
cd services/api
docker build -t ghcr.io/leok974/applylens/api:0.5.0 -f Dockerfile.prod .
docker tag ghcr.io/leok974/applylens/api:0.5.0 ghcr.io/leok974/applylens/api:latest

# Build Web image
cd ../../apps/web
docker build -t ghcr.io/leok974/applylens/web:0.5.0 -f Dockerfile.prod .
docker tag ghcr.io/leok974/applylens/web:0.5.0 ghcr.io/leok974/applylens/web:latest
```

#### 3.2 Push to Registry

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u leok974 --password-stdin

# Push API image
docker push ghcr.io/leok974/applylens/api:0.5.0
docker push ghcr.io/leok974/applylens/api:latest

# Push Web image
docker push ghcr.io/leok974/applylens/web:0.5.0
docker push ghcr.io/leok974/applylens/web:latest
```

#### 3.3 CI/CD Alternative

If using GitHub Actions, create `.github/workflows/deploy.yml`:

```yaml
name: Build and Deploy

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push API
        uses: docker/build-push-action@v5
        with:
          context: services/api
          file: services/api/Dockerfile.prod
          push: true
          tags: |
            ghcr.io/leok974/applylens/api:${{ github.ref_name }}
            ghcr.io/leok974/applylens/api:latest

      - name: Build and push Web
        uses: docker/build-push-action@v5
        with:
          context: apps/web
          file: apps/web/Dockerfile.prod
          push: true
          tags: |
            ghcr.io/leok974/applylens/web:${{ github.ref_name }}
            ghcr.io/leok974/applylens/web:latest
```

### 4. Pre-Deployment Testing

#### 4.1 Local Production Build Test

```bash
# Build production images locally
docker compose -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
sleep 30

# Run smoke tests
cd apps/web
E2E_BASE_URL=http://localhost:8888 \
E2E_API=http://localhost:8888/api \
USE_SMOKE_SETUP=true \
SEED_COUNT=5 \
npx playwright test tests/smoke --workers=1
```

#### 4.2 Regression Tests (Development)

```bash
# Ensure dev environment is running
docker compose up -d

# Run regression tests
cd apps/web
E2E_BASE_URL=http://127.0.0.1:8888 \
E2E_API=http://127.0.0.1:8888/api \
USE_SMOKE_SETUP=true \
SEED_COUNT=20 \
npx playwright test \
  tests/e2e/auth.demo.spec.ts \
  tests/e2e/auth.logout.spec.ts \
  tests/e2e/auth.logout.regression.spec.ts \
  tests/e2e/search-populates.spec.ts \
  --workers=2
```

**Expected Results:**
- ✅ All 5 tests pass (2 auth.demo, 1 auth.logout, 2 auth.logout.regression)
- ✅ No browser crashes
- ✅ Logout returns 200
- ✅ Session cleared properly

## 🚀 Deployment Steps

### 5. Deploy to Production (Ops Workspace)

#### 5.1 Pull Latest Images

```bash
cd /path/to/ops/workspace
docker compose -f docker-compose.prod.yml pull
```

#### 5.2 Backup Database (Optional but Recommended)

```bash
# Backup PostgreSQL
docker exec applylens_db pg_dump -U applylens applylens > backup-$(date +%Y%m%d-%H%M%S).sql

# Or use automated backup if configured
```

#### 5.3 Deploy with Zero Downtime

**Option A: Rolling Update (Watchtower)**

If using Watchtower with `com.centurylinklabs.watchtower.enable=true` labels:

```bash
# Watchtower will automatically pull and restart containers with :latest tag
# No manual intervention needed
```

**Option B: Manual Blue-Green Deployment**

```bash
# Start new containers alongside old ones
docker compose -f docker-compose.prod.yml up -d --no-deps --scale web=2 --scale api=2 web api

# Wait for health checks to pass
sleep 30
curl -f http://localhost:8888/api/healthz || exit 1

# Stop old containers
docker compose -f docker-compose.prod.yml up -d --no-deps --scale web=1 --scale api=1 web api

# Remove old containers
docker compose -f docker-compose.prod.yml rm -f
```

**Option C: Simple Restart (Brief Downtime)**

```bash
# Stop and restart all services
docker compose -f docker-compose.prod.yml up -d

# Or restart specific services
docker compose -f docker-compose.prod.yml up -d web api nginx
```

#### 5.4 Verify Deployment

```bash
# Check container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Expected output:
# NAMES                STATUS              PORTS
# applylens_nginx      Up 2 minutes        0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
# applylens_web        Up 2 minutes        80/tcp
# applylens_api        Up 2 minutes        8003/tcp
# applylens_es         Up 5 minutes        9200/tcp, 9300/tcp
# applylens_db         Up 5 minutes        5432/tcp

# Check logs for errors
docker compose -f docker-compose.prod.yml logs --tail=50 api
docker compose -f docker-compose.prod.yml logs --tail=50 web
docker compose -f docker-compose.prod.yml logs --tail=50 nginx
```

### 6. Post-Deployment Smoke Tests

#### 6.1 Health Checks (via Nginx/Cloudflared)

```bash
# Health endpoint (web)
curl -s -o /dev/null -w "%{http_code}\n" https://applylens.app/health
# Expected: 200

# API health endpoint
curl -s https://applylens.app/api/healthz
# Expected: {"status":"ok","version":"0.5.0"}

# CSRF endpoint (should return cookies)
curl -v https://applylens.app/api/auth/csrf 2>&1 | grep -i "set-cookie"
# Expected: set-cookie: csrf_token=...
```

#### 6.2 Browser Quick Path

**Manual verification steps:**

1. **Landing Page**
   ```
   Open: https://applylens.app/welcome
   ✅ Page loads
   ✅ "Connect Gmail" or "Try Demo" button visible
   ```

2. **Demo Login**
   ```
   Click: "Try Demo"
   ✅ Redirects to /inbox
   ✅ Demo user email shown in header
   ✅ Threads visible
   ```

3. **Search**
   ```
   Type query in search box
   ✅ Results appear
   ✅ No console errors
   ```

4. **Logout**
   ```
   Click: User menu → Logout
   ✅ Redirects to /welcome
   ✅ No browser crash
   ✅ Cannot access /inbox without login
   ```

#### 6.3 API Endpoint Tests

```bash
# Get CSRF token
CSRF=$(curl -s -c cookies.txt https://applylens.app/api/auth/csrf | jq -r '.csrf_token')

# Demo login
curl -s -b cookies.txt -c cookies.txt \
  -H "X-CSRF-Token: $CSRF" \
  -H "Content-Type: application/json" \
  -X POST https://applylens.app/api/auth/demo/start

# Get user info
curl -s -b cookies.txt https://applylens.app/api/auth/me | jq
# Expected: {"email":"demo@applylens.app","is_demo":true,...}

# Logout
curl -s -b cookies.txt \
  -H "X-CSRF-Token: $CSRF" \
  -X POST https://applylens.app/api/auth/logout | jq
# Expected: {"ok":true,"user":null}

# Cleanup
rm cookies.txt
```

### 7. Run Core E2E Against Production (Optional)

**⚠️ Warning:** Only run read-only tests against production if `ALLOW_DEV_ROUTES=0`.

```bash
cd apps/web

# Read-only smoke tests (safe for production)
E2E_BASE_URL=https://applylens.app \
E2E_API=https://applylens.app/api \
USE_SMOKE_SETUP=false \
npx playwright test \
  tests/e2e/auth.demo.spec.ts \
  tests/e2e/auth.logout.spec.ts \
  --workers=1 \
  --headed

# ❌ DO NOT RUN if ALLOW_DEV_ROUTES=0:
# - tests that use /api/dev/seed-*
# - tests that modify data
```

## 📊 Monitoring & Alerts

### 8. Grafana Dashboards

**Key Metrics to Monitor:**

1. **API Performance**
   - Request latency (p50, p95, p99)
   - Request rate (requests/second)
   - Error rate (5xx responses)
   - Database query time

2. **Auth Metrics**
   - Login success/failure rate
   - Logout success rate
   - Session creation/deletion
   - CSRF failures
   - Rate limit hits

3. **Infrastructure**
   - Container health (up/down)
   - CPU/Memory usage
   - Database connections
   - Elasticsearch cluster health

### 9. Alerting Rules

**Critical Alerts (PagerDuty/Slack):**

```yaml
# API Down
- alert: APIDown
  expr: up{job="api"} == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "API service is down"

# High 5xx Error Rate
- alert: HighServerErrors
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High 5xx error rate: {{ $value }}"

# CSRF Failures Spike
- alert: CSRFFailureSpike
  expr: rate(csrf_failures_total[5m]) > 10
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "CSRF failure spike: {{ $value }} failures/sec"

# Auth Failures
- alert: HighAuthFailures
  expr: rate(http_requests_total{path="/api/auth/login",status="401"}[5m]) > 5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High authentication failure rate"

# Database Connection Issues
- alert: DatabaseConnectionErrors
  expr: rate(database_errors_total[5m]) > 1
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Database connection errors detected"
```

### 10. External Uptime Monitoring

**Setup external monitoring (UptimeRobot, Pingdom, etc.):**

```yaml
Checks:
  - name: "ApplyLens Homepage"
    url: https://applylens.app/
    interval: 60s
    expected_status: 200
    expected_content: "ApplyLens"

  - name: "API Health"
    url: https://applylens.app/api/healthz
    interval: 60s
    expected_status: 200
    expected_json: {"status":"ok"}

  - name: "CSRF Endpoint"
    url: https://applylens.app/api/auth/csrf
    interval: 300s
    expected_status: 200
    expected_header: "set-cookie"
```

## 🔒 Security & Hygiene

### 11. Security Checklist

#### 11.1 Secrets Rotation

```bash
# ⚠️ Rotate these secrets after deployment:

# Session secret (generate new random string)
SESSION_SECRET=$(openssl rand -base64 32)

# Google OAuth (if credentials were exposed)
# → Regenerate in Google Cloud Console

# Database password (if needed)
# → Update in .env and restart db service

# Encryption keys (if using KMS)
# → Rotate in GCP KMS console
```

#### 11.2 Cookie & CORS Configuration

**Verify production settings:**

```nginx
# Nginx headers (should already be set)
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# CSP (adjust based on your needs)
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
```

**FastAPI cookies (already configured):**

```python
# app/routers/auth.py
response.set_cookie(
    key="session_id",
    value=session.id,
    httponly=True,           # ✅ No JavaScript access
    secure=True,             # ✅ HTTPS only (if COOKIE_SECURE=1)
    samesite="lax",         # ✅ CSRF protection
    domain="applylens.app", # ✅ Apex domain
    max_age=86400 * 30      # 30 days
)
```

#### 11.3 Pre-Commit Hooks

**Add to `.pre-commit-config.yaml`:**

```yaml
repos:
  - repo: local
    hooks:
      - id: check-session-import
        name: Check SQLAlchemy Session Import
        entry: bash -c 'if grep -r "from sqlalchemy.orm import Session" services/api/app/routers --exclude-dir=__pycache__; then echo "ERROR: Use \"from sqlalchemy.orm import Session as DBSession\" instead"; exit 1; fi'
        language: system
        pass_filenames: false

      - id: check-models-session-import
        name: Check Models Session Import in Routers
        entry: bash -c 'if grep -r "from app.models import Session[^a-zA-Z]" services/api/app/routers --exclude-dir=__pycache__; then echo "ERROR: Use \"from app.models import Session as UserSession\" instead"; exit 1; fi'
        language: system
        pass_filenames: false
```

**Install hooks:**

```bash
pip install pre-commit
pre-commit install
```

## 📚 Documentation & Runbooks

### 12. Documentation Updates

**Files to review before deployment:**

- ✅ `CHANGELOG.md` - Release notes (already created)
- ✅ `apps/web/docs/E2E_GUIDE.md` - Testing guide (already created)
- ✅ `docs/DOCKER_SETUP_COMPLETE.md` - Setup guide (already created)
- ✅ `docs/PRODUCTION_DEPLOYMENT.md` - This file

**Add Incident RCA section to `docs/DOCKER_SETUP_COMPLETE.md`:**

```markdown
## Incident RCA: Logout 500 Error

### Symptoms
- POST /api/auth/logout returned 500 Internal Server Error
- Browser crashed after clicking logout
- Users stuck in logged-in state
- Database sessions not being deleted

### Root Cause
Naming conflict between SQLAlchemy's `Session` class and our custom `Session` model.

In `app/routers/auth.py`, the code imported both:
```python
from sqlalchemy.orm import Session
from app.models import Session
```

This caused `Session` to refer to the model class, while the route expected the SQLAlchemy session type. When the code attempted `db.query(Session)`, it tried to call the model class as a function, which failed.

### Fix
1. Enforced alias pattern throughout codebase:
   ```python
   from sqlalchemy.orm import Session as DBSession
   from app.models import Session as UserSession
   ```

2. Updated logout endpoint to use correct alias:
   ```python
   db.query(UserSession).filter(UserSession.id == session_id).delete()
   ```

3. Added pre-commit hooks to prevent future violations

### Prevention
- Pre-commit hooks enforce import aliases
- Regression tests cover logout flow
- Documentation in DOCKER_SETUP_COMPLETE.md
- E2E tests validate entire auth flow
```

### 13. Rollback Procedures

**Quick Rollback Steps:**

```bash
# 1. Stop current deployment
docker compose -f docker-compose.prod.yml down

# 2. Update image tags to previous version
# Edit docker-compose.prod.yml:
#   api: ghcr.io/leok974/applylens/api:0.4.64
#   web: ghcr.io/leok974/applylens/web:0.4.64

# 3. Pull previous images
docker compose -f docker-compose.prod.yml pull

# 4. Start services
docker compose -f docker-compose.prod.yml up -d

# 5. Verify health
curl https://applylens.app/api/healthz

# 6. Restore database backup (if needed)
docker exec -i applylens_db psql -U applylens applylens < backup-YYYYMMDD-HHMMSS.sql
```

**OR use specific tag:**

```bash
docker compose -f docker-compose.prod.yml pull \
  --image api=ghcr.io/leok974/applylens/api:0.4.64 \
  --image web=ghcr.io/leok974/applylens/web:0.4.64

docker compose -f docker-compose.prod.yml up -d
```

## 🏷️ Git Tagging & Release

### 14. Tag & Publish

#### 14.1 Create Git Tag

```bash
# Ensure you're on the correct branch
git checkout main
git pull origin main

# Create annotated tag
git tag -a v0.5.0 -m "Release v0.5.0

Critical Fixes:
- Logout 500 error (Session naming conflict)
- Browser crashes on logout (hard reload)
- CSRF bootstrap implementation

Features:
- Deep linking to inbox threads
- Dev routes precedence fix

Testing:
- E2E test hardening (trace, video, console listeners)
- Regression tests for logout flow
- Comprehensive E2E guide

Documentation:
- E2E_GUIDE.md (500+ lines)
- DOCKER_SETUP_COMPLETE.md (400+ lines)
- CHANGELOG.md with migration notes

See CHANGELOG.md for full details."

# Push tag to remote
git push origin v0.5.0

# Push to GitHub (triggers CI/CD if configured)
git push origin main
```

#### 14.2 GitHub Release

Create release on GitHub with:

**Title:** `v0.5.0 - Logout Fix & E2E Hardening`

**Release Notes:**

```markdown
## 🐛 Critical Fixes

### Logout 500 Error
Fixed 500 Internal Server Error on logout caused by Session naming conflict. Users can now logout successfully without browser crashes.

### Browser Stability
Eliminated hard page reloads that caused browser crashes during auth state changes.

### CSRF Protection
Implemented comprehensive CSRF token bootstrap with automatic injection in API calls.

## ✨ Features

- **Deep linking:** `/inbox?open=<thread_id>` URLs now work
- **Dev routes:** Fixed precedence for reliable seed endpoints

## 🧪 Testing

- Playwright config improvements (trace-on-first-retry, video capture)
- Comprehensive regression test suite
- E2E testing guide with 500+ lines of documentation

## 📚 Documentation

- [E2E Testing Guide](apps/web/docs/E2E_GUIDE.md)
- [Docker Setup Guide](docs/DOCKER_SETUP_COMPLETE.md)
- [Production Deployment Checklist](docs/PRODUCTION_DEPLOYMENT.md)

## 🚀 Deployment

**Docker Images:**
- API: `ghcr.io/leok974/applylens/api:0.5.0`
- Web: `ghcr.io/leok974/applylens/web:0.5.0`

**Environment Changes:**
- Set `ALLOW_DEV_ROUTES=0` in production
- Set `COOKIE_SECURE=1` for HTTPS
- Update `COOKIE_DOMAIN` to apex domain

See [PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md) for full checklist.

## ⬇️ Upgrade from 0.4.x

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

No database migrations required.

## 🔄 Rollback

```bash
# Edit docker-compose.prod.yml to use :0.4.64
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

**Full Changelog:** https://github.com/leok974/ApplyLens/blob/main/CHANGELOG.md
```

**Attach files:**
- Docker Compose file (production version)
- Environment variable template
- Migration guide excerpt

### 15. Internal Release Announcement

**Send to team via Slack/Email:**

```markdown
🎉 **ApplyLens v0.5.0 Released**

**What's New:**
✅ Fixed logout 500 error (Session naming conflict)
✅ No more browser crashes on logout
✅ CSRF protection fully implemented
✅ Deep linking to threads
✅ Comprehensive E2E testing suite
✅ Production deployment documentation

**Deployment Status:** ⏳ Pending
**Target Date:** [DATE]

**Action Items:**
- [ ] Review CHANGELOG.md for full details
- [ ] Verify production environment variables
- [ ] Schedule deployment window
- [ ] Run pre-deployment tests
- [ ] Prepare rollback plan

**Documentation:**
📖 [CHANGELOG.md](./CHANGELOG.md)
📖 [PRODUCTION_DEPLOYMENT.md](./docs/PRODUCTION_DEPLOYMENT.md)
🧪 [E2E_GUIDE.md](./apps/web/docs/E2E_GUIDE.md)
🐳 [DOCKER_SETUP_COMPLETE.md](./docs/DOCKER_SETUP_COMPLETE.md)

**Questions?** Ask in #engineering-deploys
```

## ✅ Post-Deployment Verification

### 16. Final Checklist

After deployment, verify:

- [ ] All containers running: `docker ps`
- [ ] Health checks passing: `/health` and `/api/healthz`
- [ ] CSRF tokens working: `/api/auth/csrf` returns cookies
- [ ] Demo login works: Try Demo → Inbox
- [ ] Search functionality: Type query → Results appear
- [ ] Logout works: Settings → Logout → Redirects to /welcome
- [ ] No console errors in browser DevTools
- [ ] Grafana dashboards showing healthy metrics
- [ ] No critical alerts firing
- [ ] Logs clean (no errors/warnings)

### 17. Performance Baseline

**Capture baseline metrics for comparison:**

```bash
# API response times
curl -w "@curl-format.txt" -o /dev/null -s https://applylens.app/api/healthz

# Create curl-format.txt:
cat > curl-format.txt << EOF
    time_namelookup:  %{time_namelookup}s\n
       time_connect:  %{time_connect}s\n
    time_appconnect:  %{time_appconnect}s\n
   time_pretransfer:  %{time_pretransfer}s\n
      time_redirect:  %{time_redirect}s\n
 time_starttransfer:  %{time_starttransfer}s\n
                    ----------\n
         time_total:  %{time_total}s\n
EOF
```

**Expected baselines:**
- Health endpoint: < 50ms
- API healthz: < 100ms
- Page load (First Contentful Paint): < 1.5s
- Time to Interactive: < 3s

## 🎯 Success Criteria

Deployment is considered successful when:

1. ✅ All services healthy for 1 hour
2. ✅ Zero critical alerts
3. ✅ < 0.1% error rate on API endpoints
4. ✅ Successful manual smoke test (login → search → logout)
5. ✅ Performance metrics within baseline ±10%
6. ✅ No user-reported issues

---

## 📞 Support & Escalation

**Deployment Issues:**
- Primary: #engineering-deploys (Slack)
- Secondary: oncall@applylens.app

**Rollback Decision Maker:**
- Tech Lead or CTO

**Emergency Contact:**
- [Your contact info]

---

**Last Updated:** 2025-01-27
**Version:** 0.5.0
**Owner:** Engineering Team
