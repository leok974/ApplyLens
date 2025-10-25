# 🔄 Browser Cache Issue - v0.4.6

## Problem

The new code (v0.4.6) is deployed but the browser is serving the **old cached bundle**.

**Evidence:**
- Container has correct bundle: `index-1761250154861.CxkYtgkw.js` ✅
- Source file has correct fix: `window.location.origin` ✅
- But browser still requests `/web/search/` ❌

This means the browser cached the old JavaScript and hasn't fetched the new version.

## Solution: Force Browser to Reload

### Try these in order:

### 1. **Hard Refresh (Recommended)**
**Windows/Linux:**
- `Ctrl + Shift + R`
- OR `Ctrl + F5`

**Mac:**
- `Cmd + Shift + R`

### 2. **Clear Site Data**
1. Open DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### 3. **Clear Cache Manually**
1. Open DevTools (F12)
2. Go to Application tab → Storage → Clear site data
3. Check "Cached images and files"
4. Click "Clear site data"
5. Close DevTools and refresh

### 4. **Incognito/Private Window**
Open https://applylens.app/web/search in a new incognito window to bypass all cache.

## How to Verify It Worked

After hard refresh, check Network tab (F12 → Network):

**Before (cached):**
```
GET /web/search/?q=Interview...
Status: 200
Type: document (HTML)
```

**After (fixed):**
```
GET /api/search?q=Interview...
Status: 200 (or 401)
Type: xhr
Content-Type: application/json
```

## Why This Happens

Browsers aggressively cache JavaScript bundles for performance. When the bundle name changes (from `index-1761239234490.B53W7y_K.js` to `index-1761250154861.CxkYtgkw.js`), the browser should fetch the new one, but sometimes:

1. Service workers cache the `index.html`
2. HTTP cache headers tell browser to reuse files
3. Browser doesn't notice bundle name changed

A hard refresh forces the browser to:
- Ignore cache
- Re-download `index.html`
- Re-download all assets
- Execute new code

## Alternative: Version in URL

If this keeps happening, we can add cache-busting to the build:

```typescript
// vite.config.ts
build: {
  rollupOptions: {
    output: {
      assetFileNames: `assets/[name]-[hash]-${Date.now()}.[ext]`,
    }
  }
}
```

But for now, **just do a hard refresh (Ctrl+Shift+R)** and the new code will run! 🔄

---

**The fix IS deployed**, just need to reload the page properly!
