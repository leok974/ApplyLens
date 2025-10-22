# Manual Browser Test Procedure - Reload Loop Fix

**Date**: October 22, 2025
**Tester**: [Your Name]
**Environment**: Local Docker Compose (docker-compose.prod.yml)

## 🎯 Test Objective
Verify that the reload loop fix prevents infinite page reloads when backend returns 5xx errors.

## 📋 Pre-Test Setup

### ✅ Environment Status
```bash
# All containers running and healthy:
✓ applylens-nginx-prod       Up 2 minutes (healthy)
✓ applylens-web-prod         Up 2 minutes (healthy)
✓ applylens-api-prod         Up 2 minutes (healthy)
✓ applylens-db-prod          Up 3 minutes (healthy)
✓ applylens-es-prod          Up 3 minutes (healthy)
✓ applylens-redis-prod       Up 3 minutes (healthy)
✓ applylens-grafana-prod     Up 2 minutes (healthy)
✓ applylens-prometheus-prod  Up 2 minutes (healthy)
✓ applylens-kibana-prod      Up 2 minutes (healthy)
```

### ✅ API Health Check
```bash
GET http://localhost:8003/status
Response: HTTP 200 OK
Body: {"ok": false, "gmail": "degraded", "message": "Database: connection failed..."}
```

**Critical**: Backend returns HTTP 200 even when degraded (not 503)

---

## 🧪 Test Cases

### Test 1: Normal Operation (Baseline)
**Expected**: Application loads normally

**Steps**:
1. ✅ Open browser to `http://localhost/web/inbox`
2. ✅ Observe page load behavior
3. ✅ Open browser DevTools → Console tab
4. ✅ Open browser DevTools → Network tab

**Expected Results**:
- [ ] Page loads without errors
- [ ] No console errors
- [ ] Status polling requests visible in Network tab
- [ ] `/api/status` returns HTTP 200

**Actual Results**:
- Status: ⬜ PASS / ⬜ FAIL
- Notes:

---

### Test 2: Backend Failure (Core Test)
**Expected**: No reload loops when API is down

**Steps**:
1. ✅ Ensure browser is on `http://localhost/web/inbox` with DevTools open
2. ⬜ In terminal, run: `docker stop applylens-api-prod`
3. ⬜ Wait 10 seconds and observe browser behavior
4. ⬜ Check browser console for retry messages
5. ⬜ Check Network tab for `/api/status` requests

**Expected Results**:
- [ ] **CRITICAL**: Page does NOT reload/refresh
- [ ] LoginGuard shows "Service Temporarily Unavailable" message
- [ ] Console shows exponential backoff: 2s → 4s → 8s → 16s
- [ ] Network tab shows failed requests but NO 5xx status codes reaching frontend
- [ ] HealthBadge shows "Paused" or "Error" status
- [ ] User can still navigate the UI (no infinite reload loop)

**Actual Results**:
- Status: ⬜ PASS / ⬜ FAIL
- Page reloaded?: ⬜ YES (FAIL) / ⬜ NO (PASS)
- Console logs:
  ```
  [Record console output here]
  ```
- Network tab observations:
  ```
  [Record network behavior here]
  ```
- Screenshot: [Optional]

---

### Test 3: Backend Recovery
**Expected**: UI recovers gracefully without manual reload

**Steps**:
1. ⬜ With API still stopped, observe current UI state
2. ⬜ In terminal, run: `docker start applylens-api-prod`
3. ⬜ Wait for API to become healthy (5-10 seconds)
4. ⬜ Observe browser behavior

**Expected Results**:
- [ ] Within 2-8 seconds, status polling succeeds
- [ ] "Service Temporarily Unavailable" message disappears
- [ ] Application returns to normal state
- [ ] **NO manual page reload required**
- [ ] HealthBadge returns to "OK" status
- [ ] Exponential backoff resets to normal polling interval

**Actual Results**:
- Status: ⬜ PASS / ⬜ FAIL
- Recovery time: ___ seconds
- Manual reload required?: ⬜ YES (FAIL) / ⬜ NO (PASS)
- Notes:

---

### Test 4: Nginx Retry Behavior (Optional)
**Expected**: Nginx retries failed requests before returning error

**Steps**:
1. ⬜ Ensure API is running
2. ⬜ Open browser to `http://localhost/web/inbox`
3. ⬜ Watch Nginx logs: `docker logs -f applylens-nginx-prod`
4. ⬜ Stop API: `docker stop applylens-api-prod`
5. ⬜ Observe retry attempts in nginx logs

**Expected Results**:
- [ ] Nginx shows retry attempts (proxy_next_upstream)
- [ ] Up to 2 retry attempts per request
- [ ] Retries complete within 10s timeout

**Actual Results**:
- Status: ⬜ PASS / ⬜ FAIL
- Nginx log excerpt:
  ```
  [Record nginx retry logs here]
  ```

---

### Test 5: HealthBadge Exponential Backoff
**Expected**: Health indicator backs off gracefully

**Steps**:
1. ⬜ Ensure API is running
2. ⬜ Open browser to `http://localhost/web/inbox`
3. ⬜ Locate HealthBadge component in UI (system health indicator)
4. ⬜ Open DevTools Console
5. ⬜ Stop API: `docker stop applylens-api-prod`
6. ⬜ Monitor console for polling interval changes

**Expected Results**:
- [ ] Initial poll failure triggers exponential backoff
- [ ] Polling intervals: 2s → 4s → 8s → 16s → 32s → 60s (max)
- [ ] HealthBadge shows degraded/error state
- [ ] No excessive polling (no retry storm)

**Actual Results**:
- Status: ⬜ PASS / ⬜ FAIL
- Observed intervals: ___
- Notes:

---

## 📊 Test Summary

### Results Overview
- Total Test Cases: 5
- Passed: ___
- Failed: ___
- Skipped: ___

### Critical Issues Found
1.
2.
3.

### Non-Critical Issues
1.
2.

### Recommendation
⬜ **APPROVED FOR PRODUCTION** - All critical tests passed
⬜ **NEEDS FIXES** - Critical issues found, do not deploy
⬜ **APPROVED WITH CAVEATS** - Minor issues, safe to deploy with monitoring

---

## 🔧 Quick Reference Commands

### Start All Services
```powershell
docker-compose -f docker-compose.prod.yml up -d
```

### Stop API (Simulate Failure)
```powershell
docker stop applylens-api-prod
```

### Start API (Simulate Recovery)
```powershell
docker start applylens-api-prod
```

### Check API Status
```powershell
curl http://localhost:8003/status | ConvertFrom-Json
```

### View API Logs
```powershell
docker logs -f applylens-api-prod
```

### View Nginx Logs
```powershell
docker logs -f applylens-nginx-prod
```

### View Web Logs
```powershell
docker logs -f applylens-web-prod
```

### Check Container Health
```powershell
docker ps --filter "name=applylens-" --format "table {{.Names}}\t{{.Status}}"
```

### Stop All Services
```powershell
docker-compose -f docker-compose.prod.yml down
```

---

## 📝 Notes
- Test conducted on: [Date/Time]
- Browser: [Chrome/Firefox/Edge/Safari + Version]
- Operating System: Windows
- Docker Desktop Version: [Version]
- Tester Signature: ___________________

---

## 🎯 Next Steps After Testing

### If All Tests Pass:
1. ✅ Mark test as APPROVED FOR PRODUCTION
2. ✅ Proceed to `PRODUCTION_DEPLOYMENT_CHECKLIST.md`
3. ✅ Schedule production deployment window
4. ✅ Brief operations team on new monitoring dashboards

### If Tests Fail:
1. ❌ Document failures in detail above
2. ❌ Create GitHub issues for each critical bug
3. ❌ Review code changes in affected components
4. ❌ Fix issues and re-run tests
5. ❌ Do NOT proceed to production until all critical tests pass
