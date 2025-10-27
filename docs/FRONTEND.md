# Frontend

## Reload Loop Prevention / Session Stability

### Overview

ApplyLens implements multiple safeguards to prevent infinite page reload loops:

1. **Reload Guard** - Prevents rapid consecutive reloads
2. **Service Worker Registration** - Safe SW update handling
3. **Build ID Tracking** - Version-aware reload logic

### Reload Guard

Global reload protection that prevents any code from reloading the page more than once per 5 seconds.

**Location**: `apps/web/src/lib/reload-guard.ts`

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

### Service Worker Registration

Service worker registration with update-aware reload logic.

**Location**: `apps/web/src/lib/sw-register.ts`

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

### Build ID Tracking

**Configuration** in `vite.config.ts`:
- Generates unique build ID per deployment
- Injects build ID into HTML meta tag
- Adds build ID to asset filenames
- Exposes `__BUILD_ID__` global variable

**Verification:**
```javascript
// Check current build ID in console
console.log(window.__BUILD_ID__)
console.log(document.querySelector('meta[name="build-id"]').content)
```

### Integration Points

**Application Entry (`main.tsx`):**
```typescript
import { installGlobalReloadGuard } from './lib/reload-guard'

// Install early - before any other code runs
installGlobalReloadGuard()
```

**Error Boundaries:**
```typescript
import { safeReload } from '@/lib/reload-guard'

class ErrorBoundary extends React.Component {
  componentDidCatch(error, errorInfo) {
    // Log error...
    if (this.state.errorCount > 3) {
      safeReload() // Only reloads if > 5s since last reload
    }
  }
}
```

### Debugging

**Check Reload Guard Status:**
```javascript
// Check if reload is allowed
sessionStorage.getItem('reload_guard_timestamp')

// Reset guard (allow immediate reload)
sessionStorage.removeItem('reload_guard_timestamp')

// Manually trigger safe reload
window.location.reload() // Blocked if < 5s since last reload
```

**Check Service Worker State:**
```javascript
// List registered service workers
navigator.serviceWorker.getRegistrations()

// Check reload tracking
Object.keys(sessionStorage).filter(k => k.startsWith('sw_reload_'))
```

### Common Issues

**Issue: Page still reloads repeatedly**
- Check console for non-guarded reload sources
- Search codebase for direct `location.reload()` calls
- Replace with `safeReload()` from reload-guard

**Issue: Reload guard too aggressive**
- Adjust cooldown in `reload-guard.ts`:
```typescript
const RELOAD_COOLDOWN_MS = 3000; // 3 seconds instead of 5
```

For detailed reload prevention procedures, see `apps/web/RELOAD_PREVENTION.md`.
