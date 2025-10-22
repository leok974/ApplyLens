# Production Deployment Checklist - Reload Loop Fix

**Deployment Date**: ____________
**Engineer**: ____________
**Commit**: `e4a576f` (fix: Stop infinite reload loop from 502 errors)

## Pre-Deployment Validation ✅

- [x] All automated tests pass
  - [x] Frontend build: 6.42s, 830.95 kB bundle ✅
  - [x] API container build: 11.4s ✅
  - [x] Web container build: 8.9s ✅
  - [x] TypeScript compilation: 0 errors ✅
  - [x] Linting: All hooks pass ✅

- [x] Backend smoke tests
  - [x] `/status` returns HTTP 200 when DB down ✅
  - [x] `/ready` returns HTTP 200 with degraded state ✅
  - [x] Structured response: `{ok, gmail, message}` ✅

- [x] Configuration validation
  - [x] Nginx syntax: `nginx -t` passes ✅
  - [x] Grafana JSON: Valid syntax ✅
  - [x] Prometheus rules: 7 rules validated ✅

- [ ] Manual testing
  - [ ] Browser reload loop test (API stopped)
  - [ ] LoginGuard shows degraded UI
  - [ ] HealthBadge exponential backoff verified
  - [ ] Auto-recovery after API restart

## Deployment Steps

### Step 1: Backend API (5 min) ⏱️

```bash
# 1.1 SSH to production
ssh user@applylens.app
cd /opt/ApplyLens

# 1.2 Pull latest code
git fetch origin
git checkout e4a576f

# 1.3 Rebuild API container
cd services/api
docker-compose -f docker-compose.prod.yml build api

# 1.4 Rolling restart (zero downtime)
docker-compose -f docker-compose.prod.yml up -d api

# 1.5 Verify health (CRITICAL CHECK)
curl http://localhost:8003/status
# ✅ Expected: {"ok": true, "gmail": "ok"}
# or {"ok": false, "gmail": "degraded", "message": "..."}
# ✅ HTTP Status: 200 (NOT 503)

curl http://localhost:8003/ready
# ✅ Expected: {"status": "ready", "db": "ok", "es": "ok", ...}
# or {"status": "degraded", "db": "down", ...}
# ✅ HTTP Status: 200 (NOT 503)

# 1.6 Check logs for errors
docker logs applylens-api-prod --tail 50
# ❌ If errors: rollback immediately
```

**Decision Point 1**: API healthy?
- [ ] YES → Proceed to Step 2
- [ ] NO → ROLLBACK: `docker-compose -f docker-compose.prod.yml restart api`

---

### Step 2: Nginx Configuration (2 min) ⏱️

```bash
# 2.1 Restart nginx to load updated config
docker-compose -f docker-compose.prod.yml restart nginx

# 2.2 Validate config
docker exec applylens-nginx-prod nginx -t
# ✅ Expected: "syntax is ok" and "test is successful"

# 2.3 Verify retry directives present
docker exec applylens-nginx-prod cat /etc/nginx/conf.d/applylens.prod.conf | grep -A 3 "proxy_next_upstream"
# ✅ Expected:
# proxy_next_upstream error timeout http_502 http_503 http_504;
# proxy_next_upstream_tries 2;
# proxy_next_upstream_timeout 10s;

# 2.4 Test nginx response
curl http://localhost/api/healthz
# ✅ Expected: {"status": "ok"} or similar
```

**Decision Point 2**: Nginx healthy?
- [ ] YES → Proceed to Step 3
- [ ] NO → ROLLBACK: `docker-compose -f docker-compose.prod.yml restart nginx`

---

### Step 3: Frontend Web (5 min) ⏱️

```bash
# 3.1 Rebuild web container
cd apps/web
docker-compose -f docker-compose.prod.yml build web

# 3.2 Rolling restart
docker-compose -f docker-compose.prod.yml up -d web

# 3.3 Verify build
docker exec applylens-web-prod ls -la /usr/share/nginx/html/assets/ | grep index
# ✅ Expected: index-<timestamp>.js with recent timestamp

# 3.4 Check browser console (open http://applylens.app/web/inbox)
# ✅ No JavaScript errors
# ✅ Page loads normally
# ✅ HealthBadge shows correct status
```

**Decision Point 3**: Web app healthy?
- [ ] YES → Proceed to Step 4
- [ ] NO → ROLLBACK: Previous web image

---

### Step 4: Prometheus Alerts (3 min) ⏱️

```bash
# 4.1 Copy alert rules to Prometheus container
docker cp infra/prometheus/rules/status-health.yml applylens-prometheus-prod:/etc/prometheus/rules/

# 4.2 Reload Prometheus config
docker exec applylens-prometheus-prod killall -HUP prometheus
# OR restart: docker-compose -f docker-compose.prod.yml restart prometheus

# 4.3 Verify rules loaded
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

**Decision Point 4**: Alerts configured?
- [ ] YES → Proceed to Step 5
- [ ] NO → Non-blocking, can fix post-deploy

---

### Step 5: Grafana Dashboard (2 min) ⏱️

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

**Decision Point 5**: Dashboard visible?
- [ ] YES → Proceed to smoke test
- [ ] NO → Non-blocking, can import later

---

## Post-Deployment Smoke Test (CRITICAL) 🚨

### Test 1: Normal Operation (2 min)

```bash
# Open browser: http://applylens.app/web/inbox
```

**Checklist**:
- [ ] Page loads without errors
- [ ] No JavaScript console errors
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
  - `[LoginGuard] Backend unavailable (500), retrying...`
  - Delays: 2s, 4s, 8s, 16s (exponential backoff)
- [ ] ✅ UI remains responsive (not frozen)
- [ ] ✅ After 30 seconds, UI still usable (not crashed)

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

### Test 3: Grafana Dashboard (2 min)

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

### Test 4: Prometheus Alerts (1 min)

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

**Alert if**:
- Success rate drops below 95%
- Sustained high request rate (retry storm)
- P95 latency >1s

---

### Browser Console (Sample 5-10 Users)

**Check for**:
- [ ] No "ReloadGuard blocked" warnings (indicates loop prevented)
- [ ] LoginGuard/HealthBadge logs show exponential backoff (if degraded)
- [ ] No repeated fetch errors

---

## Success Criteria ✅

All must be TRUE:

- [ ] Frontend builds deployed successfully
- [ ] Backend `/status` returns 200 (even when DB down)
- [ ] **CRITICAL**: Stopping API does NOT cause page reload loops
- [ ] UI recovers automatically within 2-8s after API restart
- [ ] Grafana dashboard shows all panels
- [ ] Prometheus alerts loaded (7 rules)
- [ ] No new alerts firing (in healthy state)
- [ ] No user reports of reload issues (monitor Slack/email)

**Overall Status**: PASS / FAIL

---

## Rollback Procedure (If Needed) 🔄

### Quick Rollback (5 min)

```bash
# 1. Revert to previous Docker images
docker tag applylens-api:backup applylens-api:latest
docker tag applylens-web:backup applylens-web:latest
docker tag applylens-nginx:backup applylens-nginx:latest

docker-compose -f docker-compose.prod.yml up -d api web nginx

# 2. Verify rollback
curl http://localhost:8003/healthz
curl http://applylens.app/web/

# 3. Check logs
docker logs applylens-api-prod --tail 50
docker logs applylens-web-prod --tail 50
```

### Full Rollback (10 min)

```bash
# 1. Git revert
git revert e4a576f
git push origin main

# 2. Rebuild and redeploy
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 3. Remove Prometheus rules
docker exec applylens-prometheus-prod rm /etc/prometheus/rules/status-health.yml
docker-compose -f docker-compose.prod.yml restart prometheus

# 4. Remove Grafana dashboard (manual)
# UI → Dashboards → "API Status & Health Monitoring" → Delete
```

---

## Sign-Off

**Deployment Completed By**: ________________
**Date/Time**: ________________
**Status**: SUCCESS / ROLLBACK
**Notes**: ________________________________________________________________

**Reviewed By**: ________________
**Date/Time**: ________________

---

## Post-Mortem (If Issues)

**Issue Description**: ________________________________________________________________

**Root Cause**: ________________________________________________________________

**Actions Taken**: ________________________________________________________________

**Lessons Learned**: ________________________________________________________________
