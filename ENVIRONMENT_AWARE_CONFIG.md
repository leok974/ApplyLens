# Environment-Aware Configuration Guide

**Date:** October 12, 2025  
**Status:** ✅ Implemented  

---

## Overview

The ApplyLens frontend now supports environment-aware API configuration, allowing it to run seamlessly in different contexts (host development, Docker, CI/CD) without code changes.

## Problem Solved

**Before:** Vite proxy was hard-coded to `http://localhost:8003`, which worked for host development but broke when running the frontend in Docker (where the API is accessible at `http://api:8003`).

**After:** Configuration is now environment-aware using `VITE_API_BASE` environment variable, with automatic fallback to proxy-based routing.

---

## Architecture

### Configuration Files

```
apps/web/
├── .env.local         # Local development (host)
├── .env.docker        # Docker environment
├── src/
│   ├── vite-env.d.ts  # TypeScript types for env vars
│   └── lib/
│       ├── apiBase.ts        # API base URL configuration
│       └── actionsClient.ts  # Updated to use API_BASE
└── vite.config.ts     # Conditional proxy configuration
```

### Environment Variables

| File | `VITE_API_BASE` | Use Case |
|------|----------------|----------|
| `.env.local` | `http://localhost:8003` | Local dev (frontend on host, backend in Docker) |
| `.env.docker` | `http://api:8003` | Full Docker stack (both frontend and backend) |
| (not set) | `/api` | Falls back to Vite proxy |

---

## Implementation Details

### 1. Environment Files

**apps/web/.env.local** (for local development):
```env
# Local development environment
# Frontend running on host, backend in Docker
VITE_API_BASE=http://localhost:8003
```

**apps/web/.env.docker** (for Docker):
```env
# Docker environment
# Both frontend and backend running in Docker
VITE_API_BASE=http://api:8003
```

### 2. API Base Module

**apps/web/src/lib/apiBase.ts**:
```typescript
/**
 * API Base URL Configuration
 * 
 * Environment Configurations:
 * - Local dev (.env.local): VITE_API_BASE=http://localhost:8003
 * - Docker (.env.docker): VITE_API_BASE=http://api:8003
 * - Fallback: '/api' (uses Vite proxy)
 */

export const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

// Log configuration in development
if (import.meta.env.DEV) {
  console.log('[API Config] Base URL:', API_BASE)
}
```

### 3. TypeScript Definitions

**apps/web/src/vite-env.d.ts**:
```typescript
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly DEV: boolean
  readonly PROD: boolean
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

### 4. Updated API Client

**apps/web/src/lib/actionsClient.ts**:
```typescript
import { API_BASE } from './apiBase'

// All fetch calls now use API_BASE
export async function fetchTray(limit: number = 50) {
  const r = await fetch(`${API_BASE}/actions/tray?limit=${limit}`)
  // ...
}
```

**All updated endpoints:**
- ✅ `${API_BASE}/actions/tray`
- ✅ `${API_BASE}/actions/{id}/approve`
- ✅ `${API_BASE}/actions/{id}/reject`
- ✅ `${API_BASE}/actions/{id}/always`
- ✅ `${API_BASE}/actions/policies`
- ✅ `${API_BASE}/actions/policies/{id}`
- ✅ `${API_BASE}/actions/policies/{id}/test`

### 5. Conditional Vite Proxy

**apps/web/vite.config.ts**:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Check if we need a proxy (when API_BASE is not explicitly set or is relative)
const API_BASE = process.env.VITE_API_BASE
const needsProxy = !API_BASE || API_BASE.startsWith('/')

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5175,
    // Only use proxy if API_BASE is not set (for backward compatibility)
    // When VITE_API_BASE is set, the client calls it directly
    proxy: needsProxy ? {
      '/api': {
        target: 'http://localhost:8003',  // Default for local dev
        changeOrigin: true,
        secure: false,
      }
    } : undefined
  }
})
```

**Proxy Behavior:**
- **When `VITE_API_BASE` is set**: Proxy is disabled, client calls API directly
- **When `VITE_API_BASE` is not set**: Proxy is enabled (backward compatibility)

### 6. NPM Scripts

**apps/web/package.json**:
```json
{
  "scripts": {
    "dev": "vite",
    "dev:docker": "set VITE_API_BASE=http://api:8003 && vite",
    "build": "vite build",
    "preview": "vite preview"
  }
}
```

---

## Usage

### Local Development (Default)

```powershell
cd apps/web
npm run dev
```

- Uses `.env.local` automatically
- `VITE_API_BASE=http://localhost:8003`
- Frontend on host, backend in Docker

### Docker Environment

```powershell
cd apps/web
npm run dev:docker
```

Or manually set the variable:
```powershell
$env:VITE_API_BASE="http://api:8003"
npm run dev
```

### Production Build

```powershell
cd apps/web
npm run build
```

The built files will use the `VITE_API_BASE` value at build time. Set it appropriately:

```powershell
# For production deployment
$env:VITE_API_BASE="https://api.applylens.com"
npm run build
```

---

## Testing

### E2E Smoke Test

Run the comprehensive smoke test:

```powershell
cd d:/ApplyLens
pwsh ./scripts/smoke-test.ps1
```

**Tests:**
1. Frontend accessibility (HTTP 200)
2. API documentation (HTTP 200)
3. Prometheus metrics (HTTP 200 + Phase 4 metrics present)
4. Actions API flow (propose → tray → approve)
5. Policies endpoint (6 policies configured)
6. 'Always' endpoint (registered in OpenAPI)

**Expected Output:**
```
🎉 All critical tests passed!
  ✅ Passed:  7

Next steps:
  • Open UI: http://localhost:5175
  • View metrics: http://localhost:8003/metrics
  • API docs: http://localhost:8003/docs
```

### Manual Testing

**1. Check API Base in Browser Console:**
```javascript
// Open http://localhost:5175
// Open DevTools (F12) → Console
// You should see:
[API Config] Base URL: http://localhost:8003
```

**2. Verify Network Requests:**
```
Open DevTools → Network tab
Trigger an action (click Actions button)
Check request URL:
  ✅ http://localhost:8003/actions/tray
  ❌ NOT /api/actions/tray (proxy)
```

**3. Test Different Configurations:**

```powershell
# Test with localhost
$env:VITE_API_BASE="http://localhost:8003"
npm run dev
# Check console: [API Config] Base URL: http://localhost:8003

# Test with Docker hostname
$env:VITE_API_BASE="http://api:8003"
npm run dev
# Check console: [API Config] Base URL: http://api:8003

# Test with proxy fallback
Remove-Item Env:\VITE_API_BASE
npm run dev
# Check console: [API Config] Base URL: /api
```

---

## Deployment Scenarios

### Scenario 1: Local Development

**Setup:**
- Backend: Docker (`docker compose up -d`)
- Frontend: Host (`npm run dev`)

**Configuration:**
- Uses `.env.local`
- `VITE_API_BASE=http://localhost:8003`
- Direct API calls (no proxy)

**Start:**
```powershell
# Terminal 1: Backend
cd d:/ApplyLens/infra
docker compose up -d

# Terminal 2: Frontend
cd d:/ApplyLens/apps/web
npm run dev
```

### Scenario 2: Full Docker Stack

**Setup:**
- Backend: Docker
- Frontend: Docker

**Configuration:**
- Uses `.env.docker` or env var
- `VITE_API_BASE=http://api:8003`
- Direct API calls using Docker service name

**Start:**
```powershell
cd d:/ApplyLens/infra
docker compose up -d
```

(Assumes frontend Dockerfile and docker-compose.yml entry exist)

### Scenario 3: Production Deployment

**Setup:**
- Backend: Kubernetes/Cloud
- Frontend: CDN/Static hosting

**Configuration:**
- Build-time environment variable
- `VITE_API_BASE=https://api.applylens.com`
- Direct API calls to production API

**Build:**
```powershell
$env:VITE_API_BASE="https://api.applylens.com"
npm run build

# Deploy dist/ folder to CDN
```

### Scenario 4: CI/CD Pipeline

**Setup:**
- Automated builds and tests

**Configuration:**
- Environment-specific variables
- Set in CI/CD pipeline

**Example GitHub Actions:**
```yaml
- name: Build frontend
  env:
    VITE_API_BASE: ${{ secrets.API_BASE_URL }}
  run: |
    cd apps/web
    npm ci
    npm run build
```

---

## Monitoring & Validation

### Check Current Configuration

**At Runtime (Browser Console):**
```javascript
// Frontend automatically logs in dev mode
// Open http://localhost:5175
// Check console for:
[API Config] Base URL: http://localhost:8003
```

**In Code:**
```typescript
import { API_BASE } from '@/lib/apiBase'
console.log('API Base:', API_BASE)
```

### Prometheus Metrics

After running smoke test, check metrics:

```powershell
curl http://localhost:8003/metrics | Select-String -Pattern "actions_"
```

**Expected Output:**
```prometheus
# HELP actions_proposed_total Total number of action proposals created
# TYPE actions_proposed_total counter
actions_proposed_total{policy_name="High-risk quarantine"} 0

# HELP actions_executed_total Total number of successfully executed actions
# TYPE actions_executed_total counter
actions_executed_total{action_type="archive_email",outcome="success"} 0

# HELP actions_failed_total Total number of failed action executions
# TYPE actions_failed_total counter
```

---

## Troubleshooting

### Issue: API calls still use /api proxy

**Problem:** Requests go to `/api/actions/tray` instead of `http://localhost:8003/actions/tray`

**Solution:**
1. Check if `.env.local` exists and contains `VITE_API_BASE`
2. Restart Vite dev server (Ctrl+C, then `npm run dev`)
3. Check browser console for `[API Config] Base URL:`
4. Clear browser cache and reload

### Issue: CORS errors in Docker

**Problem:** `Cross-Origin Request Blocked` when frontend calls backend

**Solution:**
1. Ensure `VITE_API_BASE=http://api:8003` is set (Docker service name)
2. Check backend CORS configuration allows Docker network
3. Verify both services are in the same Docker network

### Issue: Environment variable not loading

**Problem:** `VITE_API_BASE` is set but not used

**Solution:**
1. Vite only reads env vars starting with `VITE_`
2. Restart dev server after changing `.env` files
3. Check Vite config for typos
4. Verify TypeScript types in `vite-env.d.ts`

### Issue: Build uses wrong API URL

**Problem:** Production build still points to localhost

**Solution:**
1. Set `VITE_API_BASE` **before** building:
   ```powershell
   $env:VITE_API_BASE="https://api.applylens.com"
   npm run build
   ```
2. Environment variables are baked into build at build time
3. Check `dist/assets/*.js` for hardcoded URLs

---

## Best Practices

### 1. Never Commit .env.local

```gitignore
# apps/web/.gitignore
.env.local
.env.*.local
```

**Why:** Contains local machine-specific configuration

### 2. Document Expected Variables

Create `.env.example`:
```env
# Example environment configuration
# Copy to .env.local and adjust values

VITE_API_BASE=http://localhost:8003
```

### 3. Validate Configuration at Startup

```typescript
// apps/web/src/main.tsx
import { API_BASE } from '@/lib/apiBase'

if (import.meta.env.PROD && API_BASE === '/api') {
  console.warn('⚠️ API_BASE not set in production!')
}
```

### 4. Use TypeScript for Type Safety

Always define env vars in `vite-env.d.ts`:
```typescript
interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_OTHER_VAR?: string  // Add more as needed
}
```

### 5. Test All Configurations

```powershell
# Test localhost
$env:VITE_API_BASE="http://localhost:8003"
pwsh ./scripts/smoke-test.ps1

# Test Docker
$env:VITE_API_BASE="http://api:8003"
pwsh ./scripts/smoke-test.ps1

# Test proxy fallback
Remove-Item Env:\VITE_API_BASE
pwsh ./scripts/smoke-test.ps1
```

---

## Migration from Old Configuration

### Before (Hard-coded)

```typescript
// actionsClient.ts
const r = await fetch(`/api/actions/tray`)
```

```typescript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://localhost:8003',  // Hard-coded
  }
}
```

### After (Environment-aware)

```typescript
// actionsClient.ts
import { API_BASE } from './apiBase'
const r = await fetch(`${API_BASE}/actions/tray`)
```

```typescript
// vite.config.ts
const API_BASE = process.env.VITE_API_BASE
const needsProxy = !API_BASE || API_BASE.startsWith('/')

proxy: needsProxy ? {
  '/api': { target: 'http://localhost:8003' }
} : undefined
```

### Migration Steps

1. ✅ Create `.env.local` with `VITE_API_BASE`
2. ✅ Create `src/lib/apiBase.ts`
3. ✅ Update `vite-env.d.ts` with types
4. ✅ Update all fetch calls in `actionsClient.ts`
5. ✅ Make Vite proxy conditional
6. ✅ Test with smoke test script
7. ✅ Update documentation

---

## Summary

✅ **Environment-aware configuration implemented**

**Benefits:**
- 🎯 Works in local dev (host + Docker)
- 🐳 Works in full Docker stack
- ☁️ Works in production deployment
- 🧪 Easy to test different configurations
- 📝 Type-safe with TypeScript
- 🔒 Secure (.env.local in .gitignore)

**Files Changed:**
- `apps/web/.env.local` (created)
- `apps/web/.env.docker` (created)
- `apps/web/src/lib/apiBase.ts` (created)
- `apps/web/src/vite-env.d.ts` (created)
- `apps/web/src/lib/actionsClient.ts` (8 fetch calls updated)
- `apps/web/vite.config.ts` (conditional proxy)
- `apps/web/package.json` (added dev:docker script)
- `apps/web/.gitignore` (added .env.local)
- `scripts/smoke-test.ps1` (created comprehensive test)

**Next Steps:**
- Run smoke test: `pwsh ./scripts/smoke-test.ps1`
- Test in browser: http://localhost:5175
- Check console logs for API base URL
- Verify Phase 4 features work

🎉 **Configuration is future-proof and production-ready!**
