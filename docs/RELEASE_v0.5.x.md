# 🚀 Release Runbook: v0.5.x

**Date**: 2025-01-27
**Version**: v0.5.0
**Critical Fix**: Logout 500 Error (Session naming conflict)
**Deploy Duration**: ~15 minutes
**Rollback Time**: < 5 minutes

---

## ✅ PREFLIGHT CHECKLIST

Before deploying, verify ALL items:

- [ ] **CI Status**: All GitHub Actions workflows passing (green ✅)
- [ ] **Regression Tests**: 4/4 tests passing locally
  ```bash
  # API unit tests
  pytest tests/test_routes_auth.py::test_logout_success -v
  pytest tests/test_routes_auth.py::test_logout_invalid_session -v

  # UI E2E tests
  npm run e2e -- tests/e2e/auth.logout.spec.ts
  ```
- [ ] **Version Bumped**: Check `package.json` (0.5.0) and `pyproject.toml` (0.5.0)
- [ ] **Changelog Updated**: `CHANGELOG.md` has v0.5.0 section with release notes
- [ ] **Environment Variables Set**:
  - `ALLOW_DEV_ROUTES=0` (critical - disables dev endpoints in prod)
  - `COOKIE_SECURE=1` (HTTPS-only cookies)
  - `COOKIE_SAMESITE=Lax` (CSRF protection)
  - `LOG_LEVEL=info` (not debug)
- [ ] **Rate Limits Configured**:
  - `RATE_LIMIT_ENABLED=1`
  - `RATE_LIMIT_REQUESTS=100`
  - `RATE_LIMIT_WINDOW=60`
- [ ] **Nginx Config Reviewed**: `web/nginx.conf` has security headers (X-Frame-Options, CSP)
- [ ] **Docker Images Tagged**: `web:0.5.0` and `api:0.5.0` (not just `latest`)
- [ ] **Backups Ready**: Database snapshot exists (< 1 hour old)
- [ ] **Monitoring Active**: Grafana dashboards accessible, alert rules enabled
- [ ] **Team Notified**: Deployment announced in #ops or relevant channel

---

## 🔨 BUILD & PUBLISH

### 1. Build Docker Images

```bash
# Navigate to project root
cd d:\ApplyLens

# Build web image (frontend)
docker build -t applylens/web:0.5.0 -t applylens/web:latest -f apps/web/Dockerfile.prod apps/web

# Build API image (backend)
docker build -t applylens/api:0.5.0 -t applylens/api:latest -f services/api/Dockerfile.prod services/api

# Verify images exist
docker images | grep applylens
```

### 2. Test Images Locally (Optional but Recommended)

```bash
# Start prod build locally
docker compose -f docker-compose.prod.yml up -d

# Health checks
curl http://localhost:5173/health          # Web
curl http://localhost:8003/api/healthz     # API

# Quick browser test
# Visit http://localhost:5173 → verify /welcome loads → check browser console (no errors)

# Stop local prod build
docker compose -f docker-compose.prod.yml down
```

### 3. Push Images to Registry

```bash
# Login to Docker registry (if needed)
docker login

# Push versioned tags
docker push applylens/web:0.5.0
docker push applylens/api:0.5.0

# Push latest tags
docker push applylens/web:latest
docker push applylens/api:latest

# Verify push
docker pull applylens/web:0.5.0
docker pull applylens/api:0.5.0
```

---

## 🚀 DEPLOY TO PRODUCTION

### 1. SSH to Production Server

```bash
ssh user@applylens.app
cd /opt/applylens
```

### 2. Backup Current State

```bash
# Backup database
docker exec applylens-postgres pg_dump -U postgres -d applylens > backup-$(date +%Y%m%d-%H%M%S).sql

# Backup environment file
cp .env .env.backup-$(date +%Y%m%d-%H%M%S)

# Note current image versions (for rollback)
docker compose ps | grep applylens
```

### 3. Pull New Images

```bash
# Update docker-compose.prod.yml to use 0.5.0 tags (or pull latest)
docker pull applylens/web:0.5.0
docker pull applylens/api:0.5.0
```

### 4. Deploy

```bash
# Stop current containers (graceful shutdown)
docker compose -f docker-compose.prod.yml down

# Start new containers
docker compose -f docker-compose.prod.yml up -d

# Wait 10 seconds for startup
sleep 10

# Check container status
docker compose -f docker-compose.prod.yml ps
```

### 5. Verify Health

```bash
# API health
curl https://applylens.app/api/healthz
# Expected: {"status":"ok","timestamp":"...","version":"0.5.0"}

# Web health
curl https://applylens.app/health
# Expected: {"status":"ok"}

# CSRF endpoint
curl https://applylens.app/api/auth/csrf
# Expected: {"csrfToken":"..."}
```

---

## ✅ POST-DEPLOY VERIFICATION

### 1. Automated Smoke Tests (5 minutes)

Run production-safe smoke tests from local machine:

```bash
# From apps/web directory
npm run test:prod:smoke

# Expected: 8 test suites pass
# ✅ Production Health Checks (3 tests)
# ✅ Public Pages (4 tests)
# ✅ SEO & Metadata (3 tests)
# ✅ API Endpoints - Read Only (2 tests)
# ✅ Performance & Response Times (2 tests)
# ✅ Error Handling (2 tests)
```

### 2. Manual Browser Test (2 minutes)

1. **Visit https://applylens.app** → Verify welcome page loads
2. **Open browser DevTools (F12)** → Check console (no errors)
3. **Check Network tab** → Verify `/api/healthz` returns 200
4. **Test logout** (if logged in):
   - Click logout button
   - Verify redirect to `/welcome`
   - Verify no 500 errors in DevTools Network tab
   - Verify session cleared (refresh page → still on welcome)

### 3. Monitoring Check (1 minute)

- **Grafana**: Open dashboards → Verify metrics flowing (requests/sec, response times)
- **Logs**: `docker compose logs -f --tail=100 api` → Check for errors
- **External Uptime**: Check Pingdom/UptimeRobot (if configured) → Verify up status

---

## 🎯 SUCCESS CRITERIA

All items must be ✅ to consider deployment successful:

| Metric | Target | How to Verify |
|--------|--------|---------------|
| **Health Endpoints** | 200 OK | `curl https://applylens.app/api/healthz` |
| **Logout Success Rate** | 100% (no 500s) | Test logout in browser → DevTools Network tab |
| **Page Load Time** | < 5s | Lighthouse or browser DevTools Performance tab |
| **API Response Time** | /api/healthz < 2s | `time curl https://applylens.app/api/healthz` |
| **Error Rate** | < 1% | Grafana dashboard → "HTTP 5xx Rate" panel |
| **CSRF Token Generation** | Working | `curl https://applylens.app/api/auth/csrf` → has `csrfToken` |
| **Container Status** | All `Up` | `docker compose ps` → no `Restarting` or `Exited` |
| **No Console Errors** | 0 critical errors | Browser DevTools → Console tab (warnings OK) |

---

## 🔄 ROLLBACK PROCEDURE

If deployment fails or critical issues detected:

### Quick Rollback (< 5 minutes)

```bash
# SSH to production
ssh user@applylens.app
cd /opt/applylens

# Stop containers
docker compose -f docker-compose.prod.yml down

# Pin to previous version (example: 0.4.64)
docker compose -f docker-compose.prod.yml pull applylens/web:0.4.64
docker compose -f docker-compose.prod.yml pull applylens/api:0.4.64

# Update docker-compose.prod.yml to use 0.4.64 tags
# OR manually tag old images as latest:
docker tag applylens/web:0.4.64 applylens/web:latest
docker tag applylens/api:0.4.64 applylens/api:latest

# Start containers
docker compose -f docker-compose.prod.yml up -d

# Verify health
curl https://applylens.app/api/healthz
```

### Rollback Verification

- [ ] Health endpoints return 200
- [ ] Containers running (not restarting)
- [ ] No 500 errors in logs
- [ ] Application accessible in browser
- [ ] Post rollback announcement in #ops

---

## 📊 MONITORING & ALERTS

### Critical Alerts to Watch (First 30 Minutes)

- **API Down**: Grafana alert → `/api/healthz` non-200 for > 2 minutes
- **High 5xx Rate**: > 5% of requests returning 500+ errors
- **CSRF Failures**: Sudden spike in 403 Forbidden responses
- **Auth Failures**: Logout endpoint 500 errors (regression of this fix)
- **Database Errors**: Connection pool exhausted or query timeouts

### Grafana Dashboard

**URL**: https://applylens.app/grafana (or internal monitoring URL)

**Key Panels to Monitor**:
1. **Request Rate**: Requests/sec (expect normal traffic pattern)
2. **Response Time (p95)**: Should be < 500ms for most endpoints
3. **Error Rate**: 5xx errors should be < 0.1%
4. **Logout Success Rate**: Should be 100% (0 failures)
5. **Database Connections**: Should be stable (not climbing)

**Alert Rules** (already configured):
- `ApplyLensAPIDown`: Fires if health check fails for 2 minutes
- `ApplyLensHighErrorRate`: Fires if 5xx rate > 5% for 5 minutes
- `ApplyLensCSRFFailures`: Fires if CSRF 403s spike
- `ApplyLensAuthFailures`: Fires if logout endpoint returns 500

---

## 🔐 SECURITY CHECKLIST

Post-deployment security validation:

- [ ] **Secrets Rotated**: If any secrets were exposed during incident, rotate them
  ```bash
  # Rotate JWT secret
  export JWT_SECRET=$(openssl rand -base64 32)

  # Update .env and restart
  docker compose restart api
  ```
- [ ] **Cookie Settings Verified**:
  - Secure=1 (HTTPS-only)
  - SameSite=Lax (CSRF protection)
  - HttpOnly=1 (XSS protection)
  - Check: Browser DevTools → Application → Cookies → `applylens_session`
- [ ] **CSP Headers Active**:
  ```bash
  curl -I https://applylens.app | grep Content-Security-Policy
  # Expected: Content-Security-Policy: default-src 'self'; ...
  ```
- [ ] **X-Frame-Options**:
  ```bash
  curl -I https://applylens.app | grep X-Frame-Options
  # Expected: X-Frame-Options: DENY
  ```
- [ ] **Rate Limiting Active**:
  ```bash
  # Test rate limit (should get 429 after 100 requests)
  for i in {1..105}; do curl https://applylens.app/api/healthz; done
  ```
- [ ] **Dev Routes Disabled**:
  ```bash
  curl https://applylens.app/api/dev/demo/login
  # Expected: 404 Not Found (not 200)
  ```

---

## 📝 GIT TAGGING & GITHUB RELEASE

### 1. Tag the Release

```bash
# On your local machine
git tag -a v0.5.0 -m "v0.5.0: Fix logout 500 error (Session naming conflict)"
git push origin v0.5.0
```

### 2. Create GitHub Release

**Navigate to**: https://github.com/your-org/applylens/releases/new

**Release Notes Template**:

```markdown
## 🚀 ApplyLens v0.5.0

**Release Date**: 2025-01-27
**Critical Fix**: Logout 500 Error

### 🐛 Critical Fixes

- **Logout 500 Error**: Fixed Session naming conflict causing logout failures (80% failure rate → 0%)
  - Root cause: SQLAlchemy `Session` and app model `Session` conflicting in logout route
  - Solution: Import aliasing (`as DBSession` and `as UserSession`)
  - Prevention: Pre-commit hooks to enforce aliasing pattern
- **Browser Crashes**: Fixed hard reload causing stuck "Loading..." screens
- **CSRF Bootstrap**: Fixed race condition in CSRF token initialization

### ✨ Features

- Deep linking support for inbox items (`/inbox?open=<application_id>`)
- Dev routes precedence over API routes (improves DX)

### 🧪 Testing

- Added 4 regression tests (2 API unit tests, 2 UI E2E tests)
- Added production-safe smoke tests (read-only validation)
- Created E2E testing guide (docs/E2E_GUIDE.md)

### 📚 Documentation

- Comprehensive deployment guide (docs/PRODUCTION_DEPLOYMENT.md)
- Quick deployment reference (docs/QUICK_DEPLOY.md)
- Incident RCA in docs/DOCKER_SETUP_COMPLETE.md
- Release runbook (this document)

### 🔒 Security

- Pre-commit hooks to prevent Session import violations
- Secret rotation procedures documented
- Cookie security settings validated (Secure, SameSite, HttpOnly)

### 📊 Migration Notes

**No database migrations required** - Safe to rollback to v0.4.x if needed.

**Breaking Changes**: None

**Rollback**: Pin Docker images to `0.4.64` tags

### 🙏 Contributors

- Engineering Team
- QA Team

### 📦 Docker Images

- `applylens/web:0.5.0`
- `applylens/api:0.5.0`

### 📖 Full Changelog

See [CHANGELOG.md](./CHANGELOG.md) for detailed changes.
```

---

## 📢 POST-DEPLOYMENT COMMUNICATION

### Internal Announcement (Slack/Discord)

```
🚀 **ApplyLens v0.5.0 Deployed to Production**

✅ **Status**: Deployed successfully at [timestamp]
🐛 **Critical Fix**: Logout 500 error resolved (Session naming conflict)
📊 **Metrics**: All health checks passing, 0% error rate
🔍 **Monitoring**: Grafana dashboards green, no alerts firing

**Key Changes**:
- Logout success rate: 80% → 100%
- Browser crash fix (hard reload)
- CSRF bootstrap race condition resolved

**Verification**:
- Health: https://applylens.app/api/healthz ✅
- Smoke tests: 8/8 passing ✅
- Monitoring: All green ✅

**Rollback**: Available if needed (< 5 min)
**Support**: Contact @oncall if issues detected

See release notes: https://github.com/your-org/applylens/releases/tag/v0.5.0
```

### External Announcement (Optional - Status Page)

```
✅ Maintenance Complete

We've deployed ApplyLens v0.5.0 with critical bug fixes:
- Resolved logout errors
- Improved application stability
- Enhanced security

All systems operational. Thank you for your patience!
```

---

## 🔍 ROOT CAUSE ANALYSIS SUMMARY

**Incident**: Logout 500 Error (Affecting 80% of logout attempts)

**Root Cause**:
- SQLAlchemy's `Session` class and our app's `Session` model were both imported in `routes_auth.py`
- When type-hinting logout route parameter as `session: Session`, Python couldn't resolve which `Session` to use
- FastAPI's dependency injection failed, causing 500 Internal Server Error

**Fix**:
- Import aliasing: `from sqlalchemy.orm import Session as DBSession`
- Import aliasing: `from app.models import Session as UserSession`
- Updated all type hints to use explicit aliases
- Added pre-commit hooks to prevent future violations

**Impact**:
- Before: 80% of logout attempts returned 500 error
- After: 100% logout success rate

**Prevention**:
- Pre-commit hook: `scripts/hooks/forbid_session_import.sh`
- 4 regression tests (2 API, 2 E2E)
- Documentation: Import aliasing best practices

**Full RCA**: See `docs/DOCKER_SETUP_COMPLETE.md` (Incident RCA section)

---

## ✅ DEPLOYMENT COMPLETE CHECKLIST

Final verification before marking deployment complete:

- [ ] All containers running (`docker compose ps` shows `Up`)
- [ ] Health endpoints returning 200
- [ ] Automated smoke tests passing (8/8)
- [ ] Manual browser test completed (logout works)
- [ ] Monitoring dashboards green (no alerts)
- [ ] Git tag pushed (`v0.5.0`)
- [ ] GitHub release created
- [ ] Team notified (Slack/Discord announcement)
- [ ] Documentation updated (if needed)
- [ ] Post-deployment metrics captured (baseline)

**Deployment completed by**: _____________
**Deployment timestamp**: _____________
**Rollback plan confirmed**: Yes / No
**Monitoring verified**: Yes / No

---

## 📞 SUPPORT & ESCALATION

**Immediate Issues** (First 30 Minutes):
- Check Grafana alerts
- Review logs: `docker compose logs -f api`
- Run health checks: `curl https://applylens.app/api/healthz`
- Consider rollback if critical errors detected

**On-Call Contact**:
- Primary: @oncall-primary
- Secondary: @oncall-secondary
- Escalation: @engineering-lead

**Useful Commands**:
```bash
# View API logs
docker compose logs -f --tail=100 api

# View web logs
docker compose logs -f --tail=100 web

# Restart API (if needed)
docker compose restart api

# Check resource usage
docker stats

# Database connection
docker exec -it applylens-postgres psql -U postgres -d applylens
```

---

**End of Runbook** - Keep this document updated for v0.5.x patch releases! 🚀
