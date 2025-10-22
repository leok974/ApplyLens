# 🐛 Self-Refreshing Page Prevention

## Overview

This implementation prevents infinite page reload loops in the ApplyLens web application by implementing multiple safeguards:

1. **Reload Guard** - Prevents rapid consecutive reloads
2. **Service Worker Registration** - Safe SW update handling
3. **Build ID Tracking** - Version-aware reload logic

## Files Added

### 1. `src/lib/reload-guard.ts`
Global reload protection that prevents any code from reloading the page more than once per 5 seconds.

**Features:**
- 5-second cooldown between reloads
- sessionStorage-based tracking
- Patches `window.location.reload()` globally
- Provides safe reload utilities

**Usage:**
```typescript
import { safeReload, canReload, resetReloadGuard } from '@/lib/reload-guard'

// Check if safe to reload
if (canReload()) {
  window.location.reload()
}

// Or use the safe wrapper
safeReload() // Returns true if reload triggered, false if blocked
```

### 2. `src/lib/sw-register.ts`
Service worker registration with update-aware reload logic.

**Features:**
- Disabled on localhost (development)
- Only reloads ONCE per build ID
- Waits for `activated` state before reloading
- Hourly update checks

**Usage:**
```typescript
import { registerServiceWorker } from '@/lib/sw-register'

// Register during app initialization
registerServiceWorker().catch(console.error)
```

**Note:** Currently commented out in `main.tsx` until you have a `public/sw.js` file.

### 3. `vite.config.ts` Updates
Added build ID injection and cache busting.

**Features:**
- Generates unique build ID per deployment
- Injects build ID into HTML meta tag
- Adds build ID to asset filenames
- Exposes `__BUILD_ID__` global variable

## How It Works

### Reload Guard Flow
```
User Action → Reload Triggered
                ↓
        Check Last Reload Time
                ↓
    < 5 seconds? → Block (log warning)
    > 5 seconds? → Allow (record timestamp)
                ↓
        Page Reloads
```

### Service Worker Flow
```
SW Update Available
        ↓
Installing → Installed → Activating → Activated
                                        ↓
                            controllerchange event
                                        ↓
                        Check sessionStorage
                                        ↓
            Already reloaded for this build? → Skip
            First reload for this build? → Reload (mark done)
```

## Integration Points

### 1. Application Entry (`main.tsx`)
```typescript
import { installGlobalReloadGuard } from './lib/reload-guard'

// Install early - before any other code runs
installGlobalReloadGuard()
```

### 2. Error Boundaries
If you add React error boundaries, use the safe reload:

```typescript
import { safeReload } from '@/lib/reload-guard'

class ErrorBoundary extends React.Component {
  componentDidCatch(error, errorInfo) {
    // Log error...

    // Safe reload instead of direct reload
    if (this.state.errorCount > 3) {
      safeReload() // Only reloads if > 5s since last reload
    }
  }
}
```

### 3. Auth Refresh Logic
If you implement token refresh, use safe reload:

```typescript
async function refreshToken() {
  try {
    const response = await fetch('/api/auth/refresh')
    if (!response.ok) {
      // Use safe reload instead of direct reload
      safeReload()
    }
  } catch (error) {
    safeReload()
  }
}
```

## Debugging

### Check Reload Guard Status
Open DevTools Console:
```javascript
// Check if reload is allowed
sessionStorage.getItem('reload_guard_timestamp')

// Reset guard (allow immediate reload)
sessionStorage.removeItem('reload_guard_timestamp')

// Manually trigger safe reload
window.location.reload() // Blocked if < 5s since last reload
```

### Check Service Worker State
```javascript
// List registered service workers
navigator.serviceWorker.getRegistrations()

// Check current build ID
document.querySelector('meta[name="build-id"]').content
window.__BUILD_ID__

// Check reload tracking
Object.keys(sessionStorage).filter(k => k.startsWith('sw_reload_'))
```

### Disable Service Worker
```typescript
import { unregisterServiceWorker } from '@/lib/sw-register'

// Unregister all service workers
await unregisterServiceWorker()

// Then hard reload
window.location.reload()
```

## Testing Checklist

- [ ] Page loads normally in development (localhost)
- [ ] Page loads normally in production
- [ ] Rapid reload attempts are blocked (< 5s cooldown)
- [ ] Service worker (when enabled) only reloads once per build
- [ ] DevTools console shows reload guard messages
- [ ] No infinite reload loops occur
- [ ] Build ID is visible in HTML meta tag
- [ ] Build ID is accessible via `window.__BUILD_ID__`

## Common Issues

### Issue: Page still reloads repeatedly
**Solution:** Check console for non-guarded reload sources:
```bash
# Search for direct reload calls
grep -r "location.reload" apps/web/src
grep -r "window.location.reload" apps/web/src

# Replace with safe reload
import { safeReload } from '@/lib/reload-guard'
safeReload()
```

### Issue: Service worker not updating
**Solution:**
1. Check console for SW registration errors
2. Verify `/sw.js` exists in public folder
3. Try hard reload: Ctrl+Shift+R (Chrome) / Cmd+Shift+R (Mac)
4. Unregister SW and retry

### Issue: Reload guard too aggressive
**Solution:** Adjust cooldown in `reload-guard.ts`:
```typescript
const RELOAD_COOLDOWN_MS = 3000; // 3 seconds instead of 5
```

## Production Deployment

### Build Process
```bash
# Build with custom build ID
BUILD_ID=v1.2.3 npm run build

# Or let it auto-generate
npm run build  # Uses timestamp
```

### Environment Variables
```bash
# Optional: Set custom build ID
BUILD_ID=v1.2.3

# Existing Vite variables still work
VITE_API_BASE=/api
VITE_BASE_PATH=/
```

### Verification
After deployment, check:
```javascript
// Should match your build ID
console.log(window.__BUILD_ID__)
console.log(document.querySelector('meta[name="build-id"]').content)
```

## Future Enhancements

- [ ] Add service worker when offline support is needed
- [ ] Implement WebSocket reconnect with backoff
- [ ] Add React Query with `refetchIntervalInBackground: false`
- [ ] Create error boundary with safe reload logic
- [ ] Add reload attempt metrics/logging

## References

- Original fix document: `self_refreshing_page_rapid_triage_fix_apply_lens_web.md`
- Service Worker API: https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API
- Vite Build Config: https://vitejs.dev/config/build-options.html
