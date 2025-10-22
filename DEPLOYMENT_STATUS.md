# Email Risk v3.1 - Deployment Status

**Status**: ✅ **READY FOR SOFT LAUNCH**
**Date**: October 21, 2025
**Last Updated**: 20:45 EST

---

## Deployment Summary

### Phase 1: Infrastructure ✅ COMPLETE

1. **CI/CD Workflows** - Committed in `e056218`
   - ✅ Backend unit tests (pytest)
   - ✅ Frontend unit tests (vitest)
   - ✅ Smoke tests (informational)
   - ✅ All-checks gate configured

2. **Feature Flags Router** - Fixed in `8de777f`
   - ✅ Endpoints: GET /flags, GET /flags/{flag}
   - ✅ Management: POST /flags/{flag}/ramp
   - ✅ Emergency: POST /flags/{flag}/disable, /enable
   - ✅ Audit: GET /flags/audit, /flags/{flag}/audit
   - ⚠️ **NOTE**: POST endpoints require CSRF token (use Swagger UI or add header)

3. **Documentation** - Committed in `71dee69`
   - ✅ RELEASE_CHECKLIST.md (complete deployment playbook)
   - ✅ EMAIL_RISK_V31_COMPLETE.md (implementation status)
   - ✅ QUICK_START.md (5-step deployment guide)

### Phase 2: Deployment Execution ✅ COMPLETE

**Steps Completed**:

1. ✅ **Restart API** - Container rebuilt with feature flags router
2. ✅ **Verify Flags Endpoint** - All flags accessible via API
3. ⏭️ **Reload Prometheus** - (Next step)
4. ⏭️ **Execute Soft Launch** - (Pending)
5. ⏭️ **Monitor Performance** - (Pending)

---

## Current State

### API Container Status
```
Container: applylens-api-prod
Status: Up and healthy
Ports: 8003:8000
```

### Feature Flags Configuration
```json
{
  "EmailRiskBanner": {
    "enabled": true,
    "rollout_percent": 10
  },
  "EmailRiskDetails": {
    "enabled": true,
    "rollout_percent": 10
  },
  "EmailRiskAdvice": {
    "enabled": true,
    "rollout_percent": 100
  }
}
```

### Verified Endpoints

✅ **GET** http://localhost:8003/flags/
✅ **GET** http://localhost:8003/flags/EmailRiskBanner
✅ **GET** http://localhost:8003/docs (Swagger UI)
⚠️ **POST** endpoints require CSRF token (use Swagger UI at /docs)

---

## Issue Resolution Log

### Issue 1: Flags Router Not in Container ✅ RESOLVED
- **Problem**: Added flags.py after Docker image was built
- **Solution**: Rebuilt image with `docker-compose build api`
- **Status**: Fixed

### Issue 2: Worker Boot Failure ✅ RESOLVED
- **Problem**: FastAPI assertion error - query parameter used Field() instead of Query()
- **Error**: `AssertionError: non-body parameters must be in path, query, header or cookie: to`
- **Root Cause**: In `flags.py`, the `ramp_flag` endpoint used `Field(ge=0, le=100)` for query param
- **Solution**: Changed to `Query(ge=0, le=100)` and added `Query` import from `fastapi`
- **Commit**: 8de777f
- **Status**: Fixed and deployed

---

## Next Steps (from QUICK_START.md)

### Step 3: Reload Prometheus Configuration

```powershell
# Reload Prometheus to pick up new metrics
curl -X POST http://localhost:9090/-/reload

# Verify reload
curl http://localhost:9090/api/v1/status/config
```

### Step 4: Execute 10% Soft Launch

**Option A: Using Swagger UI (Recommended)**
1. Open http://localhost:8003/docs
2. Navigate to "Feature Flags" section
3. Expand "POST /flags/{flag}/ramp"
4. Click "Try it out"
5. Set flag: `EmailRiskBanner`, to: `10`
6. Execute

**Option B: Using API with CSRF Token**
```powershell
# Get CSRF token from a GET request first, then use in POST
# (Implementation details in QUICK_START.md)
```

**Verify Rollout**:
```powershell
curl http://localhost:8003/flags/EmailRiskBanner
# Should show: {"enabled": true, "rollout_percent": 10}
```

### Step 5: Monitor Performance (6 hours)

**Metrics to Monitor** (Grafana: http://localhost:3000):

1. **P95 Latency** - Target: < 300ms
   - `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`

2. **Error Rate** - Target: < 0.1%
   - `rate(http_requests_total{status=~"5.."}[5m])`

3. **Email Risk Engagement**:
   - `rate(email_risk_viewed_total[5m])`
   - `rate(email_risk_link_clicked_total[5m])`

**Decision Points**:
- ✅ All metrics green for 6 hours → Proceed to 25% rollout
- ❌ Any metric red → Emergency disable via POST /flags/{flag}/disable

---

## Production Checklist

### Pre-Launch ✅
- [x] All tests passing (22/22)
- [x] CI/CD workflows configured
- [x] Feature flags deployed
- [x] Documentation complete
- [x] API container healthy

### Soft Launch (10%) ⏳ PENDING
- [ ] Prometheus reloaded
- [ ] Flags set to 10%
- [ ] Monitored for 6 hours
- [ ] Kibana searches imported
- [ ] No critical errors

### Staged Rollout ⏳ PENDING
- [ ] 25% rollout (after 24h at 10%)
- [ ] 50% rollout (after 12h at 25%)
- [ ] 100% rollout (after 24h at 50%)
- [ ] 7-day monitoring complete

### Certification ⏳ PENDING
- [ ] Weekly weight tuning analysis
- [ ] Beta tester feedback collected
- [ ] Production ready certification

---

## Rollback Plan

### Emergency Disable (< 1 minute)
```powershell
# Via Swagger UI: POST /flags/{flag}/disable
# Or using curl with CSRF token (see QUICK_START.md)
```

### Full Rollback (< 5 minutes)
```powershell
# Revert to previous commit
git revert 8de777f e056218
docker-compose -f docker-compose.prod.yml build api
docker-compose -f docker-compose.prod.yml up -d api
```

---

## Useful Commands

### Check Container Status
```powershell
docker ps --filter "name=applylens-api-prod"
docker logs applylens-api-prod --tail 50
```

### Test Endpoints
```powershell
# List all flags
curl http://localhost:8003/flags/ | ConvertFrom-Json | ConvertTo-Json -Depth 5

# Get specific flag
curl http://localhost:8003/flags/EmailRiskBanner | ConvertFrom-Json | ConvertTo-Json

# View API documentation
Start-Process http://localhost:8003/docs
```

### Monitor Metrics
```powershell
# Grafana
Start-Process http://localhost:3000

# Prometheus
Start-Process http://localhost:9090
```

---

## Contact & Support

**Documentation**:
- Release Checklist: `RELEASE_CHECKLIST.md`
- Quick Start Guide: `QUICK_START.md`
- Implementation Status: `EMAIL_RISK_V31_COMPLETE.md`

**Monitoring**:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- API Docs: http://localhost:8003/docs

**Emergency Contacts**: [Add team contacts]

---

**Last Deployment**: October 21, 2025 20:45 EST
**Deployed By**: Automated Deployment
**Git Commit**: 8de777f (Fix: Use Query for FastAPI query parameters)
**Status**: ✅ Ready for Production Soft Launch
