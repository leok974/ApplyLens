# Deployment Validation Guardrails

**DO NOT BLAME CLOUDFLARE BY DEFAULT**

When deployments "look stale" or "aren't working", follow this checklist **in order**:

---

## 1. Is the container running the new image?

```powershell
# Check image tag
docker ps --filter "name=applylens-web-prod" --format "IMAGE={{.Image}}  STATUS={{.Status}}"

# Get exact image ID
docker inspect applylens-web-prod --format "{{.Image}}"

# Compare with available images
docker image ls leoklemet/applylens-web --format "{{.Repository}}:{{.Tag}}  {{.ID}}"
```

**Guardrail**: If the image ID doesn't match the newly built image, **Cloudflare is irrelevant**. You're serving the old container.

**Fix**:
```powershell
# Pull new tag (if pushed to registry)
docker pull leoklemet/applylens-web:thread-viewer-v1

# Recreate container
docker stop applylens-web-prod
docker rm applylens-web-prod
# ... run with new image
```

---

## 2. Does the app report the new version?

### Check version endpoint

```powershell
curl -s https://applylens.app/version.json
```

**If 404**: Need to add `version.json` to web app (see below)

### Check HTML metadata

```powershell
curl -s https://applylens.app/ | Select-String "build-id"
```

**Expected**: `<meta name="build-id" content="thread-viewer-v1-2025-11-15" />`

**If empty**: Build process doesn't inject version metadata

### Browser DevTools check

1. Open `https://applylens.app` in **incognito window**
2. Open DevTools → Network tab
3. **Check "Disable cache"**
4. Reload page
5. Search main JS bundle for version string

**Guardrail**: If bundle contains old version (e.g. `v0.4.64`), your container is old OR build pipeline didn't update version string.

---

## 3. Are tests pointed at the right URL?

### Prod API smoke tests

```powershell
# These hit https://api.applylens.app (JSON only, no UI)
$env:APPLYLENS_PROD_API_BASE='https://api.applylens.app'
npx playwright test e2e/prod-companion-smoke.spec.ts
```

**Guardrail**: Cloudflare caching on API should be minimal (`Cache-Control: no-store`)

### Bandit E2E tests (LOCAL)

```powershell
# These hit http://127.0.0.1:5177 (or whatever playwright.config.ts says)
npx playwright test e2e/autofill-bandit.spec.ts
```

**Guardrail**: **Cloudflare never sees these requests**. If behavior is "still the same":
- Check test harness structure (`autofill-bandit.spec.ts`)
- Verify port/baseURL in `playwright.config.ts`
- Ensure test actually calls `runScanAndSuggest()`

---

## 4. Check Cloudflare cache status (LAST)

**Only check this AFTER steps 1-3 pass.**

```powershell
# Main page
curl -I https://applylens.app/ 2>&1 | Select-String "CF-Cache-Status"

# Assets
curl -I https://applylens.app/assets/index.js 2>&1 | Select-String "CF-Cache-Status"
```

**Expected**: `CF-Cache-Status: DYNAMIC` or `MISS` or `BYPASS`

**Guardrail**: If status is `DYNAMIC` or `MISS`, **stop blaming Cloudflare**. The edge is NOT serving stale assets.

### Cache purge (if needed)

```bash
# Full cache clear
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'
```

**Note**: Cache purge is NOT instant (5-10 min), but if `CF-Cache-Status` shows `MISS`, purge already happened.

---

## Common Mistakes

### ❌ "Just waiting for Cloudflare cache clearance"

**Wrong assumption**: Cache was the bottleneck

**Reality check**:
1. Container running old image → redeploy container
2. Build doesn't embed version → fix build pipeline
3. Test pointing at wrong URL → fix test config

### ❌ "Cloudflare is caching my API responses"

**Check first**:
```powershell
curl -I https://api.applylens.app/profile/me 2>&1 | Select-String "Cache-Control|CF-Cache-Status"
```

**Expected**:
- `Cache-Control: no-store, no-cache, must-revalidate`
- `CF-Cache-Status: DYNAMIC`

**If seeing HIT**: API endpoints missing cache headers (backend issue, not Cloudflare)

### ❌ "Bandit E2E test failing because of stale cache"

**Reality**: E2E tests run locally on `http://127.0.0.1:5177` → Cloudflare never sees these requests

**Actual issues**:
- Test harness doesn't call `runScanAndSuggest()` properly
- Port mismatch in `playwright.config.ts`
- Test expects structure that changed in `thread-viewer-v1` branch

---

## Version Tracking Setup

### Add version.json endpoint

**File**: `apps/web/public/version.json`

```json
{
  "version": "thread-viewer-v1",
  "buildDate": "2025-11-15T19:30:00Z",
  "commitSha": "abc123def",
  "env": "production"
}
```

**Auto-generate during build** (in `apps/web/package.json`):

```json
{
  "scripts": {
    "build": "vite build && node scripts/write-version.js"
  }
}
```

**File**: `apps/web/scripts/write-version.js`

```javascript
const fs = require('fs');
const path = require('path');

const version = {
  version: process.env.VERSION || 'dev',
  buildDate: new Date().toISOString(),
  commitSha: process.env.COMMIT_SHA || 'local',
  env: process.env.NODE_ENV || 'production'
};

const versionPath = path.join(__dirname, '../dist/version.json');
fs.writeFileSync(versionPath, JSON.stringify(version, null, 2));
console.log('✅ Version file written:', versionPath);
```

### Update HTML metadata

**File**: `apps/web/index.html`

```html
<meta name="build-id" content="%BUILD_ID%" />
<meta name="version" content="%VERSION%" />
```

**Replace during build** (in Vite config or build script):

```javascript
// vite.config.ts
export default {
  define: {
    __BUILD_ID__: JSON.stringify(process.env.BUILD_ID || 'dev'),
    __VERSION__: JSON.stringify(process.env.VERSION || 'dev')
  }
}
```

---

## Validation Checklist

Use this EVERY deployment:

- [ ] **Container check**: `docker ps` shows new image tag/ID
- [ ] **Version endpoint**: `curl https://applylens.app/version.json` returns new version
- [ ] **HTML metadata**: `build-id` meta tag shows new version
- [ ] **Browser test**: Incognito + DevTools + Disable cache confirms new bundle
- [ ] **CF cache status**: `CF-Cache-Status` is `DYNAMIC` or `MISS`
- [ ] **Test URLs**: Prod tests hit `https://api.applylens.app`, E2E hit `localhost`

**Only if ALL above pass**, then investigate Cloudflare caching.

---

## Quick Reference

| Issue | First Check | NOT Cloudflare |
|-------|-------------|----------------|
| Website looks old | Container image ID | ✅ |
| API returning stale data | `Cache-Control` headers | ✅ |
| E2E test failing | Test baseURL (`localhost`) | ✅ |
| Version string wrong | Build pipeline injects version | ✅ |
| Assets 404 after deploy | Container has new files | ✅ |

**Last Updated**: 2025-11-15
**Author**: Leo Klemet
