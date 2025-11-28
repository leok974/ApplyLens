# Authentication 401 Errors Investigation

## Issue Summary
**Date**: 2025-11-27
**Reporter**: User
**Environment**: Production (applylens.app)
**Symptoms**: User reports being logged in but seeing 401 errors for `/auth/me` endpoint

## Evidence from Screenshot

### Console Errors
```
Failed to load resource: the server responded with a status of 401 ()
https://api.applylens.app/auth/me -> 401

Multiple errors:
- index-DVFK-9OT.js:15:487
- index-DVFK-9OT.js:16:7210
- index-DVFK-9OT.js:16:6322
- index-DVFK-9OT.js:15:6819
```

### UI State
- Settings page shows: "Signed in as **Loading...**"
- This indicates `accountEmail` state is stuck at null
- User believes they are logged in (not redirected to login)

## Probable Root Causes

### 1. Cookie/Session Issues (Most Likely)
**Hypothesis**: Cookies not being sent with requests

**Evidence**:
- Recent commit: "fix(api): use signed tokens for OAuth state instead of session cookies" (6d5d950)
- CORS/cookie configuration may have changed
- Production API at different domain (`api.applylens.app` vs `applylens.app`)

**Checks Needed**:
- [ ] Verify `SameSite` cookie attribute (should be `None` for cross-origin)
- [ ] Verify `Secure` flag is set (required for `SameSite=None`)
- [ ] Check if cookies are being sent in browser DevTools Network tab
- [ ] Verify CORS `Access-Control-Allow-Credentials: true`
- [ ] Check if session cookie domain is correct (`.applylens.app`)

### 2. Session Expired
**Hypothesis**: Valid UI state but expired backend session

**Evidence**:
- User thinks they're logged in
- But API returns 401

**Checks Needed**:
- [ ] Check session expiration settings
- [ ] Verify if session was invalidated server-side
- [ ] Check if user needs to re-authenticate

### 3. CSRF Protection Issue
**Hypothesis**: CSRF middleware blocking legitimate requests

**Evidence**:
- Recent commits show CSRF exemptions being added
- `/auth/logout` was exempted (commit 6213e79)
- `/auth/me` might need similar exemption

**Checks Needed**:
- [ ] Verify if CSRF token is required for GET /auth/me
- [ ] Check CSRF middleware configuration
- [ ] Verify CSRF token is being sent if required

### 4. OAuth State Token Issue
**Hypothesis**: Recent OAuth state refactoring broke session handling

**Evidence**:
- Recent commit changed from session cookies to signed tokens (6d5d950)
- This was for OAuth state, but may have affected general session handling

**Checks Needed**:
- [ ] Verify SessionMiddleware is still properly configured
- [ ] Check if SessionMiddleware is before other middleware
- [ ] Verify session secret is configured

## Technical Context from Code

###  LoginGuard.tsx Behavior
```tsx
// From apps/web/src/pages/LoginGuard.tsx line 52-56
// 401/403 is a STABLE unauthenticated state - don't retry!
if (r.status === 401 || r.status === 403) {
  console.info("[LoginGuard] User not authenticated (401/403)");
  return null;
}
```

The code properly handles 401 as "not authenticated", so the UI should show login prompt, not "Loading...".

### Settings.tsx Loading State
```tsx
// From apps/web/src/pages/Settings.tsx line 78
<span>{accountEmail ?? "Loading..."}</span>
```

The "Loading..." state means:
1. `getCurrentUser()` returned null (no cache)
2. `fetchAndCacheCurrentUser()` hasn't resolved yet OR returned null
3. This suggests the API call is failing silently

## Recommended Investigation Steps

### 1. Browser DevTools Check
```bash
# Open DevTools -> Network tab
# Filter for: auth/me
# Check:
- Request headers (Cookie header present?)
- Response headers (Set-Cookie present?)
- Response body
- Status code
```

### 2. Check Production API Logs
```bash
# Look for /auth/me requests with 401
# Check for error messages like:
- "Invalid session"
- "CSRF validation failed"
- "Cookie not found"
```

### 3. Verify Cookie Configuration
Check API middleware setup for:
```python
# SessionMiddleware should be configured with:
session_cookie="applylens_session"
max_age=14 * 24 * 60 * 60  # 14 days
same_site="none"  # For cross-origin
https_only=True   # Required for SameSite=None
domain=".applylens.app"  # Wildcard for subdomains
```

### 4. Check CORS Configuration
```python
# CORSMiddleware should have:
allow_origins=["https://applylens.app"]
allow_credentials=True  # Required for cookies
allow_methods=["GET", "POST", "PUT", "DELETE"]
allow_headers=["*"]
```

## Potential Fixes

### Fix 1: Update Cookie Settings (If using separate domains)
```python
# In API middleware configuration
SessionMiddleware(
    app,
    secret_key=settings.SECRET_KEY,
    session_cookie="applylens_session",
    same_site="none",  # Changed from "lax"
    https_only=True,
    domain=".applylens.app",  # Added wildcard domain
)
```

### Fix 2: Exempt /auth/me from CSRF (If CSRF is blocking)
```python
# Similar to commit 6213e79 for /auth/logout
@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    if request.url.path in ["/auth/logout", "/auth/me"]:
        return await call_next(request)
    # ... CSRF validation
```

### Fix 3: Add Retry Logic to Settings Page
```tsx
// In Settings.tsx, add exponential backoff
const [retryCount, setRetryCount] = useState(0)

useEffect(() => {
  const fetchWithRetry = async () => {
    try {
      const user = await fetchAndCacheCurrentUser()
      if (user?.email) {
        setAccountEmail(user.email)
      } else if (retryCount < 3) {
        // Retry after delay
        setTimeout(() => setRetryCount(retryCount + 1), 1000 * (retryCount + 1))
      }
    } catch (err) {
      console.error('Failed to fetch user:', err)
      if (retryCount < 3) {
        setTimeout(() => setRetryCount(retryCount + 1), 1000 * (retryCount + 1))
      }
    }
  }
  fetchWithRetry()
}, [retryCount])
```

### Fix 4: Better Error Handling in LoginGuard
```tsx
// Add more detailed logging
if (r.status === 401 || r.status === 403) {
  const cookieHeader = document.cookie
  console.error("[LoginGuard] 401/403 received", {
    url: r.url,
    status: r.status,
    hasCookies: Boolean(cookieHeader),
    cookies: cookieHeader.split(';').map(c => c.split('=')[0].trim())
  })
  return null
}
```

## Next Steps

1. **Immediate**: Check browser DevTools Network tab for `/auth/me` request
2. **Backend**: Review API logs for 401 errors and session validation failures
3. **Config**: Verify cookie and CORS configuration match cross-origin requirements
4. **Code**: Add better error logging to identify exact failure point

## Related Commits

- `6d5d950` - fix(api): use signed tokens for OAuth state instead of session cookies
- `305fe29` - fix(api): move SessionMiddleware before CSRFMiddleware for OAuth state
- `6213e79` - fix(api): exempt /auth/logout from CSRF protection
- `1d4a0ef` - fix(agent): Implement proper session-based user resolution

## Status

✅ **ROOT CAUSE IDENTIFIED** - Session cookie missing

## Investigation Results (2025-11-28 04:01 UTC)

### Network Analysis from DevTools

**Request Headers:**
```
Cookie: csrf_token=vkhVnFNkQPojHb7LQCIoFPrMnD5hicJSJ7-HFLPbk3w
```

**Response Headers:**
```
Status: 401 Unauthorized
Set-Cookie: csrf_token=vkhVnFNkQPojHb7LQCIoFPrMnD5hicJSJ7-HFLPbk3w; SameSite=Lax; Path=/
access-control-allow-credentials: true
access-control-allow-origin: https://applylens.app
```

### Root Cause

**The `applylens_session` cookie is completely missing!**

The user is NOT actually logged in. Only the CSRF token exists, but no session cookie. This means:
1. User never completed login flow, OR
2. Session cookie was cleared/expired, OR
3. Session cookie has wrong domain/path and isn't being stored

### Why UI Shows "Signed in as Loading..."

The UI bug is in `Settings.tsx`:
- `getCurrentUser()` returns `null` (no cached user)
- `fetchAndCacheCurrentUser()` makes API call to `/auth/me`
- API returns 401 (no session)
- `fetchAndCacheCurrentUser()` likely returns `null` silently
- UI stays stuck at "Loading..." because `accountEmail` remains `null`

The UI should detect the 401 and redirect to login, but it's not.

## Immediate Fix Required

### Fix 1: Detect Missing Session and Redirect to Login

The `Settings.tsx` page should redirect unauthenticated users to login instead of showing "Loading..." forever.

### Fix 2: Check Why Session Cookie Missing

Possible reasons:
1. User logged out but frontend state not cleared
2. Session cookie expired (check max_age setting)
3. Session cookie domain mismatch (should be `.applylens.app` not `api.applylens.app`)
4. Logout endpoint cleared session but UI didn't refresh
5. User manually cleared cookies

### Status

🔴 **OPEN** - Awaiting investigation data from production environment
