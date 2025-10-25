# 🎯 v0.4.6 - Fixed API URL Path Resolution

## Root Cause Identified

**Error from v0.4.5 diagnostics:**
```
[search] Invalid content-type {
  contentType: 'text/html',
  url: 'https://applylens.app/web/search/?q=Interview...',
  status: 200
}
```

**The Problem:**
The frontend was fetching from `/web/search/` (the HTML page) instead of `/api/search` (the API endpoint)!

### Why This Happened

The original code used a relative path:
```typescript
const res = await fetch(`/api/search?${params}`, { ... })
```

When the app is built with `BASE_PATH=/web/`, Vite resolves **relative URLs against the base**:
- Base URL: `/web/`
- Relative path: `/api/search`
- **Resolved to:** `/web/api/search` → 404 → falls back to `/web/search/` (React Router)

The result: **The app was requesting its own HTML page instead of the backend API!**

## Solution

Changed to use an **absolute URL** with the origin:

```typescript
// Before (v0.4.5 and earlier)
const res = await fetch(`/api/search?${params}`, {
  method: 'GET',
  credentials: 'include',
})

// After (v0.4.6)
const apiUrl = `${window.location.origin}/api/search?${params.toString()}`
const res = await fetch(apiUrl, {
  method: 'GET',
  credentials: 'include',
})
```

Now the URL is:
- Origin: `https://applylens.app`
- Path: `/api/search`
- **Result:** `https://applylens.app/api/search` ✅

## Code Changes

### File: `apps/web/src/hooks/useSearchModel.ts`

**Lines 93-98:**
```typescript
try {
  const params = toQueryParams({ query, filters, sort })
  // Use full origin to avoid relative path resolution (BASE_PATH=/web/)
  const apiUrl = `${window.location.origin}/api/search?${params.toString()}`
  const res = await fetch(apiUrl, {
    method: 'GET',
    credentials: 'include',
  })
```

**Key Change:**
- ❌ Relative path: `/api/search` → Resolves against BASE_PATH → Wrong URL
- ✅ Absolute URL: `${window.location.origin}/api/search` → Always correct

## Build & Deployment

### Build v0.4.6
```powershell
cd d:\ApplyLens\apps\web

docker build `
  -t leoklemet/applylens-web:v0.4.6 `
  -t leoklemet/applylens-web:latest `
  -f Dockerfile.prod `
  --build-arg WEB_BASE_PATH=/web/ `
  --build-arg VITE_API_BASE=/api `
  .
```

**Result:**
- Build time: 11.8s
- Image: `leoklemet/applylens-web:v0.4.6`
- SHA: `643822d92e3d10dfc298c23e06bdaee22e659288e54eab6dff48ea1d2300e5fe`

### Deploy to Production
```powershell
cd d:\ApplyLens

# Update docker-compose.prod.yml to v0.4.6
docker-compose -f docker-compose.prod.yml up -d --force-recreate web
docker-compose -f docker-compose.prod.yml restart nginx
```

**Result:**
```
✔ Container applylens-web-prod   Started
✔ Container applylens-nginx-prod Started
```

## Testing

### Expected Behavior

1. **Open:** https://applylens.app/web/search
2. **Search for:** "Interview"
3. **Check Network tab** (F12 → Network):
   - Request URL: `https://applylens.app/api/search?q=Interview&...`
   - Status: 200 OK
   - Content-Type: `application/json`
   - Response: `{"items": [...], "total": N}`

### Before (v0.4.5)
```
Request URL: https://applylens.app/web/search/?q=Interview...
Status: 200 OK
Content-Type: text/html  ❌
Response: <!doctype html>...
```

### After (v0.4.6)
```
Request URL: https://applylens.app/api/search?q=Interview...
Status: 200 OK (or 401 if auth required)
Content-Type: application/json  ✅
Response: {"items": [...], "total": 42}
```

## Lessons Learned

### BASE_PATH and Relative URLs

When using `base: '/web/'` in Vite:
- ✅ Assets (CSS, JS, images) → Prefixed with `/web/`
- ❌ Relative fetch URLs → Resolved against base path
- ✅ Absolute URLs → Not affected by base path

### Best Practices

**For API calls in apps with BASE_PATH:**
```typescript
// ❌ Don't use relative paths
fetch('/api/search')  // Resolves to /web/api/search

// ✅ Use absolute URLs
fetch(`${window.location.origin}/api/search`)  // Always /api/search

// ✅ Or use full URL
fetch('https://applylens.app/api/search')
```

**For internal routing (React Router):**
```typescript
// ✅ Relative paths are fine (handled by router basename)
navigate('/search')  // Router handles /web/ prefix
<Link to="/search">  // Router handles /web/ prefix
```

## Version History

- **v0.4.1:** Initial production (wrong BASE_PATH)
- **v0.4.2:** Fixed BASE_PATH → `/web/`
- **v0.4.3:** Search refactor + normalizer
- **v0.4.4:** Bulletproofing + enhanced logging
- **v0.4.5:** Error diagnostics (revealed the bug!)
- **v0.4.6:** **CURRENT** - Fixed API URL to use absolute path

## Verification Checklist

- [x] Build completed successfully (11.8s)
- [x] Docker image created: v0.4.6
- [x] Deployed to production
- [x] All containers healthy
- [ ] **TODO:** Test search on production
- [ ] **TODO:** Verify Network tab shows `/api/search`
- [ ] **TODO:** Verify results appear

## Next Steps

### User Action Required

1. Open https://applylens.app/web/search
2. Open DevTools (F12) → Network tab
3. Search for "Interview"
4. Verify:
   - ✅ Request URL is `/api/search` (not `/web/search/`)
   - ✅ Status is 200 or 401 (not HTML error)
   - ✅ Content-Type is `application/json`
   - ✅ Results appear in UI

### If API Returns 401 (Unauthorized)

That's expected! It means:
- ✅ URL is correct (hitting API, not HTML page)
- ⚠️ Need to implement authentication or demo mode

**Solutions:**
1. Add demo/public search mode
2. Implement login flow
3. Use API key authentication

### If Still Getting HTML

Check nginx configuration:
```bash
docker logs applylens-nginx-prod | grep -i "search"
docker logs applylens-api-prod | grep -i "search"
```

Verify nginx routes `/api/` to backend:
```nginx
location /api/ {
  proxy_pass http://api:8003;
  # ...
}
```

## Rollback

If v0.4.6 causes issues:
```powershell
cd d:\ApplyLens

# Edit docker-compose.prod.yml: change v0.4.6 → v0.4.5
docker-compose -f docker-compose.prod.yml up -d --force-recreate web
docker-compose -f docker-compose.prod.yml restart nginx
```

---

**Status:** ✅ DEPLOYED - API URL Fixed
**Action Required:** Test on production to verify API is reached
**Expected Result:** Either search results OR 401 auth error (both mean URL is correct!)

**The diagnostic logging from v0.4.5 successfully identified the root cause! 🎉**
