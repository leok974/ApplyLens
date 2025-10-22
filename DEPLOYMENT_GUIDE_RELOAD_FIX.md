# Reload Loop Fix - Deployment Guide

**Commit**: `e4a576f`
**Priority**: P0 - Production Hotfix
**Estimated Downtime**: 0 seconds (rolling deploy)

## Pre-Deployment Checklist

- [x] All code changes committed and tested
- [x] Frontend build passes (6.42s)
- [x] TypeScript compilation clean
- [x] No linting errors
- [ ] Backend smoke test passed
- [ ] Grafana dashboard JSON validated
- [ ] Prometheus rules syntax validated
- [ ] Rollback plan reviewed

## Deployment Order (Critical!)

Deploy in this exact order to minimize exposure to reload loops:

### Step 1: Backend API (5 min)

```bash
# SSH into production server
ssh user@applylens.app

# Pull latest code
cd /opt/ApplyLens
git pull origin main

# Rebuild API container (includes new /status endpoint)
cd services/api
docker-compose -f docker-compose.prod.yml build api

# Rolling restart (zero downtime)
docker-compose -f docker-compose.prod.yml up -d api

# Verify health
curl http://localhost:8003/ready
# Expected: {"status": "ready", "db": "ok", "es": "ok", ...}

curl http://localhost:8003/status
# Expected: {"ok": true, "gmail": "ok"}
```

**Validation:**
```bash
# Check logs for errors
docker logs applylens-api-1 --tail 50

# Test degraded state (simulate DB down)
docker stop applylens-postgres-1
curl http://localhost:8003/status
# Expected: {"ok": false, "gmail": "degraded", "message": "..."}
docker start applylens-postgres-1
```

### Step 2: Nginx (2 min)

```bash
# Update nginx config (adds proxy_next_upstream retry)
docker-compose -f docker-compose.prod.yml restart nginx

# Validate config
docker exec applylens-nginx-1 nginx -t
# Expected: "syntax is ok" and "test is successful"

# Check retry config is active
docker exec applylens-nginx-1 cat /etc/nginx/conf.d/applylens.prod.conf | grep -A 3 "proxy_next_upstream"
# Expected:
# proxy_next_upstream error timeout http_502 http_503 http_504;
# proxy_next_upstream_tries 2;
# proxy_next_upstream_timeout 10s;
```

### Step 3: Frontend Web (5 min)

```bash
# Rebuild web container (includes new statusClient.ts, LoginGuard, HealthBadge)
cd apps/web
docker-compose -f docker-compose.prod.yml build web

# Rolling restart
docker-compose -f docker-compose.prod.yml up -d web

# Verify build
docker exec applylens-web-1 ls -la /usr/share/nginx/html/assets/
# Should see: index-<build-id>.js with recent timestamp
```

### Step 4: Prometheus Alerts (3 min)

```bash
# Mount alert rules
# Edit docker-compose.prod.yml:
# prometheus:
#   volumes:
#     - ./infra/prometheus/rules:/etc/prometheus/rules:ro

# Update prometheus.yml config
# rule_files:
#   - /etc/prometheus/rules/*.yml

# Restart Prometheus
docker-compose -f docker-compose.prod.yml restart prometheus

# Validate rules loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].name'
# Expected: "api_status_health"
```

### Step 5: Grafana Dashboard (2 min)

```bash
# Option A: Auto-provision (recommended)
# Copy dashboard JSON to Grafana provisioning directory
cp infra/grafana/dashboards/api-status-health.json /var/lib/grafana/provisioning/dashboards/
docker-compose -f docker-compose.prod.yml restart grafana

# Option B: Manual import
# 1. Open Grafana UI: http://applylens.app/grafana
# 2. Dashboards → Import → Upload JSON
# 3. Select file: infra/grafana/dashboards/api-status-health.json
# 4. Set datasource: Prometheus
# 5. Click "Import"
```

## Post-Deployment Smoke Test (10 min)

### Test 1: Normal Operation

```bash
# Open browser: http://applylens.app/web/inbox
# Expected:
# - Page loads normally
# - No console errors
# - HealthBadge shows "Warehouse OK" (green)
```

### Test 2: Simulate Backend Degradation (CRITICAL)

```bash
# Stop API container
docker stop applylens-api-1

# Open browser: http://applylens.app/web/inbox
# Expected:
# - LoginGuard shows "Service Temporarily Unavailable" message
# - NO page reload loops (critical!)
# - Console shows retry attempts with increasing delays: 2s, 4s, 8s, 16s...
# - After 30s, UI still responsive (not frozen)

# Start API
docker start applylens-api-1

# Expected:
# - UI recovers within 2-8 seconds WITHOUT manual reload
# - LoginGuard disappears, inbox loads
# - HealthBadge recovers to green
```

### Test 3: Grafana Dashboard

```bash
# Open: http://applylens.app/grafana/d/api-status-health
# Expected panels visible:
# 1. Success Rate Gauge (should be ~100% if healthy)
# 2. Request Rate by Status (2xx line visible)
# 3. Database Status (green "UP")
# 4. Elasticsearch Status (green "UP")
# 5. Response Time chart (P50/P95/P99)
# 6. 5xx Errors by Endpoint (should be near zero)
```

### Test 4: Prometheus Alerts

```bash
# Check alerts are loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name=="api_status_health") | .rules[].name'

# Expected output:
# "StatusEndpointDegraded"
# "StatusEndpointCritical"
# "DatabaseDown"
# "ElasticsearchDown"
# "HighApiErrorRate"
# "StatusEndpointSlowResponse"
# "StatusEndpointRetryStorm"

# During smoke test (API stopped), expect alerts to fire:
# - DatabaseDown (after 1m)
# - StatusEndpointCritical (after 2m)
```

## Monitoring During Rollout

**Watch these metrics for 30 minutes post-deploy:**

1. **Grafana "API Status & Health" Dashboard:**
   - Success Rate Gauge: Should stay ≥99% (green)
   - Database/ES Status: Should be "UP" (green)
   - Request Rate: No abnormal spikes (retry storm)

2. **Prometheus Alerts:**
   - No firing alerts (unless expected during test)
   - StatusEndpointRetryStorm should NOT fire

3. **Browser Console (sample 5-10 users):**
   - No "ReloadGuard blocked" messages (indicates loop prevented)
   - LoginGuard/HealthBadge retry logs show exponential backoff

## Success Criteria

- ✅ Frontend builds and deploys successfully
- ✅ Backend `/status` returns 200 always (even when DB down)
- ✅ Nginx retry config active (`nginx -t` passes)
- ✅ **CRITICAL**: Stopping API does NOT cause page reload loops
- ✅ UI recovers automatically within 2-8s after API restart
- ✅ Grafana dashboard shows all panels correctly
- ✅ Prometheus alerts loaded (7 rules in `api_status_health` group)
- ✅ No alerts firing in steady state

## Rollback Procedure (if reload loop persists)

### Quick Rollback (5 min)

```bash
# Revert to previous Docker images
docker tag applylens-api:backup applylens-api:latest
docker tag applylens-web:backup applylens-web:latest
docker tag applylens-nginx:backup applylens-nginx:latest

docker-compose -f docker-compose.prod.yml up -d api web nginx

# Verify rollback
git log --oneline -5  # Note current commit
git revert e4a576f    # Revert this commit
git push origin main
```

### Full Rollback (10 min)

```bash
# Option 1: Git revert
git revert e4a576f
git push origin main

# Option 2: Git reset (if safe)
git reset --hard HEAD~1
git push --force origin main

# Redeploy previous version
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Remove Prometheus rules
docker exec applylens-prometheus-1 rm /etc/prometheus/rules/status-health.yml
docker-compose -f docker-compose.prod.yml restart prometheus

# Remove Grafana dashboard (manual)
# UI → Dashboards → "API Status & Health Monitoring" → Delete
```

## Troubleshooting

### Issue: Frontend still reloads on errors

**Debug:**
```bash
# Check if new code deployed
docker exec applylens-web-1 cat /usr/share/nginx/html/index.html | grep "build-id"
# Should see recent timestamp

# Check browser console
# Should see: [LoginGuard] Backend unavailable (500), retrying...
# NOT see: Rapid "Loading Gmail status..." loops

# Check LoginGuard source in DevTools
# Should have: if (r.status >= 500 && r.status < 600) { ... setAuthState("degraded") }
```

**Fix:**
```bash
# Hard refresh browser (Ctrl+Shift+R)
# Clear cache and reload
# Check service worker not cached old code
```

### Issue: Backend returns 503 instead of 200

**Debug:**
```bash
# Check which version deployed
docker exec applylens-api-1 cat /app/app/health.py | grep "raise HTTPException"
# Should NOT see: raise HTTPException(status_code=503

# Check logs
docker logs applylens-api-1 | grep "status_code=503"
```

**Fix:**
```bash
# Rebuild and redeploy API
docker-compose -f docker-compose.prod.yml build api --no-cache
docker-compose -f docker-compose.prod.yml up -d api
```

### Issue: Prometheus alerts not firing

**Debug:**
```bash
# Check rules loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].file'

# Check for rule errors
docker logs applylens-prometheus-1 | grep -i error
```

**Fix:**
```bash
# Validate YAML syntax
docker exec applylens-prometheus-1 promtool check rules /etc/prometheus/rules/status-health.yml

# Restart Prometheus
docker-compose -f docker-compose.prod.yml restart prometheus
```

## Next Steps (Post-Deployment)

1. **Monitor for 24 hours:**
   - Review Grafana dashboard daily
   - Check for any alert firings
   - Verify no user reports of reload issues

2. **Capacity planning:**
   - Baseline normal request rate to status endpoints
   - Set up alerting thresholds based on actual traffic

3. **Future enhancements:**
   - Add circuit breaker after N consecutive failures
   - Emit custom metric for "UI degraded state" count
   - Add browser-side telemetry (Sentry) for better visibility

## Contact

- **On-call Engineer**: [Your contact]
- **Escalation**: [Manager contact]
- **Incident Channel**: #incidents-prod
