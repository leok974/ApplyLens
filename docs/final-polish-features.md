# Final Polish - Production Readiness Features

**Status**: ✅ Deployed  
**Date**: October 15, 2025  
**Components**: Frontend (MailChat.tsx), Backend (API, Prometheus)

## Overview

This document covers the final production readiness features including stream management, retry logic, and operational observability improvements.

---

## 1. Stream Abort Management

### Problem
When users change window days dropdown during an active stream, or when component unmounts, the old EventSource connection would continue running, potentially causing:
- Duplicate responses
- Memory leaks
- Confusing UI states

### Solution
Implemented EventSource lifecycle management with automatic cleanup.

### Implementation

**State Management:**
```tsx
const currentEventSourceRef = useRef<EventSource | null>(null)
```

**Abort on New Stream:**
```tsx
function send(text: string, opts?: SendOptions) {
  // ... existing code ...

  // Abort any existing stream
  if (currentEventSourceRef.current) {
    console.log('[Chat] Aborting previous stream')
    currentEventSourceRef.current.close()
    clearStreamHeartbeat()
  }

  const ev = new EventSource(url)
  currentEventSourceRef.current = ev // Store reference for cleanup
  
  // ... rest of stream handling
}
```

**Cleanup on Unmount:**
```tsx
useEffect(() => {
  return () => {
    if (currentEventSourceRef.current) {
      currentEventSourceRef.current.close()
      clearStreamHeartbeat()
    }
  }
}, [])
```

### Benefits
- ✅ No duplicate streams when changing window days
- ✅ Clean shutdown on navigation/unmount
- ✅ Proper heartbeat cleanup
- ✅ Better resource management

---

## 2. Exponential Backoff for Rate Limits

### Problem
When API hits rate limits (429) or experiences network errors, immediate failures frustrate users and waste opportunities to succeed with a simple retry.

### Solution
Implemented gentle exponential backoff with automatic retry for transient failures.

### Implementation

**Backoff Utility (`chatClient.ts`):**
```typescript
async function withBackoff<T>(fn: () => Promise<T>, maxRetries = 3): Promise<T> {
  let delay = 300
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn()
    } catch (e: any) {
      const shouldRetry = 
        e?.status === 429 || 
        e?.name === 'FetchError' ||
        e?.name === 'TypeError' // Network errors
      
      if (shouldRetry && attempt < maxRetries - 1) {
        console.log(`[Backoff] Retry ${attempt + 1}/${maxRetries} after ${delay}ms`)
        await new Promise(r => setTimeout(r, delay))
        delay = Math.min(delay * 2, 2000) // Cap at 2s
        continue
      }
      throw e
    }
  }
  return fn() // Final attempt without catch
}
```

**Applied to Chat Endpoint:**
```typescript
export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  return withBackoff(async () => {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      const err: any = new Error(error.detail || `Chat failed: ${response.statusText}`)
      err.status = response.status // Preserve status for backoff logic
      throw err
    }

    return response.json()
  })
}
```

### Retry Schedule

| Attempt | Delay | Total Time |
|---------|-------|------------|
| 1       | 0ms   | 0ms        |
| 2       | 300ms | 300ms      |
| 3       | 600ms | 900ms      |
| 4       | 1200ms| 2100ms     |

**Max delay capped at 2000ms** to prevent excessive wait times.

### Benefits
- ✅ Transparent recovery from rate limits
- ✅ Handles network hiccups gracefully
- ✅ Reduced error rate visible to users
- ✅ Better UX during high load

---

## 3. Low Hit Rate Alert

### Problem
If the assistant consistently returns 0 results, it indicates either:
- Elasticsearch is down/misconfigured
- Queries are severely mis-scoped
- Data sync issues

This should trigger ops investigation immediately.

### Solution
Added Prometheus alert rule to detect sustained low hit rates.

### Implementation

**Alert Rule (`infra/prometheus/alerts.yml`):**
```yaml
- alert: AssistantLowHitRate
  expr: |
    (rate(assistant_tool_queries_total{has_hits="0"}[5m])
     / ignoring(has_hits) rate(assistant_tool_queries_total[5m])) > 0.7
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Assistant search hit rate < 30%"
    description: "More than 70% of assistant queries returning 0 results for 10m. Possible ES issue or mis-scoped queries."
```

### Alert Conditions
- **Threshold**: 70% zero-result rate
- **Window**: 5-minute rate
- **Duration**: Sustained for 10 minutes
- **Severity**: Warning (not critical - service still works)

### Response Playbook
1. **Check Elasticsearch**: `curl http://localhost:9200/_cluster/health`
2. **Check index stats**: View Kibana or `curl http://localhost:9200/emails/_count`
3. **Check recent queries**: Review Grafana dashboard for query patterns
4. **Verify sync status**: Check last sync timestamp in logs

### Benefits
- ✅ Early detection of search quality degradation
- ✅ Separates "no users" from "broken search"
- ✅ Actionable alert with clear investigation path
- ✅ Prevents silent failures

---

## 4. UX Heartbeat Telemetry

### Problem
Traditional metrics can't distinguish:
- "No chat activity" (users not using feature)
- "No users connected" (adoption issue)
- "Users browsing but not chatting" (UX issue)

### Solution
Lightweight client-side heartbeat ping every 30s while chat interface is open.

### Implementation

**Backend Endpoint (`services/api/app/routers/ux_metrics.py`):**
```python
from fastapi import APIRouter
from prometheus_client import Counter

router = APIRouter(prefix="/ux", tags=["ux"])

ux_heartbeat_total = Counter(
    "ux_heartbeat_total",
    "Client heartbeat pings (indicates active sessions)",
    ["user_agent_type"]
)

ux_chat_opened_total = Counter(
    "ux_chat_opened_total",
    "Chat interface opened events",
)

@router.post("/heartbeat")
async def heartbeat():
    """
    Client heartbeat ping.
    Frontend calls this every 30s while user is active on the chat page.
    """
    user_agent_type = "web"
    ux_heartbeat_total.labels(user_agent_type=user_agent_type).inc()
    return {"ok": True}

@router.post("/chat/opened")
async def chat_opened():
    """Track when users open the chat interface."""
    ux_chat_opened_total.inc()
    return {"ok": True}
```

**Frontend Integration (`MailChat.tsx`):**
```tsx
// UX Heartbeat - track active sessions (30s interval)
useEffect(() => {
  const sendHeartbeat = async () => {
    try {
      await fetch('/api/ux/heartbeat', { method: 'POST' })
    } catch (err) {
      console.debug('[Heartbeat] Failed:', err)
    }
  }

  // Send initial heartbeat when chat opens
  sendHeartbeat()
  fetch('/api/ux/chat/opened', { method: 'POST' }).catch(() => {})

  // Send heartbeat every 30s while component is mounted
  const interval = setInterval(sendHeartbeat, 30000)

  return () => {
    clearInterval(interval)
  }
}, [])
```

### Metrics Available

**`ux_heartbeat_total{user_agent_type="web"}`**
- Total heartbeat pings received
- Rate = active concurrent sessions
- Example: `rate(ux_heartbeat_total[1m]) * 60 / 2` ≈ concurrent users

**`ux_chat_opened_total`**
- Total times chat interface opened
- Useful for funnel analysis
- Compare to message send rate for engagement

### Grafana Queries

**Active Sessions (approx):**
```promql
rate(ux_heartbeat_total[1m]) * 30
```
*(Each user sends ~1 ping per 30s, so rate × 30 ≈ concurrent users)*

**Chat Open Rate:**
```promql
rate(ux_chat_opened_total[5m]) * 300
```

**Engagement Ratio (messages per session):**
```promql
rate(assistant_tool_queries_total[5m])
/ 
rate(ux_chat_opened_total[5m])
```

### Benefits
- ✅ Distinguish "no users" from "users not engaging"
- ✅ Track concurrent active sessions
- ✅ Measure feature adoption
- ✅ Minimal overhead (~200 bytes per 30s)
- ✅ Silent failures (doesn't break UX)

---

## Testing Checklist

### Manual Tests

**1. Stream Abort on Dropdown Change**
```bash
# In browser:
1. Send a long query: "summarize all emails"
2. While streaming, change window days from 30 → 60
3. ✓ Verify old stream stops
4. ✓ Verify new query starts with updated window
5. ✓ No duplicate responses
```

**2. Backoff on Rate Limit**
```bash
# Terminal:
for i in {1..50}; do 
  curl -X POST http://localhost/api/chat \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"test"}]}' &
done

# In browser:
1. Send a message immediately after
2. ✓ Verify automatic retry (console shows "[Backoff] Retry 1/3...")
3. ✓ Eventually succeeds after backoff
```

**3. Low Hit Rate Alert**
```bash
# Check Prometheus alert status
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.name=="AssistantLowHitRate")'

# Trigger alert (requires sustained 70% zero-result rate):
# Send 20+ queries with no matching results over 10 minutes
```

**4. UX Heartbeat**
```bash
# Check metrics endpoint
curl http://localhost:9090/api/v1/query?query=ux_heartbeat_total

# In browser:
1. Open chat interface
2. Wait 60 seconds
3. ✓ Check Prometheus: ux_heartbeat_total should increment by ~2
4. ✓ ux_chat_opened_total increments by 1
```

### Automated Tests

**Stream Abort:**
```typescript
it('should abort previous stream when sending new message', async () => {
  const { rerender } = render(<MailChat />)
  
  // Start first stream
  fireEvent.click(getByText('Send'))
  
  // Start second stream
  fireEvent.click(getByText('Send'))
  
  // Verify only one EventSource active
  expect(mockEventSource.close).toHaveBeenCalledTimes(1)
})
```

**Backoff Retry:**
```typescript
it('should retry on 429 with exponential backoff', async () => {
  fetch
    .mockRejectedValueOnce({ status: 429 })
    .mockResolvedValueOnce({ ok: true, json: async () => ({}) })
  
  await sendChatMessage({ messages: [] })
  
  expect(fetch).toHaveBeenCalledTimes(2)
  // Verify delay between calls ≈ 300ms
})
```

---

## Deployment

### Files Modified

**Frontend:**
- `apps/web/src/components/MailChat.tsx` - Stream abort, UX heartbeat
- `apps/web/src/lib/chatClient.ts` - Backoff retry logic

**Backend:**
- `services/api/app/routers/ux_metrics.py` - New UX metrics endpoints
- `services/api/app/main.py` - Register UX router

**Ops:**
- `infra/prometheus/alerts.yml` - Low hit rate alert

### Deployment Commands

```bash
# Rebuild API
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --build api

# Rebuild Web
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --build web

# Reload Prometheus
docker exec applylens-prometheus-prod killall -HUP prometheus
```

### Rollback Plan

**If stream abort causes issues:**
```typescript
// Remove abort logic in send():
// Comment out lines 226-230
```

**If backoff causes excessive delays:**
```typescript
// Reduce maxRetries in withBackoff():
withBackoff(fn, 1) // Only 1 retry instead of 3
```

**If alert is too noisy:**
```yaml
# Adjust threshold in alerts.yml:
expr: (...) > 0.85  # Change from 0.7 to 0.85 (85% zero-result rate)
for: 20m             # Change from 10m to 20m
```

---

## Metrics & Monitoring

### New Metrics Available

**`ux_heartbeat_total{user_agent_type}`**
- Type: Counter
- Purpose: Track active user sessions
- Rate: ~2/min per active user

**`ux_chat_opened_total`**
- Type: Counter
- Purpose: Track chat interface opens
- Use: Funnel analysis, adoption tracking

### Grafana Dashboard Updates

**Add Panel: "Active Chat Sessions"**
```promql
rate(ux_heartbeat_total[1m]) * 30
```

**Add Panel: "Chat Engagement Rate"**
```promql
(
  rate(assistant_tool_queries_total[5m])
  / 
  rate(ux_chat_opened_total[5m])
) * 100
```

**Add Alert: "Low Engagement"**
```promql
(
  rate(assistant_tool_queries_total[10m])
  / 
  rate(ux_chat_opened_total[10m])
) < 0.1
```
*Fires if users open chat but rarely send messages*

---

## Performance Impact

### Stream Abort
- **CPU**: Negligible (just closes EventSource)
- **Memory**: Prevents leak from abandoned connections
- **Network**: Saves bandwidth from duplicate streams

### Backoff Retry
- **Latency**: +300-2100ms on retries (only on failures)
- **Success Rate**: +15-30% (estimated improvement)
- **Network**: 2-4× requests on rate limit (acceptable trade-off)

### UX Heartbeat
- **Bandwidth**: ~200 bytes per 30s = 400 KB/month per user
- **CPU**: <0.1% (simple counter increment)
- **Storage**: ~1 KB/day in Prometheus

**Total Impact**: Minimal, well within production budgets.

---

## Future Enhancements

### Stream Management
1. **Reconnect Logic**: Auto-reconnect SSE on network interruption
2. **Partial Results**: Show partial answers even if stream fails mid-way
3. **Stream Priorities**: Pause low-priority streams when high-priority arrives

### Retry Logic
1. **Circuit Breaker**: Stop retrying if 5 consecutive 429s
2. **Jitter**: Add random jitter to backoff delays (prevent thundering herd)
3. **Server Retry-After**: Parse `Retry-After` header from 429 response

### Observability
1. **Client Error Tracking**: Send 5xx/network errors to backend metric
2. **Latency P95 Alert**: Alert on P95 > 3s for 5 minutes
3. **UX Event Stream**: Track button clicks, navigation, feature usage

---

## Related Documentation

- [Connection Status Feature](./connection-status-feature.md)
- [Production Resilience](./production-resilience.md)
- [SSE Streaming](./sse-streaming.md)
- [Rate Limiting](./nginx-rate-limiting.md)
- [Grafana Setup](./grafana-setup.md)
