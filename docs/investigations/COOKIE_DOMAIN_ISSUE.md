# Cookie Domain Issue - Session Not Persisting

## Problem
User can "log in" but session cookie isn't being saved/sent, resulting in immediate 401 errors.

## Root Cause Analysis

### Evidence from Network Tab
```
Response Headers (from api.applylens.app):
set-cookie: csrf_token=vkhVnFNkQPojHb7LQCIoFPrMnD5hicJSJ7-HFLPbk3w; SameSite=Lax; Path=/
```

**CRITICAL ISSUE**: No `Domain` attribute on the cookie!

### Cookie Domain Behavior
When a cookie is set WITHOUT a Domain attribute:
- Browser sets it for the **exact hostname** that responded
- Cookie from `api.applylens.app` response → stored as `api.applylens.app` cookie
- Request from `applylens.app` → browser WON'T send the cookie (different domain)

This is why:
1. Login appears to work (cookie is set)
2. Immediate 401 on next request (cookie not sent from applylens.app)
3. Only csrf_token visible in requests (it's being set, but to wrong domain)

## Required Server-Side Fix

### In FastAPI app configuration (main.py or similar):

```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="applylens_session",
    max_age=14 * 24 * 60 * 60,  # 14 days
    same_site="none",            # Required for cross-origin
    https_only=True,             # Required for SameSite=None
    domain=".applylens.app",     # ← THIS IS THE CRITICAL FIX
)
```

### CSRF Cookie Domain Fix

The CSRF token also needs proper domain. In CSRF middleware setup:

```python
# In CSRF middleware or cookie setting code
response.set_cookie(
    key="csrf_token",
    value=token,
    httponly=True,
    secure=True,
    samesite="none",
    domain=".applylens.app",  # ← Add this
    path="/",
)
```

## Why This Breaks Cross-Origin Setup

### Current Architecture
```
Frontend: https://applylens.app
API:      https://api.applylens.app
```

### Cookie Domain Rules
- Cookie set for `api.applylens.app` (no Domain attr)
  → Only sent to `api.applylens.app`
  → NOT sent to `applylens.app`

- Cookie set for `.applylens.app` (with leading dot)
  → Sent to `applylens.app`, `api.applylens.app`, `www.applylens.app`, etc.
  → Works for cross-subdomain requests

### SameSite Requirements
For cross-origin cookies to work:
1. `SameSite=None` (currently using `Lax` which blocks cross-site)
2. `Secure=True` (HTTPS only - already have this)
3. `Domain=.applylens.app` (wildcard subdomain - MISSING THIS)

## Alternative Fixes (if server config can't be changed immediately)

### Option 1: Same-Origin Deployment
Move frontend to same domain as API:
- API: `https://api.applylens.app`
- Frontend: `https://api.applylens.app/app` or `https://api.applylens.app`

Then cookies work without Domain attribute.

### Option 2: Proxy Setup
Add a proxy at `applylens.app/api/*` that forwards to `api.applylens.app/*`:

```nginx
# In nginx config for applylens.app
location /api/ {
    proxy_pass https://api.applylens.app/;
    proxy_set_header Host api.applylens.app;
    proxy_set_header X-Real-IP $remote_addr;
}
```

Then frontend calls `/api/auth/me` instead of `https://api.applylens.app/auth/me`, making it same-origin.

### Option 3: Move Frontend to api.applylens.app
Simplest fix - serve the frontend from `api.applylens.app` instead of `applylens.app`.

## Testing the Fix

After applying server-side cookie domain fix:

1. Clear all cookies for applylens.app and api.applylens.app
2. Log in via Google OAuth
3. Check DevTools → Application → Cookies
4. Verify cookie shows:
   - Domain: `.applylens.app` (with leading dot)
   - SameSite: `None`
   - Secure: ✓
5. Make request to `/auth/me`
6. Check Network tab → Cookie header should include `applylens_session`

## Deployment Instructions

### Backend (FastAPI/Starlette)

**File**: `services/api/app/main.py` or wherever middleware is configured

```python
# Find the SessionMiddleware configuration
# Change from:
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="applylens_session",
)

# To:
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="applylens_session",
    max_age=14 * 24 * 60 * 60,
    same_site="none",           # Changed from "lax"
    https_only=True,
    domain=".applylens.app",    # NEW - enables cross-subdomain
)
```

**Deploy**:
```bash
cd services/api
git pull origin main
docker build -t applylens-api:latest .
docker push ...
# Restart API service
```

### Verification

After deployment, have user:
1. Log out completely
2. Clear browser cookies
3. Log in fresh
4. Check if session persists

Expected: Settings page shows email immediately, no 401 errors.

## Current Status

🔴 **BLOCKED** - Requires server-side configuration change to cookie domain settings
📋 **ACTION REQUIRED** - Backend team must deploy cookie domain fix to production API

## Related Issues

- Similar issue likely affects all authenticated API calls from frontend
- May be causing intermittent auth failures for other users
- Logout flow may also be affected (can't clear cookie that was never set)
