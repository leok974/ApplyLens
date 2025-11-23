# Agent & Thread Viewer Observability

This document describes the observability instrumentation for the ApplyLens agent system and the Thread Viewer → Tracker user flow.

## Overview

We track three key stages of the user journey when interacting with the mailbox agent and navigating from thread lists to the application tracker:

1. **Agent Runs** - When a user executes a scan intent (followups, bills, etc.)
2. **Thread Lists Returned** - When the agent returns thread_list cards with actionable threads
3. **Tracker Clicks** - When a user clicks "Open in Tracker" from the Thread Viewer

This creates a conversion funnel: **Runs → Thread Lists → Tracker Clicks**

## Metrics

All metrics are exposed via Prometheus at `/metrics` and scraped automatically.

### 1. `applylens_agent_runs_total`

**Type:** Counter
**Labels:** `intent` (e.g., `followups`, `bills`, `interviews`, `suspicious`, `unsubscribe`, `clean_promos`, `generic`)

**Description:** Incremented every time an agent run completes successfully.

**Implementation:**
- Backend: `app/agent/metrics.py` - `record_agent_run()`
- Called by: `app/agent/orchestrator.py` after successful run completion

**Example PromQL:**
```promql
# Agent runs per minute by intent
sum by (intent) (rate(applylens_agent_runs_total[5m]))

# Total runs in last 24h for followups
sum(increase(applylens_agent_runs_total{intent="followups"}[24h]))
```

### 2. `applylens_agent_threadlist_returned_total`

**Type:** Counter
**Labels:** `intent`

**Description:** Incremented when an agent run returns one or more `thread_list` cards containing threads (`thread_count > 0`).

**Semantics:**
- Only increments if threads are actually returned
- If thread count is 0 or no thread_list cards exist, this counter does NOT increment
- Provides a measure of "productive" agent runs that surfaced actionable content

**Implementation:**
- Backend: `app/agent/metrics.py` - `record_threadlist_returned()`
- Called by: `app/agent/orchestrator.py` after building response cards
- Logic: Sums threads from all `thread_list` cards, increments if total > 0

**Example PromQL:**
```promql
# Thread list coverage: % of runs that return threads
(sum by (intent) (rate(applylens_agent_threadlist_returned_total{intent=~"followups|bills|interviews"}[1h]))
 /
 sum by (intent) (rate(applylens_agent_runs_total{intent=~"followups|bills|interviews"}[1h]))
) * 100
```

### 3. `applylens_agent_thread_to_tracker_click_total`

**Type:** Counter
**Labels:** `intent` (may be `None` if frontend doesn't pass it)

**Description:** Incremented when a user clicks "Open in Tracker" from the Thread Viewer.

**Implementation:**
- Frontend: `apps/web/src/components/mail/ThreadViewer.tsx`
  - Calls `POST /metrics/thread-to-tracker-click` with `{ application_id, intent }`
  - Fire-and-forget (doesn't block navigation)
- Backend: `app/routers/metrics.py` - `/metrics/thread-to-tracker-click` endpoint
  - Calls `record_thread_to_tracker_click()`
  - CSRF-exempt (added to `app/core/csrf.py::CSRF_EXEMPT_PATHS`)

**Example PromQL:**
```promql
# Clicks per minute
sum by (intent) (rate(applylens_agent_thread_to_tracker_click_total[5m]))

# Click-through rate (CTR) for scan intents over 24h
(sum by (intent) (increase(applylens_agent_thread_to_tracker_click_total{intent=~"followups|bills|interviews"}[24h]))
 /
 sum by (intent) (increase(applylens_agent_runs_total{intent=~"followups|bills|interviews"}[24h]))
) * 100
```

## Funnel Analysis

The three metrics form a conversion funnel:

```
Agent Run (intent=followups)
    ↓
Thread List Returned (count=5)
    ↓
User Clicks "Open in Tracker"
    ↓
applylens_agent_thread_to_tracker_click_total++
```

**Key Metrics to Track:**

1. **Thread List Coverage** - What % of runs return actionable threads?
   - Formula: `threadlist_returned / agent_runs`
   - Goal: High coverage = agent is surfacing relevant content

2. **Click-Through Rate (CTR)** - What % of runs lead to tracker navigation?
   - Formula: `tracker_clicks / agent_runs`
   - Goal: Higher CTR = users find value in the surfaced threads

3. **Conversion Rate (Thread → Tracker)** - Of threads shown, how many lead to clicks?
   - Formula: `tracker_clicks / threadlist_returned`
   - Goal: Measures engagement once threads are surfaced

## Grafana Dashboard

**Location:** `services/api/grafana/dashboards/applylens-agent-thread-tracker.json`

**Dashboard UID:** `applylens-agent-thread`
**Title:** ApplyLens – Agent & Thread Viewer

### Panels

1. **Agent runs by intent (per minute)** - Time series of agent execution rate
2. **Thread list coverage (scan intents)** - % of runs that return threads
3. **Thread → Tracker clicks (per minute)** - Click rate over time
4. **Click-through rate table (24h)** - CTR by intent with gradient gauge
5. **Followups funnel (24h)** - Stat panel showing runs → thread lists → clicks
6. **Bills funnel (24h)** - Same for bills intent
7. **Interviews funnel (24h)** - Same for interviews intent

**Import to Grafana:**
```bash
# Via UI: Dashboards → Import → Upload JSON
# Via API:
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d @services/api/grafana/dashboards/applylens-agent-thread-tracker.json
```

## Privacy & Security

### What We Track
- **Application IDs** (integers) - for debugging, not stored in metrics
- **Intent names** (strings) - e.g., "followups", "bills"
- **Counts** - how many times events occur

### What We DON'T Track
- ❌ Email addresses
- ❌ Email subjects or snippets
- ❌ Thread IDs or Gmail message IDs
- ❌ User names or personal data
- ❌ Email content or metadata

### CSRF Exemption

The `/metrics/thread-to-tracker-click` endpoint is exempt from CSRF protection because:
- It's a lightweight observability endpoint
- It only increments counters (no sensitive state changes)
- It only accepts non-PII data (application_id + intent)
- Exemption is granted via `app/core/csrf.py::CSRF_EXEMPT_PATHS`

## Testing

### Backend Tests

**File:** `services/api/tests/test_agent_observability.py`

**Coverage:**
- ✅ Agent run counter increments correctly
- ✅ Thread list counter only increments when threads > 0
- ✅ Click counter increments on endpoint call
- ✅ Endpoint returns 200 OK
- ✅ Endpoint accepts null intent
- ✅ Endpoint rejects invalid payloads
- ✅ Integration test: orchestrator → metrics

**Run tests:**
```bash
cd services/api
python -m pytest tests/test_agent_observability.py -v
```

### Frontend Tests

**File:** `apps/web/src/tests/ThreadViewer.application.test.tsx`

**Coverage:**
- ✅ Metrics endpoint called with correct payload (application_id + intent)
- ✅ Metrics endpoint called without intent when not provided
- ✅ Navigation works even if metrics endpoint fails
- ✅ Different intents tracked correctly
- ✅ Metrics NOT called for "Create Application" action

**Run tests:**
```bash
cd apps/web
npm test ThreadViewer.application.test.tsx
```

### E2E Tests

**File:** `apps/web/tests/e2e/chat-thread-tracker-flow.spec.ts`

**Coverage:**
- ✅ Full flow: Chat → Thread Viewer → Open in Tracker
- ✅ Tracker navigation smoke test
- ✅ appId parameter validation

**Run tests:**
```bash
cd apps/web
npx playwright test chat-thread-tracker-flow.spec.ts
```

## Monitoring & Alerts

### Recommended Alerts

1. **Low Thread List Coverage**
   ```yaml
   alert: AgentThreadListCoverageLow
   expr: |
     (sum by (intent) (rate(applylens_agent_threadlist_returned_total{intent=~"followups|bills"}[1h]))
      /
      sum by (intent) (rate(applylens_agent_runs_total{intent=~"followups|bills"}[1h]))
     ) < 0.3
   for: 15m
   labels:
     severity: warning
   annotations:
     summary: "Thread list coverage < 30% for {{ $labels.intent }}"
     description: "Agent is returning empty results too frequently"
   ```

2. **Low Click-Through Rate**
   ```yaml
   alert: AgentCTRLow
   expr: |
     (sum by (intent) (rate(applylens_agent_thread_to_tracker_click_total[6h]))
      /
      sum by (intent) (rate(applylens_agent_runs_total[6h]))
     ) < 0.05
   for: 30m
   labels:
     severity: info
   annotations:
     summary: "CTR < 5% for {{ $labels.intent }}"
     description: "Users are not engaging with surfaced threads"
   ```

3. **Agent Stalled**
   ```yaml
   alert: AgentNotRunning
   expr: |
     rate(applylens_agent_runs_total[10m]) == 0
   for: 15m
   labels:
     severity: critical
   annotations:
     summary: "No agent runs in 15 minutes"
     description: "Agent may be down or not receiving requests"
   ```

## Troubleshooting

### No Data in Grafana Dashboard

1. **Check Prometheus is scraping:**
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

2. **Verify metrics are exported:**
   ```bash
   curl http://localhost:8000/metrics | grep applylens_agent
   ```

3. **Check backend logs:**
   ```bash
   docker logs applylens-api | grep "Thread-to-tracker click"
   ```

### Metrics Not Incrementing

1. **Agent runs but no counter:**
   - Check orchestrator calls `record_agent_run()` on success
   - Verify `intent` parameter is passed correctly

2. **Threads shown but no threadlist counter:**
   - Check that `thread_count > 0` in orchestrator logic
   - Verify `record_threadlist_returned()` is called

3. **Clicks not tracked:**
   - Check browser console for fetch errors
   - Verify frontend is calling `/metrics/thread-to-tracker-click`
   - Check backend logs for CSRF errors (should be exempt)

### High CTR (Suspicious)

If CTR > 80%, investigate:
- Are threads being auto-clicked?
- Is the frontend sending duplicate requests?
- Check for bot activity or automated tests hitting production

## Future Enhancements

### Potential Additions

1. **Thread-level metrics**
   - Track which specific threads are clicked
   - Measure time-to-click (latency from display to interaction)

2. **Session-based funnels**
   - Track full user sessions: query → results → click → action
   - Measure drop-off at each stage

3. **A/B testing support**
   - Add `variant` label for UI/algorithm experiments
   - Compare CTR across different thread ranking strategies

4. **Application outcome tracking**
   - Did the user update the application after navigating from thread?
   - Link tracker activity back to email threads

### NOT Recommended

❌ **Don't add high-cardinality labels:**
- `application_id` as a label (unbounded)
- `thread_id` as a label (unbounded)
- `user_id` as a label (PII + high cardinality)

❌ **Don't log PII:**
- Email addresses, subjects, snippets
- User names or personal identifiers

## References

- **Backend Metrics:** `app/agent/metrics.py`
- **Orchestrator:** `app/agent/orchestrator.py`
- **Metrics Endpoint:** `app/routers/metrics.py`
- **CSRF Config:** `app/core/csrf.py`
- **Frontend Component:** `apps/web/src/components/mail/ThreadViewer.tsx`
- **Grafana Dashboard:** `services/api/grafana/dashboards/applylens-agent-thread-tracker.json`
- **Tests:** `services/api/tests/test_agent_observability.py`, `apps/web/src/tests/ThreadViewer.application.test.tsx`
