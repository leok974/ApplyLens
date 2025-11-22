# Web App Version Tracking

This implementation adds comprehensive version tracking to the ApplyLens web application.

## Features

### 1. Version in Code (`src/version.ts`)

```typescript
import { buildInfo } from './version';
console.info("ApplyLens Web build:", buildInfo.version);
```

- `APP_VERSION`: Read from `VITE_APP_VERSION` env var (falls back to `"dev-local"`)
- `buildInfo.version`: The version string
- `buildInfo.buildTime`: Build timestamp (optional)

### 2. Version in HTML Meta Tag

The `index.html` includes a build-id meta tag that gets replaced at build time:

```html
<meta name="build-id" content="%VITE_APP_VERSION%" />
```

When `VITE_APP_VERSION=v0.6.0-thread-viewer-v1+abc123`, this becomes:

```html
<meta name="build-id" content="v0.6.0-thread-viewer-v1+abc123" />
```

### 3. Version Endpoint (`/version.json`)

The `versionJsonPlugin` in `vite.config.ts` generates a `version.json` file in the build output:

```json
{
  "version": "v0.6.0-thread-viewer-v1+abc123",
  "buildTime": "2025-11-15T18:45:30.123Z"
}
```

This is accessible at: `https://applylens.app/version.json`

### 4. Console Log on Startup

`main.tsx` logs the version on app initialization:

```
🔍 ApplyLens Web v0.6.0-thread-viewer-v1+abc123
Build: 2025-11-15T18:45:30.123Z
Features: Theme-aware select fields for light/dark modes
```

## Usage

### Development

No special setup needed. Version defaults to `"dev-local"`:

```bash
npm run dev
# Version will be "dev-local"
```

### Production Build (Local)

Set `VITE_APP_VERSION` before building:

**PowerShell:**
```powershell
$env:VITE_APP_VERSION="v0.6.0-phase5+$(git rev-parse --short HEAD)"
npm run build
```

**Bash:**
```bash
export VITE_APP_VERSION="v0.6.0-phase5+$(git rev-parse --short HEAD)"
npm run build
```

### Docker Build

The `Dockerfile.prod` accepts `APP_VERSION` as a build arg:

```bash
docker build \
  -t leoklemet/applylens-web:latest \
  --build-arg APP_VERSION="v0.6.0-thread-viewer-v1+abc123" \
  -f Dockerfile.prod \
  .
```

**Example build scripts:**
- `build-with-version.example.sh` (Linux/Mac)
- `build-with-version.example.ps1` (Windows)

### CI/CD Integration

In GitHub Actions or similar:

```yaml
- name: Build Docker Image
  run: |
    GIT_SHA=$(git rev-parse --short HEAD)
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    APP_VERSION="v0.6.0-${GIT_BRANCH}+${GIT_SHA}"

    docker build \
      -t leoklemet/applylens-web:${GIT_BRANCH} \
      --build-arg APP_VERSION="${APP_VERSION}" \
      --build-arg GIT_SHA="${GIT_SHA}" \
      --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      -f apps/web/Dockerfile.prod \
      apps/web
```

## Verification

After deploying a new build:

### 1. Check HTML Meta Tag

```bash
curl -s https://applylens.app/ | Select-String "build-id"
```

Expected:
```html
<meta name="build-id" content="v0.6.0-phase5+abc123" />
```

### 2. Check version.json Endpoint

```bash
curl -s https://applylens.app/version.json
```

Expected:
```json
{
  "version": "v0.6.0-phase5+abc123",
  "buildTime": "2025-11-15T18:45:30.123Z"
}
```

### 3. Check Browser Console

Open DevTools Console at https://applylens.app

Look for:
```
🔍 ApplyLens Web v0.6.0-phase5+abc123
Build: 2025-11-15T18:45:30.123Z
```

## Version Format Convention

Recommended format: `v{major}.{minor}.{patch}-{branch}+{sha}`

Examples:
- `v0.6.0-thread-viewer-v1+abc123`
- `v1.0.0-main+def456`
- `v0.5.2-feature-xyz+789abc`

## Implementation Details

### Files Modified

1. **`src/version.ts`** - Version export module
2. **`index.html`** - Added `<meta name="build-id">` tag
3. **`vite.config.ts`** - Added `versionJsonPlugin()`
4. **`src/main.tsx`** - Updated console log to use `buildInfo`
5. **`Dockerfile.prod`** - Added `APP_VERSION` build arg

### Files Created

1. **`build-with-version.example.sh`** - Linux/Mac build script example
2. **`build-with-version.example.ps1`** - Windows build script example

### Backward Compatibility

- ✅ If `VITE_APP_VERSION` not set, defaults to `"dev-local"`
- ✅ No breaking changes to existing builds
- ✅ Works with current CI/CD (just add `--build-arg APP_VERSION=...`)

## Troubleshooting

### Version shows "dev-local" in production

**Cause**: `VITE_APP_VERSION` not set during build

**Fix**: Add to Dockerfile build command:
```bash
--build-arg APP_VERSION="v0.6.0-thread-viewer-v1+$(git rev-parse --short HEAD)"
```

### version.json not found (404)

**Cause**: Plugin not running or outDir incorrect

**Fix**:
1. Check build logs for `[applylens-version-json] wrote...`
2. Verify `dist/version.json` exists after build
3. Check nginx config allows serving `.json` files

### Meta tag shows literal "%VITE_APP_VERSION%"

**Cause**: Vite not replacing placeholder (VITE_APP_VERSION not in env)

**Fix**: Set env var before build:
```bash
export VITE_APP_VERSION="your-version"
npm run build
```
