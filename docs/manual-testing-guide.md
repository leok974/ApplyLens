# Manual Testing Guide - Final Polish Features

**Date**: October 15, 2025  
**Tester**: You  
**Duration**: 10-15 minutes

---

## Test 1: Connection Status Indicator (Gray → Green)

### Objective
Verify the green/gray dot accurately reflects stream connection status.

### Steps

1. **Open Chat Interface**
   ```
   Navigate to: http://localhost/
   ```

2. **Kill API Container**
   ```powershell
   docker compose -f docker-compose.prod.yml --env-file infra/.env.prod stop api
   ```
   
3. **Start a Chat Query**
   - Type any message in chat: "show me my emails"
   - Click Send
   - **Expected**: Loading state, then error after timeout

4. **Wait 35 Seconds**
   - Watch the timing footer (bottom of last message)
   - **Expected**: Green dot should turn gray after ~35 seconds

5. **Restart API**
   ```powershell
   docker compose -f docker-compose.prod.yml --env-file infra/.env.prod start api
   ```
   - Wait 10 seconds for health check

6. **Send New Message**
   - Type: "test"
   - Click Send
   - **Expected**: Green dot appears immediately and stays lit during stream

### Success Criteria
- ✅ Dot turns gray after 35s of no data
- ✅ Dot turns green when new stream starts
- ✅ Dot resets on each SSE event (stays green during active stream)

**Status**: ⬜ PASS / ⬜ FAIL

**Notes**:
_____________________________________________________________________

---

## Test 2: Rate Limit (429) Friendly Message

### Objective
Verify friendly error message displays on rate limit and auto-retry works.

### Steps

1. **Trigger Rate Limit (PowerShell)**
   ```powershell
   # Send 50 concurrent requests
   1..50 | ForEach-Object -Parallel {
     Invoke-RestMethod -Uri 'http://localhost/api/chat' `
       -Method POST `
       -ContentType 'application/json' `
       -Body '{"messages":[{"role":"user","content":"test"}]}' `
       -TimeoutSec 2
   } -ThrottleLimit 50
   ```

2. **Immediately Send UI Request**
   - In browser, type message: "test"
   - Click Send
   - **Expected**: 
     - Console shows: `[Backoff] Retry 1/3 after 300ms`
     - May see friendly error if all retries exhausted
     - Eventually succeeds

3. **Verify Error Message (if triggered)**
   - **Expected Text**: 
     ```
     "You're sending requests a bit too fast. Please wait a moment and try again."
     ```
   - **Color**: Amber background
   - **No Technical Jargon**: No "429", "rate_limited", etc.

### Success Criteria
- ✅ Friendly message shows (if 429 triggered)
- ✅ Auto-retry visible in console
- ✅ Eventually succeeds after backoff
- ✅ No technical error codes exposed

**Status**: ⬜ PASS / ⬜ FAIL

**Notes**:
_____________________________________________________________________

---

## Test 3: Stream Abort on Window Days Change

### Objective
Verify changing window days dropdown aborts old stream and starts new one.

### Steps

1. **Start Long Query**
   - Type: "summarize all emails"
   - Click Send
   - **Expected**: Stream starts, intent explanation appears

2. **Mid-Stream: Change Window Days**
   - While stream is active (watch for green dot)
   - Click window days dropdown (top right)
   - Select different value (e.g., 30 → 60)
   - **Expected**: 
     - Old stream stops immediately
     - New query starts with updated window
     - Console shows: `[Chat] Aborting previous stream`

3. **Verify No Duplicates**
   - Watch message area
   - **Expected**: Only ONE response appears (not two)

4. **Check Network Tab (Optional)**
   - Open DevTools → Network → EventSource
   - Verify old connection closed, new one opened

### Success Criteria
- ✅ Old stream aborts immediately
- ✅ New stream starts with updated window
- ✅ No duplicate responses
- ✅ Clean transition (no UI glitches)

**Status**: ⬜ PASS / ⬜ FAIL

**Notes**:
_____________________________________________________________________

---

## Test 4: UX Heartbeat Tracking

### Objective
Verify client sends heartbeat pings and metrics increment.

### Steps

1. **Check Initial Metric**
   ```powershell
   # Query Prometheus for current value
   $before = (curl -s "http://localhost:9090/api/v1/query?query=ux_heartbeat_total" | ConvertFrom-Json).data.result[0].value[1]
   Write-Host "Before: $before"
   ```

2. **Open Chat Interface**
   - Navigate to: `http://localhost/`
   - **Expected**: Immediate heartbeat sent

3. **Wait 60 Seconds**
   - Keep chat page open
   - Do NOT navigate away
   - **Expected**: 2 heartbeats sent (0s, 30s, 60s)

4. **Check Metric Again**
   ```powershell
   Start-Sleep -Seconds 5
   $after = (curl -s "http://localhost:9090/api/v1/query?query=ux_heartbeat_total" | ConvertFrom-Json).data.result[0].value[1]
   Write-Host "After: $after"
   Write-Host "Delta: $($after - $before)"
   ```
   - **Expected**: Delta ≈ 2-3 (initial + 2 intervals)

5. **Check Console (Optional)**
   - Open DevTools → Console
   - Filter for: "Heartbeat"
   - **Expected**: No errors (debug logs only)

### Success Criteria
- ✅ Metric increments by 2-3 after 60s
- ✅ No console errors
- ✅ Heartbeat endpoint responds with `{"ok": true}`

**Status**: ⬜ PASS / ⬜ FAIL

**Notes**:
_____________________________________________________________________

---

## Test 5: Prometheus Alert (Low Hit Rate)

### Objective
Verify alert is loaded and ready to fire on sustained low hit rate.

### Steps

1. **Check Alert Status**
   ```powershell
   $alerts = curl -s "http://localhost:9090/api/v1/rules" | ConvertFrom-Json
   $lowHitAlert = $alerts.data.groups.rules | Where-Object { $_.name -eq "AssistantLowHitRate" }
   
   if ($lowHitAlert) {
     Write-Host "✓ Alert loaded" -ForegroundColor Green
     Write-Host "  State: $($lowHitAlert.state)"
     Write-Host "  Threshold: 70% zero-result rate for 10m"
   } else {
     Write-Host "✗ Alert not found" -ForegroundColor Red
   }
   ```

2. **Expected Output**:
   ```
   ✓ Alert loaded
   State: pending (or inactive)
   Threshold: 70% zero-result rate for 10m
   ```

3. **Optional: Trigger Alert**
   - Send 20+ queries with no results over 10 minutes
   - Wait 10 minutes
   - Check alert state changes to "firing"
   - **Warning**: This is a long test, skip if time-limited

### Success Criteria
- ✅ Alert exists in Prometheus
- ✅ State is "pending" or "inactive" (not "firing" during normal ops)
- ✅ Expression compiles without errors

**Status**: ⬜ PASS / ⬜ FAIL

**Notes**:
_____________________________________________________________________

---

## Test 6: Stream Cleanup on Navigation

### Objective
Verify stream closes cleanly when navigating away from chat.

### Steps

1. **Start Chat Query**
   - Type: "test"
   - Click Send
   - **Expected**: Stream starts, green dot appears

2. **Navigate Away Mid-Stream**
   - While stream active, click "Profile" in nav
   - **Expected**: Stream closes cleanly

3. **Check Console**
   - Look for errors related to EventSource
   - **Expected**: No errors (maybe debug log)

4. **Navigate Back to Chat**
   - Click "Chat" in nav
   - **Expected**: New component mount, fresh state

5. **Send New Message**
   - Type: "test 2"
   - Click Send
   - **Expected**: Works normally, no interference from previous stream

### Success Criteria
- ✅ No console errors on navigation
- ✅ Stream closes without memory leak
- ✅ Fresh component works normally

**Status**: ⬜ PASS / ⬜ FAIL

**Notes**:
_____________________________________________________________________

---

## Overall Results

### Summary
- **Total Tests**: 6
- **Passed**: ___
- **Failed**: ___
- **Skipped**: ___

### Critical Issues Found
_____________________________________________________________________
_____________________________________________________________________
_____________________________________________________________________

### Minor Issues Found
_____________________________________________________________________
_____________________________________________________________________
_____________________________________________________________________

### Recommendations
_____________________________________________________________________
_____________________________________________________________________
_____________________________________________________________________

---

## Sign-Off

**Tested By**: _____________________  
**Date**: October 15, 2025  
**Time Spent**: _____ minutes  

**Approval**: ⬜ APPROVED / ⬜ NEEDS FIX

**Next Steps**:
_____________________________________________________________________
_____________________________________________________________________
