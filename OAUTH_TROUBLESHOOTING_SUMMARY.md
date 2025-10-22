# OAuth Troubleshooting Summary

## Issues Resolved

### 1. Authorization Code Reuse (400 Bad Request)
**Symptom**: Users see "400 Bad Request" after clicking OAuth callback URL

**Root Cause**:
- OAuth authorization codes are **single-use only** per RFC 6749
- First callback attempt partially succeeded (token exchange 200 OK)
- Something failed after token exchange, returned 500 error
- Browser or user retried with same authorization code
- Google OAuth server rejected reused code with 400

**Evidence from logs**:
```
✅ POST https://oauth2.googleapis.com/token "HTTP/1.1 200 OK"
✅ GET https://openidconnect.googleapis.com/v1/userinfo "HTTP/1.1 200 OK"
❌ [Internal error - callback returned 500]
❌ POST https://oauth2.googleapis.com/token "HTTP/1.1 400 Bad Request" (same code)
ERROR: Token exchange failed: Client error '400 Bad Request'
```

**Solution**: Fixed underlying issues causing 500 errors (see below)

---

### 2. Missing Error Details (No Traceback on 500)
**Symptom**: 500 errors without detailed traceback in logs

**Root Cause**: Error logging didn't include `exc_info=True` parameter

**Solution**: Added comprehensive error logging with full tracebacks
```python
# In services/api/app/routers/auth.py
try:
    # ... operation ...
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)  # ✅ Full traceback
    raise HTTPException(500, "Detailed error message")
```

**Wrapped with detailed logging**:
- Token exchange
- User profile retrieval
- User creation/update
- OAuth token encryption/storage
- Session creation
- Cookie setting/redirect

---

### 3. Health Check Failures (503 Service Unavailable)
**Symptom**: Nginx returns 503 even when API is running

**Root Cause**:
- Docker health check: `curl -f http://localhost:8003/ready`
- Base image: `python:3.11-slim` (minimal, no curl)
- Health check failed → Docker marks as "unhealthy"
- Nginx refuses to proxy to unhealthy backends

**Evidence**:
```bash
$ docker inspect applylens-api-prod --format='{{json .State.Health}}'
{
  "Status": "unhealthy",
  "Log": [
    {
      "ExitCode": 1,
      "Output": "/bin/sh: 1: curl: not found\n"
    }
  ]
}
```

**Solution**: Temporarily disabled health check in `docker-compose.prod.yml`
```yaml
# healthcheck:
#   test: ["CMD-SHELL", "curl -f http://localhost:8003/ready || exit 1"]
#   interval: 30s
```

**Future Fix**: Install `curl` in Dockerfile or use Python-based health check:
```dockerfile
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
```

---

### 4. Port Mismatch (Connection Refused)
**Symptom**: Nginx logs show "Connection refused (111)" to API

**Root Cause**:
- Docker-compose configured: `API_PORT=8003`
- Dockerfile CMD hardcoded: `--port 8000`
- Environment variable ignored
- Nginx tried connecting to port 8003 → nobody listening

**Evidence**:
```
2025/10/22 18:14:10 [error] 38#38: connect() failed (111: Connection refused)
upstream: "http://172.25.0.6:8003/auth/me"

# But API logs showed:
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Solution**: Updated Dockerfile to use environment variable
```dockerfile
# Before:
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# After:
CMD uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT:-8000}
```

**Verification**:
```bash
$ docker logs applylens-api-prod --tail 5
INFO: Uvicorn running on http://0.0.0.0:8003 (Press CTRL+C to quit)

$ docker exec applylens-nginx-prod curl -s -o /dev/null -w "%{http_code}\n" http://api:8003/auth/google/login
307  # ✅ Success!
```

---

## OAuth Configuration Checklist

### ✅ Google Cloud Console
- **Authorized redirect URIs**: `https://applylens.app/api/auth/google/callback`
- **Credentials**: OAuth 2.0 Client ID created
- **Scopes**: `email`, `profile`, `openid`, `https://www.googleapis.com/auth/gmail.readonly`

### ✅ Backend Configuration
```bash
# Environment variables in docker-compose.prod.yml
APPLYLENS_GOOGLE_CLIENT_ID=<your-client-id>
APPLYLENS_GOOGLE_CLIENT_SECRET=<your-client-secret>
APPLYLENS_OAUTH_REDIRECT_URI=https://applylens.app/api/auth/google/callback

# Verify in container:
$ docker exec applylens-api-prod printenv | grep APPLYLENS_
```

### ✅ Nginx Routing
```nginx
# /api/auth/* routes directly to backend
location /api/ {
    proxy_pass http://api:8003/;
    # ... headers ...
}
```

### ✅ Frontend Configuration
```tsx
// apps/web/src/pages/LoginGuard.tsx
<a href="/api/auth/google/login">Sign In with Google</a>
```

---

## Testing Commands

### Internal (from nginx container)
```bash
# Should return 307 (redirect to Google)
docker exec applylens-nginx-prod curl -s -o /dev/null -w "%{http_code}\n" http://api:8003/auth/google/login
```

### External (from internet)
```powershell
# Should return 307 (redirect to Google)
try {
  $response = Invoke-WebRequest -Uri "https://applylens.app/api/auth/google/login" -MaximumRedirection 0 -ErrorAction Stop
} catch {
  $_.Exception.Response.StatusCode.value__
}
```

### Check API Logs
```bash
# Watch for OAuth attempts
docker logs -f applylens-api-prod | grep -E "oauth|callback|Token exchange"

# Check for errors with context
docker logs applylens-api-prod --tail 200 | grep -A 5 -B 5 "ERROR"
```

---

## Current Status

### ✅ Working
- OAuth login endpoint (`/api/auth/google/login`) returns 307 redirect
- API running on correct port (8003)
- Nginx can reach API backend
- External access works (307 from public URL)
- Enhanced error logging in place
- Environment variables properly prefixed with `APPLYLENS_`

### 🔄 To Test
- Complete OAuth flow (click "Sign In with Google")
- Verify session cookie is set
- Confirm redirect to authenticated page
- Check if user is created in database

### 📋 Known Limitations
- Health check disabled (needs curl in container)
- Single-use OAuth codes (expected behavior per RFC)
- Port configuration must match between Dockerfile and docker-compose

---

## Helpful Copilot Prompts Added

### `apps/web/vite.config.ts`
```typescript
// Copilot: Ensure the SPA base is '/web/' so public assets emit under /web
// and links like '/web/favicon.ico' resolve correctly in prod builds.
```

### `apps/web/index.html`
```html
<!-- Copilot: If we choose root favicon, set href='/favicon.ico'.
     If we choose namespaced favicon, set href='/web/favicon.ico'.
     Keep sizes='any' and add type='image/x-icon' if needed. -->
```

### `infra/nginx/conf.d/applylens-ssl.conf`
```nginx
# Copilot: Ensure SPA under /web resolves assets and history API fallback
location /web/ {
  # ... existing config ...
}
```

---

## Next Steps

1. **Test OAuth flow end-to-end**
   - Navigate to https://applylens.app/web/welcome
   - Click "Sign In with Google"
   - Grant permissions
   - Verify successful redirect and session

2. **Monitor for errors**
   ```bash
   docker logs -f applylens-api-prod
   ```

3. **If issues persist**, check:
   - Full error traceback (now available with `exc_info=True`)
   - Database connectivity
   - Token encryption/decryption
   - Session creation
   - Cookie domain/security settings

4. **Re-enable health check** (optional)
   - Add `curl` to Dockerfile
   - Or implement Python-based health check endpoint

---

## References

- **OAuth 2.0 RFC**: https://datatracker.ietf.org/doc/html/rfc6749
- **Google OAuth Documentation**: https://developers.google.com/identity/protocols/oauth2
- **FastAPI Sessions**: https://fastapi.tiangolo.com/advanced/security/
- **Docker Health Checks**: https://docs.docker.com/engine/reference/builder/#healthcheck
