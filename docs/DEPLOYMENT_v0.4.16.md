# Deployment Notes: v0.4.16

**Deployed:** 2025-10-24 00:17 UTC
**Focus:** Handle 524 Gateway Timeout gracefully for long-running Gmail backfill operations

---

## 🎯 Problem Solved

### Issue
When users clicked the "Sync 60d" button to backfill 60 days of Gmail data:
- Backend operation takes 2-3 minutes to fetch thousands of emails
- Cloudflare's CDN timeout is ~100 seconds
- Frontend received `524 Gateway Timeout` error
- User saw: `Pipeline error: Error: 524`
- **User confusion**: Did the sync work? Should I retry? Is it still running?

### Root Cause
```
User clicks "Sync 60d"
→ POST /api/gmail/backfill?days=60
→ Backend fetches emails (takes 2-3 min)
→ Cloudflare timeout at 100s
→ 524 status code to frontend
→ Frontend throws error
→ User sees cryptic error message
```

The backend operation continues successfully in the background, but the frontend has no way to know this.

---

## ✨ Solution

### Frontend Changes

**1. api.ts - Graceful Timeout Detection**
```typescript
// Updated post() helper to recognize 524 as non-fatal
async function post(url: string, init: RequestInit = {}) {
  const r = await fetch(...)

  if (r.status === 524) {
    console.warn('[api] 524 Gateway Timeout - operation may still be running')
    return {
      status: 'timeout',
      message: 'Operation started but response timed out. Check back in a moment.',
      _timeout: true  // Flag for detection
    }
  }

  if (!r.ok) throw new Error(`${r.status}`)
  return r.json().catch(() => ({}))
}

// Updated backfillGmail() with specific timeout handling
export async function backfillGmail(days = 60, userEmail?: string): Promise<BackfillResponse> {
  await ensureCsrf()
  const r = await fetch(url, { method: 'POST', headers, credentials: 'include' })

  if (r.status === 524) {
    console.warn('[backfill] 524 Gateway Timeout - backfill may still be running')
    return {
      status: 'timeout',
      message: 'Backfill started but response timed out. Check your inbox in a few minutes.',
      days,
      user_email: userEmail || 'current'
    }
  }

  // ... normal error handling ...
}

// Extended type to support timeout responses
export type BackfillResponse = {
  inserted?: number      // Optional (won't exist on timeout)
  days: number
  user_email: string
  status?: string        // 'timeout' status
  message?: string       // User-friendly message
  _timeout?: boolean     // Flag for timeout detection
}
```

**2. AppHeader.tsx - Smart Pipeline Control**
```typescript
async function runPipeline(days: 7 | 60) {
  setSyncing(true)
  const syncFn = days === 7 ? sync7d : sync60d

  try {
    // Step 1: Gmail backfill
    toast({
      title: `🔄 Syncing last ${days} days...`,
      description: "Fetching emails from Gmail (may take 1-2 minutes)",
    })
    const syncResult = await syncFn()

    // NEW: Check if sync timed out
    if (syncResult && (syncResult as any)._timeout) {
      toast({
        title: "⏱️ Sync started but timed out",
        description: "The backfill is running in the background. Check back in 2-3 minutes.",
      })
      setSyncing(false)
      return // CRITICAL: Don't proceed with ML/profile if sync didn't complete
    }

    // Step 2: ML labeling (only if sync completed)
    toast({ title: "🤖 Running ML classifier..." })
    await classifyAllApplications()

    // Step 3: Profile rebuild (only if sync completed)
    toast({ title: "📊 Rebuilding search index..." })
    await rebuildProfiles()

    toast({ title: "✅ All done!", description: "Your inbox is up to date" })

  } catch (error: any) {
    console.error("Pipeline error:", error)

    // Enhanced error messaging
    let errorMessage = error?.message ?? String(error)
    if (errorMessage.includes('524')) {
      errorMessage = 'Request timed out. The sync may still be running in the background.'
    }

    toast({
      title: "❌ Sync failed",
      description: errorMessage,
      variant: "destructive",
    })
  } finally {
    setSyncing(false)
  }
}
```

---

## 🔍 User Experience

### Before v0.4.16
```
[User clicks "Sync 60d"]
[Wait... 100 seconds pass...]
❌ Pipeline error: Error: 524
[User confused: Did it work? Should I retry?]
```

### After v0.4.16
```
[User clicks "Sync 60d"]
🔄 Syncing last 60 days...
   Fetching emails from Gmail (may take 1-2 minutes)

[Wait... 100 seconds pass...]

⏱️ Sync started but timed out
   The backfill is running in the background.
   Check back in 2-3 minutes.

[User understands: Operation is running, just wait]
[2-3 minutes later: Emails appear in search]
```

---

## 🛡️ Safety Features

1. **No Cascade Failures**: If Gmail sync times out, don't run ML labeling or profile rebuild
2. **Clear Communication**: User knows operation is running in background
3. **No Data Loss**: Backend continues working after frontend timeout
4. **Retry Safe**: User can manually refresh page after 2-3 minutes
5. **Console Logging**: Warnings logged for debugging

---

## 📊 Technical Details

### Timeout Flow
```
Frontend                          Cloudflare                    Backend
   |                                   |                           |
   |-- POST /api/gmail/backfill?days=60 -----------------------> |
   |                                   |                           |
   |                                   | [100s timeout]            |
   |                                   |                           |
   |<-- 524 Gateway Timeout ---------|                           |
   |                                   |                           |
   | [Detect 524]                      |                           |
   | [Show timeout toast]              |                    [Still running]
   | [Stop pipeline]                   |                           |
   | [User waits]                      |                           |
   |                                   |                    [Completes at 2-3 min]
   |                                   |                           |
   | [User refreshes page later]       |                           |
   | [Sees new emails in search]       |                           |
```

### Cloudflare Timeout Limits
- **Standard Plan**: 100 seconds
- **Pro/Business**: Can be increased to 600s
- **Enterprise**: Can be increased further

---

## 🚀 Deployment Commands

```powershell
# 1. Update docker-compose.prod.yml
# Change version: v0.4.15 → v0.4.16

# 2. Deploy
cd d:\ApplyLens
docker-compose -f docker-compose.prod.yml up -d --force-recreate web
docker-compose -f docker-compose.prod.yml restart nginx

# 3. Purge Cloudflare cache
$env:CLOUDFLARE_API_TOKEN = "muFUbNoqVzucDwPRjIhcmnRQM3JMrtEcFW8Jogb1"
$env:CLOUDFLARE_ZONE_ID = "8b18d6fe5e67a5507f4db885748fbfe6"
.\scripts\Purge-CloudflareCache.ps1

# 4. Verify version
docker exec applylens-web-prod sh -c "grep -o 'ApplyLens Web v[0-9.]*' /usr/share/nginx/html/assets/*.js"
# Expected: ApplyLens Web v0.4.16
```

**Deployed:** 2025-10-24 00:17:39 UTC
**Cache Purged:** 2025-10-24 00:17:42 UTC
**Verification:** ✅ v0.4.16 confirmed in production

---

## 🧪 Testing

### Test Scenario 1: 60-Day Sync (Expected Timeout)
1. Click "Sync 60d" button
2. Wait ~100 seconds
3. **Expected**: Toast shows "⏱️ Sync started but timed out" with helpful message
4. **Expected**: Pipeline stops (doesn't run ML/profile steps)
5. Wait 2-3 minutes
6. Refresh page
7. **Expected**: New emails appear in search

### Test Scenario 2: 7-Day Sync (No Timeout)
1. Click "Sync 7d" button
2. **Expected**: Completes in < 100 seconds
3. **Expected**: Full pipeline runs (Gmail → ML → Profile)
4. **Expected**: Success toast: "✅ All done!"

### Test Scenario 3: Backend Logs
```bash
# Check backend logs to verify backfill continues after timeout
docker logs applylens-api-prod --tail 100

# Expected: See backfill completion logs even after frontend timed out
```

---

## 🔮 Future Improvements

### Short-Term (v0.4.17+)
- **Progress Indicator**: Show estimated time remaining during backfill
- **Polling Mechanism**: Frontend could poll `/api/jobs/{id}` to check completion
- **Smart Retry**: Automatically retry after timeout if backend confirms completion

### Long-Term (v0.5.x)
- **Async Job Pattern**:
  ```
  POST /api/gmail/backfill → 202 Accepted + job_id
  GET /api/jobs/{job_id} → Poll for completion
  Frontend displays progress bar
  ```
- **Chunked Backfill**: Break 60-day sync into smaller chunks (10 days each)
- **WebSocket Updates**: Real-time progress streaming
- **Cloudflare Timeout Increase**: Upgrade plan or use Enterprise features

---

## 📝 Version History

- **v0.4.16** (2025-10-24): 524 Gateway Timeout handling
- **v0.4.15** (2025-10-23): Empty query fallback to "*"
- **v0.4.14** (2025-10-23): Clear filters + strict URL parsing
- **v0.4.13** (2025-10-22): LoginGuard safety + nginx config
- **v0.4.12** (2025-10-22): Selective trailing slash fix

---

## 🔗 Related Files

- `apps/web/src/lib/api.ts` (lines 255-355)
- `apps/web/src/components/AppHeader.tsx` (lines 50-130)
- `apps/web/src/main.tsx` (version banner)
- `docker-compose.prod.yml` (deployment config)

---

## 📞 Troubleshooting

### Issue: User still sees 524 error
**Cause**: Old bundle cached in browser
**Solution**: Hard refresh (Ctrl+Shift+R) or clear browser cache

### Issue: Backfill doesn't complete even after 3 minutes
**Cause**: Backend error or Gmail API rate limit
**Solution**: Check backend logs:
```bash
docker logs applylens-api-prod --tail 200 | grep -i "backfill\|gmail"
```

### Issue: Pipeline proceeds to ML step after timeout
**Cause**: `_timeout` flag not detected
**Solution**: Check browser console for warnings:
```
[api] 524 Gateway Timeout - operation may still be running
[backfill] 524 Gateway Timeout - backfill may still be running
```

---

## ✅ Success Metrics

- **User Confusion**: Reduced from "What happened?" to "Operation is running"
- **False Failures**: 524 no longer treated as fatal error
- **Cascade Failures**: Prevented (ML/profile don't run on timeout)
- **Support Tickets**: Expected reduction in "sync failed" reports
- **User Trust**: Increased transparency about long-running operations
