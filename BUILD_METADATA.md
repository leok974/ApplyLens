# Build Metadata System

This document describes how build metadata (version, git SHA, build time) is injected into both frontend and backend builds.

## Overview

Every build now includes:
- **Version**: Semantic version (e.g., `0.5.2`)
- **Git SHA**: Short commit hash (e.g., `abc1234`)
- **Build Time**: ISO timestamp (e.g., `2025-11-18T20:05:23Z`)
- **Build Flavor**: Environment (`dev-local`, `prod`, `staging`)

## Frontend (apps/web)

### Console Banner

When the app loads, you'll see:
```
🔍 ApplyLens Web env=production flavor=prod version=0.5.2 sha=abc1234 builtAt=2025-11-18T20:05:23Z
Features: Theme-aware select fields for light/dark modes
```

### Settings Page Version Card

Navigate to Settings → About to see a version card displaying:
- **Service**: Backend API name (`applylens-api`)
- **Version**: Backend version from `/api/version` endpoint
- **Commit**: Backend git SHA (first 7 chars)
- **Built at**: Backend build timestamp
- **Web version**: Frontend version from build metadata
- **Web commit**: Frontend git SHA (first 7 chars)

The card will show "Loading version info..." while fetching from the API, and gracefully falls back to frontend build metadata if the API is unavailable.

### Implementation

**File: `src/version.ts`**
```typescript
export const BUILD_META = {
  env: import.meta.env.MODE,
  flavor: import.meta.env.VITE_BUILD_FLAVOR ?? "unknown",
  version: import.meta.env.VITE_BUILD_VERSION ?? "dev",
  gitSha: import.meta.env.VITE_BUILD_GIT_SHA ?? "local",
  builtAt: import.meta.env.VITE_BUILD_TIME ?? "",
};
```

**File: `src/main.tsx`**
```typescript
import { BUILD_META } from './version';

console.info(
  "🔍 ApplyLens Web",
  `env=${BUILD_META.env}`,
  `flavor=${BUILD_META.flavor}`,
  `version=${BUILD_META.version}`,
  `sha=${BUILD_META.gitSha}`,
  `builtAt=${BUILD_META.builtAt || "unknown"}`,
  "\nFeatures:",
  "Theme-aware select fields for light/dark modes"
);
```

### Environment Variables

**Development (`.env.local`):**
```bash
VITE_BUILD_FLAVOR=dev-local
VITE_BUILD_VERSION=dev
VITE_BUILD_GIT_SHA=local
VITE_BUILD_TIME=local
```

**Production (`.env.production`):**
```bash
VITE_BUILD_FLAVOR=prod
VITE_BUILD_VERSION=0.0.0  # Overridden in CI
VITE_BUILD_GIT_SHA=local  # Overridden in CI
VITE_BUILD_TIME=local     # Overridden in CI
```

### Docker Build

**File: `Dockerfile.prod`**
```dockerfile
ARG VITE_BUILD_FLAVOR=prod
ARG VITE_BUILD_VERSION=0.0.0
ARG VITE_BUILD_GIT_SHA=unknown
ARG VITE_BUILD_TIME=unknown

ENV VITE_BUILD_FLAVOR=${VITE_BUILD_FLAVOR}
ENV VITE_BUILD_VERSION=${VITE_BUILD_VERSION}
ENV VITE_BUILD_GIT_SHA=${VITE_BUILD_GIT_SHA}
ENV VITE_BUILD_TIME=${VITE_BUILD_TIME}
```

## Backend (services/api)

### Version Endpoint

**GET `/version`**
```json
{
  "app": "applylens-api",
  "version": "0.5.2",
  "sha": "abc1234",
  "built_at": "2025-11-18T20:05:23Z"
}
```

### Implementation

**File: `app/config.py`**
```python
import os

APP_VERSION = os.getenv("APP_VERSION", "dev")
APP_BUILD_SHA = os.getenv("APP_BUILD_SHA", "")
APP_BUILD_TIME = os.getenv("APP_BUILD_TIME", "")
```

**File: `app/routers/version.py`**
```python
from fastapi import APIRouter
from app.config import APP_VERSION, APP_BUILD_SHA, APP_BUILD_TIME

router = APIRouter(tags=["ops"])

@router.get("/version")
async def get_version():
    return {
        "app": "applylens-api",
        "version": APP_VERSION,
        "sha": APP_BUILD_SHA,
        "built_at": APP_BUILD_TIME,
    }
```

**File: `app/main.py`**
```python
from .routers import version as version_router

app.include_router(version_router.router)
```

### Environment Variables

Set these in your docker-compose or deployment environment:
```bash
APP_VERSION=0.5.2
APP_BUILD_SHA=abc1234
APP_BUILD_TIME=2025-11-18T20:05:23Z
```

## Local Development

### Manual Build (PowerShell)

**Build images with metadata:**
```powershell
.\scripts\build-prod-images.ps1 -Version "0.5.2" -Push
```

**Deploy with metadata:**
```powershell
.\scripts\deploy-prod.ps1 -Version "0.5.2" -Build
```

### Testing

**Check frontend console:**
1. Open browser dev tools
2. Reload the app
3. Look for the ApplyLens Web banner in console

**Check backend version:**
```bash
curl http://localhost:8003/version
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set build metadata
        id: meta
        run: |
          echo "version=${{ github.ref_name }}" >> $GITHUB_OUTPUT
          echo "sha=${{ github.sha }}" >> $GITHUB_OUTPUT
          echo "time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> $GITHUB_OUTPUT

      - name: Build web image
        run: |
          docker build \
            --build-arg VITE_BUILD_FLAVOR=prod \
            --build-arg VITE_BUILD_VERSION=${{ steps.meta.outputs.version }} \
            --build-arg VITE_BUILD_GIT_SHA=${{ steps.meta.outputs.sha }} \
            --build-arg VITE_BUILD_TIME=${{ steps.meta.outputs.time }} \
            -t myregistry/applylens-web:${{ steps.meta.outputs.version }} \
            -f apps/web/Dockerfile.prod \
            apps/web

      - name: Build API image
        run: |
          docker build \
            --build-arg GIT_SHA=${{ steps.meta.outputs.sha }} \
            --build-arg BUILD_DATE=${{ steps.meta.outputs.time }} \
            -t myregistry/applylens-api:${{ steps.meta.outputs.version }} \
            -f services/api/Dockerfile.prod \
            services/api

      - name: Deploy to production
        env:
          APP_VERSION: ${{ steps.meta.outputs.version }}
          APP_BUILD_SHA: ${{ steps.meta.outputs.sha }}
          APP_BUILD_TIME: ${{ steps.meta.outputs.time }}
        run: |
          docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Frontend shows `flavor=dev-local` in production

**Problem:** Wrong environment file was used during build.

**Solution:** Ensure Vite uses `.env.production`:
```bash
npm run build  # Uses .env.production by default
```

### Backend shows `version=dev`

**Problem:** `APP_VERSION` environment variable not set.

**Solution:** Check docker-compose environment section:
```yaml
environment:
  APP_VERSION: "0.5.2"
  APP_BUILD_SHA: "abc1234"
  APP_BUILD_TIME: "2025-11-18T20:05:23Z"
```

### Version endpoint returns 404

**Problem:** Version router not included in main app.

**Solution:** Check `app/main.py`:
```python
from .routers import version as version_router
app.include_router(version_router.router)
```

### File Checklist

### Frontend
- ✅ `src/version.ts` - BUILD_META definition
- ✅ `src/main.tsx` - Console banner using BUILD_META
- ✅ `src/lib/version.ts` - API client for `/api/version` endpoint
- ✅ `src/components/settings/VersionCard.tsx` - Settings page version display
- ✅ `src/pages/Settings.tsx` - Integrated About section with VersionCard
- ✅ `.env.local` - Dev environment variables
- ✅ `.env.production` - Prod defaults
- ✅ `Dockerfile.prod` - Build args for VITE_BUILD_*

### Backend
- ✅ `app/config.py` - APP_VERSION, APP_BUILD_SHA, APP_BUILD_TIME
- ✅ `app/routers/version.py` - Version endpoint
- ✅ `app/main.py` - Router inclusion

### Scripts
- ✅ `scripts/build-prod-images.ps1` - Build with metadata
- ✅ `scripts/deploy-prod.ps1` - Deploy with metadata

### Documentation
- ✅ `BUILD_METADATA.md` - This file
