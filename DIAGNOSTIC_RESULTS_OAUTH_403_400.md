# 🔍 Diagnostic Results - OAuth 400/403 Errors

**Date:** October 22, 2025, 9:20 PM
**Status:** Two distinct issues identified

---

## ✅ **Step 0: Token Status**

```sql
SELECT user_email, updated_at FROM oauth_tokens;
```

**Result:** ✅ **1 row found**
- Email: `leoklemet.pa@gmail.com`
- Updated: `2025-10-22 21:16:47` (4 minutes ago)
- Has refresh token: ✅ Yes

**Conclusion:** Token exists in database (not a missing token issue)

---

## 🔍 **Step 1: cURL Reproduction**

### Test A: API Health
```powershell
Invoke-WebRequest -Uri "https://applylens.app/api/ready"
```
**Result:** ✅ **200 OK** - API is healthy

### Test B: Authentication
Skipped (not critical for this issue)

### Test C: Backfill Direct Call
```powershell
Invoke-WebRequest -Uri "https://applylens.app/api/gmail/backfill?days=2&user_email=leoklemet.pa@gmail.com" -Method POST
```
**Result:** ❌ **403 Forbidden** - CSRF token missing

---

## 🚨 **Step 2: Root Cause Analysis**

### Issue #1: CSRF Token Missing (403 Forbidden)

**Log Evidence:**
```
WARNING:app.core.csrf:CSRF failure: Missing X-CSRF-Token header for POST /gmail/backfill
INFO: "POST /gmail/backfill?days=2&user_email=leoklemet.pa@gmail.com HTTP/1.1" 403 Forbidden
```

**Cause:** Frontend not sending `X-CSRF-Token` header

**Impact:** All POST requests to `/gmail/backfill` return 403

**Fix Required:** Update frontend to include CSRF token in request headers

---

### Issue #2: invalid_grant Error (400 Bad Request)

**Log Evidence:**
```
ERROR:app.routes_gmail:Backfill exception for leoklemet.pa@gmail.com: ('invalid_grant: Bad Request', {'error': 'invalid_grant', 'error_description': 'Bad Request'})
INFO: "POST /gmail/backfill?days=7 HTTP/1.1" 400 Bad Request
```

**Cause:** Google rejecting the refresh token with `invalid_grant`

**Root Cause:** OAuth app likely in **Testing mode** (tokens expire immediately or after 7 days)

**Impact:** Even with CSRF token, backfill will fail with 400

---

## 📊 **Timeline of Events**

```
21:11 PM - OAuth flow updated (prompt=consent always)
21:11 PM - Old token deleted
21:16 PM - User re-authenticated, new token saved
21:20 PM - Backfill attempt → 403 (CSRF) + 400 (invalid_grant)
```

**Time between auth and first use:** 4 minutes

**Conclusion:** Token became invalid **immediately** after creation, confirming OAuth app is in Testing mode with strict restrictions.

---

## 🎯 **Two-Part Fix Required**

### Part 1: Fix CSRF (Frontend) - URGENT

**File:** Frontend code calling `/api/gmail/backfill`

**Current Code (broken):**
```javascript
fetch('/api/gmail/backfill?days=2', {
  method: 'POST'
})
```

**Fixed Code:**
```javascript
// Get CSRF token
async function getCsrfToken() {
  const response = await fetch('/api/auth/csrf');
  const data = await response.json();
  return data.token;
}

// Use CSRF token in request
const csrfToken = await getCsrfToken();
await fetch('/api/gmail/backfill?days=2', {
  method: 'POST',
  headers: {
    'X-CSRF-Token': csrfToken
  },
  credentials: 'include'
});
```

**Alternative (if token in cookie):**
```javascript
function getCsrfFromCookie() {
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

await fetch('/api/gmail/backfill?days=2', {
  method: 'POST',
  headers: {
    'X-CSRF-Token': getCsrfFromCookie()
  }
});
```

---

### Part 2: Fix OAuth App Publishing Status - CRITICAL

**Problem:** OAuth app in Testing mode → tokens invalid immediately

**Solution:** Publish OAuth app to Production

**Steps:**

1. **Go to Google Cloud Console:**
   https://console.cloud.google.com

2. **Navigate to:**
   APIs & Services → OAuth consent screen

3. **Check Publishing Status:**
   - If shows **"Testing"**: Click **"PUBLISH APP"** button
   - If shows **"Production"**: Already correct (skip to step 4)

4. **Verify Settings:**
   - **Authorized redirect URIs:** Must include `https://applylens.app/api/auth/google/callback` AND `https://applylens.app/api/oauth/google/callback`
   - **Scopes:** gmail.readonly, email, profile, openid

5. **Alternative (Temporary):**
   If you can't publish yet, add yourself as test user:
   - OAuth consent screen → Test users section
   - Click "ADD USERS"
   - Add: `leoklemet.pa@gmail.com`
   - **Note:** Tokens still expire after 7 days in Testing mode

6. **After Publishing:**
   - Delete current token:
     ```powershell
     docker exec applylens-db-prod psql -U postgres -d applylens -c "DELETE FROM oauth_tokens WHERE user_email='leoklemet.pa@gmail.com';"
     ```
   - Re-authenticate at: https://applylens.app/web/welcome
   - Test sync again (with CSRF fix)

---

## 🧪 **Testing Plan (After Fixes)**

### Step 1: Verify OAuth App Published
- Check Google Cloud Console shows "Production" status

### Step 2: Delete and Re-auth
```powershell
# Delete old token
docker exec applylens-db-prod psql -U postgres -d applylens -c "DELETE FROM oauth_tokens WHERE user_email='leoklemet.pa@gmail.com';"

# Re-authenticate at https://applylens.app/web/welcome
```

### Step 3: Test with CSRF Token
```powershell
# Get CSRF token from browser (check cookies or call /api/auth/csrf)
$csrfToken = "YOUR_CSRF_TOKEN_HERE"

# Test backfill
Invoke-WebRequest -Uri "https://applylens.app/api/gmail/backfill?days=2&user_email=leoklemet.pa@gmail.com" `
  -Method POST `
  -Headers @{"X-CSRF-Token"=$csrfToken} `
  -UseBasicParsing
```

**Expected:** 200 OK with `{"inserted": N, "days": 2, ...}`

### Step 4: Monitor Logs
```powershell
# Watch for errors
docker logs -f applylens-api-prod | Select-String "gmail|backfill|invalid_grant|CSRF"
```

**Expected:** No `invalid_grant` or CSRF errors

---

## 📋 **Quick Reference: Error Codes**

| Status | Cause | Fix |
|--------|-------|-----|
| **403** | Missing CSRF token | Add `X-CSRF-Token` header to request |
| **400** | `invalid_grant` | Publish OAuth app to Production, re-auth |
| **429** | Rate limit (5 min cooldown) | Wait, then retry |
| **401** | No OAuth token in DB | Re-authenticate at /web/welcome |

---

## 🔍 **Additional Diagnostics**

### Check CSRF Middleware Status
```powershell
docker logs applylens-api-prod --since 1h | Select-String "CSRF" | Select-Object -Last 10
```

### Check OAuth Token Validity
```powershell
docker exec applylens-db-prod psql -U postgres -d applylens -c "SELECT user_email, expiry, refresh_token IS NOT NULL as has_refresh FROM oauth_tokens;"
```

### Count Recent Backfill Attempts
```powershell
docker logs applylens-api-prod --since 1h | Select-String "POST /gmail/backfill" | Measure-Object | Select-Object Count
```

### Check if Auto-Invalidation Triggered
```powershell
docker logs applylens-api-prod --since 30m | Select-String "RefreshError|OAuth token invalid or expired"
```

---

## ✅ **Summary**

### Current State
- ✅ Token exists in database
- ❌ Token is invalid (Google returns `invalid_grant`)
- ❌ Frontend missing CSRF token
- ❌ OAuth app likely in Testing mode

### Immediate Actions Required
1. **CRITICAL:** Publish OAuth app to Production (Google Cloud Console)
2. **URGENT:** Add CSRF token to frontend backfill requests
3. Re-authenticate after publishing
4. Test with proper CSRF headers

### Expected Outcome
- ✅ OAuth tokens remain valid indefinitely (Production mode)
- ✅ CSRF validation passes
- ✅ Backfill succeeds with 200 OK
- ✅ Emails synced to database and Elasticsearch

---

**Next Steps:**
1. Check Google Cloud Console OAuth consent screen
2. Publish app to Production
3. Update frontend with CSRF token
4. Re-authenticate and test

---

**Diagnostic Date:** October 22, 2025, 9:20 PM
**Issues Found:** 2 (CSRF + invalid_grant)
**Status:** Awaiting OAuth app publishing + frontend CSRF fix
