# 🎯 Final Diagnosis & Fix - OAuth 403/400 Errors

**Date:** October 22, 2025, 9:25 PM
**Status:** Root cause identified, fixes documented

---

## ✅ **Good News: CSRF Already Implemented!**

The frontend **already has CSRF token support**:
- ✅ `getCsrfToken()` function reads from `csrf_token` cookie
- ✅ `backfillGmail()` includes CSRF token in `X-CSRF-Token` header
- ✅ `post()` helper also includes CSRF token

**Code Location:** `apps/web/src/lib/api.ts`

```typescript
function getCsrfToken(): string | null {
  const match = document.cookie.match(/csrf_token=([^;]+)/)
  return match ? match[1] : null
}

export async function backfillGmail(days = 60, userEmail?: string): Promise<BackfillResponse> {
  const csrfToken = getCsrfToken()
  const headers: HeadersInit = {}
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken
  }

  const r = await fetch(url, {
    method: 'POST',
    headers
  })
  // ...
}
```

---

## 🔍 **The Real Problem**

### Issue #1: CSRF Cookie Not Set (403 Forbidden)

**Symptom:**
```
WARNING:app.core.csrf:CSRF failure: Missing X-CSRF-Token header for POST /gmail/backfill
INFO: "POST /gmail/backfill?days=2" 403 Forbidden
```

**Root Cause:** CSRF cookie not set in browser yet

**Why?** The CSRF middleware sets the cookie on **every response**, but if the user hasn't made any requests yet (or cookies were cleared), the cookie doesn't exist.

**Fix:** Ensure user makes at least one request before attempting backfill (e.g., visiting the inbox page first)

**Alternative Fix:** Add a dedicated CSRF endpoint to explicitly set the cookie:

```python
# In services/api/app/auth_google.py or similar
from app.core.csrf import issue_csrf_cookie

@router.get("/csrf")
def get_csrf_token(response: Response):
    """Issue CSRF token cookie"""
    issue_csrf_cookie(response)
    return {"csrf": "issued"}
```

Then call it on app load:
```typescript
// In app initialization
await fetch('/api/auth/csrf')
```

---

### Issue #2: invalid_grant Error (400 Bad Request)

**Symptom:**
```
ERROR:app.routes_gmail:Backfill exception: ('invalid_grant: Bad Request', {'error': 'invalid_grant', 'error_description': 'Bad Request'})
google.auth.exceptions.RefreshError: ('invalid_grant: Bad Request', ...)
INFO: "POST /gmail/backfill?days=7 HTTP/1.1" 400 Bad Request
```

**Root Cause:** OAuth app in **Testing mode** → tokens expire immediately or after 7 days

**Timeline:**
- 21:16 PM - User authenticated, token saved
- 21:20 PM - Token already invalid (4 minutes later!)

**Why Testing Mode Causes This:**
- Google restricts Testing mode apps
- Tokens may expire immediately for users not explicitly added as "test users"
- Even added test users get 7-day token expiration

**Critical Fix Required:** **Publish OAuth app to Production**

---

## 🚀 **Complete Fix Guide**

### Fix #1: Publish OAuth App to Production (CRITICAL)

**Steps:**

1. **Go to Google Cloud Console:**
   https://console.cloud.google.com

2. **Navigate to:**
   - APIs & Services → OAuth consent screen

3. **Check Current Status:**
   - Look for "Publishing status" section
   - If it says **"Testing"** → Continue to step 4
   - If it says **"Production"** → Already good, skip to Fix #2

4. **Publish the App:**
   - Click **"PUBLISH APP"** button
   - Confirm the publishing

5. **Verify Redirect URIs:**
   - Click "Credentials" in left sidebar
   - Find your OAuth 2.0 Client ID
   - Click to edit
   - Ensure **Authorized redirect URIs** includes:
     - `https://applylens.app/api/auth/google/callback`
     - `https://applylens.app/api/oauth/google/callback`

6. **Verify Scopes:**
   - Go back to OAuth consent screen
   - Check "Scopes" section includes:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `openid`
     - `email`
     - `profile`

7. **Save Changes**

**Expected Result:** OAuth app now in Production mode, tokens don't expire

---

### Fix #2: Ensure CSRF Cookie is Set

**Option A: Add CSRF Endpoint (Recommended)**

Add to `services/api/app/auth_google.py`:

```python
from fastapi import Response
from app.core.csrf import issue_csrf_cookie

@router.get("/csrf")
def get_csrf_token(response: Response):
    """Explicitly issue CSRF token cookie for frontend"""
    issue_csrf_cookie(response)
    return {"status": "csrf_issued"}
```

Then call in frontend app initialization (`apps/web/src/App.tsx` or similar):

```typescript
useEffect(() => {
  // Ensure CSRF cookie is set on app load
  fetch('/api/auth/csrf').catch(() => {})
}, [])
```

**Option B: Visit Inbox First**

Simpler but less robust: Just ensure user visits the inbox page (which makes a GET request) before clicking "Sync Emails". The CSRF middleware will set the cookie on that response.

---

### Fix #3: Re-authenticate After Publishing

**Steps:**

1. **Delete old invalid token:**
   ```powershell
   docker exec applylens-db-prod psql -U postgres -d applylens `
     -c "DELETE FROM oauth_tokens WHERE user_email='leoklemet.pa@gmail.com';"
   ```
   **Expected:** `DELETE 1`

2. **Clear browser cookies:**
   - Open browser DevTools (F12)
   - Application tab → Cookies → https://applylens.app
   - Delete all cookies (or just `csrf_token` and session cookies)

3. **Re-authenticate:**
   - Go to: https://applylens.app/web/welcome
   - Click "Sign in with Google"
   - Accept permissions (consent screen will show)
   - You'll be redirected back to ApplyLens

4. **Verify new token:**
   ```powershell
   docker exec applylens-db-prod psql -U postgres -d applylens `
     -c "SELECT user_email, updated_at, refresh_token IS NOT NULL as has_refresh FROM oauth_tokens;"
   ```
   **Expected:** Shows your email with fresh timestamp

---

## 🧪 **Testing After Fixes**

### Step 1: Verify OAuth App Published
- Google Cloud Console → OAuth consent screen
- **Publishing status** should show **"Production"**

### Step 2: Verify Token Valid
```powershell
docker exec applylens-db-prod psql -U postgres -d applylens `
  -c "SELECT user_email, updated_at FROM oauth_tokens ORDER BY updated_at DESC LIMIT 1;"
```
**Expected:** Shows recent timestamp (< 5 minutes ago)

### Step 3: Test Gmail Sync from UI
1. Go to: https://applylens.app/inbox (or similar)
2. Click "Sync Emails" button
3. Wait for response

**Expected Results:**
- ✅ **Success:** Banner shows "Synced X emails"
- ❌ **429 Rate Limit:** "Try again in X seconds" (wait 5 minutes)
- ❌ **Still 403:** CSRF cookie not set (implement Fix #2)
- ❌ **Still 400:** OAuth app still in Testing mode (repeat Fix #1)

### Step 4: Monitor Logs
```powershell
# Watch for errors in real-time
docker logs -f applylens-api-prod | Select-String "gmail|backfill|invalid_grant|CSRF|403|400"
```

**Expected (Success):**
```
INFO: "POST /gmail/backfill?days=7 HTTP/1.1" 200 OK
```

**Expected (Rate Limited - OK):**
```
INFO: "POST /gmail/backfill?days=7 HTTP/1.1" 429 Too Many Requests
```

**Not Expected (Errors):**
```
ERROR: invalid_grant
WARNING: CSRF failure
```

### Step 5: Verify Emails Synced
```powershell
docker exec applylens-db-prod psql -U postgres -d applylens `
  -c "SELECT COUNT(*) as total_emails FROM emails WHERE gmail_id IS NOT NULL;"
```
**Expected:** Count > 0

---

## 📊 **Decision Tree**

```
Click "Sync Emails"
        ↓
    403 Forbidden?
    ├─ YES → CSRF cookie missing
    │        → Implement Fix #2 (CSRF endpoint)
    │        → OR visit inbox first
    │
    └─ NO → 400 Bad Request?
           ├─ YES → Check logs for "invalid_grant"
           │        ├─ YES → OAuth app in Testing mode
           │        │        → Implement Fix #1 (Publish app)
           │        │        → Then Fix #3 (Re-auth)
           │        │
           │        └─ NO → Different 400 error
           │                 → Check logs for specific error
           │                 → May be validation/parameter issue
           │
           └─ NO → 429 Rate Limited?
                  ├─ YES → Wait 5 minutes, expected behavior
                  │
                  └─ NO → 200 OK?
                         ├─ YES → ✅ Success!
                         │
                         └─ NO → Check logs for unexpected error
```

---

## 🎯 **Quick Fix Checklist**

### Immediate (Do Now)
- [ ] **Publish OAuth app to Production** (Google Cloud Console)
- [ ] **Delete old token** (`DELETE FROM oauth_tokens...`)
- [ ] **Re-authenticate** at https://applylens.app/web/welcome
- [ ] **Test sync** from UI

### Short-term (Next Development Session)
- [ ] **Add `/api/auth/csrf` endpoint** for explicit cookie setting
- [ ] **Call CSRF endpoint** on app initialization
- [ ] **Add better error handling** in frontend for 403/400 responses
- [ ] **Show specific error messages** to user

### Long-term (Future Improvements)
- [ ] **Implement auto-retry** logic for rate limits
- [ ] **Add token expiration monitoring**
- [ ] **Implement token rotation** schedule
- [ ] **Add admin dashboard** for OAuth status

---

## 📋 **Summary**

### Current Issues
1. ✅ CSRF implementation exists in frontend
2. ❌ CSRF cookie not set consistently (403 errors)
3. ❌ OAuth app in Testing mode (400 invalid_grant errors)

### Required Fixes
1. **CRITICAL:** Publish OAuth app to Production
2. **HIGH:** Ensure CSRF cookie set (add endpoint or visit page first)
3. **MEDIUM:** Re-authenticate after publishing

### Expected Outcome
- ✅ OAuth tokens valid indefinitely (Production mode)
- ✅ CSRF validation passes
- ✅ Gmail sync succeeds with 200 OK
- ✅ Emails synced to database and Elasticsearch

---

## 🔗 **Related Documentation**

- **DIAGNOSTIC_RESULTS_OAUTH_403_400.md** - Detailed diagnostic results
- **OAUTH_REAUTH_GUIDE.md** - Re-authentication steps
- **OAUTH_FIX_IMPLEMENTATION_SUMMARY.md** - Code changes made
- **OAUTH_QUICK_START.md** - Quick reference guide

---

**Next Action:**
1. **Go to Google Cloud Console**
2. **Publish OAuth app**
3. **Re-authenticate**
4. **Test sync**

---

**Diagnostic Date:** October 22, 2025, 9:25 PM
**Root Cause:** OAuth app in Testing mode + CSRF cookie not consistently set
**Fix Priority:** CRITICAL (blocks all Gmail functionality)
**Estimated Fix Time:** 10 minutes (OAuth publishing + re-auth)
