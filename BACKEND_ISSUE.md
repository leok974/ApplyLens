# Backend Changes for Same-Origin /api Implementation

## Current Status

**Frontend**: ✅ Ready (uses `/api`, Settings page handles auth failures)
**Nginx**: ✅ Ready (proxies `/api/*` to backend)
**Backend**: 🔄 Needs Updates (SessionMiddleware & OAuth redirect)

## Required Changes

### 1. SessionMiddleware Configuration

**File**: `services/api/app/main.py` (line 97-103)

**Current**:
```python
app.add_middleware(
    SessionMiddleware,
    secret_key=agent_settings.SESSION_SECRET,
    max_age=3600,  # Only 1 hour
    same_site="lax",
    https_only=agent_settings.COOKIE_SECURE == "1",
)
```

**Required**:
```python
app.add_middleware(
    SessionMiddleware,
    secret_key=agent_settings.SESSION_SECRET,
    session_cookie="applylens_session",  # ← ADD: Explicit cookie name
    max_age=14 * 24 * 60 * 60,          # ← CHANGE: 14 days (not 1 hour)
    same_site="lax",                     # ✅ Keep
    https_only=agent_settings.COOKIE_SECURE == "1",  # ✅ Keep
    # NO domain parameter (host-only cookies for same-origin)
)
```

**Why**:
- `session_cookie`: Frontend expects specific cookie name
- `max_age`: User sessions should last weeks, not 1 hour
- `same_site="lax"`: Correct for same-origin `/api`
- NO `domain`: Host-only cookies work for same-origin proxy

### 2. OAuth Post-Login Redirect

**File**: `services/api/app/auth_google.py` (line 160)

**Current**:
```python
# Hardcoded dev URL
ui_url = "http://localhost:5175/?connected=google"
return RedirectResponse(ui_url)
```

**Required**:
```python
# Use environment variable for production
ui_url = agent_settings.WEB_FRONTEND_URL or "https://applylens.app"
# Optional: add success parameter
if "?" not in ui_url:
    ui_url = f"{ui_url}/?connected=google"
return RedirectResponse(ui_url)
```

**Add to config** (`services/api/app/config.py` or `settings.py`):
```python
WEB_FRONTEND_URL: str = "https://applylens.app"  # Override in .env for dev
```

**Environment variable** (`.env`):
```bash
# Development
WEB_FRONTEND_URL=http://localhost:5175

# Production
WEB_FRONTEND_URL=https://applylens.app
```

### 3. OAuth Callback URL Verification

**File**: `services/api/app/settings.py` (line 101) or environment

**Current**:
```python
OAUTH_REDIRECT_URI = "http://localhost:5175/auth/google/callback"
```

**Required for production**:
```python
OAUTH_REDIRECT_URI = "https://applylens.app/api/auth/google/callback"
#                                              ^^^^ Must include /api
```

**Environment variable** (production `.env`):
```bash
GOOGLE_REDIRECT_URI=https://applylens.app/api/auth/google/callback
```

**Google Cloud Console**: 
- Update Authorized redirect URIs to: `https://applylens.app/api/auth/google/callback`
- Remove old: `https://api.applylens.app/auth/google/callback` (if exists)

## Testing After Deployment

### 1. Cookie Verification
```bash
# In browser console on https://applylens.app
document.cookie
# Should see: applylens_session=...; csrf_token=...
```

### 2. OAuth Flow Test
```bash
# 1. Click "Login with Google"
# 2. After OAuth: should redirect to https://applylens.app (not localhost or api subdomain)
# 3. Check browser DevTools → Application → Cookies
#    - Domain should be: applylens.app (not api.applylens.app)
#    - Name should be: applylens_session
#    - Max-Age should be: 1209600 (14 days in seconds)
```

### 3. Session Persistence
```bash
# 1. Login successfully
# 2. Navigate to /settings
# 3. Should load user email (not redirect to /welcome)
# 4. Check Network tab: /api/auth/me should return 200 OK
```

### 4. API Endpoint Test
```bash
# Verify session cookie is sent
curl -i https://applylens.app/api/auth/me \
  -H "Cookie: applylens_session=<session_value>"
# Should return 200 OK with user JSON
```

## Rollback Plan

If issues occur:

1. **Quick Fix**: Revert to cross-subdomain cookies
   ```python
   # Temporary workaround (not recommended)
   app.add_middleware(
       SessionMiddleware,
       domain=".applylens.app",  # Share across subdomains
       same_site="none",         # Required for cross-origin
       # ... rest of config
   )
   ```

2. **Full Rollback**: 
   ```bash
   git revert <commit-hash>
   docker build && docker push
   kubectl rollout undo deployment/applylens-api
   ```

## Related Documentation

- **Implementation Guide**: `docs/investigations/SAME_ORIGIN_API_IMPLEMENTATION.md`
- **Verification Steps**: `docs/investigations/BACKEND_VERIFICATION_CHECKLIST.md`
- **Root Cause**: `docs/investigations/COOKIE_DOMAIN_ISSUE.md`
- **Frontend PR**: #XX (Settings page auth handling)

## Acceptance Criteria

- [ ] SessionMiddleware has explicit `session_cookie` name
- [ ] Session `max_age` is 14 days (not 1 hour)
- [ ] OAuth redirects to production URL (not localhost)
- [ ] Google OAuth callback uses `/api` path
- [ ] Cookies are set for `applylens.app` domain
- [ ] OAuth flow works end-to-end in production
- [ ] No 401 errors on Settings page
- [ ] Session persists for 14 days

## Priority

**HIGH** - Blocks production authentication

## Estimated Effort

2-3 hours (code changes + testing + deployment)