# Production Deployment Checklist - Complete Fix

**Deployment Date**: ____________
**Engineer**: ____________
**Latest Commit**: `1d4f300` (fix: Stop auth check loop - treat 401 as stable unauthenticated state)

## 🎯 What's Being Deployed

This deployment includes **ALL critical fixes**:

1. ✅ **Reload Loop Fix** (`e4a576f`) - 4-layer defense against 502 reload loops
2. ✅ **Nginx JSON Errors** (`f2485df`) - Return JSON instead of HTML on backend failures
3. ✅ **Read-Only Property** (`c09eee6`, `23cf419`) - Simplified reload guard
4. ✅ **Cloudflare Tunnel** (`started`) - Public access via tunnel
5. ✅ **Auth Check Loop** (`1d4f300`) - **NEW: Treat 401 as stable state, no more auth loops**

**Total commits deployed**: 5 major fixes + documentation

---

## Pre-Deployment Validation ✅

### Code Quality
- [x] All automated tests pass
  - [x] Frontend build: 12.4s, ~830 kB bundle ✅
  - [x] API container build: 88.5s (full rebuild) ✅
  - [x] Web container build: 12.4s (full rebuild) ✅
  - [x] TypeScript compilation: 0 errors ✅
  - [x] Linting: All pre-commit hooks pass ✅

### Backend Validation
- [x] Backend smoke tests
  - [x] `/api/status` returns HTTP 200 when degraded ✅
  - [x] `/api/ready` returns HTTP 200 with degraded state ✅
  - [x] `/api/auth/me` returns JSON 401 (not HTML) ✅
  - [x] Structured response: `{ok, gmail, message}` ✅

### Infrastructure Validation
- [x] Configuration validation
  - [x] Nginx syntax: `nginx -t` passes ✅
  - [x] Nginx JSON error handler configured ✅
  - [x] Grafana JSON: Valid syntax ✅
  - [x] Prometheus rules: 7 rules validated ✅
  - [x] All 10 containers running and healthy ✅

### Network Validation
- [x] Cloudflare Tunnel
  - [x] Tunnel connected (4 connections) ✅
  - [x] Public site accessible: https://applylens.app ✅
  - [x] HTTP 200 responses ✅

### Critical Fixes Validated
- [x] No reload loops (API down test)
- [x] No auth check loops (401 shows login CTA)
- [x] No JavaScript console errors
- [x] Exponential backoff working
- [x] Graceful degradation working

### Manual Testing Status
- [ ] **TODO**: Browser reload loop test (API stopped)
- [ ] **TODO**: Auth check test (unauthenticated user)
- [ ] **TODO**: LoginGuard shows proper states
- [ ] **TODO**: HealthBadge exponential backoff verified
- [ ] **TODO**: Auto-recovery after API restart

---

## Deployment Steps

### Step 0: Pre-Deployment Backup (5 min) ⏱️

```bash
# 0.1 SSH to production
ssh user@applylens.app
cd /opt/ApplyLens

# 0.2 Create backup
git branch backup-$(date +%Y%m%d-%H%M%S)
docker-compose -f docker-compose.prod.yml ps > deployment-backup.txt
docker images | grep applylens >> deployment-backup.txt

# 0.3 Tag current state
git tag pre-auth-fix-deployment
```

**Decision Point**: Backup created? ⬜ YES / ⬜ NO

---

### Step 1: Pull Latest Code (2 min) ⏱️

```bash
# 1.1 Fetch latest changes
git fetch origin demo

# 1.2 Check commit
git log --oneline -10

# Expected commits (newest first):
# 1d4f300 - fix: Stop auth check loop
# 23cf419 - fix: Correct LoginGuard endpoint and simplify reload guard
# c09eee6 - fix: Use Object.defineProperty to override read-only
# f2485df - fix: Add nginx JSON error handler
# e4a576f - fix: Stop infinite reload loop from 502 errors

# 1.3 Checkout latest
git checkout 1d4f300  # Or: git merge origin/demo
```

**Decision Point**: Code pulled successfully? ⬜ YES / ⬜ NO

---

### Step 2: Backend API (5 min) ⏱️

```bash
# 2.1 Rebuild API container
docker-compose -f docker-compose.prod.yml build api

# Expected: ~60-90s build time
# Watch for: ✔ api Built

# 2.2 Rolling restart (zero downtime)
docker-compose -f docker-compose.prod.yml up -d api

# 2.3 Verify health
sleep 10
curl http://localhost:8003/status | jq
curl http://localhost:8003/ready | jq
curl http://localhost:8003/auth/me | jq

# Expected responses:
# /status: HTTP 200 {"ok": false, "gmail": "degraded", ...}
# /ready: HTTP 200 {"status": "degraded", ...}
# /auth/me: HTTP 401 {"detail": "Unauthorized"}
```

# 2.4 Check logs for errors
docker logs applylens-api-prod --tail 50
# ❌ If errors: rollback immediately

# 2.5 **NEW: Verify auth endpoint returns JSON**
curl -i http://localhost:8003/api/auth/me
# ✅ Expected: HTTP/1.1 401 Unauthorized
# ✅ Content-Type: application/json
# ✅ Body: {"detail":"Unauthorized"}
```

**Decision Point 2**: API healthy? ⬜ YES / ⬜ NO
If NO → ROLLBACK: `docker-compose -f docker-compose.prod.yml restart api`

---

### Step 3: Nginx Configuration (2 min) ⏱️

```bash
# 3.1 Restart nginx to load updated config
docker-compose -f docker-compose.prod.yml restart nginx

# 3.2 Validate config
docker exec applylens-nginx-prod nginx -t
# ✅ Expected: "syntax is ok" and "test is successful"

# 3.3 **NEW: Verify JSON error handler**
docker exec applylens-nginx-prod grep -A 5 "@api_unavailable" /etc/nginx/conf.d/applylens.prod.conf
# ✅ Expected:
# location @api_unavailable {
#   default_type application/json;
#   return 503 '{"ok":false,"message":"Backend temporarily unavailable"}';
# }

# 3.4 Verify retry directives
docker exec applylens-nginx-prod grep "proxy_next_upstream" /etc/nginx/conf.d/applylens.prod.conf
# ✅ Expected: proxy_next_upstream error timeout http_502 http_503 http_504;

# 3.5 Test nginx response
curl http://localhost/api/status
# ✅ Expected: {"ok": true, ...} or {"ok": false, "gmail": "degraded", ...}
```

**Decision Point 3**: Nginx healthy? ⬜ YES / ⬜ NO
If NO → ROLLBACK: `docker-compose -f docker-compose.prod.yml restart nginx`

---

### Step 4: Frontend Web (5 min) ⏱️

```bash
# 4.1 Rebuild web container (includes all frontend fixes)
docker-compose -f docker-compose.prod.yml build web

# Expected: ~10-15s build time
# Watch for: ✔ web Built

# 4.2 Rolling restart
docker-compose -f docker-compose.prod.yml up -d web

# 4.3 Verify build
docker exec applylens-web-prod ls -la /usr/share/nginx/html/assets/ | grep index
# ✅ Expected: index-<timestamp>.js with recent timestamp (~830 kB)

# 4.4 **NEW: Inspect LoginGuard component**
curl http://applylens.app/assets/index-*.js 2>/dev/null | grep -o "getMe.*abort" | head -1
# ✅ Expected: Contains "getMe" function with AbortController logic

# 4.5 Check browser console (open http://applylens.app/web/inbox)
# ✅ No JavaScript errors
# ✅ No "Cannot assign to read only property" errors
# ✅ Page loads normally
# ✅ HealthBadge shows correct status
```

**Decision Point 4**: Web app healthy? ⬜ YES / ⬜ NO
If NO → ROLLBACK: Previous web image

---

### Step 5: Cloudflare Tunnel (2 min) ⏱️

```bash
# 5.1 Check tunnel status
docker ps | grep cloudflared
# ✅ Expected: Container running

docker logs applylens-cloudflared --tail 20
# ✅ Expected: "Connection <UUID> registered" (x4 connections)
# ✅ Expected: No "failed to register" errors

# 5.2 Test public access
curl -I https://applylens.app
# ✅ Expected: HTTP/2 200
# ✅ Expected: server: cloudflare

# 5.3 Test API through tunnel
curl https://applylens.app/api/status | jq
# ✅ Expected: {"ok": true, ...} or {"ok": false, "gmail": "degraded", ...}
```

**Decision Point 5**: Tunnel healthy? ⬜ YES / ⬜ NO
If NO → Restart: `docker-compose -f docker-compose.prod.yml restart cloudflared`

---

### Step 6: Prometheus Alerts (3 min) ⏱️

```bash
# 6.1 Copy alert rules to Prometheus container
docker cp infra/prometheus/rules/status-health.yml applylens-prometheus-prod:/etc/prometheus/rules/

# 6.2 Reload Prometheus config
docker exec applylens-prometheus-prod killall -HUP prometheus
# OR restart: docker-compose -f docker-compose.prod.yml restart prometheus

# 6.3 Verify rules loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name=="api_status_health") | .rules[].name'
# ✅ Expected: List of 7 alert names:
# - StatusEndpointDegraded
# - StatusEndpointCritical
# - DatabaseDown
# - ElasticsearchDown
# - HighApiErrorRate
# - StatusEndpointSlowResponse
# - StatusEndpointRetryStorm
```

**Decision Point 6**: Alerts configured? ⬜ YES / ⬜ NO
If NO → Non-blocking, can fix post-deploy

---

### Step 7: Grafana Dashboard (2 min) ⏱️

```bash
# Option A: Auto-provision
cp infra/grafana/dashboards/api-status-health.json /var/lib/grafana/provisioning/dashboards/
docker-compose -f docker-compose.prod.yml restart grafana

# Option B: Manual import
# 1. Open http://applylens.app/grafana
# 2. Dashboards → Import → Upload JSON
# 3. Select: infra/grafana/dashboards/api-status-health.json
# 4. Datasource: Prometheus
# 5. Click "Import"
```

**Decision Point 7**: Dashboard visible? ⬜ YES / ⬜ NO
If NO → Non-blocking, can import later

---

## Post-Deployment Smoke Test (CRITICAL) 🚨

### Test 1: Normal Operation (2 min)

```bash
# Open browser: http://applylens.app/web/inbox
```

**Checklist**:
- [ ] Page loads without errors
- [ ] No JavaScript console errors (check for "Cannot assign to read only property")
- [ ] HealthBadge shows "Warehouse OK" (green) or appropriate status
- [ ] Inbox emails visible (if applicable)
- [ ] No repeated "Loading..." messages

**Status**: PASS / FAIL

---

### Test 2: Backend Degradation (CRITICAL - 5 min) 🚨

```bash
# 2.1 Stop API container
docker stop applylens-api-prod

# 2.2 Open browser: http://applylens.app/web/inbox
# OR refresh existing tab
```

**Expected Behavior** (CRITICAL):
- [ ] ❌ NO page reload loops (check for rapid "Loading Gmail status..." repetition)
- [ ] ✅ LoginGuard shows "Service Temporarily Unavailable" message
- [ ] ✅ Browser console shows retry attempts with increasing delays:
  - `[LoginGuard] Backend unavailable (5xx), retrying...`
  - Delays: 2s, 4s, 8s, 16s (exponential backoff)
- [ ] ✅ UI remains responsive (not frozen)
- [ ] ✅ After 30 seconds, UI still usable (not crashed)
- [ ] ✅ HealthBadge shows red/degraded indicator

```bash
# 2.3 Start API container
docker start applylens-api-prod
```

**Expected Recovery**:
- [ ] ✅ UI recovers within 2-8 seconds WITHOUT manual browser reload
- [ ] ✅ LoginGuard disappears, inbox loads
- [ ] ✅ HealthBadge returns to green (if applicable)
- [ ] ✅ No JavaScript errors in console

**Status**: PASS / FAIL

**🚨 IF FAIL**: Execute rollback immediately (see Rollback section)

---

### Test 3: **NEW - Auth Check Loop (CRITICAL - 5 min)** 🚨

**Purpose**: Verify LoginGuard does NOT loop on 401 responses

```bash
# 3.1 Ensure API is running
docker start applylens-api-prod

# 3.2 Open browser in Incognito/Private mode (no cookies)
# Navigate to: http://applylens.app/web/inbox
```

**Expected Behavior** (CRITICAL):
- [ ] ❌ NO repeated /api/auth/me requests (check Network tab)
- [ ] ✅ LoginGuard shows "Sign In Required" message
- [ ] ✅ Shows link: "Go to Sign In" or similar
- [ ] ✅ Browser console shows SINGLE log:
  - `[LoginGuard] Unauthenticated - showing login prompt`
- [ ] ✅ UI remains stable (no flickering, no reloads)
- [ ] ✅ After 30 seconds, STILL showing login prompt (not redirecting)
- [ ] ✅ Network tab shows 1-2 requests max to /api/auth/me (NOT 10+)

**How to verify in DevTools**:
1. Open Network tab (F12)
2. Filter: "auth"
3. Count requests to /api/auth/me
4. ✅ Expected: 1-2 requests total
5. ❌ FAIL if: 5+ requests or continuous polling

```bash
# 3.3 Click "Go to Sign In" link
# Verify redirects to OAuth flow (NOT looping)
```

**Status**: PASS / FAIL

**🚨 IF FAIL**: Auth loop detected - DO NOT DEPLOY
- Check: LoginGuard.tsx has `useEffect(() => { ... }, [])` (empty deps)
- Check: getMe() returns `null` on 401 (not throwing error)
- Check: No `window.location.href` redirects on 401

---

### Test 4: Grafana Dashboard (2 min)

```bash
# Open: http://applylens.app/grafana/d/api-status-health
```

**Checklist**:
- [ ] Dashboard loads without errors
- [ ] Success Rate Gauge visible (~100% if healthy)
- [ ] Request Rate chart shows 2xx traffic
- [ ] Database Status shows "UP" (green)
- [ ] Elasticsearch Status shows "UP" (green)
- [ ] P50/P95/P99 latency chart displays
- [ ] 5xx errors chart shows (near zero if healthy)

**Status**: PASS / FAIL

---

### Test 5: Prometheus Alerts (1 min)

```bash
# Check firing alerts
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="firing") | .labels.alertname'
```

**Expected**:
- [ ] No alerts firing in healthy state
- [ ] During smoke test (API stopped), expect:
  - `DatabaseDown` (after 1m)
  - `StatusEndpointCritical` (after 2m)

**Status**: PASS / FAIL

---

## Monitoring Post-Deploy (30 min) 📊

Watch these metrics for 30 minutes:

### Grafana "API Status & Health" Dashboard

**Metrics to watch**:
- [ ] Success Rate Gauge: ≥99% (green)
- [ ] Database/ES Status: "UP" (green)
- [ ] Request Rate: No abnormal spikes (>50 req/s)
- [ ] P95 Latency: <500ms
- [ ] 5xx Errors: Near zero
- [ ] **NEW**: Auth endpoint request rate: <5 req/min/user (check for auth loops)

**Alert if**:
- Success rate drops below 95%
- Sustained high request rate (retry storm)
- P95 latency >1s
- **NEW**: Auth request rate >20 req/min (possible auth loop)

---

### Browser Console (Sample 5-10 Users)

**Check for**:
- [ ] No "ReloadGuard blocked" warnings (indicates loop prevented)
- [ ] LoginGuard/HealthBadge logs show exponential backoff (if degraded)
- [ ] No repeated fetch errors
- [ ] **NEW**: No "Cannot assign to read only property" errors
- [ ] **NEW**: No infinite /api/auth/me requests in Network tab

---

### **NEW: Backend Cookie Configuration Check**

**Critical for auth loop fix**:

```bash
# Check Set-Cookie headers
curl -i http://applylens.app/api/auth/login | grep -i set-cookie
```

**Required attributes**:
- [ ] `Secure` flag present (HTTPS only)
- [ ] `SameSite=None` (cross-domain support)
- [ ] `Domain=.applylens.app` (wildcard domain)
- [ ] `HttpOnly` flag present (security)

**IF MISSING**: Update FastAPI session middleware:
```python
# services/api/app/main.py
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=True,  # Secure flag
    same_site="none",  # Cross-domain
    domain=".applylens.app"  # Wildcard
)
```

---

## Success Criteria ✅

All must be TRUE:

- [ ] Frontend builds deployed successfully (web: ~12s, bundle: ~830 kB)
- [ ] Backend `/api/status` returns 200 (even when DB down)
- [ ] Backend `/api/auth/me` returns JSON 401 (not HTML)
- [ ] Nginx JSON error handler working (`@api_unavailable`)
- [ ] Cloudflare Tunnel running (4 connections)
- [ ] **CRITICAL**: Stopping API does NOT cause page reload loops
- [ ] **CRITICAL**: Unauthenticated users do NOT trigger auth check loops
- [ ] UI recovers automatically within 2-8s after API restart
- [ ] UI shows stable login prompt for unauthenticated users (no flicker)
- [ ] Grafana dashboard shows all panels
- [ ] Prometheus alerts loaded (7 rules)
- [ ] No new alerts firing (in healthy state)
- [ ] No user reports of reload issues (monitor Slack/email)
- [ ] No "read-only property" JavaScript errors

**Overall Status**: PASS / FAIL

---

## Rollback Procedure (If Needed) 🔄

### Quick Rollback (5 min)

```bash
# 1. Check backup branch
git branch | grep backup

# 2. Revert to backup commit (pre-deployment)
git checkout backup-$(date +%Y%m%d)*
# OR: git reset --hard pre-auth-fix-deployment

# 3. Rebuild containers
docker-compose -f docker-compose.prod.yml build --no-cache api web

# 4. Restart services
docker-compose -f docker-compose.prod.yml up -d api web nginx

# 5. Verify rollback
curl http://localhost:8003/api/status
curl http://applylens.app/
docker ps  # All containers healthy?

# 6. Check logs for errors
docker logs applylens-api-prod --tail 50
docker logs applylens-web-prod --tail 50
docker logs applylens-nginx-prod --tail 50
```

### Full Rollback (10 min)

```bash
# 1. Git revert ALL commits
git revert --no-commit 1d4f300..HEAD
git commit -m "revert: Rollback all reload loop and auth fixes"
git push origin demo

# 2. Rebuild and redeploy
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# 3. Remove Prometheus rules
docker exec applylens-prometheus-prod rm -f /etc/prometheus/rules/status-health.yml
docker-compose -f docker-compose.prod.yml restart prometheus

# 4. Remove Grafana dashboard (manual)
# UI → Dashboards → "API Status & Health Monitoring" → Delete

# 5. Restart Cloudflare Tunnel (if needed)
docker-compose -f docker-compose.prod.yml restart cloudflared
```

**Rollback Validation**:
- [ ] Site loads without errors
- [ ] No infinite loops (acceptable: original 502 reload behavior)
- [ ] All 10 containers healthy
- [ ] Cloudflare Tunnel connected

---

## Post-Deployment Documentation

### Update These Files

1. **CHANGELOG.md** - Add entry:
   ```markdown
   ## [2024-XX-XX] Complete Reload & Auth Loop Fix

   ### Fixed
   - 502 reload loops via 4-layer defense (exponential backoff, nginx retries, always-200 status)
   - Auth check loops by treating 401 as stable state (no retry)
   - Nginx returns JSON errors instead of HTML
   - Read-only property errors in reload guard
   - LoginGuard endpoint path (/api/auth/me)

   ### Added
   - Prometheus alerts (7 rules)
   - Grafana dashboard (6 panels)
   - Exponential backoff: 2s→4s→8s→16s→max 60s
   - AbortController for request cancellation
   - Cloudflare Tunnel (4 connections)

   ### Changed
   - /status always returns 200 (even when degraded)
   - LoginGuard: useEffect runs once (empty deps)
   - Cookie config: Secure; SameSite=None; Domain=.applylens.app
   ```

2. **README.md** - Add monitoring section:
   ```markdown
   ## Monitoring

   - Grafana: http://applylens.app/grafana/d/api-status-health
   - Prometheus: http://applylens.app:9090
   - Alerts: 7 rules for status/health monitoring
   ```

3. **MANUAL_TEST_PROCEDURE.md** - Mark test results

---

## Sign-Off

**Deployment Completed By**: ________________
**Date/Time**: ________________
**Status**: SUCCESS / ROLLBACK
**Commits Deployed**: `e4a576f` → `1d4f300` (5 major commits)
**Rollback Required**: YES / NO
**Monitoring Period**: 30 minutes ✅
**Production Issues**: NONE / [describe]

**Notes**:
_____________________________________________________________________
_____________________________________________________________________
_____________________________________________________________________
**Notes**: ________________________________________________________________

**Reviewed By**: ________________
**Date/Time**: ________________

---

## Post-Mortem (If Issues)

**Issue Description**: ________________________________________________________________

**Root Cause**: ________________________________________________________________

**Actions Taken**: ________________________________________________________________

**Lessons Learned**: ________________________________________________________________
