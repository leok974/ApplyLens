# v0.4.10 Deployment Guide - Complete Cache Fix

## Summary

**What**: Fix browser caching issue that prevented users from getting the latest bundle
**Why**: Vite content-hash bundles cached forever, but HTML was also cached, so users never got new hashes
**Solution**: Nginx + Cloudflare cache headers to ensure HTML is never cached

## Files Changed

### 1. Frontend Code
- ✅ `apps/web/src/lib/apiUrl.ts` - Absolute URL helper
- ✅ `apps/web/src/hooks/useSearchModel.ts` - Uses apiUrl()
- ✅ `apps/web/src/lib/api.ts` - Uses apiUrl()
- ✅ `apps/web/src/pages/LoginGuard.tsx` - Uses apiUrl()
- ✅ `apps/web/src/main.tsx` - Version banner in console

### 2. Nginx Configuration
- ✅ `apps/web/nginx.conf` - Proper route order + cache headers
  - `/api/` routes FIRST (with `^~` prefix)
  - Assets: `max-age=31536000, immutable`
  - HTML: `no-cache, no-store, must-revalidate`
  - SPA fallback LAST

### 3. Infrastructure Scripts
- ✅ `scripts/Setup-CloudflareCache.ps1` - PowerShell script to configure Cloudflare
- ✅ `scripts/setup-cloudflare-cache.sh` - Bash script for Cloudflare
- ✅ `scripts/Verify-Deployment.ps1` - Automated verification
- ✅ `docs/DEBUG_SEARCH_FETCH.js` - Browser console debugging

### 4. Documentation
- ✅ `docs/DEPLOYMENT_v0.4.10_CACHE_FIX.md` - Complete deployment guide

## Deployment Steps

### Step 1: Build & Deploy (DONE ✅)
```bash
cd apps/web
docker build -t leoklemet/applylens-web:v0.4.10 \
  -f Dockerfile.prod --no-cache .

# Update docker-compose.prod.yml
image: leoklemet/applylens-web:v0.4.10

docker-compose -f docker-compose.prod.yml up -d --force-recreate web
docker-compose -f docker-compose.prod.yml restart nginx
```

**Verify Locally:**
```powershell
.\scripts\Verify-Deployment.ps1 -BaseUrl "http://localhost"
```

### Step 2: Configure Cloudflare Cache Rules (TODO ⚠️)

**Get Your Credentials:**
1. **Zone ID**: Go to https://dash.cloudflare.com/ → Select domain → Zone ID in sidebar
2. **API Token**: https://dash.cloudflare.com/profile/api-tokens → Create Token
   - Permissions: Zone → Cache Rules: Edit + Cache Purge: Purge
   - Zone Resources: Include → Specific zone → applylens.app

**Run Setup:**
```powershell
.\scripts\Setup-CloudflareCache.ps1 `
  -CF_API_TOKEN "your_token_here" `
  -CF_ZONE_ID "your_zone_id_here"
```

**What This Does:**
- Creates 2 cache rules:
  1. **Bypass HTML**: `/`, `/web/`, `*.html` → Never cache
  2. **Immutable Assets**: `/assets/*`, `*.js`, `*.css`, etc. → Cache 1 year
- Purges existing cache for HTML files
- Takes 30-60 seconds to propagate

### Step 3: Verify Production (TODO ⚠️)

**Automated Check:**
```powershell
.\scripts\Verify-Deployment.ps1 -BaseUrl "https://applylens.app"
```

**Manual Check:**
```powershell
# 1. HTML should be no-cache
curl.exe -sI "https://applylens.app/web/" | Select-String "Cache-Control|CF-Cache-Status"
# Expected: Cache-Control: no-cache, no-store, must-revalidate

# 2. API should return JSON
curl.exe -sI "https://applylens.app/api/search?q=test&limit=1" | Select-String "Content-Type"
# Expected: Content-Type: application/json (or 401/403 if not authed)

# 3. Assets should be immutable
curl.exe -sI "https://applylens.app/assets/index-1761254202682.CgHkWaq5.js" | Select-String "Cache-Control"
# Expected: Cache-Control: public, max-age=31536000, immutable
```

### Step 4: Browser Verification (YOU MUST DO THIS ⚠️)

**Clear Browser Cache:**
1. Open DevTools (F12)
2. Go to **Application** tab
3. Click **"Clear storage"** in left sidebar
4. Check **ALL boxes**
5. Click **"Clear site data"**
6. **Close ALL tabs** of applylens.app
7. Open **fresh tab**

**Verify in Browser:**
1. Go to https://applylens.app/web/search
2. Open Console (F12)
3. Should see: `🔍 ApplyLens Web v0.4.10`
4. Paste debug script from `docs/DEBUG_SEARCH_FETCH.js`
5. Perform a search
6. Console should show: `[FETCH] https://applylens.app/api/search?q=... GET`
7. **NOT**: `[FETCH] https://applylens.app/web/search/...`

**Network Tab Check:**
1. Filter by "Fetch/XHR"
2. Click "Search" button
3. Should see request to `/api/search?q=...`
4. Status: 200 OK (or 401 if not logged in)
5. Response: JSON (not HTML)

### Step 5: Run E2E Tests

```powershell
cd apps/web
npx playwright test --grep "@prodSafe"
```

Expected: All tests pass, especially `search.contenttype.spec.ts`

## Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Code Fix (apiUrl) | ✅ DONE | v0.4.10 deployed |
| Nginx Cache Headers | ✅ DONE | Verified locally |
| Version Banner | ✅ DONE | Shows v0.4.10 in console |
| Docker Build | ✅ DONE | Hash: CgHkWaq5 |
| Local Deployment | ✅ DONE | Running on localhost |
| Cloudflare Rules | ⚠️ TODO | Need API token |
| Production Verify | ⚠️ TODO | After Cloudflare setup |
| Browser Cache Clear | ⚠️ TODO | User must do this |

## Troubleshooting

### Issue: Still seeing old bundle (CWO6njqI)
**Solution**: Clear browser cache (see Step 4 above)

### Issue: Still hitting /web/search/
**Solution**:
1. Check console version (should be v0.4.10)
2. Check Network tab for bundle filename (should be `CgHkWaq5.js`)
3. If still old bundle, clear cache again

### Issue: API returns HTML
**Solution**:
1. Check nginx route order: `docker exec applylens-web-prod nginx -T | grep "location"`
2. `/api/` should be before `/` (SPA fallback)
3. Restart nginx: `docker-compose -f docker-compose.prod.yml restart nginx`

### Issue: Cloudflare cache not working
**Solution**:
1. Verify rules are active: Check Cloudflare dashboard → Caching → Cache Rules
2. Purge cache: `curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" -H "Authorization: Bearer $TOKEN" -d '{"purge_everything":true}'`
3. Wait 5 minutes for propagation

## Rollback Plan

If v0.4.10 has issues:
```powershell
# Edit docker-compose.prod.yml
image: leoklemet/applylens-web:v0.4.9  # or v0.4.4

docker-compose -f docker-compose.prod.yml up -d --force-recreate web
docker-compose -f docker-compose.prod.yml restart nginx
```

## Success Criteria

✅ Console shows: `🔍 ApplyLens Web v0.4.10`
✅ Search requests go to `/api/search` (not `/web/search`)
✅ API returns JSON (not HTML)
✅ No more "Unexpected token '<'" errors
✅ HTML has `Cache-Control: no-cache`
✅ JS/CSS has `Cache-Control: max-age=31536000, immutable`

## References

- Bundle Hash: `index-1761254202682.CgHkWaq5.js`
- Build Time: 2025-10-23T20:58:00Z
- Git SHA: 461336d
- Deployed: October 23, 2025
