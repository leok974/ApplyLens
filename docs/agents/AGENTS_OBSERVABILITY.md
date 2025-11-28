# Agents Observability Guide

**Comprehensive monitoring, metrics, logging, and debugging for ApplyLens Agentic System**

This guide covers the complete observability stack for agents: Prometheus metrics, audit logs, SSE streaming, error tracking, and operational dashboards.

---

## Table of Contents

1. [Overview](#overview)
2. [Metrics (Prometheus)](#metrics-prometheus)
3. [Audit Logs (PostgreSQL)](#audit-logs-postgresql)
4. [Real-Time Streaming (SSE)](#real-time-streaming-sse)
5. [Dashboards (Grafana)](#dashboards-grafana)
6. [Alerting](#alerting)
7. [Debugging & Troubleshooting](#debugging--troubleshooting)
8. [Performance Tuning](#performance-tuning)

---

## Overview

### Observability Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Execution                          │
│  (warehouse_health, custom_agent, ...)                     │
└────────┬───────────┬───────────┬──────────────┬─────────────┘
         │           │           │              │
         │           │           │              │
         ▼           ▼           ▼              ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐  ┌──────────────┐
   │Prometheus│ │PostgreSQL│ │EventBus │  │  Stdout      │
   │ Metrics  │ │Audit Log │ │   SSE   │  │  Logs        │
   └────┬─────┘ └────┬─────┘ └────┬────┘  └──────┬───────┘
        │            │            │               │
        │            │            │               │
        ▼            ▼            ▼               ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐  ┌──────────────┐
   │ Grafana │ │ SQL/API │ │Frontend │  │ Loki/Splunk  │
   │Dashboard│ │ Queries │ │ Console │  │ Aggregation  │
   └─────────┘ └─────────┘ └─────────┘  └──────────────┘
```

**Data Sources:**
1. **Prometheus Metrics** - Time-series data for trends, rates, histograms
2. **Audit Logs** - Structured database records for compliance, debugging
3. **SSE Events** - Real-time streams for live dashboards, notifications
4. **Application Logs** - Unstructured stdout/stderr for detailed debugging

---

## Metrics (Prometheus)

### Available Metrics

#### 1. `agent_runs_total` (Counter)

**Description**: Total number of agent runs by type and status

**Labels**:
- `agent_type` - Agent identifier (e.g., `warehouse_health`)
- `status` - Run outcome: `success`, `failed`
- `user_email` - User who triggered run (optional)

**Example Queries:**

```promql
# Total successful runs for warehouse_health agent
agent_runs_total{agent_type="warehouse_health", status="success"}

# Success rate (last 5 minutes)
sum(rate(agent_runs_total{status="success"}[5m])) /
sum(rate(agent_runs_total[5m]))

# Failed runs by agent type
sum by (agent_type) (
  rate(agent_runs_total{status="failed"}[5m])
)

# Runs by user
sum by (user_email) (
  agent_runs_total
)
```

#### 2. `agent_run_duration_seconds` (Histogram)

**Description**: Agent execution duration in seconds

**Labels**:
- `agent_type` - Agent identifier

**Buckets**: `[1, 5, 10, 30, 60, 120, 300, 600, inf]` seconds

**Example Queries:**

```promql
# Average duration (last 5 minutes)
rate(agent_run_duration_seconds_sum{agent_type="warehouse_health"}[5m]) /
rate(agent_run_duration_seconds_count{agent_type="warehouse_health"}[5m])

# 50th percentile (median)
histogram_quantile(0.5,
  rate(agent_run_duration_seconds_bucket{agent_type="warehouse_health"}[5m])
)

# 95th percentile
histogram_quantile(0.95,
  rate(agent_run_duration_seconds_bucket{agent_type="warehouse_health"}[5m])
)

# 99th percentile
histogram_quantile(0.99,
  rate(agent_run_duration_seconds_bucket{agent_type="warehouse_health"}[5m])
)

# Slowest agent type (average duration)
topk(5,
  rate(agent_run_duration_seconds_sum[5m]) /
  rate(agent_run_duration_seconds_count[5m])
) by (agent_type)
```

### Metrics Endpoint

**URL**: `http://localhost:8000/metrics`

**Format**: Prometheus text exposition format

**Example Output:**
```
# HELP agent_runs_total Total number of agent runs
# TYPE agent_runs_total counter
agent_runs_total{agent_type="warehouse_health",status="success",user_email="ops@applylens.com"} 42.0
agent_runs_total{agent_type="warehouse_health",status="failed",user_email="ops@applylens.com"} 3.0

# HELP agent_run_duration_seconds Agent execution duration
# TYPE agent_run_duration_seconds histogram
agent_run_duration_seconds_bucket{agent_type="warehouse_health",le="1.0"} 0.0
agent_run_duration_seconds_bucket{agent_type="warehouse_health",le="5.0"} 5.0
agent_run_duration_seconds_bucket{agent_type="warehouse_health",le="10.0"} 15.0
agent_run_duration_seconds_bucket{agent_type="warehouse_health",le="30.0"} 38.0
agent_run_duration_seconds_bucket{agent_type="warehouse_health",le="+Inf"} 45.0
agent_run_duration_seconds_sum{agent_type="warehouse_health"} 687.3
agent_run_duration_seconds_count{agent_type="warehouse_health"} 45.0
```

### Prometheus Configuration

**Scrape Config** (`prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'applylens-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

**Recording Rules** (optional, for pre-computed aggregations):
```yaml
groups:
  - name: agents
    interval: 30s
    rules:
      # Agent success rate (5m window)
      - record: agent:success_rate:5m
        expr: |
          sum(rate(agent_runs_total{status="success"}[5m])) /
          sum(rate(agent_runs_total[5m]))
      
      # Agent p95 duration (5m window)
      - record: agent:duration_p95:5m
        expr: |
          histogram_quantile(0.95,
            sum(rate(agent_run_duration_seconds_bucket[5m])) by (le, agent_type)
          )
      
      # Agent failure rate by type (5m window)
      - record: agent:failure_rate:5m
        expr: |
          sum(rate(agent_runs_total{status="failed"}[5m])) by (agent_type) /
          sum(rate(agent_runs_total[5m])) by (agent_type)
```

---

## Audit Logs (PostgreSQL)

### Schema

**Table**: `agent_audit_log`

```sql
CREATE TABLE agent_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL UNIQUE,
    agent_type VARCHAR(100) NOT NULL,
    objective TEXT,
    plan JSONB,
    artifacts JSONB,
    status VARCHAR(20) NOT NULL,  -- 'success', 'failed', 'running'
    error_message TEXT,
    user_email VARCHAR(255),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_agent_audit_agent_type ON agent_audit_log(agent_type);
CREATE INDEX idx_agent_audit_status ON agent_audit_log(status);
CREATE INDEX idx_agent_audit_started_at ON agent_audit_log(started_at DESC);
CREATE INDEX idx_agent_audit_user_email ON agent_audit_log(user_email);
```

### Query Examples

#### Recent Runs
```sql
SELECT 
  run_id,
  agent_type,
  objective,
  status,
  duration_seconds,
  started_at
FROM agent_audit_log
ORDER BY started_at DESC
LIMIT 20;
```

#### Failed Runs (Last 24 Hours)
```sql
SELECT 
  run_id,
  agent_type,
  objective,
  error_message,
  started_at
FROM agent_audit_log
WHERE status = 'failed'
  AND started_at > NOW() - INTERVAL '24 hours'
ORDER BY started_at DESC;
```

#### Success Rate by Agent Type (Last 7 Days)
```sql
SELECT 
  agent_type,
  COUNT(*) FILTER (WHERE status = 'success') AS success_count,
  COUNT(*) FILTER (WHERE status = 'failed') AS failed_count,
  COUNT(*) AS total_count,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE status = 'success') / COUNT(*),
    2
  ) AS success_rate_pct
FROM agent_audit_log
WHERE started_at > NOW() - INTERVAL '7 days'
GROUP BY agent_type
ORDER BY total_count DESC;
```

#### Average Duration by Agent Type
```sql
SELECT 
  agent_type,
  COUNT(*) AS runs,
  ROUND(AVG(duration_seconds)::numeric, 2) AS avg_duration_sec,
  ROUND(MIN(duration_seconds)::numeric, 2) AS min_duration_sec,
  ROUND(MAX(duration_seconds)::numeric, 2) AS max_duration_sec,
  ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_seconds)::numeric, 2) AS p95_duration_sec
FROM agent_audit_log
WHERE status = 'success'
  AND started_at > NOW() - INTERVAL '7 days'
GROUP BY agent_type
ORDER BY avg_duration_sec DESC;
```

#### Slowest Runs (Top 10)
```sql
SELECT 
  run_id,
  agent_type,
  objective,
  duration_seconds,
  started_at
FROM agent_audit_log
WHERE status = 'success'
ORDER BY duration_seconds DESC
LIMIT 10;
```

#### User Activity (Top Users by Runs)
```sql
SELECT 
  user_email,
  COUNT(*) AS total_runs,
  COUNT(*) FILTER (WHERE status = 'success') AS success_runs,
  COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs
FROM agent_audit_log
WHERE started_at > NOW() - INTERVAL '7 days'
  AND user_email IS NOT NULL
GROUP BY user_email
ORDER BY total_runs DESC
LIMIT 10;
```

#### Artifacts Analysis (Warehouse Health Example)
```sql
SELECT 
  run_id,
  started_at,
  artifacts->'parity'->>'status' AS parity_status,
  (artifacts->'parity'->>'es_count')::int AS es_count,
  (artifacts->'parity'->>'bq_count')::int AS bq_count,
  (artifacts->'parity'->>'difference_percent')::numeric AS diff_pct,
  artifacts->'freshness'->>'within_slo' AS freshness_within_slo,
  artifacts->'summary'->>'status' AS overall_status
FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
  AND status = 'success'
  AND started_at > NOW() - INTERVAL '24 hours'
ORDER BY started_at DESC;
```

### API Queries

**Endpoint**: `GET /agents/history`

**Parameters**:
- `limit` - Number of results (default: 50, max: 1000)
- `offset` - Pagination offset (default: 0)
- `agent_type` - Filter by agent type
- `status` - Filter by status (`success`, `failed`)
- `user_email` - Filter by user
- `start_date` - Filter by start date (ISO 8601)
- `end_date` - Filter by end date (ISO 8601)

**Examples:**

```bash
# Recent runs
curl "http://localhost:8000/agents/history?limit=20"

# Failed warehouse health runs
curl "http://localhost:8000/agents/history?agent_type=warehouse_health&status=failed"

# User's runs
curl "http://localhost:8000/agents/history?user_email=ops@applylens.com"

# Date range
curl "http://localhost:8000/agents/history?start_date=2025-10-01&end_date=2025-10-17"
```

### Retention Policy

**Recommended**: Keep audit logs for compliance period (e.g., 90 days, 1 year)

**Cleanup Query:**
```sql
-- Delete logs older than 90 days
DELETE FROM agent_audit_log
WHERE created_at < NOW() - INTERVAL '90 days';
```

**Scheduled Cleanup** (pg_cron):
```sql
-- Run monthly cleanup
SELECT cron.schedule(
  'cleanup-old-agent-logs',
  '0 2 1 * *',  -- 2 AM on 1st of each month
  $$DELETE FROM agent_audit_log WHERE created_at < NOW() - INTERVAL '90 days'$$
);
```

---

## Real-Time Streaming (SSE)

### Architecture

**EventBus** (`app/events/bus.py`):
- AsyncIO pub/sub system
- Per-subscriber `asyncio.Queue`
- Thread-safe `publish_sync()` for executor
- Auto-cleanup on subscriber disconnect

**SSE Endpoint** (`GET /agents/events`):
- W3C Server-Sent Events protocol
- `Content-Type: text/event-stream`
- Auto-reconnect on disconnect
- CORS-friendly (no preflight)

### Event Types

#### 1. `run_started`

**Triggered**: When agent execution begins

**Payload:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_type": "warehouse_health",
  "objective": "Check warehouse health",
  "plan": {
    "steps": ["query_es_daily", "query_bq_daily", "check_parity", ...],
    "dry_run": true,
    "config": {...}
  },
  "timestamp": "2025-10-17T10:30:00Z"
}
```

#### 2. `run_finished`

**Triggered**: When agent execution completes successfully

**Payload:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "duration_seconds": 15.2,
  "artifacts": {
    "parity": {"status": "ok", "es_count": 15000, "bq_count": 15100},
    "freshness": {"status": "ok", "within_slo": true},
    "summary": {"status": "healthy", "checks_passed": 3, "total_checks": 3}
  },
  "timestamp": "2025-10-17T10:30:15Z"
}
```

#### 3. `run_failed`

**Triggered**: When agent execution fails with error

**Payload:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "error": "Elasticsearch connection timeout after 30s",
  "timestamp": "2025-10-17T10:30:10Z"
}
```

### Client Examples

#### JavaScript (Browser)

```javascript
const eventSource = new EventSource('http://localhost:8000/agents/events');

// Handle run_started
eventSource.addEventListener('run_started', (e) => {
  const data = JSON.parse(e.data);
  console.log(`🚀 Started: ${data.agent_type} - ${data.objective}`);
  updateDashboard({ status: 'running', ...data });
});

// Handle run_finished
eventSource.addEventListener('run_finished', (e) => {
  const data = JSON.parse(e.data);
  console.log(`✅ Finished: ${data.run_id} in ${data.duration_seconds}s`);
  updateDashboard({ status: 'success', ...data });
  showNotification('Agent completed successfully', data.artifacts);
});

// Handle run_failed
eventSource.addEventListener('run_failed', (e) => {
  const data = JSON.parse(e.data);
  console.error(`❌ Failed: ${data.run_id} - ${data.error}`);
  updateDashboard({ status: 'failed', ...data });
  showErrorNotification('Agent failed', data.error);
});

// Handle connection errors
eventSource.onerror = (err) => {
  console.error('SSE connection error:', err);
  // EventSource auto-reconnects, but you can show status
  updateConnectionStatus('reconnecting');
};

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  eventSource.close();
});
```

#### Python

```python
import requests
import json

def stream_agent_events():
    """Stream agent events from SSE endpoint."""
    response = requests.get(
        'http://localhost:8000/agents/events',
        stream=True,
        headers={'Accept': 'text/event-stream'}
    )
    
    event_type = None
    
    for line in response.iter_lines():
        if not line:
            continue
        
        line = line.decode('utf-8')
        
        if line.startswith('event: '):
            event_type = line[7:]
        elif line.startswith('data: '):
            data = json.loads(line[6:])
            handle_event(event_type, data)

def handle_event(event_type, data):
    """Handle SSE events."""
    if event_type == 'run_started':
        print(f"🚀 Started: {data['agent_type']} - {data['objective']}")
    elif event_type == 'run_finished':
        print(f"✅ Finished: {data['run_id']} in {data['duration_seconds']}s")
    elif event_type == 'run_failed':
        print(f"❌ Failed: {data['run_id']} - {data['error']}")

# Run
stream_agent_events()
```

#### cURL (Testing)

```bash
# Stream events (Ctrl+C to stop)
curl -N http://localhost:8000/agents/events

# Example output:
# event: run_started
# data: {"run_id": "...", "agent_type": "warehouse_health", ...}
#
# event: run_finished
# data: {"run_id": "...", "status": "success", ...}
```

### Deployment Considerations

**Nginx Proxy Config**:
```nginx
location /agents/events {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_buffering off;  # CRITICAL: Disable buffering for SSE
    proxy_cache off;
    proxy_read_timeout 86400s;  # 24 hours
}
```

**Load Balancer**:
- Sticky sessions required (SSE is stateful per connection)
- Long timeout (SSE connections are long-lived)
- Health checks should not use `/agents/events` endpoint

**Scaling**:
- Each subscriber holds an open connection
- 1000 concurrent subscribers = 1000 open connections
- For high scale (>10k subscribers), consider Redis pub/sub or dedicated message broker

---

## Dashboards (Grafana)

### Agent Overview Dashboard

**Panels:**

#### 1. Agent Runs Rate (Time Series)
```promql
# Query
sum(rate(agent_runs_total[5m])) by (agent_type, status)

# Legend
{{agent_type}} - {{status}}

# Panel: Stacked area chart
```

#### 2. Success Rate (Gauge)
```promql
# Query
sum(rate(agent_runs_total{status="success"}[5m])) /
sum(rate(agent_runs_total[5m])) * 100

# Unit: percent (0-100)
# Thresholds: 
#   - Red: < 90%
#   - Yellow: 90-95%
#   - Green: > 95%
```

#### 3. Average Duration (Time Series)
```promql
# Query
rate(agent_run_duration_seconds_sum[5m]) /
rate(agent_run_duration_seconds_count[5m])
by (agent_type)

# Legend
{{agent_type}}

# Unit: seconds
```

#### 4. Duration Percentiles (Time Series)
```promql
# P50 (median)
histogram_quantile(0.5,
  sum(rate(agent_run_duration_seconds_bucket[5m])) by (le, agent_type)
)

# P95
histogram_quantile(0.95,
  sum(rate(agent_run_duration_seconds_bucket[5m])) by (le, agent_type)
)

# P99
histogram_quantile(0.99,
  sum(rate(agent_run_duration_seconds_bucket[5m])) by (le, agent_type)
)
```

#### 5. Recent Failed Runs (Table)
```sql
# Data Source: PostgreSQL
SELECT 
  run_id,
  agent_type,
  objective,
  error_message,
  started_at
FROM agent_audit_log
WHERE status = 'failed'
  AND started_at > NOW() - INTERVAL '1 hour'
ORDER BY started_at DESC
LIMIT 10;
```

#### 6. Top Agents by Runs (Bar Chart)
```promql
# Query
sum(increase(agent_runs_total[1h])) by (agent_type)

# Panel: Bar chart, horizontal
```

### Warehouse Health Dashboard

**Panels:**

#### 1. Parity Status (Stat)
```sql
# PostgreSQL query
SELECT 
  artifacts->'parity'->>'status' AS status,
  (artifacts->'parity'->>'difference_percent')::numeric AS diff_pct
FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
  AND status = 'success'
ORDER BY started_at DESC
LIMIT 1;

# Color: Green (ok), Red (degraded)
```

#### 2. Freshness Status (Stat)
```sql
# PostgreSQL query
SELECT 
  artifacts->'freshness'->>'within_slo' AS within_slo,
  (artifacts->'freshness'->>'age_minutes')::numeric AS age_minutes
FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
  AND status = 'success'
ORDER BY started_at DESC
LIMIT 1;

# Color: Green (true), Red (false)
```

#### 3. ES vs BQ Counts (Time Series)
```sql
# PostgreSQL query (with time grouping)
SELECT 
  DATE_TRUNC('hour', started_at) AS time,
  AVG((artifacts->'parity'->>'es_count')::int) AS es_count,
  AVG((artifacts->'parity'->>'bq_count')::int) AS bq_count
FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
  AND status = 'success'
  AND started_at > NOW() - INTERVAL '24 hours'
GROUP BY time
ORDER BY time;
```

#### 4. Remediation Triggers (Counter)
```sql
# PostgreSQL query
SELECT 
  COUNT(*) FILTER (WHERE artifacts->'remediation'->>'triggered' = 'true') AS triggered,
  COUNT(*) AS total
FROM agent_audit_log
WHERE agent_type = 'warehouse_health'
  AND started_at > NOW() - INTERVAL '24 hours';
```

---

## Alerting

### Alert Rules (Prometheus)

**File**: `prometheus/alerts/agents.yml`

```yaml
groups:
  - name: agents
    interval: 1m
    rules:
      # High failure rate
      - alert: HighAgentFailureRate
        expr: |
          sum(rate(agent_runs_total{status="failed"}[5m])) /
          sum(rate(agent_runs_total[5m])) > 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Agent failure rate above 10%"
          description: "{{ $value | humanizePercentage }} of agent runs failed in the last 5 minutes"
      
      # Critical failure rate
      - alert: CriticalAgentFailureRate
        expr: |
          sum(rate(agent_runs_total{status="failed"}[5m])) /
          sum(rate(agent_runs_total[5m])) > 0.5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Agent failure rate above 50%"
          description: "{{ $value | humanizePercentage }} of agent runs failed - immediate attention required"
      
      # Slow execution (p95)
      - alert: SlowAgentExecution
        expr: |
          histogram_quantile(0.95,
            sum(rate(agent_run_duration_seconds_bucket[5m])) by (le, agent_type)
          ) > 60
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Agent {{ $labels.agent_type }} p95 duration above 60s"
          description: "95th percentile execution time is {{ $value }}s"
      
      # No runs in last hour (agent stuck?)
      - alert: NoAgentRuns
        expr: |
          sum(increase(agent_runs_total[1h])) == 0
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "No agent runs in the last hour"
          description: "Agents may be stuck or scheduler stopped"
      
      # Warehouse health: parity degraded
      - alert: WarehouseParity Degraded
        expr: |
          # Custom metric (requires exporting from audit logs)
          warehouse_health_parity_status == 0
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Warehouse parity check failed"
          description: "ES/BQ counts diverged beyond 5% threshold"
      
      # Warehouse health: freshness SLO violated
      - alert: WarehouseFreshnessSLOViolated
        expr: |
          # Custom metric (requires exporting from audit logs)
          warehouse_health_freshness_within_slo == 0
        for: 30m
        labels:
          severity: critical
        annotations:
          summary: "Warehouse data stale beyond SLO"
          description: "Latest event age exceeds 30 minute threshold"
```

### Alert Routing (Alertmanager)

**File**: `alertmanager/config.yml`

```yaml
route:
  receiver: 'default'
  group_by: ['alertname', 'agent_type']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    # Critical alerts to PagerDuty
    - match:
        severity: critical
      receiver: pagerduty
      continue: true
    
    # Warnings to Slack
    - match:
        severity: warning
      receiver: slack

receivers:
  - name: 'default'
    webhook_configs:
      - url: 'http://localhost:9000/webhook'
  
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts-agents'
        title: 'Agent Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
```

---

## Debugging & Troubleshooting

### Debug Mode

**Enable Detailed Logging:**
```python
# In executor or agent
import logging
logging.basicConfig(level=logging.DEBUG)
```

**API Logs:**
```bash
# Follow logs
docker logs -f applylens-api

# Filter for agent runs
docker logs applylens-api 2>&1 | grep "agent_type"
```

### Common Issues

#### 1. Agent Execution Hangs

**Symptoms:**
- Run never completes
- No `run_finished` or `run_failed` event
- Audit log shows `status='running'` indefinitely

**Debug:**
```sql
-- Find hanging runs
SELECT * FROM agent_audit_log
WHERE status = 'running'
  AND started_at < NOW() - INTERVAL '1 hour';
```

**Fix:**
- Check provider timeouts (ES, BQ queries)
- Review application logs for exceptions
- Add timeout to executor (not yet implemented)
- Kill stuck processes and mark runs as failed

#### 2. Metrics Missing

**Symptoms:**
- Empty Grafana panels
- No data in Prometheus

**Debug:**
```bash
# Check metrics endpoint
curl http://localhost:8000/metrics | grep agent_

# Check Prometheus targets
curl http://prometheus:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job == "applylens-api")'
```

**Fix:**
- Verify Prometheus scrape config
- Check API health: `curl http://localhost:8000/health`
- Trigger agent run to generate metrics
- Review Prometheus logs for scrape errors

#### 3. SSE Connection Drops

**Symptoms:**
- `EventSource.onerror` triggered
- Missing events
- Frequent reconnects

**Debug:**
```bash
# Test SSE endpoint directly
curl -N http://localhost:8000/agents/events

# Check nginx/proxy logs
tail -f /var/log/nginx/error.log
```

**Fix:**
- Disable proxy buffering: `proxy_buffering off;`
- Set long timeout: `proxy_read_timeout 86400s;`
- Check CORS headers: `Access-Control-Allow-Origin: *`
- Review load balancer sticky sessions

#### 4. Audit Logs Not Saving

**Symptoms:**
- Empty `agent_audit_log` table
- Runs execute but no database records

**Debug:**
```sql
-- Check table exists
SELECT COUNT(*) FROM agent_audit_log;

-- Check recent migrations
SELECT * FROM alembic_version;

-- Test insert
INSERT INTO agent_audit_log (run_id, agent_type, status, started_at)
VALUES (gen_random_uuid(), 'test', 'success', NOW());
```

**Fix:**
- Run migrations: `alembic upgrade head`
- Check database connection in API logs
- Verify auditor is initialized in executor
- Review exception logs for `AgentAuditor` errors

---

## Performance Tuning

### Metrics Optimization

**Problem**: High cardinality labels slow down Prometheus

**Solution**: Limit label values
```python
# Bad: Unbounded cardinality (user_email could be thousands of values)
AGENT_RUNS_TOTAL.labels(agent_type=agent_type, status=status, user_email=user_email)

# Good: Bounded cardinality (omit user_email or use user_id with limited set)
AGENT_RUNS_TOTAL.labels(agent_type=agent_type, status=status)
```

### Audit Log Optimization

**Problem**: Large `artifacts` JSONB slows down queries

**Solution**: Index JSONB fields
```sql
-- Index specific JSON paths
CREATE INDEX idx_agent_audit_parity_status 
ON agent_audit_log ((artifacts->'parity'->>'status'));

CREATE INDEX idx_agent_audit_freshness_slo
ON agent_audit_log ((artifacts->'freshness'->>'within_slo'));
```

**Solution**: Partition by date
```sql
-- Monthly partitions for large tables
CREATE TABLE agent_audit_log_2025_10 PARTITION OF agent_audit_log
FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
```

### SSE Scaling

**Problem**: Too many concurrent SSE connections

**Solution**: Use Redis pub/sub
```python
# app/events/bus.py
import redis

class RedisEventBus:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379)
        self.pubsub = self.redis.pubsub()
    
    async def subscribe(self):
        self.pubsub.subscribe('agent_events')
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                event = AgentEvent.from_json(message['data'])
                yield event
    
    def publish(self, event: AgentEvent):
        self.redis.publish('agent_events', event.to_json())
```

---

## Summary

**You've learned**:
- ✅ Prometheus metrics for agent runs and duration
- ✅ SQL queries for audit log analysis
- ✅ SSE streaming for real-time updates
- ✅ Grafana dashboard configurations
- ✅ Alert rules and routing
- ✅ Debugging techniques for common issues
- ✅ Performance optimization strategies

**Next**: Check out [RUNBOOK_WAREHOUSE_HEALTH.md](./RUNBOOK_WAREHOUSE_HEALTH.md) for operational procedures.
