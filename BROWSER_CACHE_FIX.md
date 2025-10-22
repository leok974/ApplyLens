# Browser Cache Issue - Quick Fix

## Problem
You're seeing 400/403 errors because your browser is using **old cached JavaScript** that doesn't include the CSRF token fix.

## Solution: Clear Browser Cache

### Option 1: Hard Refresh (Fastest)
**Windows/Linux:**
- Chrome/Edge: `Ctrl + Shift + R` or `Ctrl + F5`
- Firefox: `Ctrl + Shift + R` or `Ctrl + F5`

**Mac:**
- Chrome/Safari: `Cmd + Shift + R`
- Firefox: `Cmd + Shift + R`

### Option 2: Clear Cache via DevTools
1. Open DevTools (`F12` or right-click → Inspect)
2. Right-click the refresh button
3. Select **"Empty Cache and Hard Reload"**

### Option 3: Manual Cache Clear
1. Open browser settings
2. Go to Privacy/Security
3. Clear browsing data
4. Select "Cached images and files"
5. Click Clear

### Option 4: Incognito/Private Window
Open https://applylens.app in a new incognito/private window (bypasses cache)

## After Clearing Cache

1. Navigate to https://applylens.app
2. Press `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac) to hard refresh
3. Sign in if needed
4. Try "Sync Emails" again

You should now see the new JavaScript file with CSRF token support.

## Verify It Worked

Open browser console (`F12` → Console tab) and run:
```javascript
// Check if new code is loaded (should show getCsrfToken function)
document.cookie.split('; ').find(c => c.startsWith('csrf_token='))
```

If you see `csrf_token=...` then the CSRF cookie exists and the new code should work!

## Why This Happened

1. We deployed new JavaScript code at 19:19 (3:19 PM)
2. Your browser cached the old JavaScript from before
3. The old code doesn't include CSRF token headers
4. Backend rejects requests without CSRF token (403/400)

## The 404 Error

The `/api/metrics/divergence-24h` 404 is a separate issue - that endpoint doesn't exist yet. It's not breaking anything, just a missing optional feature.

---

**TL;DR: Press `Ctrl+Shift+R` (or `Cmd+Shift+R`) to hard refresh the page!**
