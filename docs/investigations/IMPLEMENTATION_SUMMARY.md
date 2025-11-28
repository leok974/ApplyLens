# Settings Page Auth Fix - Implementation Summary

**Branch:** `fix/auth-401-errors`
**Commits:** 4 commits (3ead4f5 → 66efef5)
**Status:** ✅ Complete - Ready for PR
**Tests:** 6/6 passing

---

## Problem Statement

Users visiting `/settings` when their session has expired (missing `applylens_session` cookie) would see **"Signed in as Loading..."** forever. The Settings page's `useEffect` called `fetchAndCacheCurrentUser()` but never handled the case where it returns `null` (indicating no authenticated session).

**Root Cause:** Cookie domain misconfiguration (documented in `COOKIE_DOMAIN_ISSUE.md`)

---

## Solution Implemented

### 1. Settings Page Fix (`apps/web/src/pages/Settings.tsx`)

**Added State Variables:**
- `isLoadingUser: boolean` - Track loading state
- `authError: string | null` - Track auth errors

**Updated useEffect Logic:**
```typescript
useEffect(() => {
  let cancelled = false

  async function loadUser() {
    try {
      // 1. Try cached user first (fast path)
      const cached = getCurrentUser()
      if (cached?.email) {
        setAccountEmail(cached.email)
        setIsLoadingUser(false)
        return
      }

      // 2. Fetch from API
      const fresh = await fetchAndCacheCurrentUser()

      if (cancelled) return

      // 🔑 NEW: Handle null user (session expired/missing)
      if (!fresh) {
        setAuthError('Session expired or missing.')
        navigate('/welcome', { replace: true })
        return
      }

      // 3. Handle edge case: user exists but no email
      if (fresh.email) {
        setAccountEmail(fresh.email)
      } else {
        setAuthError('Unable to load account information.')
        navigate('/welcome', { replace: true })
      }
    } catch (error) {
      // 4. Handle fetch errors
      console.error('[Settings] Failed to load current user:', error)
      if (!cancelled) {
        setAuthError('Unable to load account. Please log in again.')
        navigate('/welcome', { replace: true })
      }
    } finally {
      if (!cancelled) setIsLoadingUser(false)
    }
  }

  loadUser()
  return () => { cancelled = true }
}, [navigate])
```

**Added Render States:**
1. **Loading State:** Shows "Loading your settings…" while fetching
2. **Auth Error State:** Shows error message + "Go to sign-in" button
3. **Defensive Guard:** Fallback if `accountEmail` is still null after loading
4. **Normal State:** Existing Settings UI

---

### 2. Comprehensive Unit Tests (`apps/web/src/pages/Settings.test.tsx`)

**Test Coverage (6 tests):**

| Test | Purpose | Mocks | Assertions |
|------|---------|-------|------------|
| `redirects to /welcome when fetchAndCacheCurrentUser returns null` | **PRIMARY TEST** - Verifies core fix | `getCurrentUser()` → null<br>`fetchAndCacheCurrentUser()` → null | ✅ Shows loading initially<br>✅ Redirects to `/welcome`<br>✅ API called |
| `shows loading state while fetching user` | Loading UI test | Never-resolving promise | ✅ "Loading your settings…" displayed |
| `renders settings when user loaded from cache` | Fast path test | Cached user exists | ✅ Settings render immediately<br>✅ Email displayed<br>✅ API NOT called |
| `renders settings when user fetched from API` | API fetch test | API returns user | ✅ Loading → Settings<br>✅ Email displayed |
| `redirects when fetchAndCacheCurrentUser throws error` | Error handling test | API throws error | ✅ Redirects to `/welcome`<br>✅ Console error logged |
| `redirects when user exists but has no email` | Edge case test | User with `email: null` | ✅ Redirects to `/welcome` |

**Test Output:**
```
✓ Settings - Auth Failure Handling > redirects to /welcome when fetchAndCacheCurrentUser returns null (38ms)
✓ Settings - Auth Failure Handling > shows loading state while fetching user (3ms)
✓ Settings - Auth Failure Handling > renders settings when user is successfully loaded from cache (90ms)
✓ Settings - Auth Failure Handling > renders settings when user is successfully fetched from API (30ms)
✓ Settings - Auth Failure Handling > redirects when fetchAndCacheCurrentUser throws an error (14ms)
✓ Settings - Auth Failure Handling > redirects when user exists but has no email (16ms)

Test Files  1 passed (1)
     Tests  6 passed (6)
  Duration  1.56s
```

---

## Files Changed

| File | Status | Changes |
|------|--------|---------|
| `apps/web/src/pages/Settings.tsx` | Modified | +90 lines (added loading/error states, redirect logic) |
| `apps/web/src/pages/Settings.test.tsx` | New | +229 lines (6 comprehensive tests) |
| `patches/settings-auth-fix.tsx` | New | Reference implementation (for documentation) |

---

## Verification Steps

### Manual Testing:
1. ✅ Login normally → Settings page loads email
2. ✅ Clear `applylens_session` cookie (keep `csrf_token`) → Settings redirects to `/welcome`
3. ✅ Fast reload with cached user → No loading delay
4. ✅ Slow API response → Loading state visible

### Automated Testing:
```bash
cd apps/web
pnpm test Settings.test.tsx
# Result: 6/6 tests passing
```

---

## Deployment Notes

### Frontend Fix (This PR)
- ✅ **Immediate Impact:** Fixes infinite loading bug
- ✅ **User Experience:** Users redirected to login instead of stuck
- ✅ **Test Coverage:** Prevents regression

### Server-Side Cookie Fix (Separate Issue)
**Required for full resolution:** Backend team must deploy cookie domain fix
- File: `apps/api/src/main.py` (or equivalent SessionMiddleware config)
- Change: Add `domain=".applylens.app"` to session cookie settings
- See: `docs/investigations/COOKIE_DOMAIN_ISSUE.md` for full details

**Until server fix is deployed:**
- Users must login from `applylens.app` (not `api.applylens.app`)
- Logout/login required if session cookie is stored on wrong domain

---

## Related Documents

1. **`AUTH_401_INVESTIGATION.md`** - Initial network analysis
2. **`COOKIE_DOMAIN_ISSUE.md`** - Root cause identification (180 lines)
3. **`AUTH_401_FIX_SETTINGS.ts`** - Original code pattern (reference only)

---

## Commit History

```
66efef5 fix(settings): redirect to login when session missing
ff39f0c docs: identify cookie domain configuration issue
b35a387 docs: identify root cause of 401 errors - missing session cookie
3ead4f5 docs: add AUTH 401 investigation document
```

---

## Next Steps

1. ✅ **Push branch:** `git push origin fix/auth-401-errors`
2. ⏳ **Create PR:** Against `main` branch
3. ⏳ **Request review:** Tag frontend team + backend team
4. ⏳ **Merge & Deploy:** Frontend fix (this PR)
5. 📋 **Backend Issue:** Create ticket for cookie domain fix with reference to `COOKIE_DOMAIN_ISSUE.md`

---

## Success Criteria

**Frontend Fix (This PR):**
- ✅ Settings page detects missing auth
- ✅ Users redirected to `/welcome` instead of stuck on "Loading..."
- ✅ Unit tests prevent regression
- ✅ No infinite loading states

**Full Resolution (Requires Backend Deployment):**
- ⏸️ Session cookies include `Domain=.applylens.app` attribute
- ⏸️ Cross-subdomain authentication works correctly
- ⏸️ Users stay logged in after navigating between `applylens.app` ↔ `api.applylens.app`

---

**Prepared by:** GitHub Copilot
**Date:** 2025-01-24
**Branch:** `fix/auth-401-errors`
**Commits:** 4 total (investigation docs + implementation + tests)
