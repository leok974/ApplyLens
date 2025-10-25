# 🚨 Production 502 Error Fix - applylens.app

## Issues Identified

### 1. ❌ **502 Bad Gateway on /web/search**
**Error:** `GET https://applylens.app/web/search?q=Interview... 502`

**Root Cause:**
- Browser is requesting `/web/search` as a page route
- Nginx proxies `/web/` to the web container at `http://web:80/`
- Web container nginx receives request for `/search` (after stripping `/web/`)
- Web container tries to serve static file or SPA route
- No static `/search` file exists, so it falls back to `/index.html`
- The built app has `base: '/'` in vite.config, so asset paths are wrong

**The Real Problem:**
The production build is configured with `VITE_BASE_PATH=/` but the app is served at `/web/` in production.

### 2. ⚠️ **Mixed Content - Favicon over HTTP**
**Error:** `Mixed Content: ... requested an insecure favicon 'http://applylens.app/web/favicon.ico'`

**Root Cause:**
- Favicon links in index.html use relative paths (`/favicon-16.png`)
- These become `/web/favicon-16.png` when base is `/web/`
- But somewhere a hardcoded `http://` reference exists

### 3. 🔧 **Incorrect Build Configuration**
The web Docker image needs to be built with `VITE_BASE_PATH=/web/` for production.

## Solutions

### Solution 1: Rebuild Web Image with Correct Base Path

**Update the build command to set the correct base path:**

```bash
cd d:\ApplyLens\apps\web

# Build with correct base path
$GIT_SHA = git rev-parse --short HEAD
$BUILD_DATE = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

docker build `
  -t leoklemet/applylens-web:v0.4.2-hotfix `
  -t leoklemet/applylens-web:latest `
  -f Dockerfile.prod `
  --build-arg GIT_SHA=$GIT_SHA `
  --build-arg BUILD_DATE=$BUILD_DATE `
  --build-arg VITE_API_BASE=/api `
  --build-arg WEB_BASE_PATH=/web/ `
  .
```

### Solution 2: Update Docker Compose to Use Correct Build Args

**File: `docker-compose.prod.yml`**

Update the web service to pass build args:

```yaml
web:
  build:
    context: ./apps/web
    dockerfile: Dockerfile.prod
    args:
      VITE_API_BASE: /api
      WEB_BASE_PATH: /web/
      GIT_SHA: ${GIT_SHA:-unknown}
      BUILD_DATE: ${BUILD_DATE:-2025-01-01}
  image: leoklemet/applylens-web:v0.4.2-hotfix
  container_name: applylens-web-prod
```

### Solution 3: Fix Favicon References

The nginx CSP header already includes `upgrade-insecure-requests`, but we need to ensure all favicon references are relative.

**File: `apps/web/nginx.conf`** - Already has CSP fix! ✅
```nginx
add_header Content-Security-Policy "upgrade-insecure-requests" always;
```

### Solution 4: Update Nginx Config to Handle SPA Routing at /web/

**File: `infra/nginx/conf.d/applylens.prod.conf`**

The current config proxies `/web/` to `http://web:80/` which is correct, but we need to ensure the web container can handle this.

**Current (Lines 123-155):**
```nginx
location /web/ {
    # Normalize /web -> /web/
    if ($request_uri = "/web") {
        return 301 /web/;
    }

    # Proxy to production web container (nginx serving static files)
    proxy_pass http://web:80/;
    # ... headers ...

    # SPA Routing Support
    proxy_intercept_errors on;
    error_page 404 = @web_fallback;
}
```

This is already correct! The issue is the build configuration.

## Immediate Fix Steps

### Step 1: Rebuild Web Image

```powershell
cd d:\ApplyLens\apps\web

# Get metadata
$GIT_SHA = git rev-parse --short HEAD
$BUILD_DATE = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

Write-Host "Building with base path /web/ for production..." -ForegroundColor Yellow

# Build with correct base path
docker build `
  -t leoklemet/applylens-web:v0.4.2 `
  -t leoklemet/applylens-web:latest `
  -f Dockerfile.prod `
  --build-arg GIT_SHA=$GIT_SHA `
  --build-arg BUILD_DATE=$BUILD_DATE `
  --build-arg VITE_API_BASE=/api `
  --build-arg WEB_BASE_PATH=/web/ `
  .
```

### Step 2: Update Docker Compose

```yaml
# File: docker-compose.prod.yml
web:
  image: leoklemet/applylens-web:v0.4.2
  # ... rest of config
```

### Step 3: Deploy

```powershell
cd d:\ApplyLens

# Update compose file image tag
# Then recreate container
docker-compose -f docker-compose.prod.yml up -d --force-recreate web

# Verify
docker logs applylens-web-prod --tail 20
curl https://applylens.app/web/
```

### Step 4: Verify

1. **Check asset paths in HTML:**
   ```bash
   curl https://applylens.app/web/ | grep -E "href=|src="
   ```
   Should show paths like `/web/assets/...`

2. **Check search page:**
   ```bash
   curl -I https://applylens.app/web/search
   ```
   Should return 200 and serve index.html

3. **Check favicon:**
   ```bash
   curl -I https://applylens.app/web/favicon-32.png
   ```
   Should return 200

## Root Cause Analysis

### Why It Worked Locally But Not in Production

1. **Local Development:**
   - Dev server runs at `http://localhost:5175/`
   - Base path is `/` (default)
   - Assets served from root
   - API proxy handles `/api` → `http://localhost:8003`

2. **Production:**
   - App deployed at `https://applylens.app/web/`
   - Base path **must be** `/web/`
   - Assets must be at `/web/assets/...`
   - Main nginx handles `/api` → `http://api:8003`

### The Missing Link

The `Dockerfile.prod` hardcodes:
```dockerfile
ARG WEB_BASE_PATH=/
ENV VITE_BASE_PATH=${WEB_BASE_PATH}
```

But for production at applylens.app, it **must be**:
```dockerfile
ARG WEB_BASE_PATH=/web/
ENV VITE_BASE_PATH=${WEB_BASE_PATH}
```

## Alternative: Serve at Root Path

If you want to serve the web app at root (`https://applylens.app/`) instead of `/web/`:

**Update: `infra/nginx/conf.d/applylens.prod.conf`**

```nginx
# Replace the current /web/ location with:
location / {
    proxy_pass http://web:80/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # SPA Routing Support
    proxy_intercept_errors on;
    error_page 404 = @web_fallback;
}
```

Then build with `WEB_BASE_PATH=/` (default).

## Testing the Fix

### Local Test (Simulate Production Path)

```bash
# Build with /web/ base
cd apps/web
docker build -t test-web -f Dockerfile.prod --build-arg WEB_BASE_PATH=/web/ .

# Run locally
docker run -p 8080:80 test-web

# Test in browser
open http://localhost:8080/web/
```

### Production Smoke Test

After deployment:

```bash
# 1. Check index.html
curl -s https://applylens.app/web/ | grep '<script'
# Should show: <script type="module" crossorigin src="/web/assets/index-...js"></script>

# 2. Check search page
curl -I https://applylens.app/web/search
# Should return: 200 OK

# 3. Check API call from browser
# Open: https://applylens.app/web/search?q=test
# Network tab should show: GET /api/search?q=test (not /web/search)

# 4. Check favicon
curl -I https://applylens.app/web/favicon-32.png
# Should return: 200 OK
```

## Summary

- ❌ **Bug:** Web app built with `base: '/'` but deployed at `/web/`
- ✅ **Fix:** Rebuild with `--build-arg WEB_BASE_PATH=/web/`
- 🔧 **Deploy:** Update image and recreate container
- ✅ **CSP:** Already fixed with `upgrade-insecure-requests`

**Time to fix:** ~5 minutes (build + deploy)
