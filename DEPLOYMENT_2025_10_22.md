# Production Deployment - October 22, 2025 ✅

**Time**: 19:57 UTC
**Status**: All Changes Deployed Successfully

## Summary

✅ **Metrics Endpoint Fixed**: Now responding at `/api/metrics/divergence-24h`
✅ **UI Button Renamed**: "Inbox (Actions)" → "Actions"
✅ **Web Container Fixed**: Now serving production build with nginx (was Vite dev mode)
✅ **Containers Rebuilt**: API and Web using latest code
✅ **Production Verified**: No more 404 or 502 errors

---

## Issues Resolved

### 1. Metrics Endpoint 404 ✅
**Error**: `GET https://applylens.app/api/metrics/divergence-24h 404 (Not Found)`

**Root Cause**: Router prefix `/api/metrics` didn't match nginx proxy path
- Browser requests: `https://applylens.app/api/metrics/divergence-24h`
- Nginx proxies to: `http://api:8003/metrics/divergence-24h` (strips `/api`)
- Router expected: `/api/metrics/divergence-24h` ❌ Mismatch!

**Solution**: Changed router prefix to `/metrics`

**File**: `services/api/app/routers/metrics.py` line 37
```python
router = APIRouter(prefix="/metrics", tags=["metrics"])  # was "/api/metrics"
```

**Rebuild Commands**:
```powershell
docker build --no-cache -t leoklemet/applylens-api:latest services/api/
docker-compose -f docker-compose.prod.yml up -d --force-recreate api
```

**Verification**:
```powershell
curl http://localhost/api/metrics/divergence-24h
# Returns: {"suspicious_divergence_pp": -100.0, "error_rate_5m": 0.0, ...}
```

---

### 2. Web Container 502 Bad Gateway ✅
**Error**: `GET https://applylens.app/web/ 502 (Bad Gateway)`

**Root Cause**: Container running Vite dev server instead of nginx production build
- Container was running: `vite --host` on port 5173
- Health check looking for: nginx on port 80
- Result: Container status "unhealthy" → 502 errors

**Discovery**: Used wrong Dockerfile
- ❌ `apps/web/Dockerfile` = Dev mode (Vite)
- ✅ `apps/web/Dockerfile.prod` = Production (nginx)

**Solution**: Rebuild with correct Dockerfile

**Rebuild Commands** (CRITICAL - note the `-f` flag):
```powershell
docker build -f apps/web/Dockerfile.prod -t leoklemet/applylens-web:latest apps/web/
docker-compose -f docker-compose.prod.yml up -d --force-recreate web
```

**Verification**:
```powershell
docker ps | Select-String "applylens-web-prod"
# Output: Up 20 seconds (healthy) ✅

curl -s http://localhost/web/ | Select-String "script"
# Output: <script ... src="/assets/index-1761177439323.BEBR919J.js"></script>
# (Production bundle with timestamp/hash)
```

**Container Status**:
- **Before**: Unhealthy (Vite dev server, wrong port)
- **After**: Healthy (nginx, port 80, serving built assets)

---

### 3. Mixed Content Warning ⚠️ (Minor)
**Error**: `Mixed Content: requested insecure favicon http://applylens.app/web/favicon.ico`

**Root Cause**: Favicon path should be `/web/favicon.svg` not `/favicon.svg`

**Status**: Non-blocking, cosmetic issue (can fix in `index.html` later)

---

## Code Changes Deployed

### 1. API - Metrics Router Prefix
**File**: `services/api/app/routers/metrics.py`
```python
# Line 37 - Changed from:
router = APIRouter(prefix="/api/metrics", tags=["metrics"])

# To:
router = APIRouter(prefix="/metrics", tags=["metrics"])
```

**Why**: Nginx configuration strips `/api` prefix when proxying:
```nginx
location /api/ {
    proxy_pass http://api:8003/;  # Trailing slash strips /api
}
```

### 2. Web - Button Rename
**File**: `apps/web/src/components/Nav.tsx`
```typescript
// Line 20 - Changed from:
{link('/inbox-actions', 'Inbox (Actions)')}

// To:
{link('/inbox-actions', 'Actions')}
```

**File**: `apps/web/src/components/AppHeader.tsx`
```typescript
// Line 136 - Changed from:
["Inbox (Actions)", "/inbox-actions"]

// To:
["Actions", "/inbox-actions"]
```

### 3. Docker Compose Configuration
**File**: `docker-compose.prod.yml`
```yaml
web:
  image: leoklemet/applylens-web:latest  # Uses pre-built image
  # Was: build: context: ./apps/web, dockerfile: Dockerfile.prod
```

---

## Container Status (Current)

```
NAME                     STATUS                  IMAGE
applylens-web-prod       Up 5 min (healthy)      leoklemet/applylens-web:latest
applylens-api-prod       Up 25 min               leoklemet/applylens-api:latest
applylens-nginx-prod     Up 7 hours (healthy)    nginx:1.27-alpine
applylens-grafana-prod   Up 1 hour (healthy)     grafana/grafana:11.1.0
applylens-db-prod        Up 7 hours (healthy)    postgres:15-alpine
applylens-es-prod        Up 7 hours (healthy)    elasticsearch:8.13.0
applylens-redis-prod     Up 7 hours (healthy)    redis:7-alpine
```

**Web Container Details**:
- ✅ Running nginx 1.27-alpine (production mode)
- ✅ Serving built assets from `/usr/share/nginx/html`
- ✅ Health check passing (port 80)
- ✅ Production bundle: `index-1761177439323.BEBR919J.js`
- ✅ Button text verified: Old "Inbox (Actions)" not found in build

---

## Testing on Production

### 1. Metrics Endpoint ✅
**URL**: https://applylens.app/api/metrics/divergence-24h

**Browser Test**:
```javascript
fetch('/api/metrics/divergence-24h')
  .then(r => r.json())
  .then(data => console.log(data))
```

**Expected**: JSON with risk divergence data (no 404)

### 2. Web Application ✅
**URL**: https://applylens.app/web/

**Verification Steps**:
1. Hard refresh: `Ctrl+Shift+R` or `Cmd+Shift+R`
2. Check navigation bar shows "Actions" (not "Inbox (Actions)")
3. Open DevTools > Network tab > Verify production build (bundled JS files)
4. Check console for no 502 errors

**What to Look For**:
- ✅ Page loads successfully (no 502)
- ✅ Script tags show bundled files like `index-[hash].js`
- ✅ Button text is "Actions"
- ⚠️ Favicon warning (cosmetic, ignore)

---

## Key Lessons Learned

### ❌ Wrong Build Command (Causes 502)
```powershell
# This builds DEV image with Vite dev server
docker build -t leoklemet/applylens-web:latest apps/web/
```
**Problem**: Uses `Dockerfile` which runs `npm run dev --host` (port 5173)

### ✅ Correct Build Command (Production)
```powershell
# This builds PRODUCTION image with nginx
docker build -f apps/web/Dockerfile.prod -t leoklemet/applylens-web:latest apps/web/
```
**Why**: Uses `Dockerfile.prod` which:
1. Builds with `npm run build` → creates `/app/dist`
2. Copies `/app/dist` → `/usr/share/nginx/html` in nginx image
3. Exposes port 80 (not 5173)
4. Runs nginx (not Vite)

### Docker Build Caching Issue
When code changes aren't appearing, use `--no-cache`:
```powershell
docker build --no-cache -t leoklemet/applylens-api:latest services/api/
```

Or force container recreation:
```powershell
docker-compose -f docker-compose.prod.yml up -d --force-recreate api
```

### Container Image Updates
`docker-compose restart` doesn't pull new images. Use:
```powershell
docker-compose -f docker-compose.prod.yml up -d --force-recreate
```

---

## Deployment Timeline

| Time (UTC) | Action | Result |
|------------|--------|--------|
| 19:35 | Initial build attempt (used wrong Dockerfile) | ❌ Web in dev mode |
| 19:44 | Fixed API router prefix (`/metrics`) | ✅ API fix ready |
| 19:48 | Deployed API with `--no-cache` | ✅ Metrics working |
| 19:52 | Discovered web using dev Dockerfile | 🔍 Root cause found |
| 19:57 | Rebuilt web with `Dockerfile.prod` | ✅ Production build |
| 19:58 | All services healthy | ✅ **Deployment complete** |

---

## Files Modified

1. ✅ `services/api/app/routers/metrics.py` - Router prefix
2. ✅ `apps/web/src/components/Nav.tsx` - Button label
3. ✅ `apps/web/src/components/AppHeader.tsx` - Button label + Tailwind
4. ✅ `docker-compose.prod.yml` - Web image configuration

---

## Related Documentation

- `PRODUCTION_DEPLOYMENT.md` - Full production deployment guide
- `GRAFANA_DASHBOARDS_COMPLETE.md` - Monitoring setup
- `VERIFICATION_GUIDE.md` - How to verify changes

---

## Next Steps (Optional)

### 1. Fix Favicon Path
**File**: `apps/web/index.html` or Vite config
```html
<!-- Change from: -->
<link rel="icon" href="/favicon.svg" />

<!-- To: -->
<link rel="icon" href="/web/favicon.svg" />
```

### 2. Monitor Production
```powershell
# Watch logs
docker logs -f applylens-api-prod | Select-String "metrics"
docker logs -f applylens-web-prod

# Check resource usage
docker stats applylens-api-prod applylens-web-prod
```

### 3. Set Up Alerts
- Configure Grafana alerts for error rates
- Set up uptime monitoring (Uptime Robot, Pingdom)

---

**Status**: ✅ All Changes Live on Production
**Verified**: API metrics working, web serving production build, button renamed
