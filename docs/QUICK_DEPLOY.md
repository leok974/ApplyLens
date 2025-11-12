# ApplyLens v0.5.0 - Quick Deployment Summary

**Version:** 0.5.0
**Release Date:** 2025-01-27
**Status:** ✅ Ready for Production

---

## 📦 What Changed

### Critical Fixes
- ✅ **Logout 500 Error** - Fixed Session naming conflict (Session vs UserSession)
- ✅ **Browser Crashes** - Eliminated hard reloads, using React Router navigation
- ✅ **CSRF Bootstrap** - Implemented `ensureCsrf()` + `apiFetch()` wrapper

### Features
- ✅ **Deep Linking** - `/inbox?open=<thread_id>` URLs work
- ✅ **Dev Routes Fix** - Precedence fixed for reliable seed endpoints

### Testing
- ✅ **E2E Hardening** - Trace-on-first-retry, video capture, console listeners
- ✅ **Regression Tests** - API unit test + 2 UI E2E tests
- ✅ **Documentation** - 900+ lines of testing & setup guides

---

## 🚀 Quick Deploy (5 Minutes)

### 1. Pull & Deploy

```bash
cd /path/to/ops/workspace

# Pull latest images
docker compose -f docker-compose.prod.yml pull

# Backup database (optional but recommended)
docker exec applylens_db pg_dump -U applylens applylens > backup-$(date +%Y%m%d).sql

# Deploy
docker compose -f docker-compose.prod.yml up -d

# Verify
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### 2. Update Environment Variables

**Edit `.env` or `docker-compose.prod.yml`:**

```bash
# Critical for production
ALLOW_DEV_ROUTES=0              # ⚠️ MUST be 0 in prod
COOKIE_SECURE=1                 # ⚠️ MUST be 1 for HTTPS
COOKIE_DOMAIN=applylens.app     # Your apex domain
SESSION_SECRET=<new-random>     # ⚠️ Rotate after debugging

# Recommended
RATE_LIMIT_MAX_REQ=100          # More permissive for real users
LOG_LEVEL=INFO                  # Production logging
```

### 3. Health Checks (2 minutes)

```bash
# API health
curl https://applylens.app/api/healthz
# Expected: {"status":"ok","version":"0.5.0"}

# Web health
curl -s -o /dev/null -w "%{http_code}\n" https://applylens.app/health
# Expected: 200

# CSRF
curl -v https://applylens.app/api/auth/csrf 2>&1 | grep set-cookie
# Expected: set-cookie: csrf_token=...
```

### 4. Manual Smoke Test (2 minutes)

1. Open https://applylens.app/welcome
2. Click "Try Demo" → Should land on /inbox
3. Search for something → Results appear
4. Click User Menu → Logout → Should redirect to /welcome
5. ✅ **No browser crash!**

---

## 🔄 Rollback Plan

If something goes wrong:

```bash
# Edit docker-compose.prod.yml to use previous version
# api: ghcr.io/leok974/applylens/api:0.4.64
# web: ghcr.io/leok974/applylens/web:0.4.64

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Restore database (if needed)
docker exec -i applylens_db psql -U applylens < backup-YYYYMMDD.sql
```

**No database migrations in v0.5.0 - rollback is safe!**

---

## 📊 Success Metrics

| Metric | Target | Check |
|--------|--------|-------|
| API Health | 200 OK | `curl /api/healthz` |
| Logout Success | 100% | Manual test |
| Browser Crashes | 0 | Manual test |
| Error Rate | < 0.1% | Grafana |
| Response Time | < 100ms | `/api/healthz` |

---

## 📚 Full Documentation

**Before deploying, review:**

1. **[PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)** (17 steps, ~40 min read)
   - Complete checklist with environment variables
   - Build & push instructions
   - Monitoring setup
   - Security checklist
   - Rollback procedures

2. **[CHANGELOG.md](../CHANGELOG.md)** (~20 min read)
   - Detailed release notes
   - Migration notes
   - Rollback instructions
   - Known issues

3. **[DOCKER_SETUP_COMPLETE.md](./DOCKER_SETUP_COMPLETE.md)** (15 min read)
   - Docker configuration
   - Known issues & fixes
   - Best practices
   - **Incident RCA** (logout bug)

4. **[E2E_GUIDE.md](../apps/web/docs/E2E_GUIDE.md)** (Optional, 25 min read)
   - Testing guide
   - Running tests against production
   - Debugging tips

---

## ⚡ TL;DR

```bash
# 1. Update env vars
ALLOW_DEV_ROUTES=0
COOKIE_SECURE=1
SESSION_SECRET=<new-random>

# 2. Deploy
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# 3. Test
curl https://applylens.app/api/healthz
# Try demo login → logout in browser

# 4. Monitor
# Watch Grafana for 1 hour, ensure no alerts
```

**Expected downtime:** < 30 seconds (rolling restart)

---

## 🆘 Support

**Issues during deployment?**

1. Check logs: `docker compose logs api --tail=100`
2. Verify env vars: `docker compose config`
3. Health check: `curl http://localhost:8888/api/healthz`
4. Rollback if needed (see above)

**Emergency contact:** [Your team contact]

---

## ✅ Deployment Checklist

- [ ] Reviewed CHANGELOG.md
- [ ] Updated environment variables (ALLOW_DEV_ROUTES=0, COOKIE_SECURE=1)
- [ ] Backed up database
- [ ] Pulled latest images
- [ ] Deployed services
- [ ] Verified health checks
- [ ] Ran manual smoke test
- [ ] Monitoring dashboards healthy
- [ ] No critical alerts
- [ ] Team notified

**Sign-off:** ________________  **Date:** ________

---

**Questions?** Read the full [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) or ask in #engineering-deploys
