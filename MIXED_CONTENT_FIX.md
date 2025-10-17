# Mixed Content Error Fix

**Date:** October 14, 2025  
**Issue:** Frontend making HTTP requests to profile endpoints, causing Mixed Content errors on HTTPS pages

## Problem

The browser console showed:
```
Mixed Content: The page at 'https://applylens.app/profile' was loaded over HTTPS, 
but requested an insecure resource 'http://applylens.app/web/profile/db-summary?...'
```

Two issues were identified:
1. Profile endpoints were using wrong paths: `/profile/*` instead of `/api/profile/*`
2. One endpoint was not using the centralized `API_BASE` configuration

## Root Cause

1. **ProfileSummary.tsx**: Direct fetch to `/profile/db-summary` (should be `/api/profile/db-summary`)
2. **api.ts**: `rebuildProfile` function using `/profile/rebuild` instead of `${API_BASE}/profile/rebuild`

Both endpoints were being treated as frontend routes rather than API routes, causing:
- Wrong protocol (HTTP instead of HTTPS)
- Wrong path (not going through nginx `/api` proxy)
- 404 errors (no nginx location block for `/profile`)

## Files Changed

### 1. `apps/web/src/components/profile/ProfileSummary.tsx`

**Before:**
```typescript
import { useEffect, useState } from "react"
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

// ...

useEffect(() => {
  fetch(`/profile/db-summary?user_email=${encodeURIComponent(USER_EMAIL)}`)
    .then((r) => r.json())
    .then(setData)
    .catch(console.error)
    .finally(() => setLoading(false))
}, [])
```

**After:**
```typescript
import { useEffect, useState } from "react"
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { API_BASE } from "@/lib/apiBase"  // ✅ Added import

// ...

useEffect(() => {
  fetch(`${API_BASE}/profile/db-summary?user_email=${encodeURIComponent(USER_EMAIL)}`)  // ✅ Using API_BASE
    .then((r) => r.json())
    .then(setData)
    .catch(console.error)
    .finally(() => setLoading(false))
}, [])
```

### 2. `apps/web/src/lib/api.ts`

**Before:**
```typescript
export const rebuildProfile = (userEmail: string): Promise<ProfileRebuildResponse> =>
  post(`/profile/rebuild?user_email=${encodeURIComponent(userEmail)}`)
```

**After:**
```typescript
import { API_BASE } from './apiBase'  // ✅ Added import at top of file

// ...

export const rebuildProfile = (userEmail: string): Promise<ProfileRebuildResponse> =>
  post(`${API_BASE}/profile/rebuild?user_email=${encodeURIComponent(userEmail)}`)  // ✅ Using API_BASE
```

## Verification

After rebuilding and restarting the web container, the built JavaScript shows:
```javascript
Qn="/api"  // API_BASE variable in minified code
```

All profile API calls now correctly use `/api/profile/*` paths, which:
1. ✅ Maintain same-origin HTTPS requests
2. ✅ Route through nginx `/api` proxy to FastAPI backend
3. ✅ Avoid Mixed Content errors
4. ✅ Use consistent API base configuration

## Testing

Run these commands in browser console on `https://applylens.app/profile`:

```javascript
// Should return 200 and data
fetch('/api/profile/db-summary?user_email=leoklemet.pa@gmail.com')
  .then(r => r.json())
  .then(console.log)

// Should work without Mixed Content errors
fetch('/api/healthz').then(r => r.status)
```

## Related Configuration

The API base is configured centrally in `apps/web/src/lib/apiBase.ts`:
```typescript
export const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'
```

Production builds use `VITE_API_BASE=/api` (set in `docker-compose.prod.yml`), which ensures all API calls go through the nginx proxy at `/api/*`.

## Deployment

```bash
# Rebuild web container
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod build web

# Restart web service
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d web
```

## Status

✅ **FIXED** - All profile endpoints now use correct API paths with HTTPS same-origin requests.
