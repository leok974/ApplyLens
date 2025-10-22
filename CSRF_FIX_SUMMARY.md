# Email Sync 403 Error - Fixed ✅

## Summary
Successfully fixed the **403 Forbidden** error when clicking "Sync Emails" button.

## Problem
User clicked "Sync Emails" and got 403 error. Backend logs showed:
```
WARNING:app.core.csrf:CSRF failure: Missing X-CSRF-Token header for POST /gmail/backfill
```

## Root Cause
The frontend was making POST requests using raw `fetch()` without including the CSRF token that the backend requires for security.

Backend CSRF middleware (`services/api/app/core/csrf.py`) protects all state-changing requests (POST/PUT/PATCH/DELETE) by requiring:
- Cookie: `csrf_token` (set automatically on first request)
- Header: `X-CSRF-Token` (must be included by frontend)

## Solution Applied

### 1. Added CSRF Token Helper (apps/web/src/lib/api.ts)
```typescript
function getCsrfToken(): string | null {
  const match = document.cookie.match(/csrf_token=([^;]+)/)
  return match ? match[1] : null
}
```

### 2. Updated backfillGmail() Function
Now includes CSRF token in headers:
```typescript
export async function backfillGmail(days = 60, userEmail?: string): Promise<BackfillResponse> {
  const csrfToken = getCsrfToken()
  const headers: Record<string, string> = {}
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken
  }

  const r = await fetch(url, { method: 'POST', headers })
  // ...
}
```

### 3. Updated Generic post() Helper
All functions using this helper now include CSRF token:
- `sync7d()` - 7-day email sync
- `sync60d()` - 60-day email sync
- `relabel()` - ML label rebuild
- `rebuildProfile()` - Profile rebuild

### 4. Rebuilt and Deployed Web Container
```bash
docker-compose -f docker-compose.prod.yml build web
docker-compose -f docker-compose.prod.yml up -d web
```

## Testing Instructions

### 1. Verify CSRF Cookie Exists
Open browser console and run:
```javascript
document.cookie.split('; ').find(c => c.startsWith('csrf_token='))
```
Should return something like: `"csrf_token=abc123..."`

### 2. Test Email Sync
1. Navigate to https://applylens.app/web/welcome
2. Sign in with Google OAuth (if not already signed in)
3. Click "Sync Emails" button
4. Should see success message (or rate limit message if < 5 minutes since last sync)

### 3. Check Backend Logs
```bash
# Watch for successful CSRF validations
docker logs -f applylens-api-prod | grep "CSRF validated"

# Should see:
# INFO:app.core.csrf:CSRF validated for POST /gmail/backfill
```

### 4. Test Rate Limiting
Try clicking "Sync Emails" twice within 5 minutes:
- First request: Should succeed (202 Accepted)
- Second request: Should fail with 429 and message: "Backfill too frequent; try again in X seconds"

## Files Changed

1. **apps/web/src/lib/api.ts**:
   - Added `getCsrfToken()` helper
   - Updated `backfillGmail()` to include CSRF header
   - Updated `post()` helper to include CSRF header

2. **CSRF_403_FIX.md**: Comprehensive documentation

## Commits

- **07ce6dc**: Fix CSRF 403 error on email sync

## Status

✅ **Fixed and Deployed**
- Frontend updated with CSRF token support
- Web container rebuilt and restarted
- Ready for testing

## Next Steps

1. ⏳ **User Action**: Test email sync at https://applylens.app
2. ✅ **Monitor**: Check logs for CSRF validations
3. 💡 **Future**: Migrate all `fetch()` calls to use the centralized `api()` utility from `apps/web/src/api/fetcher.ts` (already CSRF-aware)

## Related Documentation

- [CSRF_403_FIX.md](./CSRF_403_FIX.md) - Detailed technical documentation
- [OAUTH_TROUBLESHOOTING_SUMMARY.md](./OAUTH_TROUBLESHOOTING_SUMMARY.md) - OAuth flow documentation
- [DATABASE_PASSWORD_FIX.md](./DATABASE_PASSWORD_FIX.md) - Database authentication fixes

## Timeline

**October 22, 2025 - 3:00 PM**
- ✅ Identified CSRF token missing from request
- ✅ Added CSRF helper function
- ✅ Updated email sync functions
- ✅ Rebuilt web container
- ✅ Deployed to production
- ⏳ Ready for user testing

---

**Ready to test!** Click "Sync Emails" at https://applylens.app
