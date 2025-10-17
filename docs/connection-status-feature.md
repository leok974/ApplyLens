# Connection Status Indicator & Rate Limit Error Handling

**Status**: ✅ Deployed  
**Date**: 2025-10-15  
**Components**: Frontend (MailChat.tsx)

## Overview

Implemented client-side connection status indicator with visual feedback and friendly rate limit error messaging.

## Features Implemented

### 1. Connection Status Indicator

**Visual Feedback**:
- **Green dot**: Active SSE connection receiving data
- **Gray dot**: Connection inactive (35s timeout)
- **Location**: Timing footer (next to ES/LLM/Client ms)

**Implementation**:
```tsx
// State management
const [isStreamAlive, setIsStreamAlive] = useState(false)
const streamHeartbeatRef = useRef<number | null>(null)

// Helper functions
function resetStreamHeartbeat() {
  setIsStreamAlive(true)
  if (streamHeartbeatRef.current) {
    window.clearTimeout(streamHeartbeatRef.current)
  }
  streamHeartbeatRef.current = window.setTimeout(() => {
    setIsStreamAlive(false)
  }, 35000) // 35s timeout
}

function clearStreamHeartbeat() {
  setIsStreamAlive(false)
  if (streamHeartbeatRef.current) {
    window.clearTimeout(streamHeartbeatRef.current)
    streamHeartbeatRef.current = null
  }
}
```

**Lifecycle**:
1. Connection opens → call `resetStreamHeartbeat()` → green dot appears
2. Each SSE event received → call `resetStreamHeartbeat()` → resets 35s timeout
3. Stream ends ('done') → call `clearStreamHeartbeat()` → gray dot appears
4. Error occurs → call `clearStreamHeartbeat()` → gray dot appears
5. 35s of silence → timeout fires → gray dot appears

**SSE Events Tracked**:
- ✅ 'ready' event (on connection)
- ✅ 'intent' event
- ✅ 'intent_explain' event
- ✅ 'memory' event
- ✅ 'tool' event
- ✅ 'answer' event
- ✅ 'filed' event
- ✅ 'done' event (clears heartbeat)
- ✅ 'error' event (clears heartbeat)

### 2. Friendly Rate Limit (429) Error Handling

**User-Facing Message**:
```
"You're sending requests a bit too fast. Please wait a moment and try again."
```

**Implementation**:
```tsx
catch (err: any) {
  clearStreamHeartbeat()
  
  // Handle rate limit errors
  if (err instanceof Response && err.status === 429) {
    setError("You're sending requests a bit too fast. Please wait a moment and try again.")
    setBusy(false)
    return
  }
  
  // Handle other errors
  const errorMsg = err.message || 'Failed to get response'
  setError(errorMsg)
  setMessages((m) => [
    ...m,
    {
      role: 'assistant',
      content: `❌ Error: ${errorMsg}`,
      error: errorMsg,
    },
  ])
  setBusy(false)
}
```

**Trigger Conditions**:
- User exceeds 10 req/s rate limit (configured in nginx)
- Burst capacity (30 requests for /chat, 10 for /stream) exceeded

## UI/UX Details

**Timing Footer Layout**:
```
🟢 ES: 45 ms · LLM: 1200 ms · Client: 1250 ms
```

**Tooltip**:
- Green dot: "Connected"
- Gray dot: "Disconnected"

**Error Display**:
Rate limit errors appear in the standard error banner with amber colors:
```tsx
{error && (
  <div className="rounded-xl bg-amber-900/20 p-4 border border-amber-500/30">
    <div className="text-amber-200">{error}</div>
  </div>
)}
```

## Testing

### Manual Test Cases

**Test 1: Connection Status During Normal Operation**
1. Send a chat message
2. Verify green dot appears immediately
3. Wait for response to complete
4. Verify dot turns gray after 35s of inactivity

**Test 2: Connection Status During Streaming**
1. Send a long query that triggers streaming
2. Verify green dot stays lit during entire stream
3. Verify dot updates on each SSE event
4. Verify dot turns gray after stream completes + 35s

**Test 3: Rate Limit Error Handling**
```bash
# Rapid fire 40 requests to trigger rate limit
for i in {1..40}; do 
  curl -s -X POST 'http://localhost/api/chat' \
    -H 'Content-Type: application/json' \
    -d '{"messages":[{"role":"user","content":"test"}]}' &
done
```
Expected: Friendly error message after burst capacity exceeded

**Test 4: Connection Interruption**
1. Start a chat query
2. Stop nginx container: `docker stop applylens-web-prod`
3. Verify error event fires
4. Verify gray dot appears
5. Verify error message displayed

## Technical Notes

**Why 35s Timeout?**
- Server sends heartbeats every 20s (`: keep-alive\n\n`)
- 35s timeout allows one missed heartbeat before marking connection dead
- Provides buffer for network latency

**State Management**:
- `isStreamAlive`: Boolean state (true = green, false = gray)
- `streamHeartbeatRef`: Ref to store timeout handle (allows cleanup)
- Cleanup on component unmount handled by clearTimeout

**Error Type Detection**:
Rate limit errors return HTTP 429 status with Response object. The check:
```tsx
if (err instanceof Response && err.status === 429)
```

## Integration Points

**Works With**:
- ✅ SSE server heartbeats (20s keep-alive)
- ✅ Nginx rate limiting (10 req/s, burst 30/10)
- ✅ Timing footer (ES/LLM/Client ms)
- ✅ Window days dropdown
- ✅ Existing error handling

**Dependencies**:
- React useState, useEffect, useRef hooks
- EventSource API
- Nginx rate limiting configuration

## Files Modified

**apps/web/src/components/MailChat.tsx**:
- Added: `isStreamAlive` state
- Added: `streamHeartbeatRef` ref
- Added: `resetStreamHeartbeat()` helper function
- Added: `clearStreamHeartbeat()` helper function
- Modified: SSE event listeners (9 locations)
- Modified: Timing footer JSX (added green/gray dot)
- Modified: Error catch block (added 429 handler)

## Future Enhancements

**Potential Improvements**:
1. **Reconnection Logic**: Auto-retry failed connections with exponential backoff
2. **Metrics**: Track connection uptime/downtime percentages
3. **Visual Feedback**: Pulse animation on green dot during active streaming
4. **Rate Limit Countdown**: Show "Try again in 5s..." countdown timer
5. **Network Quality Indicator**: Show connection quality (good/poor/offline)

## Related Documentation

- [Production Resilience Features](./production-resilience.md)
- [SSE Streaming Implementation](./sse-streaming.md)
- [Rate Limiting Configuration](./nginx-rate-limiting.md)
- [Grafana Dashboard Setup](./grafana-setup.md)
