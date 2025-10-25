# Deployment v0.4.10 - Permanent Fix for API URL Resolution

**Date**: October 23, 2025
**Version**: v0.4.10
**Issue**: Frontend was fetching `/web/search/` instead of `/api/search`, returning HTML instead of JSON

## Root Cause

When the React app was mounted at `/web/` with `BASE_PATH=/web/`, relative URL resolution caused:
- `fetch('/api/search')` → browser resolved to `/web/api/search` → nginx SPA fallback → HTML
- **Why**: Browser resolves relative URLs against the current page's base path

## Complete Fix (3 Layers of Defense)

### 1. Code Fix: Absolute URL Helper

**File**: `apps/web/src/lib/apiUrl.ts`
```typescript
export function apiUrl(path: string, params?: URLSearchParams): string {
  const url = new URL(path, window.location.origin)
  if (params) url.search = params.toString()
  return url.toString()
}
```

**Usage**:
```typescript
// ✅ CORRECT - Always use absolute URLs
const url = apiUrl('/api/search', params)
const res = await fetch(url, { credentials: 'include' })

// ❌ WRONG - Relative URL resolution breaks with BASE_PATH
const res = await fetch('/api/search', { credentials: 'include' })
```

**Files Updated**:
- `apps/web/src/hooks/useSearchModel.ts`
- `apps/web/src/lib/api.ts`
- `apps/web/src/pages/LoginGuard.tsx`

### 2. Nginx Configuration: Proper Route Priority

**File**: `apps/web/nginx.conf`

**Key Changes**:
1. **API routes FIRST** (with `^~` prefix for exact matching)
2. **Static assets with immutable cache** (1 year for hashed files)
3. **HTML with no-cache** (always fetch fresh asset hashes)
4. **SPA fallback LAST**

```nginx
# 1. API proxy (MUST BE FIRST)
location ^~ /api/ {
  proxy_pass http://api:8003/;
  # ... proxy headers
}

# 2. Hashed static assets: cache forever
location ~* ^/assets/.*\.(js|css|woff|woff2)$ {
  expires 1y;
  add_header Cache-Control "public, max-age=31536000, immutable" always;
  try_files $uri =404;
}

# 3. HTML entry point: NO CACHE
location = /index.html {
  add_header Cache-Control "no-cache, no-store, must-revalidate" always;
  add_header Pragma "no-cache" always;
  add_header Expires "0" always;
  try_files $uri =404;
}

# 4. SPA fallback (LAST)
location / {
  add_header Cache-Control "no-cache, no-store, must-revalidate" always;
  try_files $uri $uri/ /index.html;
}
```

**Why This Works**:
- Hashed assets (`index-1761254202682.CgHkWaq5.js`) cached forever → Fast loads
- HTML never cached → Always gets new asset hashes → No stale bundles
- Browser can cache JS/CSS aggressively without ever serving stale code

### 3. E2E Safety Rails

**File**: `apps/web/tests/e2e/search.contenttype.spec.ts`
```typescript
test.describe('@prodSafe content-type', () => {
  test('search API returns JSON', async ({ request }) => {
    const res = await request.get('/api/search?q=Interview&limit=1')
    expect([200, 204, 401, 403]).toContain(res.status())
    if (res.status() !== 204) {
      expect((res.headers()['content-type'] || '')).toContain('application/json')
    }
  })
})
```

**Run Against Production**:
```bash
cd apps/web
npx playwright test --grep "@prodSafe"
```

### 4. Version Banner for Debugging

**File**: `apps/web/src/main.tsx`
```typescript
console.info(
  '%c🔍 ApplyLens Web v0.4.10%c\n' +
  'Build: 461336d @ 2025-10-23T20:58:00Z\n' +
  'Fix: apiUrl helper for absolute API URLs',
  'color: #10b981; font-weight: bold; font-size: 14px;',
  'color: #6b7280; font-size: 11px;'
)
```

Open DevTools Console → Verify version number matches deployed version

## Deployment Process

```bash
# 1. Build with --no-cache to ensure fresh compilation
cd apps/web
docker build -t leoklemet/applylens-web:v0.4.10 \
  -f Dockerfile.prod \
  --build-arg WEB_BASE_PATH=/web/ \
  --build-arg VITE_API_BASE=/api \
  --no-cache .

# 2. Verify bundle hash changed
docker run --rm leoklemet/applylens-web:v0.4.10 \
  ls -la /usr/share/nginx/html/assets/

# 3. Update docker-compose.prod.yml
image: leoklemet/applylens-web:v0.4.10

# 4. Deploy
cd ../..
docker-compose -f docker-compose.prod.yml up -d --force-recreate web
docker-compose -f docker-compose.prod.yml restart nginx
```

## User Actions After Deployment

**CRITICAL**: Hard refresh is NOT enough! Must clear storage:

1. Open DevTools (F12)
2. Go to **Application** tab
3. Click **"Clear storage"** in left sidebar
4. Check **ALL boxes** (Cache storage, Local storage, Session storage, etc.)
5. Click **"Clear site data"**
6. **Close ALL browser tabs** of applylens.app
7. Open **fresh tab** → Navigate to site

## Verification

### 1. Check Version in Console
```javascript
// Open DevTools Console
// Should see: "🔍 ApplyLens Web v0.4.10"
```

### 2. Check API URL in Network Tab
```
Network → XHR → search
URL should be: https://applylens.app/api/search?q=...
NOT: https://applylens.app/web/search/?q=...
```

### 3. Check Cache Headers
```bash
# HTML should be no-cache
curl -I https://applylens.app/index.html | grep Cache-Control
# Expected: Cache-Control: no-cache, no-store, must-revalidate

# JS should be immutable
curl -I https://applylens.app/assets/index-*.js | grep Cache-Control
# Expected: Cache-Control: public, max-age=31536000, immutable
```

### 4. Check Content-Type
```bash
# API should return JSON
curl -I https://applylens.app/api/search?q=test | grep content-type
# Expected: content-type: application/json

# Web route should return HTML
curl -I https://applylens.app/web/search | grep content-type
# Expected: content-type: text/html
```

## Why Previous Attempts Failed

| Version | Issue | Why It Failed |
|---------|-------|---------------|
| v0.4.5 | Added diagnostics | Didn't fix root cause |
| v0.4.6 | Changed to absolute URL | **Vite build cache** - didn't recompile |
| v0.4.7 | Rebuild with --no-cache | Still worked, but no cache headers |
| v0.4.8 | Added apiUrl helper | **Vite build cache again** - old code |
| v0.4.9 | Clean rebuild | Worked, but browser cached old bundle |
| v0.4.10 | ✅ All fixes + cache headers | **PERMANENT FIX** |

**Key Insight**: Even with correct source code, if the browser caches the old bundle, users will still see the old behavior. The cache headers ensure this never happens again.

## Long-Term Maintenance

### For New API Endpoints
Always use the `apiUrl` helper:
```typescript
import { apiUrl } from '@/lib/apiUrl'

const res = await fetch(apiUrl('/api/new-endpoint', params), {
  credentials: 'include'
})
```

### For Search Changes
Run the E2E test:
```bash
cd apps/web
npx playwright test search.contenttype
```

### For Nginx Changes
Always maintain this order:
1. `/api/` routes (with `^~`)
2. Static assets (with immutable cache)
3. HTML (with no-cache)
4. SPA fallback

## Rollback Plan

If v0.4.10 has issues:
```bash
# Rollback to v0.4.9 (last known good with apiUrl)
docker-compose -f docker-compose.prod.yml up -d web
# Then edit docker-compose.prod.yml to change image to v0.4.9

# Or rollback to v0.4.4 (last stable before this issue)
# image: leoklemet/applylens-web:v0.4.4
```

## References

- Original Issue: JSON parsing error ("Unexpected token '<'")
- Root Cause: Relative URL resolution with BASE_PATH=/web/
- Solution: Absolute URLs + proper nginx route priority + cache headers
- Deployed: October 23, 2025
- Bundle Hash: `CgHkWaq5` (index-1761254202682.CgHkWaq5.js)
