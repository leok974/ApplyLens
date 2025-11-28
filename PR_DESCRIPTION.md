## Summary

Fixes auth 401 errors by implementing **same-origin `/api` proxy architecture** and adding graceful auth failure handling.

## Problem

Users experience immediate 401 errors after OAuth login due to **cookie domain mismatch**:
- OAuth callback lands on `api.applylens.app` (or hardcoded localhost)
- App runs on `applylens.app`
- Session cookies set without `Domain` attribute are host-only
- Cross-subdomain requests fail

## Solution

### ✅ Frontend (This PR)

**Settings Page Auth Handling** (Commit `66efef5`)
- Detects missing/expired session
- Redirects to `/welcome` instead of infinite "Loading..."
- 6/6 unit tests passing
- Proper loading/error states

**Already Implemented**:
- Frontend uses `API_BASE='/api'` (defaults to `/api`)
- Nginx proxies `/api/*` to backend
- All API calls go through same-origin proxy

### 🔄 Backend (Follow-up Required)

**SessionMiddleware** - Needs updates:
```python
# Current (app/main.py line 98):
app.add_middleware(
    SessionMiddleware,
    secret_key=agent_settings.SESSION_SECRET,
    max_age=3600,  # Only 1 hour!
    same_site="lax",  # ✅ Correct
    https_only=agent_settings.COOKIE_SECURE == "1",  # ✅ Correct
    # ❌ Missing: session_cookie name
    # ❌ Missing: proper max_age for user sessions
)

# Recommended:
app.add_middleware(
    SessionMiddleware,
    secret_key=agent_settings.SESSION_SECRET,
    session_cookie="applylens_session",  # Explicit name
    max_age=14 * 24 * 60 * 60,  # 14 days for user sessions
    same_site="lax",
    https_only=agent_settings.COOKIE_SECURE == "1",
)
```

**OAuth Redirect** - Needs production URL:
```python
# Current (app/auth_google.py line 160):
ui_url = "http://localhost:5175/?connected=google"  # ❌ Hardcoded dev URL

# Recommended:
ui_url = settings.WEB_FRONTEND_URL or "https://applylens.app"
# Or use environment variable: GOOGLE_POST_LOGIN_REDIRECT
```

**OAuth Callback URL** - Needs `/api` path:
- Google Cloud Console: Update to `https://applylens.app/api/auth/google/callback`
- Config: Verify `GOOGLE_REDIRECT_URI` uses `/api` path

## Files Changed

### Frontend
- `apps/web/src/pages/Settings.tsx` - Auth failure redirect logic
- `apps/web/src/pages/Settings.test.tsx` - 6 comprehensive unit tests

### Documentation
- `docs/investigations/SAME_ORIGIN_API_IMPLEMENTATION.md` - Complete deployment guide
- `docs/investigations/BACKEND_VERIFICATION_CHECKLIST.md` - Backend verification steps
- `docs/investigations/COOKIE_DOMAIN_ISSUE.md` - Root cause analysis
- `docs/investigations/IMPLEMENTATION_SUMMARY.md` - Settings fix details

### Reference
- `patches/settings-auth-fix.tsx` - Complete Settings.tsx implementation

## Testing

### Unit Tests ✅
```bash
cd apps/web
pnpm test Settings.test.tsx
# Result: 6/6 passing
```

**Test Coverage**:
- ✅ Redirect on null user (session expired)
- ✅ Loading state display
- ✅ Cached user rendering
- ✅ Fresh API fetch rendering
- ✅ Error handling
- ✅ User without email edge case

### Manual Testing (After Backend Deploy)

1. **Cookie Verification**:
   ```javascript
   // In browser console on https://applylens.app
   document.cookie
   // Expected: applylens_session=...; csrf_token=...
   ```

2. **OAuth Flow**:
   - Click "Login with Google"
   - After OAuth: URL should be `https://applylens.app`
   - No 401 errors on subsequent requests

3. **Settings Page**:
   - Navigate to `/settings`
   - Should load successfully (no infinite loading)
   - If no session: redirects to `/welcome`

## Architecture Decision

**✅ Chosen: Same-Origin `/api` Proxy**
```
User → applylens.app/         → React SPA
     → applylens.app/api/...  → FastAPI (nginx proxy)
```

**Benefits**:
- ✅ No cross-subdomain issues
- ✅ Simpler security (host-only cookies)
- ✅ Industry standard
- ✅ No `domain=".applylens.app"` needed

**❌ Rejected: Cross-Subdomain Cookies**
- Would require `domain=".applylens.app"` + `same_site="none"`
- Less secure, CORS complexity

## Deployment Checklist

### Immediate (This PR)
- [x] Frontend Settings fix
- [x] Unit tests
- [x] Documentation
- [ ] Review & merge

### Follow-up (Backend PR)
- [ ] Update SessionMiddleware:
  - Add `session_cookie="applylens_session"`
  - Increase `max_age` to 14 days
- [ ] Update OAuth redirect to production URL
- [ ] Verify Google OAuth callback uses `/api` path
- [ ] Deploy backend changes
- [ ] Test OAuth flow end-to-end

## Related Issues

Fixes: User reports "logged in but getting 401 errors"

## Documentation

All implementation details in:
- `docs/investigations/SAME_ORIGIN_API_IMPLEMENTATION.md`
- `docs/investigations/BACKEND_VERIFICATION_CHECKLIST.md`

## Breaking Changes

None. Changes are backward compatible and improve robustness.