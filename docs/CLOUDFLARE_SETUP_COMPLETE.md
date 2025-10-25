# ✅ Cloudflare Cache Configuration Complete!

## Summary

**Date**: October 23, 2025 22:01 UTC
**Status**: ✅ **SUCCESSFULLY CONFIGURED**

### What Was Done

1. ✅ Created Cloudflare cache ruleset (ID: `3003b050d6fe4d66a4e96ccdca7b8163`)
2. ✅ Configured 2 cache rules:
   - **Rule 1**: Bypass cache for HTML (`/`, `/web/`, `*/index.html`)
     → Ensures browsers always get fresh HTML with latest bundle hashes
   - **Rule 2**: Immutable 1-year cache for assets (`/assets/*`, `*.js`, `*.css`, fonts, images)
     → CDN caches bundles forever by content hash
3. ✅ Purged HTML files from Cloudflare cache
4. ✅ Nginx cache headers already configured (v0.4.10)

---

## 🚀 NEXT STEP: Browser Verification (YOU MUST DO THIS)

### Step 1: Clear Browser Cache Completely

**Chrome/Edge:**
1. Open DevTools (F12)
2. Go to **Application** tab
3. Click **"Clear storage"** in left sidebar
4. ✅ Check **ALL** boxes:
   - [x] Application cache
   - [x] Cache storage
   - [x] Cookies
   - [x] File systems
   - [x] IndexedDB
   - [x] Local storage
   - [x] Service workers
   - [x] Session storage
   - [x] Web SQL
5. Click **"Clear site data"** button
6. **IMPORTANT**: Close ALL tabs of applylens.app
7. Open **fresh tab**

**Alternative - Hard Refresh:**
- Chrome/Edge: `Ctrl + Shift + R` or `Ctrl + F5`
- Firefox: `Ctrl + F5`
- Or use Incognito/Private window

---

### Step 2: Verify Version

1. Go to: **https://applylens.app/web/search**
2. Open Console (F12 → Console tab)
3. Look for the banner:
   ```
   🔍 ApplyLens Web v0.4.10
   Build: 461336d @ 2025-10-23T20:58:00Z
   Fix: apiUrl helper for absolute API URLs
   ```

**If you DON'T see v0.4.10:**
- Your browser is still using cached files
- Try incognito mode
- Or wait 5 more minutes and try again

---

### Step 3: Install Fetch Interceptor (Debug Tool)

Paste this in the Console to see all API calls:

```javascript
(function(){
  const orig = window.fetch;
  window.fetch = async function(i, init){
    const url = typeof i==='string'?i:i.url;
    console.info('[FETCH]', url, init?.method||'GET');
    return orig.apply(this, arguments);
  };
  console.log('✅ Fetch interceptor installed');
})();
```

---

### Step 4: Test Search

1. Click the **Search** button
2. In Console, you should see:
   ```
   [FETCH] https://applylens.app/api/search?q=... GET
   ```

**✅ CORRECT**: URL is `/api/search`
**❌ WRONG**: URL is `/web/search/` (old cached bundle)

3. In **Network** tab (F12 → Network):
   - Filter by "Fetch/XHR"
   - Look for `search?q=...` request
   - Click it → Check **Response** tab
   - Should see JSON data (not HTML!)

---

## Expected Results

### HTML Headers (Cloudflare)
```http
GET https://applylens.app/web/

Status: 200 OK
Content-Type: text/html
Cache-Control: no-cache, no-store, must-revalidate
CF-Cache-Status: BYPASS (or DYNAMIC)
```

### JS Bundle Headers (Cloudflare)
```http
GET https://applylens.app/assets/index-1761254202682.CgHkWaq5.js

Status: 200 OK
Content-Type: application/javascript
Cache-Control: public, max-age=31536000, immutable
CF-Cache-Status: HIT (after first load)
```

### API Headers
```http
GET https://applylens.app/api/search?q=test&limit=1

Status: 200 OK (or 401 if not logged in)
Content-Type: application/json
```

---

## Troubleshooting

### Still Seeing Old Bundle?

**Check bundle filename in DevTools:**
1. Open DevTools (F12)
2. Go to **Sources** tab
3. Expand `applylens.app` → `assets`
4. Look for `index-*.js` file
5. Should be: `index-1761254202682.CgHkWaq5.js` (v0.4.10)
6. If different hash → browser cached HTML

**Solutions:**
- Clear storage again (see Step 1 above)
- Try incognito window
- Wait 5-10 minutes (CDN propagation)

### Search Still Goes to `/web/search/`?

This means old bundle is still loaded.

**Verify:**
```javascript
// In Console
console.log(window.location.pathname); // Should be /web/search
```

**Fix:**
1. Check Console for version banner (should be v0.4.10)
2. If wrong version, clear cache again
3. Hard refresh: Ctrl+Shift+R

### API Returns HTML Instead of JSON?

**If you're not logged in:**
- API returns 401 redirect → HTML login page
- This is EXPECTED behavior
- Try logging in first

**If you ARE logged in:**
1. Check Network tab → Click failed request
2. Look at **Request URL**
3. Should be `https://applylens.app/api/search?...`
4. NOT `https://applylens.app/web/search/...`

---

## Success Checklist

- [ ] Console shows: `🔍 ApplyLens Web v0.4.10`
- [ ] Fetch interceptor shows: `[FETCH] https://applylens.app/api/search?...`
- [ ] Network tab shows: Request to `/api/search` (not `/web/search/`)
- [ ] Response is JSON (not HTML with `<!DOCTYPE html>`)
- [ ] No more "Unexpected token '<'" errors
- [ ] Search functionality works

---

## Technical Details

### Cloudflare Cache Rules

**Ruleset ID**: `3003b050d6fe4d66a4e96ccdca7b8163`

**Rule 1 - Bypass HTML**:
```json
{
  "description": "Bypass cache for HTML entry points (always fetch fresh asset hashes)",
  "action": "set_cache_settings",
  "action_parameters": { "cache": false },
  "expression": "(http.request.uri.path eq \"/\" or starts_with(http.request.uri.path, \"/web/\") or ends_with(http.request.uri.path, \"/index.html\"))",
  "enabled": true
}
```

**Rule 2 - Immutable Assets**:
```json
{
  "description": "Immutable cache for hashed assets (1 year for js/css/fonts/images)",
  "action": "set_cache_settings",
  "action_parameters": {
    "cache": true,
    "edge_ttl": { "mode": "override_origin", "default": 31536000 },
    "browser_ttl": { "mode": "respect_origin" }
  },
  "expression": "(starts_with(http.request.uri.path, \"/assets/\") or ends_with(http.request.uri.path, \".js\") or ends_with(http.request.uri.path, \".css\") or ...)",
  "enabled": true
}
```

### Bundle Info

- **Version**: v0.4.10
- **Bundle**: `index-1761254202682.CgHkWaq5.js`
- **Size**: 824,560 bytes
- **Build Time**: October 23, 2025 21:16 UTC
- **Git SHA**: 461336d

---

## Scripts for Future Use

### Check Cache Rules
```powershell
.\scripts\Verify-CloudflareCacheRules.ps1
```

### Purge HTML Cache (after new deployment)
```powershell
.\scripts\Purge-CloudflareCache.ps1
```

### Purge Everything (nuclear option)
```powershell
.\scripts\Purge-CloudflareCache.ps1 -PurgeEverything
```

### Set Credentials (new session)
```powershell
$env:CLOUDFLARE_API_TOKEN = "muFUbNoqVzucDwPRjIhcmnRQM3JMrtEcFW8Jogb1"
$env:CLOUDFLARE_ZONE_ID = "8b18d6fe5e67a5507f4db885748fbfe6"
```

---

## Support

If issues persist after following all steps:
1. Check nginx logs: `docker logs applylens-web-prod --tail 50`
2. Check API logs: `docker logs applylens-api-prod --tail 50`
3. Verify nginx config: `docker exec applylens-web-prod nginx -T | grep "location"`
4. Run verification: `.\scripts\Verify-Deployment.ps1 -BaseUrl "https://applylens.app"`

**Last updated**: October 23, 2025 22:01 UTC
**Status**: ✅ Ready for browser verification
