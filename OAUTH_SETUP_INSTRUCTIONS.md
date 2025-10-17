# OAuth Setup Instructions for ApplyLens Production

## ✅ Current Configuration Status

### Backend Configuration (VERIFIED)
The API is correctly configured and returns the proper OAuth callback URL:
```
https://applylens.app/api/auth/google/callback
```

### Environment Variables (infra/.env.prod)
```bash
PUBLIC_URL=https://applylens.app
GOOGLE_REDIRECT_URI=https://applylens.app/api/auth/google/callback
VITE_API_BASE=/api
WEB_BASE_PATH=/web/
CORS_ALLOW_ORIGINS=https://applylens.app,https://www.applylens.app
```

### Nginx Routing (CONFIGURED)
- Frontend: `https://applylens.app/web/`
- API: `https://applylens.app/api/*` → proxies to `http://api:8003/*`
- OAuth callback: `https://applylens.app/api/auth/google/callback` → `http://api:8003/auth/google/callback`

---

## ⚠️ REQUIRED ACTION: Update Google Cloud Console

### Step 1: Access Google Cloud Console
Navigate to: https://console.cloud.google.com/apis/credentials

### Step 2: Locate Your OAuth Client
Find the OAuth 2.0 Client ID:
```
813287438869-231mmrj2rhlu5n43amngca6ae5p72bhr.apps.googleusercontent.com
```

### Step 3: Edit OAuth Client Configuration
Click the **EDIT** button (pencil icon) next to your OAuth client.

### Step 4: Add Authorized Redirect URIs
In the **Authorized redirect URIs** section, add these exact URLs (one per line):

```
https://applylens.app/api/auth/google/callback
https://www.applylens.app/api/auth/google/callback
```

**Important Notes:**
- ✅ Must be HTTPS (not HTTP)
- ✅ Include `/api/auth/google/callback` path
- ✅ No trailing slash
- ✅ Add both `applylens.app` and `www.applylens.app` for flexibility

### Step 5: Add Authorized JavaScript Origins
In the **Authorized JavaScript origins** section, add:

```
https://applylens.app
https://www.applylens.app
```

**Important Notes:**
- ✅ Must be HTTPS
- ✅ No trailing slash
- ✅ These are the domains where your frontend runs

### Step 6: Save Changes
1. Click the **SAVE** button at the bottom
2. Wait **1-2 minutes** for Google's changes to propagate globally

---

## 🧪 Testing the OAuth Flow

### After Saving Google Console Changes:

1. **Clear Browser Cache** (important!)
   - Windows: `Ctrl + Shift + Delete`
   - Mac: `Cmd + Shift + Delete`

2. **Navigate to Application**
   ```
   https://applylens.app/web/
   ```

3. **Click Sign In with Google**
   - Should redirect to Google OAuth consent screen
   - After consent, should redirect back to `https://applylens.app/api/auth/google/callback`
   - Then redirect to the application dashboard

### Expected Flow:
```
User clicks "Sign in"
  ↓
Frontend: GET /api/auth/google/login
  ↓
Nginx: Proxy to http://api:8003/auth/google/login
  ↓
API: Returns 307 redirect to Google OAuth
  ↓
Google: User grants permissions
  ↓
Google: Redirects to https://applylens.app/api/auth/google/callback?code=...
  ↓
Nginx: Proxy to http://api:8003/auth/google/callback
  ↓
API: Exchanges code for tokens, creates session
  ↓
API: Redirects to https://applylens.app/web/
  ↓
User is logged in ✅
```

---

## 🔍 Troubleshooting

### Error: "redirect_uri_mismatch"
**Cause:** Google Console URIs don't match the API's redirect_uri

**Solution:**
1. Verify Google Console has exactly: `https://applylens.app/api/auth/google/callback`
2. Check for typos, extra slashes, or http vs https mismatches
3. Wait 1-2 minutes after saving in Google Console

### Error: "401 Unauthorized" or "403 Forbidden"
**Cause:** OAuth client credentials mismatch

**Solution:**
1. Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `infra/.env.prod`
2. Match them with values from Google Cloud Console

### Error: "CORS policy blocked"
**Cause:** JavaScript origin not authorized

**Solution:**
1. Add `https://applylens.app` to **Authorized JavaScript origins** in Google Console
2. Verify `CORS_ALLOW_ORIGINS` in `infra/.env.prod`

### Verify Configuration
```bash
# Check what redirect_uri the API is using
curl -I https://applylens.app/api/auth/google/login | grep -i location

# Should show a Google URL with redirect_uri=https%3A%2F%2Fapplylens.app%2Fapi%2Fauth%2Fgoogle%2Fcallback
```

---

## 📝 Summary Checklist

- [x] API configured with correct `GOOGLE_REDIRECT_URI`
- [x] Nginx proxying `/api/*` to backend
- [x] Environment variables set in `infra/.env.prod`
- [ ] **Google Console updated with redirect URIs** ← ACTION REQUIRED
- [ ] **Google Console updated with JavaScript origins** ← ACTION REQUIRED
- [ ] Tested OAuth flow after Google changes propagate

---

## 🚀 Deployment Status

All infrastructure is deployed and running:
- ✅ Cloudflare Tunnel connected (4 edges)
- ✅ Nginx routing configured correctly
- ✅ API backend healthy and responding
- ✅ Frontend serving at `/web/`
- ✅ Static assets loading correctly

**Only remaining step:** Update Google Cloud Console OAuth configuration!

---

## 📞 Support

If issues persist after updating Google Console:
1. Check API logs: `docker logs applylens-api-prod --tail 100`
2. Check nginx logs: `docker logs applylens-nginx-prod --tail 100`
3. Verify network routing: `docker network inspect applylens_applylens-prod`
