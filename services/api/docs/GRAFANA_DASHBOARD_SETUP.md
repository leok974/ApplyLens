# Agent V2 - Grafana Dashboard Import Instructions

## Overview

This dashboard provides comprehensive observability for the Mailbox Agent V2 system, tracking:
- Agent run volume and latency
- Tool usage patterns
- RAG context retrieval
- Redis cache performance
- Error rates

## Prerequisites

1. **Prometheus** scraping `/metrics` from `applylens-api-prod`
2. **Grafana** instance with Prometheus datasource configured
3. Agent V2 metrics being produced (deploy v0.5.10+)

## Metrics Used

The dashboard queries these metrics from `services/api/app/agent/metrics.py`:

- `mailbox_agent_runs_total{intent, mode, status}` - Agent run counts
- `mailbox_agent_run_duration_seconds_bucket{intent, mode}` - Run latency histogram
- `mailbox_agent_tool_calls_total{tool, status}` - Tool invocation counts
- `mailbox_agent_tool_latency_seconds{tool}` - Tool latency histogram
- `mailbox_agent_rag_context_count{source}` - RAG context usage (email/kb)
- `mailbox_agent_redis_hits_total{kind, result}` - Redis cache hits/misses

## Import Steps

### 1. Access Grafana

Navigate to your Grafana instance (typically running alongside Prometheus).

### 2. Import Dashboard

1. Click **+ Create** (top menu) → **Import**
2. Click **Upload JSON file**
3. Select: `services/api/grafana/dashboards/agent-v2-overview.json`
4. Click **Load**

### 3. Configure Datasource

1. In the import dialog, select your **Prometheus datasource** from the dropdown
2. (Optional) Choose a folder for the dashboard
3. Click **Import**

### 4. Verify Dashboard

The dashboard should now display with 9 panels:

#### Row 1 - Performance Overview
- **Agent Runs per Minute** - Requests/sec by intent (line chart)
- **Agent Run Duration** - p50/p95/p99 latency (line chart)

#### Row 2 - Tool & RAG Analysis
- **Tool Usage by Type** - Tool call counts (bar gauge)
- **Total RAG Contexts Used** - Context retrieval volume (stat)
- **Redis Cache Hit Ratio** - Cache effectiveness (stat with thresholds)
- **RAG Context Sources** - Email vs KB breakdown (pie chart)
- **Tool Call Success Rate** - Tool reliability (timeseries)

#### Row 3 - Summary & Health
- **Agent Run Summary** - Intent breakdown table (last 6h)
- **Error Rate** - Agent failure rate (stat with thresholds)

## Dashboard Features

### Variables

- **DS_PROM** - Prometheus datasource selector
- **Intent Filter** - Filter all panels by intent:
  - `suspicious` - Security scans
  - `bills` - Bill/invoice detection
  - `interviews` - Interview scheduling
  - `followups` - Follow-up suggestions
  - `profile` - Mailbox statistics
  - `generic` - General queries
  - `All` - No filtering

### Time Range

- Default: Last 6 hours
- Auto-refresh: 30 seconds
- Timezone: Browser local

### Color Coding

- **Green** - Healthy metrics (>80% cache hit, <1% error)
- **Yellow** - Warning thresholds (50-80% cache hit, 1-5% error)
- **Orange** - Degraded (high tool usage, 5-10% error)
- **Red** - Critical (low cache hit, >10% error)

## Validation

After import, verify the dashboard is working:

1. **Check for data** - All panels should show metrics (not "No data")
2. **Test intent filter** - Select different intents and verify panels update
3. **Verify time range** - Change time range and confirm data adjusts
4. **Monitor live** - With auto-refresh, metrics should update every 30s

If panels show "No data":
- Verify Prometheus is scraping `/metrics` from API
- Check that Agent V2 has been run at least once (v0.5.10+)
- Confirm metric names match `services/api/app/agent/metrics.py`

## Customization

### Adding Panels

To add custom panels:
1. Click **Add panel** (top right)
2. Use PromQL queries against the metrics above
3. Save the dashboard

### Modifying Thresholds

To adjust alert thresholds:
1. Edit panel → Field tab → Thresholds
2. Modify values (e.g., change cache hit warning from 50% → 60%)
3. Apply changes

### Exporting Changes

If you modify the dashboard:
1. Click **Share** → **Export** → **Save to file**
2. Replace `services/api/grafana/dashboards/agent-v2-overview.json`
3. Commit and push to git

## Usage Tips

### Debugging Slow Queries

1. Set **Time range** to recent window (e.g., Last 1 hour)
2. Filter by **Intent** showing high latency
3. Check **Tool Call Success Rate** - failing tools slow overall runs
4. Check **RAG Context Sources** - excessive KB lookups add latency

### Optimizing Cache

1. Check **Redis Cache Hit Ratio** stat
2. If < 50%, cache is ineffective
3. Investigate which cache types (domain risk, session) are missing
4. Consider adjusting TTLs or pre-warming cache

### Monitoring Production

1. Set **Time range** to Last 24 hours
2. Leave **Intent** on `All`
3. Monitor **Error Rate** stat (should be green/0%)
4. Watch **Agent Run Summary** table for intent distribution

## Troubleshooting

### "No data points" on all panels

**Cause**: Prometheus not scraping API metrics endpoint

**Fix**:
```bash
# Verify metrics endpoint is accessible
curl https://api.applylens.app/metrics | grep mailbox_agent
```

If no output, check API deployment.

### "Cannot read property of undefined" errors

**Cause**: Prometheus datasource not configured

**Fix**:
1. Go to **Configuration** → **Data Sources**
2. Add Prometheus datasource
3. Point to your Prometheus instance
4. Re-import dashboard and select datasource

### Panel shows flat line at 0

**Cause**: No agent runs in selected time range

**Fix**:
1. Extend time range (e.g., Last 24 hours)
2. Or run smoke test to generate metrics:
```bash
cd d:\ApplyLens\services\api
python scripts/agent_v2_intent_smoke.py
```

### Metric name mismatch errors

**Cause**: Dashboard JSON has old metric names

**Fix**:
1. Check `services/api/app/agent/metrics.py` for current names
2. Edit panel queries to match
3. Re-export JSON

## Next Steps

Once dashboard is imported and validated:

1. **Set up alerts** - Configure Grafana alerts on error rate > 5%
2. **Create SLOs** - Define SLOs for p95 latency < 5s
3. **Add annotations** - Mark deployments on timeline
4. **Export to PDF** - Generate daily reports for stakeholders

For questions, check:
- Dashboard JSON: `services/api/grafana/dashboards/agent-v2-overview.json`
- Metrics definitions: `services/api/app/agent/metrics.py`
- Instrumentation: `services/api/app/agent/orchestrator.py` (lines with `record_*`)
