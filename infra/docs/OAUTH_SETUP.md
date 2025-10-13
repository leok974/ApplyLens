# Google OAuth Setup Guide

Complete guide to configuring Google OAuth for ApplyLens to eliminate `redirect_uri_mismatch` errors.

---

## 🎯 Overview

This guide covers:

- Creating OAuth 2.0 credentials in Google Cloud Console
- Configuring authorized redirect URIs and origins
- Setting up environment variables for local and production
- Troubleshooting common OAuth errors

---

## Prerequisites

- Google Cloud account with billing enabled
- Access to Google Cloud Console
- Admin access to ApplyLens deployment

---

## Step 1: Create OAuth 2.0 Credentials

### 1.1 Navigate to Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to **APIs & Services** → **Credentials**

### 1.2 Configure OAuth Consent Screen

If you haven't already configured the OAuth consent screen:

1. Click **OAuth consent screen** in the left sidebar
2. Select **External** user type (or **Internal** if using Google Workspace)
3. Click **Create**

**Required Information:**

- **App name**: ApplyLens
- **User support email**: Your email address
- **App logo**: (Optional) Upload ApplyLens logo
- **Application home page**: `https://applylens.app`
- **Application privacy policy link**: `https://applylens.app/privacy`
- **Application terms of service link**: `https://applylens.app/terms`
- **Authorized domains**:
  - `applylens.app`
  - `localhost` (for local development)
- **Developer contact information**: Your email address

4. Click **Save and Continue**

**Scopes:**
Add the following scopes:

- `https://www.googleapis.com/auth/gmail.readonly` - Read Gmail messages
- `https://www.googleapis.com/auth/userinfo.email` - See your email address
- `openid` - Authenticate using OpenID Connect

5. Click **Save and Continue**
6. Add test users (if app is in testing mode)
7. Click **Save and Continue**
8. Review and click **Back to Dashboard**

### 1.3 Create OAuth Client ID

1. Click **Credentials** in the left sidebar
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Select **Application type**: **Web application**
4. **Name**: ApplyLens OAuth Client

---

## Step 2: Configure Authorized Redirect URIs

**CRITICAL**: The redirect URIs must **exactly match** the URIs used by your application.

### Production Environment

Add these **Authorized redirect URIs**:

```
https://api.applylens.app/auth/google/callback
https://applylens.app/auth/google/callback
https://www.applylens.app/auth/google/callback
```

**Note**:

- Use `https://api.applylens.app/auth/google/callback` if your backend handles the OAuth callback
- Use `https://applylens.app/auth/google/callback` if your frontend (SPA) handles the callback
- ApplyLens uses **backend callback** by default

### Development Environment

Add these **Authorized redirect URIs** for local development:

```
http://localhost:8003/auth/google/callback
http://localhost:5175/auth/google/callback
http://127.0.0.1:8003/auth/google/callback
```

**Ports**:

- `8003` - API server (FastAPI)
- `5175` - Web frontend (Vite/React)

### Full Configuration Screenshot

Your final configuration should look like this:

```
Authorized JavaScript origins:
  https://applylens.app
  https://www.applylens.app
  http://localhost:5175
  http://localhost:8003

Authorized redirect URIs:
  https://api.applylens.app/auth/google/callback
  https://applylens.app/auth/google/callback
  https://www.applylens.app/auth/google/callback
  http://localhost:8003/auth/google/callback
  http://localhost:5175/auth/google/callback
  http://127.0.0.1:8003/auth/google/callback
```

---

## Step 3: Configure Authorized JavaScript Origins

Add these **Authorized JavaScript origins**:

### Production

```
https://applylens.app
https://www.applylens.app
```

### Development

```
http://localhost:5175
http://localhost:8003
http://127.0.0.1:5175
```

---

## Step 4: Download Credentials

1. Click **Create** to save the OAuth client
2. A dialog will appear with your **Client ID** and **Client Secret**
3. Click **Download JSON** to download the credentials file
4. Save the file as `google.json`

**Security Note**: Keep this file secure and never commit it to version control!

---

## Step 5: Configure Environment Variables

### Local Development (.env)

1. Copy the example environment file:

   ```bash
   cd infra
   cp .env.example .env
   ```

2. Edit `.env` and add your OAuth credentials:

   ```bash
   # Google OAuth Client Credentials
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   
   # OAuth Redirect URI (local development)
   GOOGLE_REDIRECT_URI_DEV=http://localhost:8003/auth/google/callback
   
   # OAuth State Secret (generate a random 32+ character string)
   OAUTH_STATE_SECRET=your-random-32-character-or-longer-string
   
   # Legacy OAuth config (backward compatibility)
   OAUTH_REDIRECT_URI=http://localhost:8003/auth/google/callback
   
   # Google credentials file
   GOOGLE_CREDENTIALS=/secrets/google.json
   
   # OAuth scopes
   GOOGLE_OAUTH_SCOPES=https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email openid
   ```

3. Copy your `google.json` file to the secrets directory:

   ```bash
   cp /path/to/google.json infra/secrets/google.json
   ```

4. Generate a random OAuth state secret:

   ```bash
   # Using OpenSSL
   openssl rand -hex 32
   
   # Or using Python
   python -c "import secrets; print(secrets.token_hex(32))"
   
   # Or using PowerShell
   -join ((1..32) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
   ```

### Production (.env.prod)

1. Copy the production example:

   ```bash
   cd infra
   cp .env.prod.example .env.prod
   ```

2. Edit `.env.prod` with production values:

   ```bash
   # Google OAuth Client Credentials
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   
   # OAuth Redirect URI (production)
   GOOGLE_REDIRECT_URI=https://api.applylens.app/auth/google/callback
   
   # OAuth State Secret (MUST be different from dev!)
   OAUTH_STATE_SECRET=production-random-32-character-or-longer-string
   
   # Legacy OAuth config (backward compatibility)
   OAUTH_REDIRECT_URI=https://api.applylens.app/auth/google/callback
   
   # Google credentials file
   GOOGLE_CREDENTIALS=/secrets/google.json
   
   # OAuth scopes
   GOOGLE_OAUTH_SCOPES=https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email openid
   ```

---

## Step 6: Verify Configuration

### 6.1 Check Environment Variables

Run this command to verify your settings are loaded:

```bash
# Local development
docker compose -f infra/docker-compose.yml exec api python -c "
from app.settings import settings
print(f'Client ID: {settings.GOOGLE_CLIENT_ID[:20]}...')
print(f'Redirect URI: {settings.effective_redirect_uri}')
print(f'Scopes: {settings.GOOGLE_OAUTH_SCOPES}')
"
```

### 6.2 Test OAuth Flow

1. Start the application:

   ```bash
   cd infra
   docker compose up -d
   ```

2. Open your browser and navigate to:

   ```
   http://localhost:8003/auth/google/login
   ```

3. You should be redirected to Google's OAuth consent screen
4. After granting permissions, you'll be redirected back to:

   ```
   http://localhost:8003/auth/google/callback?code=...&state=...
   ```

5. If successful, you'll be redirected to the ApplyLens inbox

### 6.3 Run Smoke Tests

Run the automated smoke tests to verify OAuth configuration:

```powershell
# PowerShell
.\scripts\smoke-applylens.ps1

# Check for OAuth test results
# ✅ PASS: OAuth login redirects to Google (HTTP 302)
# ✅ PASS: Redirect URI parameter present in OAuth URL
# ✅ PASS: Client ID parameter present in OAuth URL
# ✅ PASS: OAuth callback route is accessible
```

---

## Troubleshooting

### Error: redirect_uri_mismatch

**Symptom:**

```
Error 400: redirect_uri_mismatch
The redirect URI in the request, http://localhost:8003/auth/google/callback, 
does not match the ones authorized for the OAuth client.
```

**Causes:**

1. Redirect URI not added to Google Cloud Console
2. Typo in redirect URI (trailing slash, http vs https, port mismatch)
3. Environment variable not set or incorrect
4. Nginx rewriting the redirect URI

**Solutions:**

1. **Verify Google Cloud Console Configuration:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
   - Click on your OAuth client ID
   - Check that the **exact** redirect URI is listed under **Authorized redirect URIs**
   - If using `http://localhost:8003/auth/google/callback`, ensure it's listed exactly (no trailing slash)

2. **Check Environment Variables:**

   ```bash
   # Print current redirect URI
   docker compose exec api python -c "
   from app.settings import settings
   print(f'Redirect URI: {settings.effective_redirect_uri}')
   "
   ```

3. **Verify Nginx Configuration:**
   - Check `infra/nginx/conf.d/applylens.conf`
   - Ensure `/auth/google/` routes are **not** rewritten
   - Restart Nginx after changes:

     ```bash
     docker compose restart nginx
     ```

4. **Check Application Logs:**

   ```bash
   # View API logs
   docker compose logs -f api
   
   # Look for OAuth debug messages:
   # [OAuth] Initiating login flow with redirect_uri: http://localhost:8003/auth/google/callback
   # [OAuth] Callback received with redirect_uri: http://localhost:8003/auth/google/callback
   ```

5. **Test with curl:**

   ```bash
   # Test login endpoint
   curl -I http://localhost:8003/auth/google/login
   
   # Should return 302 redirect to accounts.google.com
   # Check Location header for redirect_uri parameter
   ```

### Error: invalid_client

**Symptom:**

```
Error 401: invalid_client
The OAuth client was not found.
```

**Solution:**

1. Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set correctly
2. Check that credentials match the ones from Google Cloud Console
3. Ensure `google.json` file exists at `/secrets/google.json` in the container

### Error: access_denied

**Symptom:**

```
Error: access_denied
The user denied your request
```

**Solution:**

1. User clicked "Cancel" on the OAuth consent screen
2. Ensure all required scopes are enabled in Google Cloud Console
3. If app is in "Testing" mode, verify the user is added as a test user

### Error: invalid_grant

**Symptom:**

```
Error: invalid_grant
The provided authorization grant is invalid, expired, or revoked
```

**Solution:**

1. OAuth code expired (codes are valid for ~10 minutes)
2. Code already used (can only be exchanged once)
3. Clear browser cache and try again
4. Revoke access and re-authorize: <https://myaccount.google.com/permissions>

---

## Architecture Notes

### Backend OAuth Flow (Current Implementation)

ApplyLens uses **backend OAuth flow** where the FastAPI backend handles the OAuth callback:

```
User → /auth/google/login (FastAPI)
  ↓
Google OAuth Consent Screen
  ↓
User grants permission
  ↓
Google redirects to: https://api.applylens.app/auth/google/callback?code=...
  ↓
FastAPI backend exchanges code for tokens
  ↓
Tokens stored in database
  ↓
User redirected to: /inbox?connected=google
```

**Redirect URI**: `https://api.applylens.app/auth/google/callback`

### Frontend OAuth Flow (Alternative)

If you want the frontend to handle OAuth:

1. Update `GOOGLE_REDIRECT_URI` to point to frontend:

   ```bash
   GOOGLE_REDIRECT_URI=https://applylens.app/auth/google/callback
   ```

2. Add frontend callback route in React:

   ```typescript
   // src/pages/AuthCallback.tsx
   useEffect(() => {
     const code = new URLSearchParams(location.search).get('code');
     if (code) {
       // Send code to backend for token exchange
       fetch('/api/auth/google/exchange', {
         method: 'POST',
         body: JSON.stringify({ code })
       });
     }
   }, []);
   ```

3. Update Google Cloud Console with frontend redirect URI

---

## Security Best Practices

### 1. Secure State Parameter

The `OAUTH_STATE_SECRET` is used to prevent CSRF attacks:

- **MUST** be at least 32 characters
- **MUST** be random and unpredictable
- **MUST** be different in production vs development
- **NEVER** commit to version control

### 2. Secure Credentials Storage

- Store `google.json` in `/secrets/` directory
- Add `/secrets/` to `.gitignore`
- Use environment variables for client ID/secret
- Never log credentials

### 3. HTTPS in Production

- **ALWAYS** use HTTPS in production
- Redirect HTTP to HTTPS
- Use secure cookies (`COOKIE_SECURE=1`)
- Enable HSTS headers

### 4. Scope Minimization

Only request scopes you need:

- `gmail.readonly` - Read-only access to Gmail
- `userinfo.email` - User's email address
- `openid` - OpenID Connect authentication

**Do NOT request**:

- `gmail.modify` - Allows modifying emails
- `gmail.send` - Allows sending emails
- Unnecessary profile scopes

### 5. Token Refresh

- Store refresh tokens securely in database
- Refresh access tokens before expiry
- Implement token revocation on logout

---

## Testing Checklist

Before deploying to production:

- [ ] OAuth credentials created in Google Cloud Console
- [ ] Authorized redirect URIs configured (prod + dev)
- [ ] Authorized JavaScript origins configured
- [ ] `google.json` file copied to `/secrets/`
- [ ] `GOOGLE_CLIENT_ID` set in environment
- [ ] `GOOGLE_CLIENT_SECRET` set in environment
- [ ] `GOOGLE_REDIRECT_URI` set for production
- [ ] `GOOGLE_REDIRECT_URI_DEV` set for development
- [ ] `OAUTH_STATE_SECRET` generated (32+ characters)
- [ ] Nginx configuration allows `/auth/google/` routes
- [ ] Application logs show correct redirect_uri
- [ ] Manual OAuth flow completes successfully
- [ ] Smoke tests pass for OAuth endpoints
- [ ] Tokens stored in database after authorization
- [ ] User can access Gmail inbox after connecting

---

## Reference Links

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)
- [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
- [Gmail API Scopes](https://developers.google.com/gmail/api/auth/scopes)

---

## Support

If you encounter issues:

1. Check application logs: `docker compose logs -f api`
2. Run smoke tests: `.\scripts\smoke-applylens.ps1`
3. Verify environment variables are loaded
4. Check Nginx configuration for URL rewriting
5. Review Google Cloud Console settings

For additional help, see:

- `PHASE_2_IMPLEMENTATION.md` - API documentation
- `DEPLOYMENT.md` - Production deployment guide
- GitHub Issues: <https://github.com/yourusername/applylens/issues>

---

**Last Updated**: 2025-10-11  
**Version**: 1.0  
**Status**: Production Ready
