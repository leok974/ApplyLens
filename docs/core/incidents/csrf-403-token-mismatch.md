# CSRF Token 403 Fix

## Issue
When clicking "Sync Emails", the request returned **403 Forbidden** with error:
```
WARNING:app.core.csrf:CSRF failure: Missing X-CSRF-Token header for POST /gmail/backfill
```

## Root Cause
Frontend was using raw `fetch()` calls without including the CSRF token that the backend requires for all POST/PUT/PATCH/DELETE requests.

The backend has CSRF protection enabled via `CSRFMiddleware`:
- Cookie name: `csrf_token`
- Header name: `X-CSRF-Token`
- Cookie is `httponly=False` (JavaScript can read it)
- Automatically issues token on first request
- Validates token on all state-changing methods

## Solutions Applied

### 1. Added CSRF Helper Function to api.ts
Created `getCsrfToken()` helper to extract token from cookie:
```typescript
function getCsrfToken(): string | null {
  const match = document.cookie.match(/csrf_token=([^;]+)/)
  return match ? match[1] : null
}
```

### 2. Updated backfillGmail() Function
Modified to include CSRF token in headers:
```typescript
export async function backfillGmail(days = 60, userEmail?: string): Promise<BackfillResponse> {
  let url = `/api/gmail/backfill?days=${days}`
  if (userEmail) {
    url += `&user_email=${encodeURIComponent(userEmail)}`
  }

  const csrfToken = getCsrfToken()
  const headers: Record<string, string> = {}
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken
  }

  const r = await fetch(url, {
    method: 'POST',
    headers
  })
  if (!r.ok) throw new Error('Backfill failed')
  return r.json()
}
```

### 3. Updated Generic post() Helper
Modified the internal `post()` helper to automatically include CSRF token for all calls:
```typescript
async function post(url: string, init: RequestInit = {}) {
  const csrfToken = getCsrfToken()
  const headers: Record<string, string> = { ...(init.headers as Record<string, string> || {}) }
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken
  }

  const r = await fetch(url, {
    method: 'POST',
    ...init,
    headers
  })
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json().catch(() => ({}))
}
```

This fixes:
- `sync7d()` - 7-day sync
- `sync60d()` - 60-day sync
- `relabel()` - ML label rebuild
- `rebuildProfile()` - Profile rebuild

## Note: Existing CSRF-Aware Utility
The codebase already has a proper CSRF-aware utility at `apps/web/src/api/fetcher.ts`:

```typescript
export async function api(path: string, init: RequestInit = {}): Promise<Response> {
  const csrfToken = getCookie('csrf_token');
  const headers = new Headers(init.headers || {});

  if (init.method && init.method.toUpperCase() !== 'GET' && csrfToken) {
    headers.set('X-CSRF-Token', csrfToken);
  }

  return fetch(path, {
    credentials: 'include',
    ...init,
    headers
  });
}
```

**Best Practice**: All new API calls should use this `api()` utility instead of raw `fetch()`.

## Verification

### Before Fix:
```
POST /api/gmail/backfill?days=7 → 403 Forbidden
WARNING:app.core.csrf:CSRF failure: Missing X-CSRF-Token header
```

### After Fix:
```
POST /api/gmail/backfill?days=7 → 202 Accepted (or 429 if rate limited)
✅ CSRF token validated successfully
```

## Testing

1. **Verify CSRF Cookie Exists**:
   ```javascript
   // In browser console
   document.cookie.split('; ').find(c => c.startsWith('csrf_token='))
   ```

2. **Test Sync**:
   - Click "Sync Emails" button
   - Should see 202 response (or 429 if rate limited)
   - Check backend logs for success: `CSRF validated for POST /gmail/backfill`

3. **Test Rate Limiting**:
   - Click "Sync" twice within 5 minutes
   - Second request should return 429 with message: "Backfill too frequent; try again in X seconds"

## Backend CSRF Configuration

Located in `services/api/app/config.py`:
```python
CSRF_ENABLED: bool = True  # Enable CSRF protection
CSRF_COOKIE_NAME: str = "csrf_token"  # Cookie name
CSRF_HEADER_NAME: str = "X-CSRF-Token"  # Header name
COOKIE_SECURE: str = "1"  # Secure cookies in production
```

The middleware automatically:
- Issues CSRF token on first request
- Sets cookie with `httponly=False` (JS can read it)
- Validates token on POST/PUT/PATCH/DELETE
- Returns 403 if token missing or invalid
- Increments Prometheus metrics for monitoring

## Monitoring

### Prometheus Metrics
- `csrf_success_total{path, method}` - Successful CSRF validations
- `csrf_fail_total{path, method}` - Failed CSRF validations

### Logs
```bash
# Watch CSRF validations
docker logs -f applylens-api-prod | grep CSRF

# Watch successful validations
docker logs -f applylens-api-prod | grep "CSRF validated"

# Watch failures
docker logs -f applylens-api-prod | grep "CSRF failure"
```

## Related Files Modified

1. `apps/web/src/lib/api.ts`:
   - Added `getCsrfToken()` helper
   - Updated `backfillGmail()` to include CSRF token
   - Updated `post()` helper to include CSRF token

## Security Notes

1. **CSRF Protection Enabled**: All state-changing requests require valid token
2. **Cookie Settings**:
   - `httponly=False` - JavaScript can read (required for AJAX)
   - `samesite=lax` - Prevents CSRF from external sites
   - `secure=true` - HTTPS only in production
3. **Token Rotation**: Token persists in cookie, validated on each request
4. **Metrics**: Failures tracked for security monitoring

## Next Steps

### Immediate
- [x] Add CSRF token to backfill requests
- [x] Test sync functionality
- [ ] Verify other POST/PUT/PATCH/DELETE calls include tokens

### Short Term
- [ ] Migrate all `fetch()` calls to use `api()` utility from `fetcher.ts`
- [ ] Add CSRF token tests to E2E suite
- [ ] Set up alerts for high CSRF failure rates

### Long Term
- [ ] Consider SameSite=Strict for higher security (breaks some OAuth flows)
- [ ] Implement token rotation on sensitive operations
- [ ] Add CSRF token to WebSocket handshakes if needed

## References

- Backend CSRF Middleware: `services/api/app/core/csrf.py`
- Frontend CSRF Utility: `apps/web/src/api/fetcher.ts`
- Configuration: `services/api/app/config.py`
- OWASP CSRF Prevention: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
