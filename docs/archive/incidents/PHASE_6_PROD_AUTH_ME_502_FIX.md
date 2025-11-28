# Phase 6: Production `/api/auth/me` 502 Fix

## Problem Summary

**Symptom**: Flaky authentication in production
- `https://applylens.app/api/auth/me` → **502 Bad Gateway**
- `https://applylens.app/api/auth/me?v=123` → **401 Unauthorized** (correct)
- `https://api.applylens.app/auth/me` → **401 Unauthorized** (correct)

**Impact**:
- Users see "Service Temporarily Unavailable" screen
- LoginGuard component enters retry loop
- Frontend appears broken even though backend is healthy

## Root Cause

The web container's nginx config had an **exact-match location block** for `/api/auth/me` that returned a hardcoded 502 error:

```nginx
# Guest auth stub (PROBLEMATIC)
location = /api/auth/me {
    # Dev/offline stub for testing without backend
    return 502;
}

# Normal API proxy (never reached for exact path)
location /api/ {
    proxy_pass http://applylens-api-prod:8000;
    # ...
}
```

### Why This Happened

The stub was originally added for development/testing scenarios where the backend might be offline. It was meant to provide a "graceful degradation" path but was accidentally deployed to production.

### Why It Was Flaky

nginx's exact-match behavior:

```
Request: GET /api/auth/me
Match: location = /api/auth/me  → return 502 (stub wins)

Request: GET /api/auth/me?v=123
No exact match (query string makes it different)
Fall through to: location /api/  → proxy to backend → 401
```

This created the illusion of randomness:
- Requests without query params → 502 (stub)
- Requests with query params → 401 (backend)
- Cache layers made it even more unpredictable

## Solution

### 1. Remove the Auth Stub

**File**: `apps/web/nginx.conf`

**Before**:
```nginx
# Guest auth stub
location = /api/auth/me {
    return 502;
}

location = /api/auth/csrf {
    add_header Content-Type application/json;
    return 200 '{"csrfToken":""}';
}

location /api/ {
    proxy_pass http://applylens-api-prod:8000;
    # ...
}
```

**After**:
```nginx
# Removed auth stubs - always proxy to backend

location /api/ {
    proxy_pass http://applylens-api-prod:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Why this works**:
- All `/api/*` requests now follow the same path
- Backend handles auth state correctly (401 when not logged in)
- No special cases or stub behavior

### 2. Rebuild Web Image

```bash
cd D:\ApplyLens\apps\web

# Build new image with incremented version
docker build -f Dockerfile.prod -t leoklemet/applylens-web:0.5.1 .

# Tag as latest
docker tag leoklemet/applylens-web:0.5.1 leoklemet/applylens-web:latest

# Push both tags
docker push leoklemet/applylens-web:0.5.1
docker push leoklemet/applylens-web:latest
```

### 3. Deploy to Production

```bash
cd D:\ApplyLens\infra

# Pull new image
docker compose -f docker-compose.prod.yml pull web

# Restart web container
docker compose -f docker-compose.prod.yml up -d web

# Verify
docker ps --filter "name=applylens-web-prod"
```

### 4. Verification

#### Test from inside web container

```bash
docker exec applylens-web-prod curl -s -w "\nStatus: %{http_code}\n" http://localhost/api/auth/me
```

**Expected**: `Status: 401` (not 502)

#### Test from production

```bash
# Without query param (previously returned 502)
curl -s -w "\nStatus: %{http_code}\n" https://applylens.app/api/auth/me

# With query param (always worked)
curl -s -w "\nStatus: %{http_code}\n" https://applylens.app/api/auth/me?v=123
```

**Expected**: Both return `Status: 401`

#### Test in browser

1. Open https://applylens.app
2. Open DevTools Network tab
3. Look for `GET https://applylens.app/api/auth/me`
4. Should see **401 Unauthorized** (not 502)
5. LoginGuard should show login button (not degraded state)

## Why This Fix Works

### Before: Two Code Paths

```
Request: /api/auth/me
    ↓
nginx location = /api/auth/me
    ↓
return 502 (STUB)
```

```
Request: /api/auth/me?v=123
    ↓
nginx location /api/
    ↓
proxy_pass → backend
    ↓
401 Unauthorized
```

### After: One Code Path

```
Request: /api/auth/me (with or without query)
    ↓
nginx location /api/
    ↓
proxy_pass → backend
    ↓
401 Unauthorized (if not logged in)
200 + user data (if logged in)
```

## Preventing Recurrence

### 1. Document Stub Purpose

If auth stubs are needed for dev, add comments explaining:

```nginx
# DEV ONLY: Auth stub for testing without backend
# DO NOT DEPLOY TO PRODUCTION
# location = /api/auth/me {
#     return 502;
# }
```

### 2. Use Environment-Specific Configs

```nginx
# In Dockerfile.prod
COPY nginx.prod.conf /etc/nginx/conf.d/default.conf

# In Dockerfile.dev
COPY nginx.dev.conf /etc/nginx/conf.d/default.conf
```

### 3. Add Health Check Test

Create a Playwright test that runs against production:

```typescript
// tests/prod-health.spec.ts
test("prod auth endpoint returns 401 not 502", async ({ request }) => {
  const response = await request.get("https://applylens.app/api/auth/me");
  expect(response.status()).toBe(401);  // Not 502!
});
```

Run before deploying:

```bash
npx playwright test tests/prod-health.spec.ts --project=chromium-prod
```

### 4. Monitor 502 Rate

Add Prometheus alert:

```yaml
alert: High502Rate
expr: |
  sum(rate(nginx_http_requests_total{status="502"}[5m]))
  / sum(rate(nginx_http_requests_total[5m])) > 0.01
for: 5m
annotations:
  summary: "502 rate above 1%"
  description: "Check nginx config for stubs or backend health"
```

## Related Issues

### Issue: CSRF Endpoint Stub

The original config also had a stub for `/api/auth/csrf`:

```nginx
location = /api/auth/csrf {
    add_header Content-Type application/json;
    return 200 '{"csrfToken":""}';
}
```

**Should we remove it?**

**Analysis**:
- This returns 200 (not an error)
- Empty CSRF token might cause issues with POST requests
- Better to proxy to backend for consistency

**Recommendation**: Remove this stub too and let backend handle CSRF generation.

### Issue: Cloudflare Cache

Even after fixing nginx, browsers might cache the 502 responses:

**Solution**:
```bash
# Clear Cloudflare cache
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {api_token}" \
  -H "Content-Type: application/json" \
  -d '{"purge_everything":true}'

# Or use dashboard: Caching → Configuration → Purge Everything
```

**User-side**: Clear browser cache or test in incognito mode

## Testing Checklist

After deploying the fix:

- [ ] `curl https://applylens.app/api/auth/me` returns 401 (not 502)
- [ ] `curl https://applylens.app/api/auth/me?v=123` returns 401
- [ ] `curl https://api.applylens.app/auth/me` returns 401
- [ ] Browser DevTools shows 401 for `/api/auth/me` requests
- [ ] LoginGuard shows "Sign In" button (not "Service Unavailable")
- [ ] After login, `/api/auth/me` returns 200 with user data
- [ ] Extension can authenticate successfully
- [ ] Prometheus shows 0 rate of 502 errors on `/api/auth/me`

## Timeline

- **Discovered**: November 17, 2025
- **Root cause identified**: nginx exact-match stub returning 502
- **Fix applied**: Removed stub from `apps/web/nginx.conf`
- **Deployed**: Image `leoklemet/applylens-web:0.5.1`
- **Verified**: All auth endpoints return 401/200 correctly

## Key Learnings

1. **Exact-match locations are dangerous**: `location =` has highest precedence and can override more general patterns
2. **Dev stubs shouldn't reach production**: Use separate configs for dev/prod
3. **Query params change location matching**: `/path` and `/path?foo=bar` are different to nginx
4. **Cache makes debugging hard**: Browser + Cloudflare cache can hide the real behavior
5. **Always test without cache**: Use `curl -H "Cache-Control: no-cache"` or incognito mode

## References

- [nginx location directive docs](http://nginx.org/en/docs/http/ngx_http_core_module.html#location)
- [LoginGuard component](../apps/web/src/pages/LoginGuard.tsx)
- [Auth endpoints](../services/api/app/routers/auth.py)
- [Cloudflare Tunnel setup](./APPLYLENS_ARCHITECTURE.md#cloudflare-tunnel)
