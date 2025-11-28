# Same-Origin API Implementation Guide

## Overview

This document describes the **recommended architecture** for ApplyLens: using same-origin `/api` proxy instead of cross-subdomain cookies.

## Problem Statement

**Original Issue**: Login/callback on `api.applylens.app` but app runs on `applylens.app`
- Cookies set without `Domain` attribute are host-only
- Browser won''t send `api.applylens.app` cookies to `applylens.app`
- Results in immediate 401 errors after login

**Root Cause**: Host mismatch between OAuth callback and application frontend

## Solution: Same-Origin `/api` Proxy (Standard)

### Architecture

```
User Browser
    ↓
https://applylens.app/           → Nginx (applylens-web-prod:80)
https://applylens.app/api/...    → Proxied to FastAPI (applylens-api-prod:8003)
```

All cookies are set for `applylens.app` domain - no cross-subdomain issues.

### Implementation Checklist

#### ✅ Frontend (Already Implemented)

**File**: `apps/web/src/lib/apiBase.ts`
```typescript
export const API_BASE = import.meta.env.VITE_API_BASE ?? ''/api''
```

**File**: `apps/web/src/api/auth.ts`
```typescript
export function loginWithGoogle(): void {
  window.location.href = `${API_BASE}/auth/google/login`;  // Uses /api
}
```

**Status**: ✅ All API calls already use `API_BASE` which defaults to `/api`

#### ✅ Nginx Proxy (Already Configured)

**File**: `apps/web/nginx.conf`
```nginx
# General API proxy
location ^~ /api/ {
    proxy_pass         http://applylens-api-prod:8003/;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
    proxy_connect_timeout 5s;
    proxy_send_timeout    180s;
    proxy_read_timeout    180s;
    client_max_body_size  10m;
    proxy_intercept_errors off;
}
```

**Status**: ✅ Nginx already proxies `/api/*` to backend

#### 🔄 Backend Session Configuration (NEEDS UPDATE)

**Current State**: Unknown (need to verify backend code)

**Required Configuration**:
```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    session_cookie="applylens_session",
    same_site="lax",       # OK for same-origin /api
    https_only=True,       # Required in production
    max_age=14 * 24 * 60 * 60,  # 14 days
    # domain NOT needed for same-origin - cookies are host-only for applylens.app
)
```

**Key Points**:
- `same_site="lax"` is sufficient (all requests from applylens.app to applylens.app/api)
- `domain` parameter can be omitted (host-only cookies work for same-origin)
- If you need to support direct `api.applylens.app` access, add `domain=".applylens.app"`

#### 🔄 OAuth Callback Configuration (NEEDS VERIFICATION)

**Required Setup**:

1. **Google OAuth Console**: Callback URL must be `https://applylens.app/api/auth/google/callback`
2. **Backend OAuth Config**: Verify redirect_uri uses `/api` path

**Verification**:
```bash
# Check OAuth callback redirect
curl -I https://applylens.app/api/auth/google/login

# Should redirect to Google with redirect_uri=https://applylens.app/api/auth/google/callback
```

### Deployment Steps

1. **Verify Backend SessionMiddleware Configuration**
   ```bash
   # Check services/api/app/main.py or similar
   grep -A 10 "SessionMiddleware" services/api/app/*.py
   ```

2. **Update OAuth Callback URLs (if needed)**
   - Google Cloud Console → Credentials → OAuth 2.0 Client IDs
   - Update Authorized redirect URIs: `https://applylens.app/api/auth/google/callback`

3. **Deploy Backend Changes**
   ```bash
   cd services/api
   docker build -t applylens-api:latest .
   docker push <registry>/applylens-api:latest
   ```

4. **Verify Cookie Behavior**
   ```javascript
   // In browser console on https://applylens.app
   console.log(document.cookie)
   // Should see: applylens_session=...; csrf_token=...
   ```

5. **Test OAuth Flow**
   ```bash
   # Navigate to https://applylens.app
   # Click "Login with Google"
   # After OAuth: should redirect to https://applylens.app (NOT api.applylens.app)
   # Verify session persists (no 401 on /api/auth/me)
   ```

### Alternative: Cross-Subdomain Cookies (Not Recommended)

If you must support direct `https://api.applylens.app` browser access:

```python
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    session_cookie="applylens_session",
    same_site="none",      # Required for cross-origin
    https_only=True,       # Required for SameSite=None
    domain=".applylens.app",  # Share cookies across subdomains
)
```

**Drawbacks**:
- Less secure (cookies sent to all subdomains)
- Requires `SameSite=None` (more permissive)
- CORS complexity increases
- Not recommended for modern web apps

## Validation

### Cookie Domain Check
```javascript
// On https://applylens.app
document.cookie.split(''; '').forEach(c => console.log(c))

// Expected output:
// applylens_session=<value>
// csrf_token=<value>
```

### Session Persistence Test
```bash
# 1. Login via browser
# 2. Open DevTools → Network
# 3. Navigate to Settings page
# 4. Check /api/auth/me request

# Should see:
# Request Headers:
#   Cookie: applylens_session=...; csrf_token=...
# Response:
#   200 OK with user JSON
```

### OAuth Callback Test
```bash
# Click "Login with Google"
# After OAuth redirect:
# - URL should be https://applylens.app (NOT api.applylens.app)
# - Session should persist
# - No 401 errors on subsequent requests
```

## Relationship to Settings Page Fix

The Settings page fix (PR #XX) handles the **symptom** (redirect to login when session missing).

This same-origin implementation handles the **root cause** (prevent session from being lost).

Once deployed:
- ✅ OAuth callback lands on correct domain (`applylens.app`)
- ✅ Session cookie is set for correct domain (`applylens.app`)
- ✅ Settings page can distinguish "no session" vs "valid session"
- ✅ No more infinite "Loading..." due to cookie domain mismatch

## References

- Investigation: `docs/investigations/COOKIE_DOMAIN_ISSUE.md`
- Settings Fix: PR #XX (commit 66efef5)
- Nginx Config: `apps/web/nginx.conf`
- API Base: `apps/web/src/lib/apiBase.ts`

## Next Steps

1. [ ] Verify backend SessionMiddleware configuration
2. [ ] Update Google OAuth callback URLs if needed
3. [ ] Deploy backend changes
4. [ ] Test OAuth flow end-to-end
5. [ ] Verify cookie domain in production
6. [ ] Monitor for 401 errors in production logs