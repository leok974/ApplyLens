# Local Development Setup Guide

## Overview

This guide explains how to set up a local development environment for ApplyLens that **does not interfere** with production infrastructure.

## ⚠️ Critical Rules

1. **Never call production API from localhost** - This causes CORS errors
2. **Never reuse production Cloudflare tunnel** - Dev projects need their own tunnel
3. **Always use local API for local development**

## Quick Start

### 1. Configure Local API Base

Create or update `apps/web/.env.local`:

```bash
VITE_API_BASE=http://127.0.0.1:8003
```

**Do NOT use**:
```bash
# ❌ WRONG - Causes CORS errors
VITE_API_BASE=https://applylens.app/api
```

### 2. Start Local API Server

```powershell
cd services/api

# Set environment variables
$env:CORS_ALLOW_ORIGINS="http://127.0.0.1:5176,http://localhost:5176"
$env:APPLYLENS_DEV="1"
$env:DATABASE_URL="postgresql://user:pass@localhost:5432/applylens"

# Start API with auto-reload
uvicorn app.main:app --reload --port 8003
```

### 3. Start Local Web Dev Server

```powershell
cd apps/web

# Install dependencies (first time only)
npm install

# Start Vite dev server
npm run dev
```

The dev server will start on `http://localhost:5176` (or 5177, 5178 if port is busy).

### 4. Verify Configuration

Open browser console and check:

```
[API Config] Base URL: http://127.0.0.1:8003
```

If you see `https://applylens.app/api`, you need to restart the Vite dev server to pick up the new `.env.local`.

## Architecture

### Local Development Flow

```
Browser (localhost:5176)
    ↓
Vite Dev Server (localhost:5176)
    ↓
Local API (127.0.0.1:8003)
    ↓
Local PostgreSQL (localhost:5432)
```

**Why this works**: Same origin = No CORS issues

### Production Flow (for reference)

```
Browser (applylens.app)
    ↓
Cloudflare CDN
    ↓
Cloudflare Tunnel (cfd-a/cfd-b)
    ↓
applylens-web-prod (nginx)
    ↓
applylens-api-prod (FastAPI)
    ↓
applylens-db-prod (PostgreSQL)
```

## Common Issues

### Issue: CORS Errors in Browser Console

**Symptoms**:
```
Access to fetch at 'https://applylens.app/api/...' from origin 'http://localhost:5176'
has been blocked by CORS policy
```

**Cause**: `.env.local` is pointing to production API

**Fix**:
1. Check `apps/web/.env.local`:
   ```bash
   # Should be:
   VITE_API_BASE=http://127.0.0.1:8003
   ```
2. Restart Vite dev server
3. Hard refresh browser (Ctrl+Shift+R)

### Issue: API Returns 502

**Symptoms**: Local web gets 502 errors from production API

**Cause**: Trying to use production API from localhost (CORS + routing issues)

**Fix**: Use local API (see Quick Start above)

### Issue: Connection Refused on Port 8003

**Symptoms**: `ERR_CONNECTION_REFUSED` when calling API

**Cause**: Local API server not running

**Fix**:
```powershell
cd services/api
uvicorn app.main:app --reload --port 8003
```

### Issue: Database Connection Error

**Symptoms**: API server fails to start with database errors

**Cause**: PostgreSQL not running or wrong connection string

**Fix**:
1. Start PostgreSQL (Docker or local install)
2. Verify `DATABASE_URL` environment variable
3. Check database exists and credentials are correct

## Environment Variables Reference

### Web App (.env.local)

| Variable | Local Dev | Production |
|----------|-----------|------------|
| `VITE_API_BASE` | `http://127.0.0.1:8003` | `/api` (default, uses Vite proxy) |

### API Server

| Variable | Local Dev | Production |
|----------|-----------|------------|
| `CORS_ALLOW_ORIGINS` | `http://127.0.0.1:5176,http://localhost:5176` | `https://applylens.app,https://www.applylens.app` |
| `APPLYLENS_DEV` | `1` | Not set |
| `DATABASE_URL` | `postgresql://user:pass@localhost:5432/applylens` | `postgresql://...` (from Docker secrets) |

## Code Verification

The API base URL is defined in `apps/web/src/lib/apiBase.ts`:

```typescript
export const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

if (import.meta.env.DEV) {
  console.log('[API Config] Base URL:', API_BASE)
}
```

**Default behavior** (when `VITE_API_BASE` not set):
- Uses `/api` which triggers Vite proxy in dev mode
- In production build, uses nginx proxy

## Testing Your Setup

```powershell
# Run smoke test
.\scripts\check-applylens-prod.ps1

# Should show:
# ✅ Local dev NOT calling production API
# ✅ Production API accessible via HTTPS
# ✅ No CORS conflicts
```

## Development Workflow

1. **Start services**:
   ```powershell
   # Terminal 1: API
   cd services/api && uvicorn app.main:app --reload --port 8003

   # Terminal 2: Web
   cd apps/web && npm run dev
   ```

2. **Make changes**: Edit files, servers auto-reload

3. **Test locally**: Browser at `http://localhost:5176`

4. **Commit changes**: When ready

5. **Deploy to prod**: Follow deployment guide

## Production Testing

If you need to test against production API (e.g., for debugging):

1. **Do NOT change `.env.local`**
2. Instead, use browser DevTools:
   ```javascript
   // In browser console
   fetch('https://applylens.app/api/auth/me', {
     credentials: 'include'
   }).then(r => r.json()).then(console.log)
   ```

Or use `curl`:
```powershell
curl -I https://applylens.app/api/auth/me -H "Cache-Control: no-cache"
```

## Related Documentation

- [Production Tunnel Runbook](../infra/APPLYLENS_TUNNEL_RUNBOOK.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Development Guide](./DEVELOPMENT.md)

## Quick Reference

```powershell
# Check current API base
cd apps/web
cat .env.local

# Show active dev servers
Get-Process | Where-Object { $_.Name -match "node|uvicorn" }

# Kill stuck dev servers
Get-Process | Where-Object { $_.Name -match "node" } | Stop-Process

# Full system check
.\scripts\check-applylens-prod.ps1
```
