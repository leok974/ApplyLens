# Phase 3 — Verification Runbook

## Quick Verification Commands

### 1. Backend API (Local)

#### Start API in Demo Mode
```bash
cd services/api

# Set environment variables
export USE_WAREHOUSE_METRICS=0  # Demo mode
export DEMO_MODE=1

# Start API
uvicorn app.main:app --reload --port 8003
```

#### Test Endpoints with curl

**Divergence Endpoint (Healthy)**
```bash
curl -s http://localhost:8003/api/metrics/divergence-24h | jq
```
Expected output:
```json
{
  "es_count": 1000,
  "bq_count": 1000,
  "divergence_pct": 0.0,
  "status": "ok",
  "message": "Divergence: 0.00% (OK) [Demo Mode]"
}
```

**Activity Daily**
```bash
curl -s http://localhost:8003/api/metrics/activity-daily | jq | head -20
```

**Top Senders**
```bash
curl -s http://localhost:8003/api/metrics/top-senders-30d | jq
```

**Categories**
```bash
curl -s http://localhost:8003/api/metrics/categories-30d | jq
```

### 2. Demo Seed Script

#### Seed Healthy State
```bash
cd services/api
python scripts/seed_demo_metrics.py
```

#### Seed Degraded State
```bash
DEMO_DIVERGENCE_STATE=degraded python scripts/seed_demo_metrics.py
```

Expected output:
```
✓ Seeded divergence metrics:
  State: degraded
  Divergence: 3.5%
  Payload: {
    "es_count": 10350,
    "bq_count": 10000,
    "divergence_pct": 3.5,
    "status": "degraded",
    "message": "Divergence: 3.50% (DEGRADED)"
  }
```

#### Seed Paused State
```bash
DEMO_DIVERGENCE_STATE=paused python scripts/seed_demo_metrics.py
```

Expected output:
```
✓ Seeded divergence metrics:
  State: paused
  Divergence: None%
  Payload: {
    "es_count": 0,
    "bq_count": 0,
    "divergence_pct": null,
    "status": "paused",
    "message": "System paused due to high divergence or error"
  }
```

#### Custom Divergence Percentage
```bash
DEMO_DIVERGENCE_PCT=1.2 python scripts/seed_demo_metrics.py
```

### 3. Frontend Testing

#### Start Web App
```bash
cd apps/web

# Set demo mode
export VITE_DEMO_MODE=1

# Start dev server
npm run dev
```

#### Visual Verification
1. **Open Dashboard** → `http://localhost:5173/`
2. **Check Top-Right Corner** → HealthBadge should be visible
3. **Verify States:**
   - Green badge: "Warehouse OK (0.0%)"
   - Yellow badge: "Degraded (3.5%)" 
   - Gray badge: "Paused"

#### Change States Dynamically
```bash
# Terminal 1: Keep app running

# Terminal 2: Seed different states
cd services/api
DEMO_DIVERGENCE_STATE=ok python scripts/seed_demo_metrics.py
# Wait 30 seconds for cache expiry or refresh page

DEMO_DIVERGENCE_STATE=degraded python scripts/seed_demo_metrics.py
# Wait 30 seconds

DEMO_DIVERGENCE_STATE=paused python scripts/seed_demo_metrics.py
```

### 4. Run Tests

#### Backend Tests
```bash
cd services/api
pytest tests/test_metrics_divergence.py -v
```

Expected output:
```
test_divergence_states[10050-10000-ok-0.5] PASSED
test_divergence_states[10200-10000-degraded-2.0] PASSED
test_divergence_states[11000-10000-paused-10.0] PASSED
test_divergence_warehouse_disabled PASSED
test_divergence_bigquery_error PASSED
test_divergence_null_when_paused PASSED
test_divergence_network_timeout PASSED
...
```

#### Frontend Unit Tests
```bash
cd apps/web
npm run test HealthBadge
```

#### E2E Tests
```bash
cd apps/web
npm run test:e2e health-badge
```

Expected output:
```
✓ displays green badge for healthy state
✓ displays yellow badge for degraded state  
✓ displays gray badge for paused state
✓ auto-refreshes every 60 seconds
...
```

### 5. Grafana Dashboard

#### Prerequisites
```bash
# Install JSON API datasource plugin
grafana-cli plugins install marcusolsson-json-datasource

# Restart Grafana
sudo systemctl restart grafana-server
```

#### Add Data Source
1. **Navigate:** Configuration → Data Sources → Add data source
2. **Select:** JSON API
3. **Configure:**
   - Name: `ApplyLens API`
   - URL: `http://localhost:8003` (or `https://applylens.app`)
   - Timeout: `30s`
4. **Save & Test**

#### Import Dashboard
1. **Navigate:** Dashboards → Import
2. **Copy JSON** from `docs/PHASE_3_GRAFANA_DASHBOARD.md`
3. **Paste** into "Import via panel json"
4. **Select** data source: `ApplyLens API`
5. **Import**

#### Verify Panels
- **Panel 1:** Divergence stat shows `0.00%` (green)
- **Panel 2:** Activity by Day shows 30-day bar chart
- **Panel 3:** Top Senders shows table with 10 rows
- **Panel 4:** Categories shows horizontal bar chart with 5 categories

### 6. Performance Verification

#### Check Response Times
```bash
# Divergence endpoint (target: < 1.2s)
time curl -s http://localhost:8003/api/metrics/divergence-24h > /dev/null

# Should show: real 0m0.XXXs (where XXX < 1200ms)
```

#### Check Cache Headers
```bash
curl -I http://localhost:8003/api/metrics/divergence-24h
```

Look for cache indicators in response.

#### Load Test (Optional)
```bash
# Install hey
go install github.com/rakyll/hey@latest

# Run load test (100 requests, 10 concurrent)
hey -n 100 -c 10 http://localhost:8003/api/metrics/divergence-24h
```

Expected:
- Average latency: < 100ms (with cache)
- First call: < 1.2s (without cache)

## Verification Checklist

### Backend API
- [ ] `/api/metrics/divergence-24h` returns `{status: "ok|degraded|paused"}`
- [ ] `divergence_pct` is `null` when status is `paused`
- [ ] All queries have 800ms timeout
- [ ] All endpoints have 30s cache TTL
- [ ] Demo mode works without warehouse

### Demo Seed Script
- [ ] Script runs without errors
- [ ] Can seed all 3 states (ok/degraded/paused)
- [ ] `DEMO_DIVERGENCE_STATE` env var works
- [ ] `DEMO_DIVERGENCE_PCT` env var works
- [ ] Cache is populated correctly

### Frontend
- [ ] HealthBadge visible in top-right corner
- [ ] `data-testid="health-badge"` present
- [ ] Shows green badge for ok state
- [ ] Shows yellow badge for degraded state
- [ ] Shows gray badge for paused state
- [ ] Tooltip shows divergence percentage
- [ ] Demo mode tooltip shows "(Demo data)"
- [ ] Auto-refreshes every 60 seconds

### Tests
- [ ] Backend: 15+ tests pass
- [ ] Frontend: 8+ tests pass
- [ ] E2E: 11+ tests pass
- [ ] All tests use correct endpoint `/api/metrics/divergence-24h`
- [ ] Tests cover null divergence_pct scenario
- [ ] Tests cover network timeout scenario

### Grafana
- [ ] JSON API plugin installed
- [ ] Data source configured
- [ ] Dashboard imports without errors
- [ ] All 4 panels show data
- [ ] Divergence stat has color thresholds (green/yellow/red)
- [ ] Auto-refresh works (30s interval)

### Performance
- [ ] Divergence endpoint < 1.2s without cache
- [ ] Divergence endpoint < 100ms with cache
- [ ] No timeout errors in logs
- [ ] Cache hit rate > 80% under load

## Troubleshooting

### Divergence endpoint returns 412
**Issue:** Warehouse disabled but not in demo mode  
**Fix:**
```bash
export USE_WAREHOUSE_METRICS=0  # Disable warehouse
# Or enable it:
export USE_WAREHOUSE_METRICS=1
```

### HealthBadge shows "Paused" always
**Issue:** API not running or unreachable  
**Fix:**
```bash
# Check API is running
curl http://localhost:8003/health

# Check logs
tail -f services/api/logs/app.log
```

### Grafana panels show "No data"
**Issue:** Data source not configured correctly  
**Fix:**
1. Check data source URL: `http://localhost:8003` (no trailing slash)
2. Test data source connection
3. Check browser console for CORS errors
4. Verify API is running: `curl http://localhost:8003/api/metrics/divergence-24h`

### Seed script fails
**Issue:** Redis not running or import errors  
**Fix:**
```bash
# Start Redis
redis-server

# Or check if Redis is running
redis-cli ping
# Should return: PONG

# Check Python path
cd services/api
python -c "from app.utils.cache import cache_set; print('OK')"
```

### Tests fail with import errors
**Issue:** Missing dependencies or wrong directory  
**Fix:**
```bash
cd services/api
pip install -r requirements.txt

cd apps/web
npm install
```

## Evidence Collection (for Devpost)

### Screenshots to Capture

1. **Divergence Endpoint JSON (Healthy)**
   ```bash
   curl -s http://localhost:8003/api/metrics/divergence-24h | jq > divergence-healthy.json
   # Screenshot of JSON output
   ```

2. **HealthBadge - All 3 States**
   - Open app, capture green badge
   - Seed degraded: `DEMO_DIVERGENCE_STATE=degraded python scripts/seed_demo_metrics.py`
   - Wait 30s, capture yellow badge
   - Seed paused: `DEMO_DIVERGENCE_STATE=paused python scripts/seed_demo_metrics.py`
   - Wait 30s, capture gray badge

3. **Grafana Dashboard - Full View**
   - All 4 panels visible
   - Data populated
   - Color coding visible on divergence stat

4. **Test Output**
   ```bash
   pytest tests/test_metrics_divergence.py -v | tee test-output.txt
   # Screenshot of passing tests
   ```

### Video Clip (30 seconds)
1. **0-10s:** Show HealthBadge (green)
2. **10-15s:** Run seed script in terminal: `DEMO_DIVERGENCE_STATE=degraded ...`
3. **15-20s:** Wait and show badge turn yellow
4. **20-25s:** Run: `DEMO_DIVERGENCE_STATE=paused ...`
5. **25-30s:** Show badge turn gray

### Metrics to Report
- Response time: `< 1.2s` (cold) / `< 100ms` (cached)
- Test coverage: `32 tests passing`
- Endpoints: `4 metrics endpoints`
- States: `3 health states (ok/degraded/paused)`
- Cache TTL: `30 seconds`
- Query timeout: `800ms`

## Next Steps

After verification:
1. [ ] Commit all changes
2. [ ] Push to GitHub
3. [ ] Collect evidence (screenshots/video)
4. [ ] Update Devpost with evidence
5. [ ] Prepare 2-minute demo walkthrough

## Demo Script (2 minutes)

**Intro (15s):**
"Phase 3 adds real-time warehouse health monitoring with a 3-state badge, Grafana dashboards, and graceful degradation."

**Show HealthBadge (30s):**
- "Green badge shows healthy state with < 2% divergence"
- "Auto-refreshes every 60 seconds"
- "Tooltip shows exact percentage"

**Show State Changes (45s):**
- "When divergence increases to 2-5%, badge turns yellow (degraded)"
- Run seed script, show yellow badge
- "Above 5% or on errors, system enters paused state (gray)"
- Run seed script, show gray badge

**Show Grafana (20s):**
- "4 panels show activity, top senders, and categories"
- "Divergence stat has color thresholds"
- "Auto-refreshes every 30 seconds"

**Outro (10s):**
"All endpoints cached for 30s, queries timeout at 800ms, ensuring < 1.2s response time even under load."

---

**✓ Runbook Complete**
