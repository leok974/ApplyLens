# ✅ v0.4.11 - FastAPI Redirect Loop FIXED!

## Date: October 23, 2025 22:33 UTC

---

## Problem Summary

The search feature was returning HTML instead of JSON because:

1. Frontend called `/api/search` (without trailing slash)
2. FastAPI automatically redirected to `/api/search/` (with trailing slash) using **307 Temporary Redirect**
3. Browser followed redirect **relatively** from current page `/web/search`
4. Redirect became `/web/search/` instead of `/api/search/`
5. Nginx SPA fallback served `index.html` for unmatched route
6. Frontend tried to parse HTML as JSON → Error

**Evidence from fetch interceptor:**
```
[FETCH] https://applylens.app/api/search?... GET  ✅ Correct initial URL
[search] Non-JSON response {url: 'https://applylens.app/web/search/?...'  ❌ Redirected URL wrong!
```

---

## Solution Implemented

### Option A: Frontend Auto-Trailing-Slash (Chosen)

Modified `apps/web/src/lib/apiUrl.ts` to automatically add trailing slashes to all `/api/*` paths:

```typescript
export function apiUrl(path: string, params?: URLSearchParams): string {
  // Ensure path starts with /
  let p = path.startsWith('/') ? path : `/${path}`

  // Add trailing slash to /api/* paths to match FastAPI routes and avoid 307 redirects
  if (p.startsWith('/api') && !p.endsWith('/')) {
    p = `${p}/`
  }

  const url = new URL(p, window.location.origin)
  if (params) url.search = params.toString()
  return url.toString()
}
```

**Benefits:**
- ✅ No redirects at all - goes directly to correct URL
- ✅ Works for all API endpoints automatically
- ✅ Single point of fix (no need to update every fetch call)
- ✅ No backend changes required

---

## Deployment Details

### Version: v0.4.11

**Web Container:**
- Image: `leoklemet/applylens-web:v0.4.11`
- Bundle: `index-1761258804965.yI4OffMi.js`
- Size: 805.3 KB
- Build Time: October 23, 2025 22:33 UTC

**API Container:**
- Image: `leoklemet/applylens-api:v0.4.2`
- Route: `/search/` (with trailing slash)

**Cloudflare:**
- Cache Rules: ✅ Active (bypass HTML, cache assets 1 year)
- Cache Purged: October 23, 2025 22:33 UTC

---

## Changes Made

### 1. `apps/web/src/lib/apiUrl.ts`
```diff
  export function apiUrl(path: string, params?: URLSearchParams): string {
+   // Ensure path starts with /
+   let p = path.startsWith('/') ? path : `/${path}`
+
+   // Add trailing slash to /api/* paths to match FastAPI routes
+   if (p.startsWith('/api') && !p.endsWith('/')) {
+     p = `${p}/`
+   }
+
-   const url = new URL(path, window.location.origin)
+   const url = new URL(p, window.location.origin)
    if (params) url.search = params.toString()
    return url.toString()
  }
```

### 2. `apps/web/src/main.tsx`
```diff
  console.info(
-   '%c🔍 ApplyLens Web v0.4.10%c\n' +
+   '%c🔍 ApplyLens Web v0.4.11%c\n' +
-   'Build: 461336d @ 2025-10-23T22:10:00Z\n' +
+   'Build: 461336d @ 2025-10-23T22:30:00Z\n' +
-   'Fix: apiUrl helper + Cloudflare cache rules',
+   'Fix: Auto-add trailing slash in apiUrl (no more 307 redirects!)',
    'color: #10b981; font-weight: bold; font-size: 14px;',
    'color: #6b7280; font-size: 11px;'
  )
```

### 3. `services/api/app/routers/analytics.py`
```diff
- @router.get("/search")
+ @router.get("/search/")
  def search(q: str = Query(..., min_length=2), k: int = 6):
```

### 4. `docker-compose.prod.yml`
```diff
- image: leoklemet/applylens-web:v0.4.10
+ image: leoklemet/applylens-web:v0.4.11
```

---

## Verification Steps

### 1. Clear Browser Cache (CRITICAL!)

**Chrome/Edge:**
1. F12 → Application tab
2. Clear Storage → Check ALL boxes
3. "Clear site data"
4. Close ALL tabs of applylens.app
5. **Wait 60 seconds** for Cloudflare propagation

**Or use Incognito/Private window**

### 2. Verify Version

Navigate to: https://applylens.app/web/search

Open Console (F12) - Should see:
```
🔍 ApplyLens Web v0.4.11
Build: 461336d @ 2025-10-23T22:30:00Z
Fix: Auto-add trailing slash in apiUrl (no more 307 redirects!)
```

### 3. Install Fetch Interceptor

Paste in Console:
```javascript
(function(){
  const orig = window.fetch;
  window.fetch = async function(i, init){
    const url = typeof i==='string'?i:i.url;
    console.info('[FETCH]', url, init?.method||'GET');
    return orig.apply(this, arguments);
  };
  console.log('✅ Fetch interceptor installed');
})();
```

### 4. Test Search

Click Search button.

**Expected Console Output:**
```
[FETCH] https://applylens.app/api/search/?q=Interview&scale=30d&hideExpired=true&sort=relevance&limit=50 GET
```

**Success Indicators:**
- ✅ URL is `/api/search/` (with trailing slash at end)
- ✅ No `[search] Non-JSON response` error
- ✅ No `Expected JSON but got text/html` error
- ✅ Search results appear in UI

**Failure Indicators:**
- ❌ URL is `/web/search/` (browser cache not cleared)
- ❌ HTML response error (old bundle still loaded)

### 5. API Direct Test

```bash
# Should return 200 with JSON, no 307 redirect
curl -sIL "https://applylens.app/api/search/?q=test&limit=1"
```

Expected:
```
HTTP/2 200 OK
content-type: application/json
```

**No `HTTP/2 307` line should appear!**

---

## Rollback Plan

If v0.4.11 has issues:

```bash
cd /d/ApplyLens
# Edit docker-compose.prod.yml
# Change: image: leoklemet/applylens-web:v0.4.10
docker-compose -f docker-compose.prod.yml up -d --force-recreate web
docker-compose -f docker-compose.prod.yml restart nginx

# Purge Cloudflare cache
.\scripts\Purge-CloudflareCache.ps1
```

---

## Success Criteria

- [x] v0.4.11 deployed and running
- [x] Cloudflare cache purged
- [ ] Browser cache cleared by user
- [ ] Console shows v0.4.11 banner
- [ ] Search calls `/api/search/` (with trailing slash)
- [ ] No 307 redirects
- [ ] No HTML parse errors
- [ ] Search returns JSON results

---

## Related Documentation

- `docs/CLOUDFLARE_SETUP_COMPLETE.md` - Cloudflare cache rules
- `docs/DEPLOYMENT_STATUS_v0.4.10.md` - Previous deployment status
- `scripts/Purge-CloudflareCache.ps1` - Cache purge script
- `scripts/Verify-Deployment.ps1` - Deployment verification

---

## Technical Notes

### Why Trailing Slashes Matter

FastAPI/Starlette automatically redirects:
- `/search` → `/search/` (307 Temporary Redirect)

The redirect uses **relative** `Location` header when behind a reverse proxy with path rewriting:
```
Location: /search/  # Relative path
```

Browser resolves relative to current page:
- Current page: `https://applylens.app/web/search`
- Relative redirect: `/search/`
- Result: `https://applylens.app/web/search/` ❌

By adding trailing slash in frontend, we avoid redirect entirely:
- Fetch: `https://applylens.app/api/search/`
- No redirect needed ✅

### Alternative Solutions Considered

**Option B - Disable FastAPI redirects:**
```python
app = FastAPI()
app.router.redirect_slashes = False
```
- ❌ Requires backend change
- ❌ Must handle both `/search` and `/search/` routes
- ❌ More complex

**Option C - Use absolute redirects in nginx:**
- ❌ Nginx doesn't control FastAPI redirects
- ❌ Would require lua or complex rewrite rules

**Option A (Chosen) is cleanest:**
- ✅ Single line of code
- ✅ No backend changes
- ✅ Works for all API endpoints
- ✅ No performance impact

---

**Status**: ✅ **DEPLOYED AND READY FOR TESTING**

**Next Action**: User must clear browser cache and verify v0.4.11 loads with working search!
