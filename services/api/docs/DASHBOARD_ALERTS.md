# Dashboard & Alerts Guide

This guide explains how to use the ApplyLens monitoring dashboards and alerting system to track agent performance in real-time.

## Table of Contents

- [Overview](#overview)
- [Dashboard Setup](#dashboard-setup)
- [Understanding the Dashboard](#understanding-the-dashboard)
- [Alert Configuration](#alert-configuration)
- [Alert Routing](#alert-routing)
- [Troubleshooting](#troubleshooting)
- [Custom Metrics](#custom-metrics)

## Overview

The ApplyLens monitoring stack provides real-time visibility into agent performance:

```
┌─────────────────────────────────────────────────────┐
│             Monitoring Architecture                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐                                  │
│  │   Agents     │                                  │
│  └──────┬───────┘                                  │
│         │ metrics                                  │
│  ┌──────▼───────────────┐                          │
│  │  Prometheus Exporter │  (app/eval/metrics.py)  │
│  └──────┬───────────────┘                          │
│         │ /metrics endpoint                        │
│  ┌──────▼───────────┐                              │
│  │   Prometheus     │  (scrapes metrics)           │
│  └──────┬───────────┘                              │
│         │                                           │
│         ├──────────────────┐                        │
│         │                  │                        │
│  ┌──────▼──────┐    ┌──────▼──────────┐            │
│  │   Grafana   │    │  Alertmanager   │            │
│  │ (visualize) │    │  (notify)       │            │
│  └─────────────┘    └──────┬──────────┘            │
│                            │                        │
│                     ┌──────▼──────┐                 │
│                     │ Slack/Email │                 │
│                     └─────────────┘                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Components

1. **Prometheus**: Metrics collection and storage
2. **Grafana**: Visualization and dashboards
3. **Alertmanager**: Alert routing and notification
4. **Metrics Exporter**: Exposes agent metrics for Prometheus

## Dashboard Setup

For detailed setup instructions, see [grafana/README.md](../grafana/README.md).

### Quick Setup (Docker Compose)

```yaml
# docker-compose.yml

version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./prometheus/agent_alerts.yml:/etc/prometheus/agent_alerts.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./grafana/agent_evaluation_dashboard.json:/etc/grafana/provisioning/dashboards/agent_eval.json
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=grafana-piechart-panel

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./prometheus/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'

volumes:
  prometheus-data:
  grafana-data:
```

Start services:
```bash
docker-compose up -d
```

### Prometheus Configuration

```yaml
# prometheus/prometheus.yml

global:
  scrape_interval: 30s
  evaluation_interval: 30s

# Alert rules
rule_files:
  - 'agent_alerts.yml'

# Scrape configs
scrape_configs:
  - job_name: 'agent-metrics'
    static_configs:
      - targets: ['api:8000']  # Your API service
    metrics_path: '/metrics'  # Default Prometheus endpoint
```

### Enable Metrics Endpoint

The metrics exporter runs automatically. To expose metrics:

```python
# In app/main.py (already configured)

from prometheus_client import make_asgi_app

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

Now Prometheus can scrape `http://your-api:8000/metrics`.

## Understanding the Dashboard

The dashboard has 13 panels across 6 rows.

### Row 1: Overview (4 Panels)

#### Panel 1: Overall Quality Status
- **Metric**: `avg(agent_quality_score)`
- **Type**: Stat (single value)
- **Thresholds**: 
  - Green: ≥ 90
  - Yellow: 85-90
  - Red: < 85
- **What It Means**: Average quality across all agents
- **Action If Red**: Check which agents are dragging down average

#### Panel 2: Success Rate
- **Metric**: `avg(agent_success_rate)`
- **Type**: Stat
- **Thresholds**:
  - Green: ≥ 95%
  - Yellow: 90-95%
  - Red: < 90%
- **What It Means**: % of agent executions without errors
- **Action If Red**: Check error logs for common failures

#### Panel 3: Budget Violations (24h)
- **Metric**: `sum(increase(agent_budget_violations_total[24h]))`
- **Type**: Stat
- **Thresholds**:
  - Green: 0
  - Yellow: 1-5
  - Red: > 5
- **What It Means**: Number of budget violations in last 24h
- **Action If Red**: Review violations, tighten agent controls

#### Panel 4: Invariant Pass Rate
- **Metric**: `avg(agent_invariant_pass_rate)`
- **Type**: Stat
- **Thresholds**:
  - Green: ≥ 95%
  - Yellow: 90-95%
  - Red: < 90%
- **What It Means**: % of invariant checks that pass
- **Action If Red**: Investigate failing invariants

### Row 2: Quality Trends (2 Panels)

#### Panel 5: Quality Score by Agent
- **Metric**: `agent_quality_score{agent="..."}`
- **Type**: Time series (line graph)
- **Time Range**: Last 7 days
- **What It Means**: Quality trends per agent over time
- **How to Read**:
  - **Upward trend**: Agent improving ✅
  - **Flat line**: Stable performance ➡️
  - **Downward trend**: Quality degrading ⚠️
  - **Sudden drop**: Investigate recent changes 🔍

#### Panel 6: Latency p95 by Agent
- **Metric**: `agent_latency_p95_ms{agent="..."}`
- **Type**: Time series
- **What It Means**: 95th percentile latency per agent
- **Action If High**:
  - Check for slow database queries
  - Look for API timeouts
  - Profile agent execution

### Row 3: Performance (2 Panels)

#### Panel 7: Success Rate by Agent
- **Metric**: `agent_success_rate{agent="..."}`
- **Type**: Time series
- **What It Means**: Success rate trends per agent
- **Action If Dropping**:
  - Check error logs
  - Look for new error types
  - Verify external dependencies (APIs, DB)

#### Panel 8: Red Team Detection Rate
- **Metric**: `agent_redteam_detection_rate{agent="..."}`
- **Type**: Time series
- **What It Means**: % of red team attacks blocked
- **Action If Low**:
  - Review failed detections
  - Add invariants for missed attacks
  - Update detection patterns

### Row 4: Violation Analysis (3 Panels)

#### Panel 9: Violations by Type
- **Metric**: `sum by (budget_type) (agent_budget_violations_total)`
- **Type**: Bar gauge (horizontal bars)
- **What It Means**: Which budget types are violated most
- **Common Types**:
  - `quality`: Below quality threshold
  - `latency`: Exceeds latency budget
  - `success_rate`: Too many failures
  - `invariants`: Invariant violations

#### Panel 10: Violations by Severity
- **Metric**: `sum by (severity) (agent_budget_violations_total)`
- **Type**: Pie chart
- **Severities**:
  - **Critical**: Must fix immediately
  - **Warning**: Should investigate
  - **Info**: FYI only
- **Action**: Focus on critical violations first

#### Panel 11: Top Failing Invariants
- **Metric**: `topk(10, sum by (invariant_id) (agent_invariants_failed_total))`
- **Type**: Table
- **Columns**: Invariant ID, Failure Count
- **What It Means**: Which invariants fail most often
- **Action**: Fix root causes or update invariant logic

### Row 5: System Metrics (2 Panels)

#### Panel 12: Agent Execution Rate
- **Metric**: `sum(rate(agent_total_runs_total[5m])) by (agent)`
- **Type**: Time series
- **What It Means**: Requests per second per agent
- **Action If Zero**: Agent not receiving traffic
- **Action If Spike**: Check for load issues

#### Panel 13: Cost Weight Trends
- **Metric**: `agent_cost_weight{agent="..."}`
- **Type**: Time series
- **What It Means**: Agent execution cost over time
- **Action If Increasing**: Optimize expensive operations

## Alert Configuration

The system includes 20+ pre-configured alerts across 6 categories.

### Alert Categories

#### 1. Quality Alerts (4 rules)

**AgentQualityScoreCritical**
```yaml
- alert: AgentQualityScoreCritical
  expr: agent_quality_score < 70
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Agent {{ $labels.agent }} quality critically low"
    description: "Quality score is {{ $value | humanize }}%, below 70% threshold"
```
- **Triggers**: Quality < 70% for 5+ minutes
- **Action**: Immediate investigation required

**AgentQualityScoreLow**
```yaml
expr: agent_quality_score < 85
for: 10m
```
- **Triggers**: Quality < 85% for 10+ minutes
- **Action**: Review recent changes

**AgentSuccessRateCritical** & **AgentSuccessRateLow**
- Similar to quality alerts, for success rate

#### 2. Performance Alerts (3 rules)

**AgentLatencyHigh**
```yaml
- alert: AgentLatencyHigh
  expr: agent_latency_p95_ms > 5000
  for: 5m
```
- **Triggers**: p95 latency > 5000ms
- **Action**: Profile and optimize

**AgentLatencyElevated**
```yaml
expr: agent_latency_p95_ms > 2000
for: 10m
```
- **Triggers**: p95 latency > 2000ms
- **Action**: Monitor, investigate if persists

**AgentLatencySpike**
```yaml
expr: |
  (agent_latency_p95_ms - agent_latency_p95_ms offset 10m)
  / agent_latency_p95_ms offset 10m > 0.5
for: 2m
```
- **Triggers**: Latency increases > 50% suddenly
- **Action**: Check for incidents (deployment, traffic spike)

#### 3. Budget Alerts (4 rules)

**AgentBudgetViolationCritical**
```yaml
expr: |
  sum by (agent) (
    increase(agent_budget_violations_total{severity="critical"}[10m])
  ) > 0
for: 2m
```
- **Triggers**: Any critical budget violation
- **Action**: Block deployment, investigate

**AgentBudgetViolationsMultiple**
```yaml
expr: |
  sum by (agent) (
    rate(agent_budget_violations_total[1h])
  ) >= 5
for: 10m
```
- **Triggers**: ≥ 5 violations/hour
- **Action**: Something is seriously wrong

#### 4. Invariant Alerts (3 rules)

**AgentInvariantFailures**
```yaml
expr: |
  sum by (agent, invariant_id) (
    increase(agent_invariants_failed_total[10m])
  ) > 0
for: 5m
```
- **Triggers**: Any invariant failures
- **Action**: Review violations

**AgentInvariantFailureRepeated**
```yaml
expr: |
  sum by (agent, invariant_id) (
    rate(agent_invariants_failed_total[1h])
  ) >= 3
```
- **Triggers**: ≥ 3 failures/hour for same invariant
- **Action**: Fix root cause immediately

#### 5. Red Team Alerts (3 rules)

**AgentRedTeamDetectionLow**
```yaml
expr: agent_redteam_detection_rate < 0.70
for: 15m
```
- **Triggers**: Detection rate < 70%
- **Action**: Strengthen defenses

**AgentRedTeamAttacksMissed**
```yaml
expr: |
  sum by (agent) (
    rate(agent_redteam_attacks_missed_total[1h])
  ) >= 3
```
- **Triggers**: ≥ 3 attacks missed/hour
- **Action**: Add invariants for missed patterns

#### 6. Availability Alerts (2 rules)

**AgentNotExecuting**
```yaml
expr: |
  rate(agent_total_runs_total[10m]) == 0
for: 10m
```
- **Triggers**: No executions for 10 minutes
- **Action**: Check if agent is down or no traffic

### Testing Alerts

Test if alerts fire correctly:

```bash
# Trigger quality alert (lower quality temporarily)
curl -X POST http://localhost:8000/api/test/set-quality \
  -d '{"agent": "inbox_triage", "quality": 65}'

# Wait 5 minutes, check Alertmanager
curl http://localhost:9093/api/v2/alerts

# Reset quality
curl -X POST http://localhost:8000/api/test/reset-quality
```

## Alert Routing

Configure where alerts are sent.

### Alertmanager Configuration

```yaml
# prometheus/alertmanager.yml

global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

# Route configuration
route:
  receiver: 'default'
  group_by: ['alertname', 'agent']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  
  routes:
    # Critical alerts -> Slack + PagerDuty
    - match:
        severity: critical
      receiver: 'critical-alerts'
      continue: false
    
    # Warning alerts -> Slack only
    - match:
        severity: warning
      receiver: 'warning-alerts'
      continue: false

# Receivers
receivers:
  - name: 'default'
    email_configs:
      - to: 'team@company.com'
  
  - name: 'critical-alerts'
    slack_configs:
      - channel: '#agent-alerts'
        title: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        send_resolved: true
    
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
  
  - name: 'warning-alerts'
    slack_configs:
      - channel: '#agent-warnings'
        title: '⚠️  WARNING: {{ .GroupLabels.alertname }}'
```

### Slack Integration

1. **Create Slack App**: https://api.slack.com/apps
2. **Enable Incoming Webhooks**
3. **Add webhook to workspace**
4. **Copy webhook URL** to alertmanager.yml

Test Slack alerts:
```bash
# Send test alert
curl -X POST http://localhost:9093/-/reload

# Check Slack channel
```

### PagerDuty Integration

1. **Create PagerDuty Service**
2. **Get Integration Key**
3. **Add to alertmanager.yml**:

```yaml
pagerduty_configs:
  - service_key: 'YOUR_INTEGRATION_KEY'
    description: '{{ .GroupLabels.alertname }}: {{ .GroupLabels.agent }}'
    severity: '{{ .CommonLabels.severity }}'
```

### Email Integration

```yaml
receivers:
  - name: 'email-team'
    email_configs:
      - to: 'team@company.com'
        from: 'alerts@company.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@company.com'
        auth_password: 'YOUR_APP_PASSWORD'
        headers:
          Subject: '[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}'
        html: |
          <h2>Alert: {{ .GroupLabels.alertname }}</h2>
          <p><strong>Agent:</strong> {{ .GroupLabels.agent }}</p>
          <p><strong>Severity:</strong> {{ .CommonLabels.severity }}</p>
          {{ range .Alerts }}
          <p>{{ .Annotations.description }}</p>
          {{ end }}
```

### Alert Silencing

Temporarily silence alerts during maintenance:

```bash
# Silence specific alert
curl -X POST http://localhost:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {"name": "alertname", "value": "AgentLatencyHigh", "isRegex": false},
      {"name": "agent", "value": "inbox_triage", "isRegex": false}
    ],
    "startsAt": "2025-10-17T10:00:00Z",
    "endsAt": "2025-10-17T12:00:00Z",
    "comment": "Planned maintenance - optimizing database",
    "createdBy": "john@company.com"
  }'
```

## Troubleshooting

### Dashboard Shows No Data

**Problem**: Panels display "No data"

**Diagnosis**:
```bash
# 1. Check if Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# 2. Check if metrics endpoint is working
curl http://localhost:8000/metrics | grep agent_quality_score

# 3. Query Prometheus directly
curl 'http://localhost:9090/api/v1/query?query=agent_quality_score'
```

**Solutions**:
- Verify Prometheus scrape config points to correct target
- Check if metrics exporter is running (`/metrics` endpoint accessible)
- Ensure firewall allows Prometheus → API traffic
- Check Prometheus logs: `docker logs prometheus`

### Alerts Not Firing

**Problem**: Expected alerts don't trigger

**Diagnosis**:
```bash
# Check if alert rules are loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.type=="alerting")'

# Check current alerts
curl http://localhost:9090/api/v1/alerts

# Check Alertmanager status
curl http://localhost:9093/api/v2/alerts
```

**Solutions**:
- Verify alert rule syntax (YAML indentation!)
- Check `for` duration - alert may need more time
- Ensure Prometheus can reach Alertmanager
- Check Alertmanager logs: `docker logs alertmanager`

### Slack Notifications Not Received

**Problem**: Alerts fire but Slack not notified

**Diagnosis**:
```bash
# Test webhook directly
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -H 'Content-Type: application/json' \
  -d '{"text": "Test message"}'

# Check Alertmanager logs
docker logs alertmanager | grep slack
```

**Solutions**:
- Verify webhook URL is correct
- Check Slack app permissions
- Ensure Alertmanager can reach Slack (check proxy/firewall)
- Test with simple receiver first, then add complexity

### High Cardinality Issues

**Problem**: Prometheus slow, high memory usage

**Diagnosis**:
```bash
# Check cardinality
curl http://localhost:9090/api/v1/status/tsdb | jq '.data.seriesCountByMetricName'
```

**Solutions**:
- Reduce label cardinality (avoid user IDs, email addresses in labels)
- Increase Prometheus retention if needed
- Use recording rules for expensive queries
- Consider Thanos/Cortex for long-term storage

## Custom Metrics

Add your own metrics to track custom agent behaviors.

### Define Custom Metric

```python
# In app/eval/metrics.py

from prometheus_client import Counter, Histogram

# Custom counter
agent_custom_events = Counter(
    'agent_custom_events_total',
    'Custom business events',
    ['agent', 'event_type']
)

# Custom histogram
agent_processing_time = Histogram(
    'agent_processing_time_seconds',
    'Time spent in different processing stages',
    ['agent', 'stage'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)
```

### Export Custom Metrics

```python
# In your agent code
def process_email(email):
    with agent_processing_time.labels(agent='inbox_triage', stage='parsing').time():
        parsed = parse_email(email)
    
    with agent_processing_time.labels(agent='inbox_triage', stage='classification').time():
        labels = classify(parsed)
    
    # Increment custom counter
    agent_custom_events.labels(
        agent='inbox_triage',
        event_type='email_classified'
    ).inc()
    
    return labels
```

### Create Dashboard Panel

Add to Grafana dashboard JSON:

```json
{
  "id": 14,
  "title": "Custom Event Rate",
  "type": "timeseries",
  "targets": [
    {
      "expr": "sum(rate(agent_custom_events_total[5m])) by (event_type)",
      "legendFormat": "{{ event_type }}"
    }
  ]
}
```

## Best Practices

### 1. Set Meaningful Thresholds

Base alert thresholds on:
- Historical baselines (p95, p99)
- SLA requirements
- User experience impact
- Business criticality

### 2. Avoid Alert Fatigue

- **Don't alert on everything**: Only actionable issues
- **Use appropriate severity**: Reserve `critical` for real emergencies
- **Group related alerts**: Use `group_by` in Alertmanager
- **Set sensible `for` durations**: Avoid flapping alerts

### 3. Document Alert Runbooks

For each alert, document:
- What it means
- How to diagnose
- How to fix
- Who to contact

Example:
```yaml
annotations:
  summary: "Agent quality critically low"
  description: "Quality is {{ $value }}%, below 70%"
  runbook_url: "https://wiki.company.com/runbooks/agent-quality-low"
```

### 4. Test Alerts Regularly

Schedule monthly alert tests:
```bash
# Trigger each alert type
# Verify notifications received
# Update escalation paths if needed
```

### 5. Monitor the Monitors

Set up alerts for monitoring infrastructure:
- Prometheus down
- Grafana unreachable
- Alertmanager not sending notifications

## Next Steps

- See [grafana/README.md](../grafana/README.md) for detailed setup
- See [BUDGETS_AND_GATES.md](./BUDGETS_AND_GATES.md) for quality gates
- See [INTELLIGENCE_REPORT.md](./INTELLIGENCE_REPORT.md) for weekly reports
- See [EVAL_GUIDE.md](./EVAL_GUIDE.md) for evaluation system overview
