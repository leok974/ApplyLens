# Datadog Setup Guide – ApplyLens Observability Copilot Hackathon

This guide provides step-by-step instructions for creating the Datadog dashboard, SLOs, and monitors for the hackathon demo.

## Prerequisites

- Datadog account with API access
- Datadog API key configured in `.env.hackathon`
- Hackathon environment running (`scripts/hackathon-start.ps1`)
- Traffic generator running to generate baseline metrics

## 1️⃣ Dashboard Setup

### Dashboard: "ApplyLens Observability Copilot – Hackathon"

**Steps to create:**
1. Navigate to **Dashboards** → **New Dashboard**
2. Name: `ApplyLens Observability Copilot – Hackathon`
3. Add widgets as described below

---

### Section A: LLM Health

#### Widget 1: LLM Latency (Top-left)
**Type:** Timeseries
**Title:** LLM Classification Latency (p50/p95/p99)
**Queries:**
```
avg:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(avg, 60)
p95:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(max, 60)
p99:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(max, 60)
```
**Display:**
- Y-axis: milliseconds
- Line style: p50 (solid), p95 (dashed), p99 (dotted)
- Alert threshold: 2000ms (SLO target)

#### Widget 2: LLM Error Rate (Top-right)
**Type:** Timeseries
**Title:** LLM Error Rate
**Query:**
```
(sum:applylens.llm.error_total{env:hackathon}.as_rate() /
 sum:applylens.llm.request_total{env:hackathon}.as_rate()) * 100
```
**Display:**
- Y-axis: percentage (0-100%)
- Rollup: 5m
- Alert threshold: 5%
- Color: red when > 5%

**Note:** If you don't emit `request_total`, approximate with:
```
sum:applylens.llm.error_total{env:hackathon}.as_count().rollup(sum, 300)
```

#### Widget 3: Token Usage (Second row, left)
**Type:** Query Value
**Title:** Tokens / 5min
**Query:**
```
sum:applylens.llm.tokens_used{env:hackathon}.rollup(sum, 300)
```
**Display:**
- Unit: tokens
- Precision: 0 decimals
- Optional: split by `task_type` for classify vs extract breakdown

#### Widget 4: Cost Estimate (Second row, right)
**Type:** Query Value
**Title:** Estimated Cost / Hour
**Query:**
```
sum:applylens.llm.cost_estimate_usd{env:hackathon}.rollup(sum, 3600)
```
**Display:**
- Unit: USD ($)
- Precision: 4 decimals
- Color: orange if > $1/hr, red if > $5/hr

#### Widget 5: Task Type Breakdown (Second row, wide)
**Type:** Toplist or Table
**Title:** LLM Operations by Task Type
**Queries:**
```
sum:applylens.llm.latency_ms{env:hackathon} by {task_type}.rollup(avg, 60)
sum:applylens.llm.tokens_used{env:hackathon} by {task_type}.rollup(sum, 300)
```
**Display:**
- Columns: Task Type, Avg Latency (ms), Tokens Used
- Sort by: Tokens Used (descending)

---

### Section B: Ingest Freshness

**Note:** These widgets are optional if you haven't implemented ingest lag metrics.

#### Widget 6: Ingest Lag
**Type:** Timeseries
**Title:** Email Ingest Lag
**Query:**
```
avg:applylens.ingest_lag_seconds{env:hackathon}
```
**Display:**
- Y-axis: seconds
- Alert threshold: 300s (5 minutes SLO)
- Color: green < 60s, yellow < 300s, red > 300s

#### Widget 7: SLO Compliance
**Type:** Query Value
**Title:** % Within Ingest SLO (< 5min)
**Query:**
```
(count:applylens.ingest_event_total{env:hackathon,lag_slo_status:ok} /
 count:applylens.ingest_event_total{env:hackathon}) * 100
```
**Display:**
- Unit: percentage
- Target: 99%
- Color: green > 99%, yellow > 95%, red < 95%

**Alternative (if no lag_slo_status tag):**
Use a monitor-based SLO widget instead (see SLO section below).

---

### Section C: Security Signals

**Note:** These are stretch goals if you have security metrics implemented.

#### Widget 8: High-Risk Email Rate
**Type:** Timeseries
**Title:** High-Risk Detection Rate
**Query:**
```
avg:applylens.security_high_risk_rate{env:hackathon}
```
**Display:**
- Y-axis: percentage
- Baseline: show 7-day average
- Alert on anomalies (3x baseline)

#### Widget 9: Quarantine Actions
**Type:** Bar Chart or Query Values
**Title:** Quarantine Actions (Last 24h)
**Queries:**
```
sum:applylens.quarantine_actions_total{env:hackathon,action:quarantine}.rollup(sum, 86400)
sum:applylens.quarantine_actions_total{env:hackathon,action:release}.rollup(sum, 86400)
```
**Display:**
- Quarantine: red bar
- Release: green bar
- Side-by-side comparison

---

### Section D: Infrastructure Overview

#### Widget 10: API Request Duration
**Type:** Timeseries
**Title:** API Request Duration (p95)
**Query:**
```
p95:trace.http.request.duration.by.service{service:applylens-api-hackathon}
```
**Display:**
- Y-axis: milliseconds
- Show by endpoint if available
- Color code by status (2xx green, 4xx yellow, 5xx red)

#### Widget 11: API Error Rate
**Type:** Timeseries
**Title:** API Error Count
**Query:**
```
sum:trace.http.request.errors{service:applylens-api-hackathon}.as_count()
```
**Display:**
- Y-axis: count
- Rollup: 1m
- Stack by error type if available

#### Widget 12: Service Uptime
**Type:** Query Value
**Title:** API Uptime %
**Query:**
```
(sum:trace.http.request{service:applylens-api-hackathon,http.status_code:2*}.as_count() /
 sum:trace.http.request{service:applylens-api-hackathon}.as_count()) * 100
```
**Display:**
- Unit: percentage
- Target: 99.9%
- Time window: Last 24h

---

### Section E: SLO Widgets

After creating SLOs (see section 2 below), add these widgets to the top of the dashboard:

#### Widget 13: LLM Latency SLO
**Type:** SLO Summary Widget
**SLO:** "ApplyLens – LLM Classify Latency SLO"
**Display:**
- Show current status (✓ or ✗)
- Show remaining error budget
- Link to full SLO page

#### Widget 14: Ingest Freshness SLO (if implemented)
**Type:** SLO Summary Widget
**SLO:** "ApplyLens – Ingest Freshness SLO"
**Display:**
- Same as above

---

### Dashboard Layout Recommendation

```
┌─────────────────────────────────────────────────────────────┐
│  📊 SLOs Row                                                 │
│  [LLM Latency SLO] [Ingest Freshness SLO]                   │
├─────────────────────────────────────────────────────────────┤
│  🤖 LLM Health                                               │
│  [Latency p50/95/99]      [Error Rate %]                    │
│  [Tokens/5min] [Cost/hr]  [Task Type Breakdown]             │
├─────────────────────────────────────────────────────────────┤
│  📥 Ingest Freshness (optional)                              │
│  [Ingest Lag Timeseries]  [% Within SLO]                    │
├─────────────────────────────────────────────────────────────┤
│  🛡️ Security Signals (optional)                              │
│  [High-Risk Rate]         [Quarantine Actions]              │
├─────────────────────────────────────────────────────────────┤
│  🏗️ Infrastructure                                           │
│  [API Duration p95]       [API Errors]                      │
│  [Uptime %]                                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ SLO Configuration

### SLO 1: LLM Classification Latency

**Navigate to:** Monitors → Service Level Objectives → New SLO

**Configuration:**
- **Name:** `ApplyLens – LLM Classify Latency SLO`
- **Type:** Metric-based
- **Metric Query (Good Events):**
  ```
  sum:applylens.llm.latency_ms{env:hackathon,task_type:classify}.as_count() -
  sum:applylens.llm.latency_ms{env:hackathon,task_type:classify,latency_bucket:over_2000ms}.as_count()
  ```
- **Metric Query (Total Events):**
  ```
  sum:applylens.llm.latency_ms{env:hackathon,task_type:classify}.as_count()
  ```
- **Target:** 99.0%
- **Time Window:** 7 days (rolling)
- **Tags:** `env:hackathon`, `component:llm`, `task:classify`
- **Description:** Ensures 99% of LLM classification calls complete within 2000ms

**Alternative (if using APM spans):**
- **Type:** Monitor-based
- **Monitor Query:** `p95:trace.applylens.llm.classify.duration{env:hackathon} > 2000`
- **Target:** 99% uptime (monitor not alerting)

**Alert Configuration:**
- **Warning:** Error budget < 10%
- **Critical:** Error budget < 5%
- **Notifications:** Create incident, link to dashboard

---

### SLO 2: Ingest Freshness (Optional)

**Configuration:**
- **Name:** `ApplyLens – Ingest Freshness SLO`
- **Type:** Metric-based (good/total)
- **Good Events Query:**
  ```
  sum:applylens.ingest_event_total{env:hackathon,lag_slo_status:ok}.as_count()
  ```
- **Total Events Query:**
  ```
  sum:applylens.ingest_event_total{env:hackathon}.as_count()
  ```
- **Target:** 99.0%
- **Time Window:** 7 days
- **Tags:** `env:hackathon`, `component:ingest`
- **Description:** 99% of emails ingested within 5 minutes

**If no lag_slo_status tag:**
Use a monitor-based SLO with monitor query:
```
avg:applylens.ingest_lag_seconds{env:hackathon} > 300
```

---

## 3️⃣ Monitor Configuration

### Monitor 1: LLM Latency Spike

**Navigate to:** Monitors → New Monitor → Metric Monitor

**Configuration:**
- **Name:** `ApplyLens – LLM latency spike (hackathon)`
- **Query:**
  ```
  max(last_5m):p95:applylens.llm.latency_ms{env:hackathon} > 3000
  ```
- **Alert Conditions:**
  - **Warning:** p95 > 2500ms
  - **Critical:** p95 > 3000ms
- **Notify:**
  - Create Datadog Incident
  - Severity: SEV-2
  - Attach dashboard link
- **Tags:** `env:hackathon`, `component:llm`, `priority:high`

**Message Template:**
```
{{#is_alert}}
⚠️ LLM Latency Spike Detected

Impact: Users experiencing slow email classification/extraction
Metric: {{value}} ms (p95 latency over last 5m)
Threshold: 3000ms

🔍 First Response Steps:
1. Open LLM Health Dashboard: [Dashboard Link]
2. Check if spike correlates with traffic increase
3. Inspect recent traces: task_type:classify or task_type:extract
4. Review Gemini API status

🛠️ Mitigation Options:
- If Gemini unstable: Reduce traffic rate or enable heuristic-only mode
- If traffic spike: Scale up workers or throttle requests
- Check for prompt changes that increased token count

{{/is_alert}}

{{#is_recovery}}
✅ LLM Latency Recovered
Latency returned to normal (p95 < 3000ms).
{{/is_recovery}}
```

**Incident Template Fields:**
- **Title:** "LLM Latency Spike – {{value}}ms p95"
- **Severity:** SEV-2
- **Customer Impact:** Degraded performance
- **Root Cause:** (To be determined during investigation)

---

### Monitor 2: LLM Error Burst

**Configuration:**
- **Name:** `ApplyLens – LLM error burst (hackathon)`
- **Query:**
  ```
  100 * (sum(last_5m):applylens.llm.error_total{env:hackathon}.as_count() /
         sum(last_5m):applylens.llm.request_total{env:hackathon}.as_count()) > 5
  ```
- **Alert Conditions:**
  - **Warning:** Error rate > 3%
  - **Critical:** Error rate > 5%
- **Notify:** Create incident, ping on-call
- **Tags:** `env:hackathon`, `component:llm`, `priority:critical`

**Message Template:**
```
{{#is_alert}}
🚨 LLM Error Burst Detected

Impact: {{value}}% of LLM requests failing
Threshold: 5% error rate over last 5 minutes

🔍 Investigation Steps:
1. Check LLM Health Dashboard → Error Rate panel
2. Filter logs by env:hackathon AND error
3. Check error_type distribution (timeout vs auth vs validation)
4. Review Gemini API status page

🛠️ Common Causes & Fixes:
- **Provider outage:** Enable heuristic-only mode (set USE_GEMINI_FOR_CLASSIFY=0)
- **Auth misconfiguration:** Verify GOOGLE_CLOUD_PROJECT and credentials
- **Invalid inputs:** Check recent email parsing changes
- **Rate limiting:** Reduce traffic generator rate

📊 Quick Links:
- Dashboard: [Link]
- Recent Traces: [APM Link with env:hackathon filter]
- Logs: [Log Explorer with error filter]
{{/is_alert}}

{{#is_recovery}}
✅ LLM Error Rate Recovered
Error rate back below 5% threshold.
{{/is_recovery}}
```

**Alternative Query (if no request_total):**
```
sum(last_5m):applylens.llm.error_total{env:hackathon}.as_count() > 10
```
Alert if absolute error count exceeds 10 in 5 minutes.

---

### Monitor 3: Token/Cost Anomaly

**Configuration:**
- **Name:** `ApplyLens – LLM token usage anomaly (hackathon)`
- **Query (Anomaly Detection):**
  ```
  avg(last_10m):sum:applylens.llm.tokens_used{env:hackathon} >
  (3 * avg(last_1h):sum:applylens.llm.tokens_used{env:hackathon})
  ```
- **Alert Conditions:**
  - **Warning:** 2x baseline
  - **Critical:** 3x baseline
- **Notify:** Create incident (low priority)
- **Tags:** `env:hackathon`, `component:llm`, `priority:low`

**Message Template:**
```
{{#is_alert}}
⚠️ LLM Token Usage Anomaly

Current Usage: {{value}} tokens/10min
Baseline (1h avg): {{baseline}} tokens/10min
Ratio: {{ratio}}x normal

🔍 Possible Causes:
- Traffic generator running in token_bloat mode
- Prompt drift (prompts getting longer)
- Retry loop or duplicate processing
- Legitimate traffic spike

📊 Investigation:
1. Check traffic generator history:
   python scripts/traffic_generator.py --mode normal_traffic --rate 0.5
2. Review recent traces for repeated operations
3. Check if task_type:extract spike (higher token usage)
4. Inspect prompt templates for unexpected expansion

💰 Cost Impact:
Estimated hourly cost: ${{hourly_cost}} USD
If sustained, daily cost: ${{daily_cost}} USD

🛠️ Mitigation:
- Adjust traffic generator rate if testing
- Review and optimize prompts if production
- Enable rate limiting if necessary
{{/is_alert}}

{{#is_recovery}}
✅ Token Usage Normalized
Usage returned to baseline levels.
{{/is_recovery}}
```

**Alternative (Cost-based):**
```
avg(last_10m):sum:applylens.llm.cost_estimate_usd{env:hackathon} >
(3 * avg(last_1h):sum:applylens.llm.cost_estimate_usd{env:hackathon})
```

---

### Monitor 4: Security Risk Anomaly (Bonus)

**Configuration:**
- **Name:** `ApplyLens – Security risk anomaly (hackathon)`
- **Query:**
  ```
  avg(last_10m):applylens.security_high_risk_rate{env:hackathon} >
  (3 * avg(last_1h):applylens.security_high_risk_rate{env:hackathon})
  ```
- **Alert Conditions:**
  - **Warning:** 2x baseline
  - **Critical:** 3x baseline
- **Notify:** Security team, create incident
- **Tags:** `env:hackathon`, `component:security`, `priority:high`

**Message Template:**
```
{{#is_alert}}
🛡️ Security Risk Anomaly Detected

Current Risk Rate: {{value}}%
Baseline (1h avg): {{baseline}}%
Ratio: {{ratio}}x normal

🔍 Investigation Required:
1. Check Security Signals dashboard
2. Review high-risk email samples
3. Verify detection rules aren't over-triggering
4. Check for coordinated attack patterns

🛠️ Response:
- Review quarantine queue for false positives
- Adjust risk scoring thresholds if needed
- Enable additional logging for suspicious patterns
{{/is_alert}}

{{#is_recovery}}
✅ Security Risk Rate Normalized
{{/is_recovery}}
```

---

## 4️⃣ Quick Setup Commands

### Export Dashboard as JSON (for version control)

After creating the dashboard manually, export it:

```bash
# Install Datadog CLI (if not already installed)
pip install datadog-api-client

# Export dashboard JSON
# Replace DASHBOARD_ID with your dashboard's ID from the URL
python -c "
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.dashboards_api import DashboardsApi

config = Configuration()
with ApiClient(config) as api_client:
    api = DashboardsApi(api_client)
    dashboard = api.get_dashboard('DASHBOARD_ID')
    import json
    print(json.dumps(dashboard.to_dict(), indent=2))
" > hackathon/datadog_dashboard.json
```

### Import Monitors Programmatically (Optional)

If you want to script monitor creation:

```python
# See scripts/create_datadog_monitors.py (to be created if needed)
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.monitors_api import MonitorsApi
from datadog_api_client.v1.model.monitor import Monitor

config = Configuration()
with ApiClient(config) as api_client:
    api = MonitorsApi(api_client)

    # Create LLM latency monitor
    monitor = Monitor(
        name="ApplyLens – LLM latency spike (hackathon)",
        type="metric alert",
        query="max(last_5m):p95:applylens.llm.latency_ms{env:hackathon} > 3000",
        message="LLM latency spike detected...",
        tags=["env:hackathon", "component:llm"],
    )
    result = api.create_monitor(body=monitor)
    print(f"Created monitor: {result.id}")
```

---

## 5️⃣ Testing & Validation

### Verify Metrics Are Flowing

Before creating monitors, ensure metrics are being emitted:

```bash
# In Datadog Metrics Explorer, search for:
applylens.llm.latency_ms
applylens.llm.error_total
applylens.llm.tokens_used
applylens.llm.cost_estimate_usd

# Check that env:hackathon tag is present
# Should see data points within last 5 minutes
```

### Test Monitors with Traffic Generator

```bash
# Generate normal traffic (should NOT trigger monitors)
python scripts/traffic_generator.py \
  --mode normal_traffic \
  --rate 1.0 \
  --duration 300

# Trigger latency monitor
python scripts/traffic_generator.py \
  --mode latency_injection \
  --rate 2.0 \
  --duration 300

# Wait 5 minutes, verify monitor alerts

# Trigger error monitor
python scripts/traffic_generator.py \
  --mode error_injection \
  --rate 2.0 \
  --duration 300

# Trigger token anomaly monitor
python scripts/traffic_generator.py \
  --mode token_bloat \
  --rate 1.0 \
  --duration 600
```

### Validate SLOs

```bash
# Generate 1 hour of clean traffic to establish baseline
python scripts/traffic_generator.py \
  --mode normal_traffic \
  --rate 1.0 \
  --duration 3600

# Check SLO status in Datadog UI
# Both SLOs should be > 99% (green)

# Generate failure scenarios
python scripts/traffic_generator.py \
  --mode latency_injection \
  --rate 0.5 \
  --duration 600

# Check error budget burn rate
# Should see SLO status drop slightly but remain above critical threshold
```

---

## 6️⃣ Dashboard Sharing & Demo

### Make Dashboard Public (for demo video)

1. Open dashboard → Settings (⚙️) → Generate Public URL
2. Copy link for demo video description
3. **Security:** Ensure no sensitive data visible (PII, API keys)

### Dashboard Snapshots

Take screenshots for hackathon submission:

1. **Full dashboard view** (all sections visible)
2. **LLM Health during normal traffic** (baseline)
3. **LLM Health during latency spike** (red alerts)
4. **SLO widget showing error budget burn**
5. **Incident created from monitor alert**

### Live Demo Script

```
1. Show dashboard in normal state (2 min):
   - All green, low latency, no errors
   - SLOs at 100%, full error budget

2. Trigger latency spike (2 min):
   python scripts/traffic_generator.py --mode latency_injection --rate 2
   - Watch p95 latency climb above 3000ms
   - Monitor triggers, creates incident
   - Show incident details with dashboard link

3. Show recovery (1 min):
   python scripts/traffic_generator.py --mode normal_traffic --rate 1
   - Latency drops back to normal
   - Monitor recovers, incident resolves
   - SLO error budget slightly consumed

4. Highlight key features:
   - Real-time metrics from Gemini integration
   - Automatic incident creation
   - Dashboard links in runbooks
   - Cost tracking per hour
```

---

## 7️⃣ Troubleshooting

### Metrics Not Showing Up

**Check Datadog agent logs:**
```bash
docker compose -f docker-compose.hackathon.yml logs datadog-agent | grep ERROR
```

**Verify StatsD is receiving metrics:**
```bash
# In app container
docker compose -f docker-compose.hackathon.yml exec api python -c "
from datadog import statsd
statsd.increment('test.metric', tags=['env:hackathon'])
print('Test metric sent')
"

# Check Datadog Metrics Explorer for 'test.metric'
```

**Common issues:**
- `DD_API_KEY` not set or invalid
- Datadog agent container not running
- StatsD port 8125 not accessible
- Tags not properly formatted (use `key:value` not `key=value`)

### Monitors Not Triggering

**Check monitor evaluation:**
1. Open monitor → Show monitor evaluation graph
2. Verify query returns data
3. Check if threshold is reasonable (too high/low)

**Test monitor query directly:**
- Copy query to Metrics Explorer
- Adjust time range to see if data exists
- Check tag filters (env:hackathon present?)

### SLOs Not Calculating

**Common issues:**
- Not enough data points (need at least 1 hour of data)
- Good/total event queries misconfigured
- Monitor-based SLO using incorrect monitor
- Time window too short for meaningful calculation

**Fix:**
- Generate sustained traffic for 1+ hour
- Verify good events < total events
- Check monitor has evaluated at least once

---

## 8️⃣ Next Steps

After completing this setup:

1. ✅ **Run full demo workflow** (see TRAFFIC_GENERATOR.md)
2. ✅ **Take screenshots** for hackathon submission
3. ✅ **Export dashboard JSON** for version control
4. ✅ **Document any custom modifications** in this file
5. ✅ **Prepare 3-minute video** showing dashboard + incidents

**Demo Day Checklist:**
- [ ] Dashboard public URL generated
- [ ] All monitors enabled and tested
- [ ] SLOs showing green status
- [ ] Traffic generator scripts ready
- [ ] Incident creation tested end-to-end
- [ ] Screenshots saved to `hackathon/screenshots/`
- [ ] Video recording equipment tested

---

## Additional Resources

- **Datadog Dashboard API:** https://docs.datadoghq.com/api/latest/dashboards/
- **Datadog Monitor API:** https://docs.datadoghq.com/api/latest/monitors/
- **Datadog SLO Guide:** https://docs.datadoghq.com/service_management/service_level_objectives/
- **ApplyLens Hackathon Docs:**
  - Architecture: `hackathon/ARCHITECTURE.md`
  - Traffic Generator: `hackathon/TRAFFIC_GENERATOR.md`
  - Main Guide: `HACKATHON.md`

---

**Last Updated:** 2024-11-25
**Hackathon:** Google Cloud AI Partner Catalyst
**Team:** ApplyLens
