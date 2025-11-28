# Cookie Domain Issue - Session Not Persisting

## Problem Statement

User experiences immediate 401 errors after OAuth login, appearing to be "logged in" but unable to make authenticated requests.

**Root Cause**: **Host mismatch between OAuth callback and application frontend**
- OAuth callback lands on `api.applylens.app`
- Application runs on `applylens.app`
- Cookies set without `Domain` attribute are host-only → cross-subdomain requests fail

This is a **cross-subdomain authentication issue**, not a general "cookies without Domain never work" problem.

## Evidence from Network Analysis

### Response Headers (from api.applylens.app)
```
set-cookie: csrf_token=vkhVnFNkQPojHb7LQCIoFPrMnD5hicJSJ7-HFLPbk3w; SameSite=Lax; Path=/
```

**CRITICAL ISSUE**: No `Domain` attribute on the cookie!

### Cookie Domain Behavior
When a cookie is set WITHOUT a Domain attribute:
- Browser stores it for the **exact hostname** that responded
- Cookie from `api.applylens.app` response → stored as `api.applylens.app` cookie
- Request from `applylens.app` → browser WON''T send the cookie (different subdomain)

### Why This Causes the Bug
1. ✅ OAuth callback hits `api.applylens.app/auth/google/callback`
2. ✅ Backend sets `applylens_session` cookie (but for `api.applylens.app` only)
3. ✅ Callback redirects to `applylens.app`
4. ❌ Browser won''t send `api.applylens.app` cookies to `applylens.app`
5. ❌ Frontend makes request to `api.applylens.app/auth/me` → 401 Unauthorized

Result: User appears "logged in" but all API requests fail with 401.

## Two Solution Paths

### ✅ **Solution 1: Same-Origin `/api` Proxy** (RECOMMENDED)

Use same-origin architecture - all requests from `applylens.app` to `applylens.app/api/*` (proxied to backend).

**Benefits**:
- ✅ No cross-subdomain cookie issues
- ✅ Simpler security model (host-only cookies)
- ✅ Standard modern web architecture
- ✅ No `Domain` attribute needed

**Implementation**: See `SAME_ORIGIN_API_IMPLEMENTATION.md`

**Status**: 
- ✅ Frontend already uses `/api` via `API_BASE`
- ✅ Nginx already configured to proxy `/api/*`
- 🔄 Backend SessionMiddleware needs verification
- 🔄 OAuth callback URLs need verification

### ⚠️ **Solution 2: Cross-Subdomain Cookies** (NOT RECOMMENDED)

Set cookies with `domain=".applylens.app"` to share across subdomains.

**Required Backend Changes**:
```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    session_cookie="applylens_session",
    same_site="none",            # Required for cross-origin
    https_only=True,             # Required for SameSite=None
    domain=".applylens.app",     # Share cookies across subdomains
)
```

**Drawbacks**:
- ❌ Less secure (cookies sent to ALL subdomains)
- ❌ Requires `SameSite=None` (more permissive)
- ❌ CORS complexity
- ❌ Not industry standard for modern apps

## Recommended Action Plan

1. **Implement Solution 1** (same-origin `/api` proxy)
   - Frontend: ✅ Already done
   - Nginx: ✅ Already done
   - Backend: 🔄 Verify SessionMiddleware config
   - OAuth: 🔄 Update callback URLs to use `/api` path

2. **Deployment Steps**:
   ```bash
   # 1. Update Google OAuth Console
   # Callback URL: https://applylens.app/api/auth/google/callback
   
   # 2. Verify backend SessionMiddleware (can omit domain for same-origin)
   # services/api/app/main.py or similar
   
   # 3. Deploy and test
   # - Login should redirect to applylens.app (not api.applylens.app)
   # - Session should persist
   # - No 401 errors
   ```

3. **Validation**:
   ```javascript
   // On https://applylens.app in browser console
   document.cookie
   // Should show: applylens_session=...; csrf_token=...
   ```

## Relationship to Settings Page Fix

**Settings Page Fix** (commit 66efef5): Handles the **symptom**
- Detects missing/invalid session
- Redirects to login instead of showing "Loading..." forever

**Same-Origin Implementation**: Handles the **root cause**
- Prevents session from being lost due to cookie domain mismatch
- Ensures OAuth callback lands on correct domain
- Maintains session across all requests

**Together**: Robust authentication flow
- Backend sets cookies correctly (same-origin)
- Frontend detects auth failures gracefully (Settings fix)
- User experience: seamless login, clear error states

## References

- **Implementation Guide**: `docs/investigations/SAME_ORIGIN_API_IMPLEMENTATION.md`
- **Settings Fix**: Commit 66efef5
- **Network Analysis**: Original investigation in this document
- **Frontend API Base**: `apps/web/src/lib/apiBase.ts`
- **Nginx Config**: `apps/web/nginx.conf`