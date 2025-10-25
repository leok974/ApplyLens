# 🔍 v0.4.5 - Better Error Diagnostics

## Issue Identified

**Error:** `SyntaxError: Unexpected token '<', "<!doctype "... is not valid JSON`

**Root Cause:** The `/api/search` endpoint is returning HTML instead of JSON. This typically means:
1. API is redirecting to a login/error page
2. API endpoint doesn't exist (404 page)
3. Nginx is serving an error page
4. API is crashing and returning default error HTML

## Solution Deployed (v0.4.5)

### Enhanced Error Logging

Added comprehensive diagnostics to identify why the API returns HTML:

```typescript
// Before parsing JSON, check content-type
const contentType = res.headers.get('content-type')
if (!contentType || !contentType.includes('application/json')) {
  console.error('[search] Invalid content-type', {
    contentType,
    url: res.url,
    status: res.status,
  })

  const text = await res.text()
  console.error('[search] Response body (first 200 chars):', text.substring(0, 200))
  throw new Error(`Expected JSON but got ${contentType || 'unknown content type'}`)
}
```

### HTTP Error Details

Added logging for non-200 responses:

```typescript
if (!res.ok) {
  const contentType = res.headers.get('content-type')
  console.error('[search] HTTP error', {
    status: res.status,
    statusText: res.statusText,
    contentType,
    url: res.url,
  })

  const text = await res.text()
  throw new Error(`Search failed: ${res.status} ${res.statusText}. ${text.substring(0, 100)}`)
}
```

## How to Diagnose

### Step 1: Open Production Search
https://applylens.app/web/search

### Step 2: Open Browser DevTools Console
Press F12 → Console tab

### Step 3: Trigger Search
Type "Interview" and press Enter

### Step 4: Check Console Logs

You'll now see detailed error information:

**If API returns HTML (200 OK):**
```javascript
[search] Invalid content-type {
  contentType: "text/html",
  url: "https://applylens.app/api/search?q=Interview...",
  status: 200
}
[search] Response body (first 200 chars): <!doctype html><html><head>...
```

**If API returns error status:**
```javascript
[search] HTTP error {
  status: 401,
  statusText: "Unauthorized",
  contentType: "text/html",
  url: "https://applylens.app/api/search?q=Interview..."
}
[search] error Error: Search failed: 401 Unauthorized. <!doctype html>...
```

**If API returns redirect:**
```javascript
[search] HTTP error {
  status: 307,
  statusText: "Temporary Redirect",
  contentType: null,
  url: "https://applylens.app/search/?q=Interview..."  // Note: /search/ not /api/search
}
```

## Common Scenarios

### Scenario 1: 307 Redirect
**Console shows:**
```
status: 307
url: "https://applylens.app/search/?q=Interview"  // Note: no /api/
```

**Diagnosis:** API is redirecting `/api/search` to `/search/` (web route)

**Cause:** Backend search endpoint might be doing a redirect for unauthenticated users

**Fix Options:**
1. Check backend `/api/search` route - should return JSON, not redirect
2. Verify authentication cookies are being sent
3. Check CORS settings allow credentials

### Scenario 2: 401 Unauthorized
**Console shows:**
```
status: 401
contentType: "text/html"
```

**Diagnosis:** User not authenticated

**Cause:** Session expired or credentials not sent

**Fix Options:**
1. Verify `credentials: 'include'` in fetch (✅ already done)
2. Check cookies in DevTools → Application → Cookies
3. Try logging in again

### Scenario 3: 404 Not Found
**Console shows:**
```
status: 404
contentType: "text/html"
url: "https://applylens.app/api/search?..."
```

**Diagnosis:** API endpoint doesn't exist

**Cause:** Backend route not configured

**Fix Options:**
1. Check backend has `/api/search` route
2. Verify nginx proxy passes `/api/` to backend
3. Check API logs for 404 errors

### Scenario 4: 500 Internal Server Error
**Console shows:**
```
status: 500
contentType: "text/html"
Response body: <!doctype html>... Internal Server Error ...
```

**Diagnosis:** Backend crash

**Cause:** Bug in search endpoint

**Fix Options:**
1. Check API container logs: `docker logs applylens-api-prod`
2. Look for Python traceback
3. Fix backend bug

## Testing from Command Line

### Test API directly (bypassing web app)

```bash
# Test with cookies (requires valid session)
curl -v -H "Cookie: session=..." https://applylens.app/api/search?q=Interview&limit=1

# Check what the endpoint returns
curl -I https://applylens.app/api/search?q=Interview&limit=1

# See first 100 chars of response
curl -s https://applylens.app/api/search?q=Interview&limit=1 | head -c 100
```

### Expected responses

**Success (JSON):**
```
HTTP/1.1 200 OK
Content-Type: application/json
...
{"items":[...], "total":42}
```

**Auth required (Redirect):**
```
HTTP/1.1 307 Temporary Redirect
Location: /search/?q=Interview
...
```

**No results (Empty):**
```
HTTP/1.1 204 No Content
...
(empty body)
```

## Deployment Info

**Version:** v0.4.5
**Deployed:** October 23, 2025 1:08 PM
**Build Time:** 13.9s
**Status:** ✅ DEPLOYED

**Changes:**
- Content-type validation before JSON parsing
- Detailed error logging with URL, status, content-type
- First 200 chars of HTML response logged for diagnosis

## What You Should Do Now

### 1. Test on Production
Visit: https://applylens.app/web/search

### 2. Check Console Logs
Look for:
- `[search] Invalid content-type` - Shows what content-type was received
- `[search] HTTP error` - Shows status code and URL
- `[search] Response body` - Shows first 200 chars of HTML

### 3. Report Findings

**If you see 307 redirect:**
Backend is redirecting `/api/search` to web route. Need to fix backend.

**If you see 401 unauthorized:**
Authentication issue. Check cookies or try logging in.

**If you see 404:**
API endpoint doesn't exist. Check backend routing.

**If you see 500:**
Backend crash. Check `docker logs applylens-api-prod` for errors.

### 4. Check Backend Logs

```bash
# Check API logs for errors
docker logs applylens-api-prod --tail 50

# Follow logs in real-time
docker logs -f applylens-api-prod

# Look for /api/search requests
docker logs applylens-api-prod | grep -i "search"
```

## Next Steps Based on Diagnosis

### If API redirects (307)
**Backend needs to return JSON, not redirect**

Check `services/api` for search route and ensure it:
- Returns `{"items": [...], "total": N}` as JSON
- Doesn't redirect to web routes
- Handles authentication properly

### If authentication fails (401)
**Frontend needs valid session**

Options:
1. Login to applylens.app first
2. Check demo auth is working
3. Verify CORS allows credentials

### If endpoint missing (404)
**Backend needs search route**

Check:
- `services/api/routers/` has search.py or similar
- Route is registered in main.py
- Nginx proxies `/api/` correctly

### If backend crashes (500)
**Fix backend bug**

1. Read error from `docker logs applylens-api-prod`
2. Fix Python code
3. Rebuild API: `docker-compose -f docker-compose.prod.yml up -d --force-recreate api`

## Files Changed in v0.4.5

- `apps/web/src/hooks/useSearchModel.ts` - Enhanced error logging (~30 lines)
- `docker-compose.prod.yml` - Version bump to v0.4.5

## Rollback

If needed:
```bash
cd d:\ApplyLens
# Edit docker-compose.prod.yml: change v0.4.5 → v0.4.4
docker-compose -f docker-compose.prod.yml up -d --force-recreate web
docker-compose -f docker-compose.prod.yml restart nginx
```

---

**Status:** ✅ DEPLOYED - DIAGNOSTIC LOGGING ACTIVE
**Action Required:** Test on production and check Console for detailed error information
**Purpose:** Identify WHY the API returns HTML instead of JSON

**Open https://applylens.app/web/search and check the Console now!** 🔍
