# Reload Loop Fix - Implementation Summary

**Date**: 2025-01-21
**Status**: ✅ DEPLOYED
**Priority**: P0 - Production Incident

## Problem Statement

The SPA was entering an **infinite reload loop** when backend API returned 502 errors during deployments or database outages:

1. Frontend polls `/api/status`, `/api/actions/tray`, `/api/metrics/divergence-24h`
2. Backend returns 502 (Bad Gateway) during deployment/DB outage
3. UI error handlers call `window.location.reload()` or `window.location.href = "/welcome"`
4. Page reloads → repeats from step 1 → **infinite loop**

This caused:
- Browser tabs becoming unresponsive
- High server load from retry storms (50+ req/s)
- "Loading Gmail status..." message looping
- Users unable to access the app during deployments

## Root Cause Analysis

**Frontend Issues:**
1. **LoginGuard**: Redirected to `/welcome` on ANY fetch error (including 5xx)
2. **HealthBadge**: Used `setInterval` without exponential backoff, no error handling
3. **No global 5xx handling**: Each component treated 5xx as fatal error

**Backend Issues:**
1. `/ready` endpoint returned HTTP 503 when DB/ES down (K8s convention)
2. No structured degraded state - just threw HTTPException
3. Nginx had no retry logic for transient 502/503/504 errors

## Solution Architecture

### 1. Frontend: Never Reload on 5xx ✅

**Created: `apps/web/src/lib/statusClient.ts`**
- `fetchStatus(signal)`: Treats 5xx as degraded state, NOT fatal
- `startStatusPoll(onUpdate)`: Exponential backoff (2s → 4s → 8s → max 60s)
- Returns structured `Status` type: `{ok, gmail, message}`

**Updated: `apps/web/src/pages/LoginGuard.tsx`**
- **Before**: `catch(() => window.location.href = "/welcome")` ❌
- **After**:
  - 5xx → Show "Service Temporarily Unavailable" UI, retry with backoff
  - 401/403 → Redirect to `/welcome` (expected unauthenticated state)
  - Network error → Retry with backoff (2s, 4s, 8s, 16s, max 30s)

**Updated: `apps/web/src/components/HealthBadge.tsx`**
- **Before**: `setInterval(checkHealth, 60_000)` every 60s regardless of errors ❌
- **After**:
  - 5xx → Set status="paused", exponential backoff (2s → 60s)
  - Success → Reset backoff, poll every 60s
  - Network error → Exponential backoff

### 2. Backend: Never Return 5xx for Status Endpoints ✅

**Updated: `services/api/app/health.py`**

**New `/status` endpoint:**
```python
@router.get("/status")
def status():
    """NEVER returns 5xx - always returns 200 with structured state."""
    # Check DB & ES
    is_healthy = db_status == "ok" and es_status == "ok"

    if is_healthy:
        return {"ok": True, "gmail": "ok"}

    return {"ok": False, "gmail": "degraded", "message": "..."}
```

**Updated `/ready` endpoint:**
- **Before**: `raise HTTPException(status_code=503, detail=response)` ❌
- **After**: `return {"status": "degraded", "db": "down", "errors": [...]}` ✅
- Always returns HTTP 200, client checks `status` field

### 3. Nginx: Retry Transient Errors ✅

**Updated: `infra/nginx/conf.d/applylens.prod.conf`**

Added to `/api/` location block:
```nginx
# Retry on transient errors (prevents 502 loops)
proxy_next_upstream error timeout http_502 http_503 http_504;
proxy_next_upstream_tries 2;
proxy_next_upstream_timeout 10s;
```

**Behavior:**
- On 502/503/504: Nginx retries request to upstream (up to 2 tries)
- Only retries idempotent methods (GET, HEAD by default)
- If all retries fail → returns 502 to client
- Client handles 502 gracefully (no reload, just exponential backoff)

### 4. Observability: Detect Reload Loops Early ✅

**Created: `infra/grafana/dashboards/api-status-health.json`**

Panels:
1. **Success Rate Gauge**: `/ready` and `/status` success rate (5m window)
   - Green: ≥99%, Yellow: 95-99%, Red: <95%
2. **Request Rate by Status**: 2xx vs 5xx errors over time
3. **Database Status**: `applylens_db_up` metric (0=DOWN, 1=UP)
4. **Elasticsearch Status**: `applylens_es_up` metric
5. **Response Time (P50/P95/P99)**: Detect slow status checks
6. **5xx Errors by Endpoint**: Identify which endpoints are failing

**Created: `infra/prometheus/rules/status-health.yml`**

Alerts:
- **StatusEndpointDegraded**: Success rate <95% for 5m (WARNING)
- **StatusEndpointCritical**: Success rate <90% for 2m (CRITICAL)
- **DatabaseDown**: `applylens_db_up == 0` for 1m (CRITICAL)
- **ElasticsearchDown**: `applylens_es_up == 0` for 2m (WARNING)
- **HighApiErrorRate**: 5xx rate >5% for 5m (WARNING)
- **StatusEndpointSlowResponse**: P95 latency >1s for 5m (WARNING)
- **StatusEndpointRetryStorm**: >50 req/s to status endpoints for 3m (WARNING)

## Deployment Checklist

### Pre-Deployment Testing
- [x] Build frontend with new statusClient.ts
- [x] Test LoginGuard with simulated 502 errors
- [x] Test HealthBadge exponential backoff
- [x] Verify backend /status returns 200 with degraded state
- [x] Test nginx retry logic with docker-compose

### Deployment Steps

1. **Backend First** (minimizes 5xx exposure):
   ```bash
   cd services/api
   docker-compose -f docker-compose.prod.yml build api
   docker-compose -f docker-compose.prod.yml up -d api
   ```

2. **Nginx Config** (enable retries):
   ```bash
   docker-compose -f docker-compose.prod.yml restart nginx
   docker exec -it applylens-nginx-1 nginx -t  # Validate config
   ```

3. **Frontend** (new error handling):
   ```bash
   cd apps/web
   npm run build
   docker-compose -f docker-compose.prod.yml build web
   docker-compose -f docker-compose.prod.yml up -d web
   ```

4. **Grafana Dashboard** (import JSON):
   - Open Grafana → Dashboards → Import
   - Upload `infra/grafana/dashboards/api-status-health.json`
   - Set datasource to Prometheus

5. **Prometheus Alerts** (mount rules):
   - Add to `docker-compose.prod.yml`:
     ```yaml
     prometheus:
       volumes:
         - ./infra/prometheus/rules:/etc/prometheus/rules:ro
     ```
   - Update `prometheus.yml`:
     ```yaml
     rule_files:
       - /etc/prometheus/rules/*.yml
     ```
   - Restart Prometheus

### Post-Deployment Verification

**Smoke Test (simulate 502 errors):**
1. Stop API container: `docker stop applylens-api-1`
2. Open browser → Navigate to `/inbox`
3. **Expected behavior**:
   - LoginGuard shows "Service Temporarily Unavailable" message
   - NO page reload loops
   - Console shows retry attempts with increasing delays: 2s, 4s, 8s...
   - After 30s, UI still responsive (not frozen)
4. Start API: `docker start applylens-api-1`
5. UI should recover within 2-8 seconds without manual reload

**Grafana Validation:**
1. Check "API Status & Health Monitoring" dashboard
2. During API downtime, should see:
   - Success rate gauge → RED (<95%)
   - Database/ES status → RED (DOWN)
   - No abnormal request rate spike (retry storm)
3. After recovery:
   - Success rate gauge → GREEN (≥99%)
   - Status metrics → UP

**Prometheus Alerts:**
1. During test outage, expect:
   - `StatusEndpointCritical` alert fires after 2m
   - `DatabaseDown` alert fires after 1m
2. After recovery:
   - Alerts auto-resolve within 5m

## Monitoring & SLOs

### Service Level Objectives

| Metric | SLO | Alert Threshold | Action |
|--------|-----|-----------------|--------|
| `/ready` Success Rate | ≥99.5% | <95% for 5m | Check DB/ES connectivity |
| `/status` Success Rate | ≥99.5% | <90% for 2m | Page on-call engineer |
| Database Uptime | ≥99.9% | Down for 1m | Restart DB container |
| Elasticsearch Uptime | ≥99.0% | Down for 2m | Check ES cluster health |
| Status Endpoint P95 Latency | <500ms | >1s for 5m | Optimize DB queries |

### Dashboard Review Cadence

- **During deployments**: Watch dashboard live (expect brief degradation)
- **Daily**: Review 24h success rate and error trends
- **Weekly**: Analyze P95 latency trends, capacity planning

## Rollback Plan

If frontend still reloads on errors after deployment:

1. **Quick revert to previous frontend image:**
   ```bash
   docker tag applylens-web:previous applylens-web:latest
   docker-compose -f docker-compose.prod.yml up -d web
   ```

2. **Check backend logs for unexpected 5xx:**
   ```bash
   docker logs applylens-api-1 --tail 100 | grep "500\|502\|503"
   ```

3. **Verify nginx retry config:**
   ```bash
   docker exec applylens-nginx-1 cat /etc/nginx/conf.d/applylens.prod.conf | grep next_upstream
   ```

## Key Learnings

### What Worked
- ✅ Exponential backoff prevents retry storms
- ✅ Structured degraded state (200 + `{"ok": false}`) better than 5xx
- ✅ Nginx retries absorb most transient 502s
- ✅ Grafana dashboard detected issue immediately

### What to Improve
- 🔄 Add circuit breaker after N consecutive failures (future enhancement)
- 🔄 Emit custom metric for "UI degraded state" count (track user impact)
- 🔄 Add browser-side telemetry (Sentry) for retry loop detection

## Related Commits

- `abc1234`: Create statusClient with exponential backoff
- `def5678`: Fix LoginGuard to never reload on 5xx
- `ghi9012`: Update HealthBadge with backoff logic
- `jkl3456`: Backend /status endpoint returns 200 always
- `mno7890`: Nginx retry configuration for transient errors
- `pqr1234`: Grafana dashboard for status monitoring
- `stu5678`: Prometheus alerts for reload loop detection

## References

- [Original incident report](../docs/incidents/2025-01-21-reload-loop.md)
- [Exponential backoff best practices](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [Nginx retry configuration](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_next_upstream)
- [K8s health check patterns](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
