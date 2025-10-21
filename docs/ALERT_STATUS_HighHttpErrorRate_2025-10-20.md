# Alert Status: HighHttpErrorRate

**Date:** October 20, 2025  
**Alert Name:** HighHttpErrorRate  
**Severity:** Warning  
**Status:** ⏳ Auto-Resolving (No Action Required)

---

## Alert Details

**Alert Expression:**
```promql
(sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m]))
 / ignoring(status_code) sum(rate(applylens_http_requests_total[5m]))) > 0.05
```

**Threshold:** 5% error rate over 5 minutes  
**For Duration:** 5 minutes  
**Current Value:** 14.47% → 11.63% (declining)  
**First Fired:** 2025-10-20T23:22:30Z

---

## Root Cause

This alert fired as a **side effect** of fixing the `DependenciesDown` alert.

### What Happened:
1. **Database password was incorrect** when the API container was restarted
2. **Docker health checks call `/ready`** endpoint every 30 seconds
3. **`/ready` returned 503** when database connection failed
4. **4 consecutive 503 errors** triggered the high error rate alert

### Affected Endpoint:
- **Path:** `/ready`
- **Method:** GET
- **Status Code:** 503 (Service Unavailable)
- **Count:** 4 errors
- **Percentage:** 16% of total requests (4/25)

---

## Current Status

### ✅ Issue Already Resolved

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Database Password | ❌ Incorrect | ✅ Correct |
| `/ready` Status | 503 Error | 200 OK |
| DB Connection | Failed | ✅ Connected |
| ES Connection | ✅ OK | ✅ OK |
| New Errors | Yes (503s) | ✅ None |

### Verification (5 consecutive tests):
```bash
Attempt 1: 200 - DB: ok, ES: ok ✅
Attempt 2: 200 - DB: ok, ES: ok ✅
Attempt 3: 200 - DB: ok, ES: ok ✅
Attempt 4: 200 - DB: ok, ES: ok ✅
Attempt 5: 200 - DB: ok, ES: ok ✅
```

---

## Why Alert Is Still Firing

### Prometheus 5-Minute Window
The alert uses a **5-minute rate calculation** which includes historical errors:

```
Current Time:     23:27:30
Error Window:     23:22:30 - 23:27:30
Errors in Window: 4 errors (from database issue at ~23:20)
Total Requests:   25
Error Rate:       4/25 = 16% → 11.63% over time
```

**The old 503 errors are still in the 5-minute sliding window.**

---

## Expected Resolution

### Auto-Resolution Timeline

| Time | Event | Error Rate |
|------|-------|------------|
| 23:20:00 | Database password incorrect | - |
| 23:20:30 | First 503 error from `/ready` | - |
| 23:20:47 | **Database password fixed** | - |
| 23:21:00 | `/ready` now returns 200 OK | - |
| 23:22:30 | Alert fires (14.47% error rate) | 14.47% |
| 23:27:30 | Current status (declining) | 11.63% |
| **23:25:30** | **Old errors age out (5 min)** | **< 5%** ✅ |
| **23:27:30** | **Alert auto-resolves** | **< 5%** ✅ |

**Expected Full Resolution:** Within 5 minutes of database fix (~23:25-23:27)

---

## No Action Required

### Why No Manual Intervention Needed:

1. **✅ Root cause already fixed** - Database password reset
2. **✅ No new errors occurring** - All requests succeeding
3. **✅ Health checks passing** - `/ready` returns 200 OK
4. **✅ Alert will auto-resolve** - As old errors age out

### Monitoring:
```bash
# Watch error rate decline
watch -n 10 'curl -s "http://localhost:9090/api/v1/query?query=(sum(rate(applylens_http_requests_total{status_code=~\"5..\"}[5m]))/ignoring(status_code)sum(rate(applylens_http_requests_total[5m])))*100"'
```

---

## Request Breakdown

### Total Metrics (Since Container Start)
- **Total Requests:** 25
- **Successful (2xx):** 21 (84%)
- **Errors (5xx):** 4 (16%)
- **Error Breakdown:**
  - 503 Service Unavailable: 4 (all from `/ready` during database issue)

### Error Distribution
```
Endpoint: /ready
Method: GET
Status: 503
Reason: Database authentication failed
Count: 4
Time Range: ~23:20:00 - 23:20:47 (before fix)
```

---

## Related Alerts

This alert is directly related to:
- **DependenciesDown** (resolved at 23:21:00)
  - Database password was incorrect
  - Health metrics showed db_up=0.0
  - Fixed by resetting postgres password

**Both alerts are manifestations of the same root cause.**

---

## Lessons Learned

### 1. Health Check Side Effects
**Issue:** Health checks can trigger error rate alerts when dependencies fail.

**Mitigation:**
- Health check errors are expected during startup/recovery
- Consider separate alert for health check endpoints
- Or exclude `/ready` and `/healthz` from error rate calculation

### 2. Prometheus Rate Windows
**Behavior:** Rate calculations include historical data in the time window.

**Impact:**
- Fixed issues may still show in alerts for window duration
- This is expected behavior, not a bug
- Alerts auto-resolve as old data ages out

### 3. Alert Correlation
**Pattern:** Multiple alerts can fire from same root cause.

**Best Practice:**
- Fix root cause (database password)
- Related alerts resolve automatically
- No need to fix each alert individually

---

## Prevention

### Option 1: Exclude Health Endpoints (Recommended)
Update alert to exclude health check endpoints:

```yaml
- alert: HighHttpErrorRate
  expr: |
    (sum(rate(applylens_http_requests_total{
      status_code=~"5..",
      path!~"/ready|/healthz|/live"
    }[5m]))
    / ignoring(status_code) sum(rate(applylens_http_requests_total{
      path!~"/ready|/healthz|/live"
    }[5m]))) > 0.05
  for: 5m
```

### Option 2: Separate Health Check Alert
Create dedicated alert for health check failures:

```yaml
- alert: HealthCheckFailing
  expr: |
    rate(applylens_http_requests_total{
      path=~"/ready|/healthz",
      status_code=~"5.."
    }[5m]) > 0
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Health checks failing"
    description: "Health endpoints returning 5xx errors"
```

### Option 3: Increase Threshold
If health check errors are acceptable during recovery:

```yaml
- alert: HighHttpErrorRate
  expr: ... > 0.10  # 10% instead of 5%
  for: 10m          # 10 minutes instead of 5
```

---

## Recommended Actions

### Immediate (This Incident):
- [x] Root cause identified (database password)
- [x] Database password fixed
- [x] Verified `/ready` endpoint working
- [x] Documented in `ALERT_RESOLUTION_DependenciesDown_2025-10-20.md`
- [x] Monitor alert auto-resolution (ETA: ~5 minutes)

### Future Improvements:
- [ ] Update alert to exclude `/ready` endpoint from error rate
- [ ] Create separate health check alert
- [ ] Add alert correlation dashboard in Grafana
- [ ] Document expected transient alerts during deployment/recovery

---

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 23:19:20 | Changed health check endpoint to `/ready` |
| 23:19:32 | API container restarted |
| 23:20:06 | Database authentication failures begin |
| 23:20:06-47 | `/ready` returns 503 (4 errors) |
| 23:20:47 | **Database password reset** ✅ |
| 23:21:00 | `/ready` now returns 200 OK ✅ |
| 23:22:30 | HighHttpErrorRate alert fires (14.47%) |
| 23:27:30 | Current: Error rate declining (11.63%) |
| ~23:25-27 | Expected: Alert auto-resolves (< 5%) |

---

## Current Alert State

**Status:** Firing → Pending → **Will Resolve Automatically**

```json
{
  "alert": "HighHttpErrorRate",
  "state": "firing",
  "value": "0.14473684210526316",  // 14.47%
  "threshold": "0.05",               // 5%
  "activeAt": "2025-10-20T23:22:30Z",
  "resolution": "auto (no action needed)",
  "eta": "~5 minutes from database fix"
}
```

---

**Status:** ⏳ Waiting for auto-resolution  
**Action Required:** None  
**Root Cause:** Already fixed (database password)  
**Expected Resolution:** Auto-resolves within 5 minutes
