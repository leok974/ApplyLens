# Backend Verification Checklist

This checklist helps verify the backend configuration for same-origin `/api` implementation.

## Files to Check

### 1. SessionMiddleware Configuration

**Expected Location**: `services/api/app/main.py` or `services/api/app/__init__.py`

**Search for**:
```bash
grep -A 15 "SessionMiddleware" services/api/app/*.py
```

**Required Configuration**:
```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,  # or similar
    session_cookie="applylens_session",      # exact name matters
    same_site="lax",                         # "lax" for same-origin
    https_only=True,                         # required in production
    max_age=14 * 24 * 60 * 60,              # optional: 14 days
    # domain NOT needed for same-origin /api proxy
)
```

**What to Check**:
- [ ] `session_cookie` name matches what frontend expects
- [ ] `same_site="lax"` (not "none" unless you need cross-origin)
- [ ] `https_only=True` for production
- [ ] NO `domain` parameter (or comment it out for same-origin)

### 2. CSRF Cookie Configuration

**Search for**:
```bash
grep -rn "csrf_token" services/api/app/ | grep -i cookie
```

**Required**: CSRF cookies should also NOT have Domain attribute for same-origin

### 3. OAuth Callback Configuration

**Google OAuth Settings**:
- [ ] Login URL: `https://applylens.app/api/auth/google/login`
- [ ] Callback URL: `https://applylens.app/api/auth/google/callback`

**Backend OAuth Config**:
```bash
grep -rn "redirect_uri\|oauth\|google" services/api/app/auth/ services/api/app/routers/
```

**What to Check**:
- [ ] OAuth redirect_uri uses base domain (applylens.app) not subdomain
- [ ] After OAuth success, redirect goes to applylens.app (not api.applylens.app)

### 4. CORS Configuration (Should be Minimal)

For same-origin `/api`, CORS is NOT needed (all requests are same-origin).

**Search for**:
```bash
grep -A 10 "CORSMiddleware" services/api/app/*.py
```

**Expected**: CORS middleware may not be needed at all for same-origin.
If present, verify it doesn''t interfere with cookie handling.

## Verification Commands

### Check Current Deployment

```bash
# 1. Check if API is accessible via /api proxy
curl -I https://applylens.app/api/auth/csrf

# Expected: 200 OK with Set-Cookie headers

# 2. Check OAuth login redirect
curl -I https://applylens.app/api/auth/google/login

# Expected: 307 Redirect to accounts.google.com
# Verify redirect_uri parameter points to applylens.app (not api.applylens.app)

# 3. Test session persistence
# (Requires browser or authenticated curl session)
```

### Local Testing

```bash
# 1. Start backend locally
cd services/api
uvicorn app.main:app --reload --port 8003

# 2. Start frontend with proxy
cd apps/web
VITE_API_BASE=/api npm run dev

# 3. Test OAuth flow
# - Navigate to http://localhost:5173
# - Click "Login with Google"
# - After OAuth: should redirect to localhost:5173 (not localhost:8003)
# - Verify session persists
```

## Code Changes Needed

If backend is NOT configured for same-origin, here are the required changes:

### File: `services/api/app/main.py` (or wherever SessionMiddleware is added)

```python
# BEFORE (cross-subdomain - problematic):
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="applylens_session",
    same_site="none",             # ← Remove "none"
    https_only=True,
    domain=".applylens.app",      # ← Remove domain
)

# AFTER (same-origin - recommended):
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="applylens_session",
    same_site="lax",              # ← Change to "lax"
    https_only=True,
    max_age=14 * 24 * 60 * 60,   # Optional: 14 days
    # domain removed - host-only cookies for applylens.app
)
```

### File: OAuth callback handler (e.g., `services/api/app/auth/oauth.py`)

```python
# BEFORE (redirect to API subdomain - problematic):
return RedirectResponse(
    url="https://api.applylens.app/",
    status_code=307
)

# AFTER (redirect to main domain - correct):
return RedirectResponse(
    url="https://applylens.app/",
    status_code=307
)
```

## Google Cloud Console Updates

If OAuth callback URLs need updating:

1. Go to: https://console.cloud.google.com/apis/credentials
2. Select your OAuth 2.0 Client ID
3. Update **Authorized redirect URIs**:
   - Remove: `https://api.applylens.app/auth/google/callback`
   - Add: `https://applylens.app/api/auth/google/callback`
4. Save changes

**Note**: Google may take a few minutes to propagate changes.

## Testing Checklist

After backend deployment:

- [ ] OAuth login redirects to `applylens.app` (not `api.applylens.app`)
- [ ] Session cookie appears in browser DevTools for `applylens.app`
- [ ] `/api/auth/me` returns 200 OK with user data (not 401)
- [ ] Settings page loads successfully (no infinite "Loading...")
- [ ] Logout works correctly
- [ ] Re-login works correctly

## Rollback Plan

If issues occur after deployment:

1. **Quick Fix**: Add `domain=".applylens.app"` to SessionMiddleware (reverts to cross-subdomain)
2. **Full Rollback**: Revert backend deployment
3. **Investigation**: Check browser console, network tab, backend logs

## Related Documentation

- **Implementation Guide**: `docs/investigations/SAME_ORIGIN_API_IMPLEMENTATION.md`
- **Root Cause Analysis**: `docs/investigations/COOKIE_DOMAIN_ISSUE.md`
- **Settings Fix**: Commit 66efef5 (frontend graceful degradation)
- **Nginx Config**: `apps/web/nginx.conf` (already configured)