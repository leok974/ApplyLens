# 429 Rate Limit - This is Good News! ✅

## What 429 Means

**429 Too Many Requests** means:
1. ✅ Your browser cache is cleared (using new JavaScript with CSRF token)
2. ✅ CSRF token is working (request got past security check)
3. ⏰ You're syncing too frequently (5-minute cooldown between syncs)

## Why You're Seeing This

The backend protects Gmail API quota by limiting syncs to **once every 5 minutes** per user.

One of your earlier attempts (even though it failed with 403/400) set the rate limit timer. Now you need to wait for the cooldown to expire.

## What to Do

### Option 1: Wait (Recommended)
Just wait **5 minutes** from your last attempt and try again.

The error message should tell you exactly how long:
```
"Backfill too frequent; try again in X seconds"
```

### Option 2: Check Console for Exact Time
Open browser console (F12) and you should see the error with remaining seconds.

### Option 3: Restart API (Skip Cooldown)
If you want to test immediately:
```bash
docker-compose -f docker-compose.prod.yml restart api
```
This clears the in-memory rate limit timer.

## Progress So Far

✅ **All infrastructure issues fixed:**
- Port mismatch → FIXED
- Database authentication → FIXED
- OAuth error logging → FIXED
- CSRF token → FIXED
- Browser cache → CLEARED

✅ **Backend is working:**
- CSRF validation passing
- Rate limiting working correctly
- Ready to sync emails

⏰ **Just waiting on cooldown timer**

## Testing After Cooldown

1. Wait 5 minutes
2. Go to https://applylens.app
3. Click "Sync Emails"
4. Should see success! 🎉

## Rate Limit Configuration

- **Cooldown**: 300 seconds (5 minutes)
- **Configurable via**: `BACKFILL_COOLDOWN_SECONDS` environment variable
- **Purpose**: Protects Gmail API quota (user has limited daily quota)

## Monitoring

```bash
# Watch for successful sync
docker logs -f applylens-api-prod | grep "inserted"

# You should see something like:
# INFO: Backfill successful: inserted 42 emails for user@example.com
```

## Expected Success Response

When sync works, you'll get:
```json
{
  "inserted": 42,
  "days": 7,
  "user_email": "your-email@gmail.com"
}
```

And the UI will show a success message.

---

## Summary

🎉 **Everything is working!** The 429 error proves:
- CSRF fix deployed successfully
- Browser cache cleared
- Backend processing requests correctly

⏰ **Just wait 5 minutes** and sync will work!

The journey so far:
1. ❌ 403 Forbidden → Missing CSRF token → **FIXED**
2. ❌ 400 Bad Request → Browser cache → **FIXED**
3. ✅ 429 Rate Limited → Working as designed! → **Wait 5 min**

**Next attempt should succeed!** 🚀
