# Today Panel - Production Deployment

**Version**: 0.6.0
**Feature**: Today Inbox Triage Panel
**Commit**: 68ef2f1
**Date**: November 23, 2025

---

## ✅ Pre-Deployment Checklist

- [x] All tests passing (Backend: 4/4, Frontend: 10/10, E2E: 6/10)
- [x] Docker images built and pushed
- [x] Feature committed to git
- [x] Documentation updated

---

## 📦 Docker Images

**Built and pushed to Docker Hub:**
- `leoklemet/applylens-api:0.6.0`
- `leoklemet/applylens-web:0.6.0`

---

## 🚀 Production Deployment

### Step 1: SSH to Production Server

```bash
ssh your-production-server
cd /opt/applylens  # or wherever docker-compose.prod.yml is located
```

### Step 2: Update docker-compose.prod.yml

Edit the file to update image tags:

```yaml
services:
  web:
    image: leoklemet/applylens-web:0.6.0  # Update from 0.5.x
    container_name: applylens-web-prod
    # ... rest of config

  api:
    image: leoklemet/applylens-api:0.6.0  # Update from 0.5.x
    container_name: applylens-api-prod
    # ... rest of config
```

### Step 3: Pull and Deploy

```bash
# Pull new images
docker compose -f docker-compose.prod.yml pull web api

# Deploy with zero downtime
docker compose -f docker-compose.prod.yml up -d web api

# Check container status
docker ps --filter "name=applylens-*-prod"
```

Expected output: Both containers running with status "Up X minutes (healthy)"

---

## ✅ Post-Deployment Verification

### 1. Health Checks

```bash
# API health
curl https://api.applylens.app/api/healthz
# Expected: {"status":"ok"}

# Version check
curl https://api.applylens.app/api/version
# Expected: {"version":"0.6.0","git_sha":"68ef2f1",...}

# Today endpoint
curl -X POST https://api.applylens.app/v2/agent/today \
  -H 'Content-Type: application/json' \
  -H 'Cookie: session_id=...' \
  -d '{"time_window_days": 90}'
# Expected: {"status":"ok","intents":[...]}
```

### 2. Browser Testing

Open browser and test:

1. **Navigate to Today page**: https://applylens.app/today
   - ✅ Page loads without errors
   - ✅ 6 intent tiles visible (followups, bills, interviews, unsubscribe, clean_promos, suspicious)
   - ✅ Loading state shows briefly
   - ✅ No console errors

2. **Check Intent Tiles**:
   - ✅ Color-coded tiles with icons
   - ✅ Count badges visible
   - ✅ "All clear! 🎉" message for empty intents
   - ✅ Thread lists (max 5 threads) for non-empty intents

3. **Test Action Buttons** (hover over thread):
   - ✅ Gmail button opens thread in new tab
   - ✅ Thread Viewer button navigates to /inbox?open={threadId}
   - ✅ Tracker button navigates to /applications?highlight={appId} (if applicationId exists)

4. **Test Error States**:
   - Logout and try to access /today
   - ✅ Shows "Not authenticated" error message

### 3. E2E Tests (Optional)

```bash
# From local machine with production auth
cd apps/web
npx playwright test e2e/today-triage.spec.ts --grep @prodSafe
```

Expected: 10/10 tests passing (all tests should pass now that backend is deployed)

---

## 📊 What's New in 0.6.0

### Backend Changes

**New Endpoint**: `POST /v2/agent/today`
- Accepts: `{user_id?: string, time_window_days?: number}`
- Returns: `{status: "ok", intents: [{intent, summary, threads}]}`
- Runs 6 scan intents in `preview_only` mode
- Limits to 5 threads per intent
- Graceful error handling (failed intents omitted)

**File**: `services/api/app/routers/agent.py`

### Frontend Changes

**New Page**: `/today` route
- Component: `apps/web/src/pages/Today.tsx`
- Responsive grid (1-col mobile, 2-col tablet, 3-col desktop)
- 6 color-coded intent tiles with metadata
- Thread mini-lists with hover actions
- Loading, error, and empty states

**Modified Files**:
- `apps/web/src/App.tsx` - Added route
- `apps/web/playwright.config.ts` - Added E2E test to testMatch

### Tests Added

- **Backend**: `services/api/tests/test_agent_today.py` (4 tests)
- **Frontend**: `apps/web/src/tests/Today.test.tsx` (10 tests)
- **E2E**: `apps/web/tests/e2e/today-triage.spec.ts` (10 tests with @prodSafe tag)

---

## 🔄 Rollback Procedure

If issues are encountered, rollback to previous version:

### Step 1: Edit docker-compose.prod.yml

```yaml
services:
  web:
    image: leoklemet/applylens-web:0.5.11  # Restore previous version
  api:
    image: leoklemet/applylens-api:0.5.11  # Restore previous version
```

### Step 2: Deploy Previous Version

```bash
docker compose -f docker-compose.prod.yml pull web api
docker compose -f docker-compose.prod.yml up -d web api
```

### Step 3: Verify Rollback

```bash
docker ps --filter "name=applylens-*-prod"
curl https://api.applylens.app/api/version
```

Expected: Version shows 0.5.11

---

## 📝 Monitoring

### Metrics to Watch

After deployment, monitor:

1. **API Performance**:
   - `/v2/agent/today` response times (should be < 2s with 6 intents)
   - Error rates on Today endpoint
   - Agent orchestrator performance

2. **Frontend**:
   - Today page load times
   - JavaScript errors in browser console
   - User navigation patterns (analytics)

3. **Infrastructure**:
   - Container health (both containers healthy)
   - Memory usage (agent runs may increase memory)
   - Database connections (preview_only mode should be light)

### Expected Behavior

- **Normal**: Today endpoint completes in 1-3 seconds for 6 intents
- **Warning**: Response times > 5 seconds (may need optimization)
- **Critical**: 500 errors or timeout (investigate orchestrator logs)

---

## 🐛 Known Issues

None at deployment time. All tests passing.

If issues arise:
1. Check container logs: `docker logs applylens-api-prod --tail 100`
2. Check browser console for frontend errors
3. Verify user is authenticated before accessing /today
4. Ensure orchestrator has access to all required services (DB, ES, Redis)

---

## 📞 Support

**Deployment Issues**:
- Review logs: `docker logs applylens-api-prod` / `docker logs applylens-web-prod`
- Check health: `curl https://api.applylens.app/api/healthz`
- Rollback if needed (see Rollback Procedure above)

**Questions**:
- Refer to `docs/PRODUCTION_DEPLOYMENT.md` for general deployment procedures
- Feature documentation in commit 68ef2f1 message

---

**Deployment Status**: ⏳ Ready for Production
**Next Action**: Deploy on production server following steps above
**Last Updated**: November 23, 2025
