# Agent Evaluation Dashboard Setup

This directory contains Grafana dashboard configurations and Prometheus alert rules for monitoring the ApplyLens agent evaluation system.

## 📊 Contents

- **`agent_evaluation_dashboard.json`** - Grafana dashboard JSON (import this)
- **`../prometheus/agent_alerts.yml`** - Prometheus alert rules

## 🚀 Quick Start

### 1. Import Grafana Dashboard

**Option A: Via UI**
1. Open Grafana (e.g., `http://localhost:3000`)
2. Navigate to **Dashboards** → **Import**
3. Upload `agent_evaluation_dashboard.json`
4. Select your Prometheus data source
5. Click **Import**

**Option B: Via API**
```bash
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d @agent_evaluation_dashboard.json
```

**Option C: Provisioning** (recommended for production)
```yaml
# grafana/provisioning/dashboards/dashboards.yml
apiVersion: 1
providers:
  - name: 'ApplyLens'
    folder: 'Agent Evaluation'
    type: file
    options:
      path: /etc/grafana/dashboards/applylens
```

Then copy `agent_evaluation_dashboard.json` to `/etc/grafana/dashboards/applylens/`.

### 2. Configure Prometheus

Add alert rules to your Prometheus configuration:

```yaml
# prometheus.yml
rule_files:
  - 'agent_alerts.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'localhost:9093'  # Alertmanager
```

Reload Prometheus:
```bash
curl -X POST http://localhost:9090/-/reload
```

### 3. Configure Alertmanager

Create Alertmanager configuration for routing alerts:

```yaml
# alertmanager.yml
global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

route:
  receiver: 'team-slack'
  group_by: ['alertname', 'agent']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  
  routes:
    # Critical alerts go to PagerDuty
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true
    
    # All alerts also go to Slack
    - receiver: 'team-slack'

receivers:
  - name: 'team-slack'
    slack_configs:
      - channel: '#agent-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

### 4. Enable Metrics Export

The API automatically exposes metrics at `/metrics` (scraped by Prometheus).

To manually trigger export:
```bash
curl -X POST http://localhost:8000/metrics/export?lookback_days=7
```

Configure Prometheus to scrape:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'applylens-api'
    scrape_interval: 30s
    static_configs:
      - targets: ['localhost:8000']
```

## 📈 Dashboard Panels

The dashboard includes 13 panels:

### Overview (Row 1)
1. **Overall Quality Status** - Average quality score across all agents
2. **Success Rate** - Average success rate
3. **Budget Violations (24h)** - Total violations in last day
4. **Invariant Pass Rate** - Percentage of invariant checks passing

### Time Series (Rows 2-4)
5. **Quality Score by Agent** - Quality trends over time
6. **Latency p95 by Agent** - 95th percentile latency
7. **Success Rate by Agent** - Success rate trends
8. **Red Team Detection Rate** - Attack detection percentage

### Violation Analysis (Row 5)
9. **Budget Violations by Type** - Bar chart of violation types
10. **Budget Violations by Severity** - Pie chart (critical/error/warning)
11. **Invariant Failures by ID** - Table of top failing invariants

### System Metrics (Row 6)
12. **Agent Execution Rate** - Requests per second
13. **Cost Weight Trend** - Cost metrics over time

## 🚨 Alert Rules

The system includes 20+ alert rules across 6 categories:

### Quality Alerts
- **AgentQualityScoreCritical** - Quality < 70% (fires in 5min)
- **AgentQualityScoreLow** - Quality < 85% (fires in 10min)
- **AgentSuccessRateCritical** - Success < 80% (fires in 5min)
- **AgentSuccessRateLow** - Success < 95% (fires in 10min)

### Performance Alerts
- **AgentLatencyHigh** - p95 > 5000ms (fires in 5min)
- **AgentLatencyElevated** - p95 > 2000ms or avg > 1000ms (fires in 10min)
- **AgentLatencySpike** - >50% increase in 15min (fires in 2min)

### Budget Alerts
- **AgentBudgetViolationCritical** - Critical violations detected
- **AgentBudgetViolationsMultiple** - ≥5 violations in 1 hour
- **AgentQualityRegression** - Quality regressed vs baseline
- **AgentLatencyRegression** - Latency increased vs baseline

### Invariant Alerts
- **AgentInvariantFailures** - Any invariant failures (fires in 2min)
- **AgentInvariantFailureRepeated** - ≥3 failures of same invariant
- **AgentInvariantPassRateLow** - Pass rate < 95%

### Red Team Alerts
- **AgentRedTeamDetectionLow** - Detection < 70% (fires in 15min)
- **AgentRedTeamAttacksMissed** - ≥3 attacks missed in 1 hour
- **AgentRedTeamFalsePositivesHigh** - FP rate > 30%

### Availability Alerts
- **AgentNotExecuting** - No executions in 10min
- **AgentExecutionRateLow** - Execution rate < 0.1 req/s
- **EvaluationMetricsStale** - No metric updates in 5min

## 🔧 Customization

### Adjust Thresholds

Edit alert rules in `../prometheus/agent_alerts.yml`:

```yaml
- alert: AgentQualityScoreCritical
  expr: agent_quality_score < 70  # Change this threshold
  for: 5m  # Change detection time
```

### Add Custom Panels

1. Edit dashboard in Grafana UI
2. Export JSON via **Share** → **Export**
3. Save to `agent_evaluation_dashboard.json`
4. Commit changes

### Configure Alert Routing

Edit `alertmanager.yml` to route specific alerts:

```yaml
routes:
  # Route inbox.triage alerts to different channel
  - match:
      agent: 'inbox.triage'
    receiver: 'inbox-team-slack'
```

## 📊 Metrics Reference

### Gauges (Current State)
- `agent_quality_score{agent}` - Quality score (0-100)
- `agent_success_rate{agent}` - Success rate (0.0-1.0)
- `agent_latency_p50_ms{agent}` - p50 latency
- `agent_latency_p95_ms{agent}` - p95 latency
- `agent_latency_p99_ms{agent}` - p99 latency
- `agent_latency_avg_ms{agent}` - Average latency
- `agent_cost_weight{agent}` - Cost metric
- `agent_invariant_pass_rate{agent}` - Invariant pass rate
- `agent_redteam_detection_rate{agent}` - Detection rate

### Counters (Cumulative)
- `agent_total_runs_total{agent}` - Total executions
- `agent_successful_runs_total{agent}` - Successful executions
- `agent_failed_runs_total{agent}` - Failed executions
- `agent_budget_violations_total{agent,budget_type,severity}` - Violations
- `agent_invariants_passed_total{agent}` - Invariant passes
- `agent_invariants_failed_total{agent,invariant_id}` - Invariant failures
- `agent_redteam_attacks_detected_total{agent}` - Attacks detected
- `agent_redteam_attacks_missed_total{agent}` - Attacks missed
- `agent_redteam_false_positives_total{agent}` - False positives

### Histograms
- `agent_latency_ms{agent}` - Latency distribution

## 🔗 Integration

### Slack Notifications

Configure in `alertmanager.yml`:
```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#agent-alerts'
        title: '🚨 {{ .GroupLabels.alertname }}'
        text: |
          *Agent:* {{ .Labels.agent }}
          *Severity:* {{ .Labels.severity }}
          *Description:* {{ .Annotations.description }}
```

### PagerDuty Integration

```yaml
receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_SERVICE_KEY'
        description: '{{ .GroupLabels.alertname }}: {{ .Annotations.summary }}'
```

### Email Notifications

```yaml
receivers:
  - name: 'email'
    email_configs:
      - to: 'team@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alertmanager@example.com'
        auth_password: 'YOUR_PASSWORD'
```

## 🐛 Troubleshooting

### No Data in Dashboard

1. **Check Prometheus is scraping**:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

2. **Verify metrics are being exported**:
   ```bash
   curl http://localhost:8000/metrics | grep agent_
   ```

3. **Trigger manual export**:
   ```bash
   curl -X POST http://localhost:8000/metrics/export
   ```

### Alerts Not Firing

1. **Check alert rules are loaded**:
   ```bash
   curl http://localhost:9090/api/v1/rules
   ```

2. **Verify Alertmanager connection**:
   ```bash
   curl http://localhost:9090/api/v1/alertmanagers
   ```

3. **Check alert status**:
   ```bash
   curl http://localhost:9090/api/v1/alerts
   ```

### Dashboard Not Loading

1. **Validate JSON**:
   ```bash
   cat agent_evaluation_dashboard.json | jq .
   ```

2. **Check Grafana logs**:
   ```bash
   docker logs grafana
   ```

3. **Verify data source**:
   - Grafana UI → Configuration → Data Sources
   - Test connection to Prometheus

## 📚 Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [PromQL Queries](https://prometheus.io/docs/prometheus/latest/querying/basics/)

## 🆘 Support

For issues or questions:
- Create an issue in the repository
- Check existing documentation
- Review Prometheus/Grafana logs
