# API Route Policy & Trailing Slash Reference

## Overview

This document defines the canonical trailing slash policy for all API routes. This policy prevents FastAPI redirect loops and ensures consistent behavior.

## The Problem

**Root Cause of v0.4.5-v0.4.11 Issues:**

1. **Relative URL Resolution**: `fetch('/api/search')` → browser resolves relative to current page `/web/` → becomes `/web/api/search`
2. **Nginx SPA Fallback**: No route `/web/api/` → serves `index.html` (HTML)
3. **JSON Parsing Error**: Frontend expects JSON, gets HTML → "Unexpected token '<'"

**Fix v0.4.10**: Use absolute URLs via `apiUrl()` helper

4. **FastAPI Trailing Slash Redirects**: `/api/search` (no slash) → FastAPI redirects to `/search/` (relative Location header)
5. **Nginx Proxy Pass**: `/api/` → `http://api:8003/` strips `/api` prefix from redirects
6. **Redirect Loop**: Browser follows redirect to `/web/search/` → HTML again

**Fix v0.4.11 (FAILED)**: Add trailing slash to ALL `/api/*` routes
- Problem: `/api/auth/me/` → FastAPI redirects to `/me` (no slash) → loses `/api` prefix

**Fix v0.4.12 (SUCCESS)**: Selective trailing slash - only for routes that need it

## Trailing Slash Policy

### Routes WITH Trailing Slash (FastAPI defines with `/`)

| Route | FastAPI Definition | apiUrl() Output | Reason |
|-------|-------------------|-----------------|--------|
| `/api/search` | `@router.get("/search/")` | `/api/search/` | FastAPI has `/search/` route |
| `/api/emails` | `@router.get("/emails/")` | `/api/emails/` | FastAPI has `/emails/` route |
| `/api/applications` | `@router.get("/applications/")` | `/api/applications/` | FastAPI has `/applications/` route |

### Routes WITHOUT Trailing Slash (FastAPI defines without `/`)

| Route | FastAPI Definition | apiUrl() Output | Reason |
|-------|-------------------|-----------------|--------|
| `/api/auth/me` | `@router.get("/me")` | `/api/auth/me` | FastAPI has `/me` route (no slash) |
| `/api/auth/session` | `@router.get("/session")` | `/api/auth/session` | FastAPI has `/session` route (no slash) |
| `/api/auth/login` | `@router.post("/login")` | `/api/auth/login` | FastAPI has `/login` route (no slash) |

## Implementation

### Frontend: `apiUrl()` Helper

**Location**: `apps/web/src/lib/apiUrl.ts`

```typescript
export function apiUrl(path: string, params?: URLSearchParams): string {
  let p = path.startsWith('/') ? path : `/${path}`

  // Selective trailing slash - only for routes that need it
  const needsTrailingSlash = [
    '/api/search',
    '/api/emails',
    '/api/applications',
  ]

  if (needsTrailingSlash.some(route => p.startsWith(route)) && !p.endsWith('/')) {
    p = `${p}/`
  }

  const url = new URL(p, window.location.origin)
  if (params) url.search = params.toString()
  return url.toString()
}
```

**Usage**:
```typescript
// Search (adds trailing slash)
fetch(apiUrl('/api/search', new URLSearchParams({ q: 'Interview' })))
// → https://applylens.app/api/search/?q=Interview

// Auth (no trailing slash)
fetch(apiUrl('/api/auth/me'))
// → https://applylens.app/api/auth/me
```

### Nginx: Route Priority

**Location**: `apps/web/nginx.conf`

```nginx
# API routes FIRST (with ^~ for exact matching, highest priority)
location ^~ /api/ {
  proxy_pass http://api:8003/;
  proxy_intercept_errors off;  # CRITICAL: Don't map API 401/403 to index.html
  # ... proxy headers ...
}

# Immutable assets (1 year cache)
location ~* ^/assets/.*\.(js|css|woff|woff2)$ {
  expires 1y;
  add_header Cache-Control "public, max-age=31536000, immutable" always;
}

# HTML (no cache - always fetch fresh asset hashes)
location = /index.html {
  add_header Cache-Control "no-cache, no-store, must-revalidate" always;
}

# SPA fallback LAST (after all specific routes)
location / {
  try_files $uri /index.html;
}
```

**Critical Setting**: `proxy_intercept_errors off;`
- Without this, nginx maps API 401/403 responses to `index.html` (HTML)
- With this, API errors return JSON as intended

## Adding New Routes

When adding a new API route, follow these steps:

### 1. Check FastAPI Definition

```python
# Has trailing slash → add to needsTrailingSlash list
@router.get("/new-endpoint/")
def new_endpoint():
    return {"data": "..."}

# No trailing slash → use as-is (don't add to list)
@router.get("/new-endpoint")
def new_endpoint():
    return {"data": "..."}
```

### 2. Update apiUrl() if Needed

If FastAPI has trailing slash, add to `needsTrailingSlash`:

```typescript
const needsTrailingSlash = [
  '/api/search',
  '/api/emails',
  '/api/applications',
  '/api/new-endpoint',  // ← Add here
]
```

### 3. Test with E2E

Add test to `apps/web/tests/e2e/api-routes.spec.ts`:

```typescript
test('new-endpoint: /api/new-endpoint/ (with slash) returns JSON', async ({ request }) => {
  const res = await request.get('/api/new-endpoint/?param=value', {
    maxRedirects: 0,
    failOnStatusCode: false,
  });

  // Should not redirect
  expect(res.status()).not.toBeGreaterThanOrEqual(300);
  expect(res.status()).not.toBeLessThan(400);

  // Should return JSON
  expect([200, 204, 401, 403]).toContain(res.status());
  if (res.status() !== 204) {
    const ct = res.headers()['content-type'] || '';
    expect(ct).toContain('application/json');
  }
});
```

### 4. Run Sanity Check

```powershell
.\scripts\verify-api-routes.ps1 -BaseUrl "https://applylens.app"
```

## Error Handling Best Practices

### Frontend: Always Check Content-Type

```typescript
const res = await fetch(apiUrl('/api/endpoint'), {
  credentials: 'include',
  redirect: 'manual'  // Don't follow redirects automatically
})

// Handle redirects (treat as error)
if (res.status >= 300 && res.status < 400) {
  console.warn('Unexpected redirect', res.headers.get('location'))
  throw new Error('API redirect detected')
}

// Check content-type BEFORE parsing
const ct = res.headers.get('content-type') || ''
if (!ct.includes('application/json') && res.status !== 204) {
  const body = (await res.text()).slice(0, 200)
  console.error('Non-JSON response', { url: res.url, status: res.status, ct, body })
  throw new Error(`Expected JSON but got ${ct}`)
}

// Safe to parse now
const data = res.status === 204 ? null : await res.json()
```

### Example: LoginGuard

See `apps/web/src/pages/LoginGuard.tsx` for a production example:

```typescript
async function getMe(signal?: AbortSignal): Promise<Me | "degraded"> {
  try {
    const r = await fetch(apiUrl("/api/auth/me"), {
      credentials: "include",
      signal,
      redirect: "manual", // Never follow redirects
    });

    // 3xx: Treat as unauthenticated (don't follow to HTML login page)
    if (r.status >= 300 && r.status < 400) {
      console.warn('[LoginGuard] Redirect detected')
      return null
    }

    // 401/403: Stable unauthenticated state
    if (r.status === 401 || r.status === 403) {
      return null
    }

    // Check content-type before parsing JSON
    const ct = r.headers.get('content-type') || ''
    if (!ct.includes('application/json')) {
      console.error('[LoginGuard] Non-JSON response')
      return null  // Treat as unauthenticated, don't crash
    }

    return await r.json()
  } catch (err) {
    // Network error → degraded state (retry)
    return "degraded"
  }
}
```

## Testing

### E2E Tests (@prodSafe)

Run tests tagged with `@prodSafe` after every deployment:

```bash
pnpm test:e2e --grep @prodSafe
```

Tests verify:
1. Routes with trailing slashes don't redirect
2. Routes without trailing slashes don't redirect
3. All API responses are JSON (or 204), never HTML
4. No redirect loops occur

### Manual Verification

```powershell
# Test trailing slash routes
curl -I "https://applylens.app/api/search/?q=test"
# Expected: 200/204/401 (not 307 redirect)

# Test no-slash routes
curl -I "https://applylens.app/api/auth/me"
# Expected: 200/401 (not 307 redirect)

# Sanity check all routes
.\scripts\verify-api-routes.ps1
```

## Troubleshooting

### "Unexpected token '<'" Error

**Symptom**: `Unexpected token '<', "<!doctype "... is not valid JSON`

**Cause**: Frontend received HTML instead of JSON

**Debug Steps**:
1. Check browser Network tab → find failing request
2. Check Response body → is it HTML?
3. Check Response URL → did it redirect? (should be same as Request URL)
4. Check `apiUrl()` output → does it have correct trailing slash?

**Common Causes**:
- Route not in `needsTrailingSlash` list but FastAPI has `/` route
- Route in `needsTrailingSlash` list but FastAPI has no-slash route
- Nginx serving `index.html` for API errors (`proxy_intercept_errors on`)

### 307 Redirect Loop

**Symptom**: API request redirects to HTML page

**Cause**: Trailing slash mismatch between frontend and FastAPI

**Fix**:
1. Check FastAPI route definition (with or without `/`)
2. Update `needsTrailingSlash` list in `apiUrl.ts`
3. Rebuild and deploy

### Nginx Returns HTML for API Errors

**Symptom**: 401/403 responses contain HTML instead of JSON

**Cause**: `proxy_intercept_errors` not disabled

**Fix**:
1. Add `proxy_intercept_errors off;` to `/api/` location
2. Rebuild nginx container
3. Verify with `curl -I https://applylens.app/api/auth/me`

## Version History

- **v0.4.5**: Original bug - HTML instead of JSON
- **v0.4.10**: Fixed with `apiUrl()` helper (absolute URLs)
- **v0.4.11**: Added universal trailing slash → broke auth
- **v0.4.12**: Selective trailing slash → fixed all routes ✅

## References

- LoginGuard: `apps/web/src/pages/LoginGuard.tsx`
- apiUrl helper: `apps/web/src/lib/apiUrl.ts`
- Nginx config: `apps/web/nginx.conf`
- E2E tests: `apps/web/tests/e2e/api-routes.spec.ts`
- Sanity check: `scripts/verify-api-routes.ps1`
