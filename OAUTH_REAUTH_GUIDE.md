# OAuth Re-Authentication Guide - October 22, 2025, 9:11 PM

## ✅ **Automatic Token Invalidation Implemented**

The API now **automatically detects and deletes invalid OAuth tokens**, prompting users to re-authenticate.

### How It Works

When a `google.auth.exceptions.RefreshError` occurs (invalid_grant, etc.):
1. ✅ **Detect** the error in `_get_creds()`
2. ✅ **Delete** the invalid token from database
3. ✅ **Prompt** user with clear message: "Please re-authenticate at /api/auth/google/login"

**Code Location:** `services/api/app/gmail_service.py` → `_get_creds()` function

---

## 🚀 **Re-Authentication Steps**

### Step 1: Visit ApplyLens
Navigate to: **https://applylens.app/web/welcome**

### Step 2: Sign In with Google
Click **"Sign in with Google"** button

**What happens:**
- Redirects to Google OAuth consent screen
- With `prompt=consent`, you'll ALWAYS see the consent screen
- This guarantees a fresh refresh token

### Step 3: Grant Permissions
Accept the following permissions:
- ✅ Read your email messages and settings
- ✅ View your email address
- ✅ View your basic profile info

### Step 4: Verify Token Saved
Run this command to confirm:

```powershell
docker exec applylens-db-prod psql -U postgres -d applylens `
  -c "SELECT user_email, created_at, updated_at FROM oauth_tokens ORDER BY updated_at DESC LIMIT 3;"
```

**Expected Output:**
```
      user_email       |         created_at         |         updated_at
-----------------------+----------------------------+----------------------------
 leoklemet.pa@gmail.com| 2025-10-22 21:11:00.123456 | 2025-10-22 21:11:00.123456
```

---

## 🧪 **Test Gmail Sync**

### Using cURL (from PowerShell)

```powershell
# Get your user email (if needed)
$userEmail = "leoklemet.pa@gmail.com"

# Test Gmail sync (backfill last 2 days)
curl -s -X POST "https://applylens.app/api/gmail/backfill?days=2&user_email=$userEmail" `
  -w "\nHTTP Status: %{http_code}\n"
```

### Expected Responses

#### ✅ **Success (200)**
```json
{
  "inserted": 42,
  "days": 2,
  "user_email": "leoklemet.pa@gmail.com"
}
HTTP Status: 200
```

#### ⚠️ **Rate Limited (429)**
```json
{
  "detail": "Backfill too frequent; try again in 287 seconds."
}
HTTP Status: 429
```
**Solution:** Wait 5 minutes between sync attempts

#### ❌ **OAuth Error (400) - Auto-Fixed**
```json
{
  "detail": "OAuth token invalid or expired. Please re-authenticate at /api/auth/google/login"
}
HTTP Status: 400
```
**What happened:**
1. API tried to refresh token
2. Google returned `invalid_grant`
3. API automatically deleted the bad token
4. API prompted you to re-authenticate

**Solution:** Re-authenticate at https://applylens.app/web/welcome

---

## 🔍 **Troubleshooting**

### Issue 1: Token Not Saved After Re-Auth

**Symptom:** Database shows 0 rows after signing in

**Check OAuth callback logs:**
```powershell
docker logs applylens-api-prod --tail 50 | Select-String "OAuth|callback|token"
```

**Possible Causes:**
- OAuth callback failed
- Redirect URI mismatch
- Google Cloud Console misconfiguration

**Solution:** Check Google Cloud Console redirect URI matches:
```
https://applylens.app/api/auth/google/callback
```

### Issue 2: Consent Screen Doesn't Appear

**This shouldn't happen** with `prompt=consent`, but if it does:

**Revoke app access manually:**
1. Go to: https://myaccount.google.com/permissions
2. Find "ApplyLens"
3. Click **"Remove Access"**
4. Try authenticating again

### Issue 3: Still Getting invalid_grant

**Check OAuth app publishing status:**

1. Go to: https://console.cloud.google.com
2. Navigate to: **APIs & Services** → **OAuth consent screen**
3. Check **Publishing status**:
   - If **"Testing"**: Tokens expire after 7 days
   - If **"Production"**: Tokens don't expire

**Options:**
- **A. Publish to Production** (recommended)
  - Click **"PUBLISH APP"** button
  - Tokens will be valid indefinitely

- **B. Add yourself as test user**
  - Scroll to **"Test users"** section
  - Click **"ADD USERS"**
  - Add: `leoklemet.pa@gmail.com`
  - Tokens valid for 7 days (renewable)

### Issue 4: Different Error After Auto-Delete

**Check detailed logs:**
```powershell
docker logs -f applylens-api-prod | Select-String "error|exception|traceback" -Context 3
```

**Report errors with:**
- Full error message
- Timestamp
- Request details (endpoint, parameters)

---

## 📊 **Verification Commands**

### Check Token Status
```powershell
docker exec applylens-db-prod psql -U postgres -d applylens `
  -c "SELECT user_email, refresh_token IS NOT NULL as has_refresh, expiry, updated_at FROM oauth_tokens;"
```

### Check Gmail Connection Status
```powershell
curl "https://applylens.app/api/gmail/status?user_email=leoklemet.pa@gmail.com"
```

**Expected Response:**
```json
{
  "connected": true,
  "user_email": "leoklemet.pa@gmail.com",
  "provider": "google",
  "has_refresh_token": true,
  "total": 0
}
```

### Check Email Count in Database
```powershell
docker exec applylens-db-prod psql -U postgres -d applylens `
  -c "SELECT COUNT(*) as total_emails FROM emails WHERE gmail_id IS NOT NULL;"
```

### Monitor Sync in Real-Time
```powershell
docker logs -f applylens-api-prod | Select-String "Backfill|gmail|inserted"
```

---

## 🎯 **Quick Reference**

| Step | Command | Expected Result |
|------|---------|----------------|
| 1. Delete old token | `docker exec applylens-db-prod psql -U postgres -d applylens -c "DELETE FROM oauth_tokens WHERE user_email='leoklemet.pa@gmail.com';"` | `DELETE 1` or `DELETE 0` |
| 2. Re-authenticate | Visit https://applylens.app/web/welcome | Redirects to Google consent |
| 3. Verify token | `docker exec applylens-db-prod psql -U postgres -d applylens -c "SELECT user_email FROM oauth_tokens;"` | Shows your email |
| 4. Test sync | `curl -X POST "https://applylens.app/api/gmail/backfill?days=2"` | Returns `{"inserted": N, ...}` |

---

## 🛡️ **Security Improvements**

### Automatic Token Cleanup
✅ Invalid tokens are automatically deleted
✅ Users get clear re-authentication prompts
✅ No stale credentials left in database

### Fresh Tokens Every Time
✅ `prompt=consent` forces consent screen
✅ Guarantees new refresh token on each auth
✅ Reduces token expiration issues

### Better Error Messages
✅ Clear instructions: "re-authenticate at /api/auth/google/login"
✅ Specific error types handled separately
✅ Detailed logging for debugging

---

## 📚 **Related Documentation**

- **OAuth Flow Update:** `OAUTH_REFRESH_TOKEN_FIX.md`
- **OAuth Diagnostics:** `OAUTH_INVALID_GRANT_DIAGNOSTIC.md`
- **Rate Limiting:** `RATE_LIMIT_429.md`
- **API Restart:** `API_RESTART_SUMMARY.md`

---

## 🎉 **Summary**

✅ **Automatic token invalidation** implemented
✅ **OAuth flow updated** to always request fresh tokens
✅ **API rebuilt and restarted** with new code
✅ **Ready for re-authentication**

**Next Action:** Visit **https://applylens.app/web/welcome** and sign in with Google!

---

**Updated:** October 22, 2025, 9:11 PM
**Status:** Ready for testing
**Feature:** Auto-delete invalid tokens + prompt re-auth
