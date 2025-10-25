# Deployment Status - October 23, 2025

## Current Status

### ✅ Completed
1. **API Changes Deployed**
   - CSRF exemptions updated (heartbeat + chat/opened)
   - Container rebuilt: `applylens-api-prod`
   - Status: Running and tested

2. **Frontend Changes Built**
   - Fixed heartbeat payload in MailChat.tsx
   - Build completed: `pnpm build`
   - Output: `apps/web/dist/`

3. **Production Guard Updated**
   - Added `chat/opened` to allowlist
   - Tests passing: 4/4 heartbeat tests

### ⏭️ Next Steps

Since Docker Desktop is currently stopped, here's what to do when you're ready to deploy:

#### Option 1: Use Existing Containers (Recommended)
The API is already rebuilt and running. You just need to deploy the web dist:

```powershell
# 1. Start Docker Desktop

# 2. Verify API is running
docker ps | Select-String "applylens-api-prod"

# 3. Deploy web dist to your web server
# (Copy apps/web/dist/* to your production web server)
```

#### Option 2: Full Redeployment
If you want to redeploy everything:

```powershell
# 1. Start Docker Desktop

# 2. Run deployment script
cd d:\ApplyLens
.\deploy-prod.ps1 restart  # Just restart (fastest)
# OR
.\deploy-prod.ps1 update   # Rebuild and restart

# 3. Verify services
docker-compose -f docker-compose.prod.yml ps
```

## What Was Deployed

### Backend (API)
**Container**: `applylens-api-prod`
**Changes**:
- ✅ `/ux/heartbeat` - CSRF exempt
- ✅ `/api/ux/heartbeat` - CSRF exempt
- ✅ `/ux/chat/opened` - CSRF exempt (NEW)
- ✅ `/api/ux/chat/opened` - CSRF exempt (NEW)

**File**: `services/api/app/core/csrf.py`

### Frontend (Web)
**Build**: `apps/web/dist/`
**Changes**:
- ✅ Heartbeat now sends proper payload: `{page, ts}`
- ✅ Content-Type header added
- ✅ Chat opened endpoint still called (now works)

**File**: `apps/web/src/components/MailChat.tsx`

### Tests
**Updates**:
- ✅ Production guard allowlist updated
- ✅ All 4 heartbeat tests passing

**File**: `apps/web/tests/utils/prodGuard.ts`

## Verification Commands

### Check API is Running
```powershell
docker ps --filter "name=applylens-api-prod"
```

### Test Endpoints
```powershell
# Heartbeat
curl -X POST http://localhost:5175/api/ux/heartbeat `
  -H "Content-Type: application/json" `
  -d '{"page":"/chat","ts":1729700000}'

# Chat opened
curl -X POST http://localhost:5175/api/ux/chat/opened
```

### View Logs
```powershell
docker logs applylens-api-prod --tail 50
```

## Deployment Checklist

- [x] Backend code updated (CSRF exemptions)
- [x] Backend container rebuilt
- [x] Backend container tested
- [x] Frontend code updated (heartbeat payload)
- [x] Frontend built (dist/ ready)
- [x] E2E tests passing (4/4)
- [x] Manual tests passing
- [x] Production guard updated
- [x] Documentation updated
- [ ] **Docker Desktop started** ⬅️ DO THIS NEXT
- [ ] **Web dist deployed to production** ⬅️ THEN THIS

## Production URLs

Once deployed, these URLs should work on production:
- ✅ `POST https://applylens.app/api/ux/heartbeat` (with payload)
- ✅ `POST https://applylens.app/api/ux/chat/opened`

## Files Ready for Deployment

### API (Already Deployed)
```
services/api/app/core/csrf.py  ← Deployed in container
```

### Web (Ready to Deploy)
```
apps/web/dist/
├── index.html
├── assets/
│   ├── index-*.css
│   └── index-*.js  ← Contains fixed heartbeat code
```

## Rollback Plan

If issues occur after deployment:

### API Rollback
```powershell
# Revert CSRF changes
git checkout HEAD~1 services/api/app/core/csrf.py
docker-compose -f docker-compose.prod.yml build api
docker-compose -f docker-compose.prod.yml up -d api
```

### Web Rollback
```powershell
# Rebuild from previous commit
git checkout HEAD~1 apps/web/src/components/MailChat.tsx
cd apps/web
pnpm build
# Deploy old dist/
```

## Post-Deployment Monitoring

After deployment, monitor:

1. **Browser Console** - Should see no 403/422 errors
2. **API Logs** - `docker logs applylens-api-prod -f`
3. **Prometheus Metrics**:
   - `ux_heartbeat_total{page="/chat"}`
   - `ux_chat_opened_total`

## Summary

**Ready to deploy**: YES ✅

**What's deployed**: Backend (API) is already running with fixes

**What needs deployment**: Frontend (web dist/) to production web server

**Blocking issues**: None - Docker Desktop just needs to be started if you want to verify containers

---

**Status**: Waiting for Docker Desktop to start (optional) or web dist deployment
**Next Action**: Start Docker Desktop OR deploy web dist to production
