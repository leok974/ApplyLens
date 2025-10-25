# 🔍 Root Cause Analysis: HTML Instead of JSON

## The Error (v0.4.5 Diagnostics)

```javascript
[search] Invalid content-type {
  contentType: 'text/html',
  url: 'https://applylens.app/web/search/?q=Interview...',  // ❌ WRONG!
  status: 200
}
[search] Response body: <!doctype html>...
```

## Root Cause

**The app was requesting its own HTML page instead of the backend API!**

### Why?

```typescript
// Original code (v0.4.5 and earlier)
fetch(`/api/search?${params}`)
```

When built with `BASE_PATH=/web/`, this **relative URL** gets resolved against the base:
- Base: `/web/`
- Path: `/api/search`
- **Resolved to:** `/web/api/search` → 404 → React Router → `/web/search/` HTML page

## The Fix (v0.4.6)

```typescript
// New code
const apiUrl = `${window.location.origin}/api/search?${params.toString()}`
fetch(apiUrl)
```

Now:
- Origin: `https://applylens.app`
- Path: `/api/search`
- **Result:** `https://applylens.app/api/search` ✅

## Visual Comparison

### Before (v0.4.5)
```
User → Web App → fetch('/api/search')
                   ↓
              Vite BASE_PATH=/web/
                   ↓
              Resolved: /web/api/search
                   ↓
              Nginx → 404 (no such route)
                   ↓
              Falls back to: /web/search/ (React Router)
                   ↓
              Returns: HTML page ❌
```

### After (v0.4.6)
```
User → Web App → fetch('https://applylens.app/api/search')
                   ↓
              Absolute URL (not affected by BASE_PATH)
                   ↓
              Nginx → /api/search
                   ↓
              Proxy to: api:8003/search
                   ↓
              Returns: JSON or 401 ✅
```

## Key Insight

**The v0.4.5 diagnostics worked perfectly!** They showed:
1. ✅ Actual URL requested: `/web/search/` (wrong)
2. ✅ Content-Type: `text/html` (not JSON)
3. ✅ Response body: `<!doctype html>` (HTML page)

This made the root cause immediately obvious.

## Test Now

1. Open: https://applylens.app/web/search
2. Search: "Interview"
3. Check Network tab:
   - ✅ URL should be `/api/search` (not `/web/search/`)
   - ✅ Content-Type should be `application/json` (or 401 if auth required)

---

**v0.4.6 is deployed!** 🚀
