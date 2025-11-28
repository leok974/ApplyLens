# Metrics & Dashboards

## Overview

ApplyLens uses **Prometheus** for metrics collection and **Grafana** for visualization. This document covers the key metrics, dashboards, alerts, and how to use them for monitoring and debugging.

## Prometheus Setup

### Service Configuration

**Location**: `infra/prometheus/prometheus.yml`

**Scrape targets**:
```yaml
scrape_configs:
  - job_name: 'applylens-api'
    static_configs:
      - targets: ['applylens-api-prod:8000']
    scrape_interval: 15s

  - job_name: 'applylens-web'
    static_configs:
      - targets: ['applylens-web-prod:80']
    scrape_interval: 30s

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

**Access Prometheus**:
- Local: `http://localhost:9090`
- Production: `http://applylens-prometheus:9090` (internal Docker network)

### Metrics Endpoint

**API metrics**: `http://localhost:8003/metrics`

**Format**: OpenMetrics (Prometheus compatible)

**Example output**:
```
# HELP autofill_policy_total Total autofill requests by policy
# TYPE autofill_policy_total counter
autofill_policy_total{policy="exploit",segment="greenhouse|engineering|senior"} 142
autofill_policy_total{policy="explore",segment="greenhouse|engineering|senior"} 28
autofill_policy_total{policy="fallback",segment="greenhouse|engineering|senior"} 3

# HELP helpful_ratio_gauge Current helpful ratio by segment
# TYPE helpful_ratio_gauge gauge
helpful_ratio_gauge{segment="greenhouse|engineering|senior"} 0.87
helpful_ratio_gauge{segment="lever|marketing|mid"} 0.76
```

## Key Metrics

### 1. Autofill Policy Metrics

**Metric**: `autofill_policy_total`

**Type**: Counter

**Labels**:
- `policy`: `exploit`, `explore`, `fallback`
- `segment`: `{ats_family}|{role_category}|{seniority}`
- `style_id`: Generation style used (e.g., `concise_bullets_v2`)

**Purpose**: Track which bandit policy is being used for autofill requests

**PromQL queries**:

```promql
# Total autofill requests in last hour
sum(rate(autofill_policy_total[1h])) * 3600

# Breakdown by policy
sum by (policy) (rate(autofill_policy_total[1h]))

# Explore rate by segment
sum by (segment) (rate(autofill_policy_total{policy="explore"}[1h]))
/
sum by (segment) (rate(autofill_policy_total[1h]))

# Fallback spike detection
rate(autofill_policy_total{policy="fallback"}[5m]) > 0.1
```

**What to look for**:
- ✅ **Exploit ~70%**: Most requests should use best-known style
- ✅ **Explore ~20%**: Healthy exploration of new styles
- ⚠️ **Fallback <10%**: Fallback should be rare
- 🚨 **Fallback spike**: Indicates bandit degradation or kill switch triggered

### 2. Helpful Ratio Gauge

**Metric**: `helpful_ratio_gauge`

**Type**: Gauge

**Labels**:
- `segment`: `{ats_family}|{role_category}|{seniority}`

**Purpose**: Track quality of autofill suggestions by segment

**Calculation**:
```python
helpful_ratio = accepted_autofills / total_autofills
```

**PromQL queries**:

```promql
# Current helpful ratio by segment
helpful_ratio_gauge

# Average helpful ratio across all segments
avg(helpful_ratio_gauge)

# Segments with low helpful ratio (<0.6)
helpful_ratio_gauge < 0.6

# Helpful ratio trend over time
avg_over_time(helpful_ratio_gauge{segment="greenhouse|engineering|senior"}[1h])
```

**What to look for**:
- ✅ **>0.7**: Good quality, users accepting most suggestions
- ⚠️ **0.5-0.7**: Moderate quality, room for improvement
- 🚨 **<0.5**: Poor quality, investigate style or segment issues

### 3. Extension API Metrics

**Metric**: `applylens_http_requests_total`

**Type**: Counter

**Labels**:
- `path`: API endpoint (e.g., `/api/extension/generate-form-answers`)
- `method`: HTTP method (GET, POST)
- `status`: HTTP status code (200, 401, 500)

**Purpose**: Track extension API usage and errors

**PromQL queries**:

```promql
# Extension API request rate
sum(rate(applylens_http_requests_total{path=~"/api/extension/.*"}[5m]))

# Error rate (5xx responses)
sum(rate(applylens_http_requests_total{status=~"5.."}[5m]))

# 502 errors specifically
sum(rate(applylens_http_requests_total{status="502"}[5m]))

# Success rate by endpoint
sum by (path) (rate(applylens_http_requests_total{status="200"}[5m]))
/
sum by (path) (rate(applylens_http_requests_total[5m]))
```

**What to look for**:
- ✅ **Success rate >95%**: Healthy API
- ⚠️ **Success rate 90-95%**: Minor issues, investigate
- 🚨 **502 errors**: Backend connectivity issues (check nginx config)

### 4. Learning Events Metrics

**Metric**: `learning_events_total`

**Type**: Counter

**Labels**:
- `event_type`: `autofill_accepted`, `autofill_edited`, `autofill_rejected`
- `segment`: `{ats_family}|{role_category}|{seniority}`

**Purpose**: Track user learning events (edits to autofill suggestions)

**PromQL queries**:

```promql
# Learning events per hour
sum(rate(learning_events_total[1h])) * 3600

# Edit rate by segment
sum by (segment) (rate(learning_events_total{event_type="autofill_edited"}[1h]))
/
sum by (segment) (rate(learning_events_total[1h]))

# Rejection rate (high = poor quality)
sum(rate(learning_events_total{event_type="autofill_rejected"}[1h]))
/
sum(rate(learning_events_total[1h]))
```

**What to look for**:
- ✅ **Low edit rate**: Users accepting suggestions as-is
- ⚠️ **High edit rate**: Suggestions need improvement
- 🚨 **High rejection rate**: Major quality issues

### 5. Backend Performance Metrics

**Metric**: `applylens_http_request_duration_seconds`

**Type**: Histogram

**Labels**:
- `path`: API endpoint
- `method`: HTTP method

**Purpose**: Track API response times

**PromQL queries**:

```promql
# P95 latency by endpoint
histogram_quantile(0.95, sum by (path, le) (
  rate(applylens_http_request_duration_seconds_bucket[5m])
))

# P99 latency for autofill endpoint
histogram_quantile(0.99, sum by (le) (
  rate(applylens_http_request_duration_seconds_bucket{path="/api/extension/generate-form-answers"}[5m])
))

# Slow requests (>2s)
sum(rate(applylens_http_request_duration_seconds_bucket{le="2.0"}[5m]))
```

**What to look for**:
- ✅ **P95 <1s**: Fast responses
- ⚠️ **P95 1-3s**: Acceptable but monitor
- 🚨 **P95 >3s**: Performance degradation

## Grafana Dashboards

### Access Grafana

- **Local**: `http://localhost:3001`
- **Production**: `http://grafana.applylens.internal:3001` (VPN required)
- **Default credentials**: admin / admin (change on first login)

### Dashboard: ApplyLens - Companion Bandit (Phase 6)

**Location**: Grafana → Dashboards → ApplyLens - Companion Bandit (Phase 6)

**UID**: `companion-bandit-phase6`

**Panels**:

#### 1. Autofill Policy Distribution
- **Visualization**: Pie chart
- **Query**:
  ```promql
  sum by (policy) (rate(autofill_policy_total[1h]))
  ```
- **Purpose**: Show exploit/explore/fallback split
- **Expected**: ~70% exploit, ~20% explore, ~10% fallback

#### 2. Helpful Ratio by Segment
- **Visualization**: Time series
- **Query**:
  ```promql
  helpful_ratio_gauge
  ```
- **Purpose**: Track quality trends over time
- **Expected**: Gradual increase as bandit learns

#### 3. Autofill Request Rate
- **Visualization**: Graph
- **Query**:
  ```promql
  sum(rate(autofill_policy_total[5m])) * 60
  ```
- **Purpose**: Monitor usage volume
- **Unit**: Requests per minute

#### 4. Explore Rate by Segment
- **Visualization**: Heatmap
- **Query**:
  ```promql
  sum by (segment) (rate(autofill_policy_total{policy="explore"}[1h]))
  /
  sum by (segment) (rate(autofill_policy_total[1h]))
  ```
- **Purpose**: Ensure exploration is distributed across segments
- **Expected**: ~20% for all segments

#### 5. Fallback Events
- **Visualization**: Single stat + sparkline
- **Query**:
  ```promql
  sum(rate(autofill_policy_total{policy="fallback"}[5m])) * 300
  ```
- **Purpose**: Detect fallback spikes
- **Alert threshold**: >10 events in 5 minutes

#### 6. Learning Events Volume
- **Visualization**: Bar gauge
- **Query**:
  ```promql
  sum by (event_type) (rate(learning_events_total[1h])) * 3600
  ```
- **Purpose**: Track user interaction with autofill
- **Breakdown**: Accepted / Edited / Rejected

#### 7. API Error Rate
- **Visualization**: Time series
- **Query**:
  ```promql
  sum(rate(applylens_http_requests_total{status=~"5.."}[5m]))
  /
  sum(rate(applylens_http_requests_total[5m]))
  ```
- **Purpose**: Monitor extension API health
- **Alert threshold**: >5% error rate

### Dashboard: ApplyLens - System Health

**Panels**:

#### 1. CPU Usage
- **Query**: `rate(process_cpu_seconds_total[1m])`
- **Alert**: >80% for 5 minutes

#### 2. Memory Usage
- **Query**: `process_resident_memory_bytes / 1024 / 1024 / 1024`
- **Unit**: GB
- **Alert**: >4GB (API container has 6GB limit)

#### 3. Database Connections
- **Query**: `pg_stat_activity_count`
- **Alert**: >80 connections (pool size is 100)

#### 4. Elasticsearch Health
- **Query**: `elasticsearch_cluster_health_status`
- **Values**: 0 (red), 1 (yellow), 2 (green)
- **Alert**: <2 (not green)

#### 5. Redis Memory Usage
- **Query**: `redis_memory_used_bytes / 1024 / 1024`
- **Unit**: MB
- **Alert**: >500MB (eviction threshold)

## Alerts

### Alertmanager Configuration

**Location**: `infra/prometheus/alertmanager.yml`

**Notification channels**:
- Email: `alerts@applylens.app`
- Slack: `#applylens-alerts` (if configured)

### Alert Rules

**Location**: `infra/prometheus/rules/applylens.yml`

#### 1. High Fallback Rate

```yaml
- alert: HighFallbackRate
  expr: |
    sum(rate(autofill_policy_total{policy="fallback"}[5m]))
    /
    sum(rate(autofill_policy_total[5m]))
    > 0.2
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Bandit fallback rate above 20%"
    description: "{{ $value | humanizePercentage }} of autofill requests falling back (expected <10%)"
```

**What it means**: Bandit is degraded or kill switch is active

**Action**:
1. Check if bandit kill switch is enabled (backend or extension)
2. Review recent deployments or config changes
3. Check Prometheus targets are healthy
4. Verify segment data is available

#### 2. Explore Rate Too High

```yaml
- alert: ExploreRateTooHigh
  expr: |
    sum(rate(autofill_policy_total{policy="explore"}[1h]))
    /
    sum(rate(autofill_policy_total[1h]))
    > 0.3
  for: 30m
  labels:
    severity: info
  annotations:
    summary: "Bandit explore rate above 30%"
    description: "{{ $value | humanizePercentage }} of requests exploring (expected ~20%)"
```

**What it means**: Bandit is over-exploring (may indicate segment issues)

**Action**:
1. Check if segments have enough data for exploitation
2. Review epsilon value in bandit config
3. Verify helpful_ratio is being calculated correctly

#### 3. API Error Rate High

```yaml
- alert: APIErrorRateHigh
  expr: |
    sum(rate(applylens_http_requests_total{status=~"5.."}[5m]))
    /
    sum(rate(applylens_http_requests_total[5m]))
    > 0.05
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "API error rate above 5%"
    description: "{{ $value | humanizePercentage }} of API requests failing"
```

**What it means**: Backend or infrastructure issues

**Action**:
1. Check Docker container health: `docker ps`
2. Check API logs: `docker logs applylens-api-prod --tail 100`
3. Verify database connectivity
4. Check nginx proxy configuration

#### 4. No Autofill Requests

```yaml
- alert: NoAutofillRequests
  expr: |
    sum(rate(autofill_policy_total[30m])) == 0
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "No autofill requests in last hour"
    description: "Extension may not be working or users are inactive"
```

**What it means**: Extension is down or no users are active

**Action**:
1. Verify extension is published and accessible
2. Check extension API endpoints are reachable
3. Review user activity logs
4. Check if it's expected downtime (e.g., late night)

#### 5. Low Helpful Ratio

```yaml
- alert: LowHelpfulRatio
  expr: helpful_ratio_gauge < 0.5
  for: 2h
  labels:
    severity: warning
  annotations:
    summary: "Helpful ratio below 0.5 for {{ $labels.segment }}"
    description: "{{ $value | humanizePercentage }} acceptance rate (expected >70%)"
```

**What it means**: Autofill quality is poor for a segment

**Action**:
1. Review generation styles for this segment
2. Check if ATS detection is working correctly
3. Analyze user edit patterns to understand issues
4. Consider disabling bandit for this segment temporarily

## Querying Metrics

### Using Prometheus UI

1. Navigate to `http://localhost:9090`
2. Click **Graph** tab
3. Enter PromQL query in expression field
4. Click **Execute**
5. Switch between **Graph** and **Table** views

**Example queries**:

```promql
# Current autofill rate (requests per minute)
sum(rate(autofill_policy_total[5m])) * 60

# Autofill requests in last 24 hours
sum(increase(autofill_policy_total[24h]))

# Top 5 segments by volume
topk(5, sum by (segment) (rate(autofill_policy_total[1h])))

# Helpful ratio change (last hour vs previous hour)
avg(helpful_ratio_gauge) - avg(helpful_ratio_gauge offset 1h)
```

### Using Grafana Explore

1. Navigate to Grafana → Explore
2. Select **Prometheus** datasource
3. Enter PromQL query
4. Adjust time range in top right
5. Click **Run query**

**Advantages over Prometheus UI**:
- Better visualization options
- Multiple queries on same graph
- Export to dashboard panels
- Share links to specific queries

### Using cURL

```bash
# Query current metric values
curl 'http://localhost:9090/api/v1/query?query=autofill_policy_total'

# Query metric range
curl 'http://localhost:9090/api/v1/query_range?query=sum(rate(autofill_policy_total[5m]))&start=2025-11-17T00:00:00Z&end=2025-11-17T23:59:59Z&step=300s'

# Query labels
curl 'http://localhost:9090/api/v1/label/segment/values'
```

## Debugging with Metrics

### Scenario 1: Users Report Autofill Not Working

**Check**:
1. Autofill request rate:
   ```promql
   sum(rate(autofill_policy_total[5m]))
   ```
   If zero → Extension not sending requests

2. API error rate:
   ```promql
   sum(rate(applylens_http_requests_total{path="/api/extension/generate-form-answers",status=~"5.."}[5m]))
   ```
   If high → Backend issue

3. Fallback rate:
   ```promql
   sum(rate(autofill_policy_total{policy="fallback"}[5m]))
   /
   sum(rate(autofill_policy_total[5m]))
   ```
   If 100% → Bandit disabled or degraded

### Scenario 2: Poor Autofill Quality

**Check**:
1. Helpful ratio by segment:
   ```promql
   helpful_ratio_gauge
   ```
   Identify which segments have low ratios

2. Edit rate:
   ```promql
   sum by (segment) (rate(learning_events_total{event_type="autofill_edited"}[1h]))
   ```
   High edit rate = suggestions need improvement

3. Policy distribution:
   ```promql
   sum by (policy) (rate(autofill_policy_total[1h]))
   ```
   If mostly fallback → Bandit not learning properly

### Scenario 3: Slow Autofill Responses

**Check**:
1. P95 latency:
   ```promql
   histogram_quantile(0.95, sum by (le) (
     rate(applylens_http_request_duration_seconds_bucket{path="/api/extension/generate-form-answers"}[5m])
   ))
   ```

2. Database query time (if instrumented):
   ```promql
   avg(rate(db_query_duration_seconds_sum[5m]))
   /
   avg(rate(db_query_duration_seconds_count[5m]))
   ```

3. OpenAI API latency (if instrumented):
   ```promql
   histogram_quantile(0.95, sum by (le) (
     rate(openai_api_duration_seconds_bucket[5m])
   ))
   ```

### Scenario 4: Bandit Kill Switch Verification

**Check if kill switch is active**:

1. Backend environment variable:
   ```bash
   docker exec applylens-api-prod env | grep COMPANION_BANDIT_ENABLED
   ```

2. Fallback rate (should be 100% if disabled):
   ```promql
   sum(rate(autofill_policy_total{policy="fallback"}[5m]))
   /
   sum(rate(autofill_policy_total[5m]))
   ```

3. Extension flag (check browser console):
   ```javascript
   window.__APPLYLENS_BANDIT_ENABLED
   ```

## Metric Retention

### Prometheus

**Default retention**: 15 days

**Configuration**: `infra/prometheus/prometheus.yml`
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

storage:
  tsdb:
    retention_time: 15d
    retention_size: 10GB
```

**Change retention**:
```bash
# Edit docker-compose.yml
services:
  prometheus:
    command:
      - '--storage.tsdb.retention.time=30d'
      - '--storage.tsdb.retention.size=20GB'
```

### Grafana

**Dashboard snapshots**: Persist indefinitely

**Query history**: 30 days

**Annotations**: Persist indefinitely

## Exporting Metrics

### CSV Export from Grafana

1. Open dashboard panel
2. Click panel title → Inspect → Data
3. Click **Download CSV**

### JSON Export via API

```bash
# Export metric data as JSON
curl -G 'http://localhost:9090/api/v1/query_range' \
  --data-urlencode 'query=autofill_policy_total' \
  --data-urlencode 'start=2025-11-17T00:00:00Z' \
  --data-urlencode 'end=2025-11-17T23:59:59Z' \
  --data-urlencode 'step=300s' \
  | jq . > metrics_export.json
```

### Snapshot Dashboard

1. Click **Share** icon in dashboard
2. Click **Snapshot** tab
3. Set expiration (or never)
4. Click **Publish to snapshot.raintank.io**
5. Share generated URL

## Best Practices

### 1. Use Rate for Counters
```promql
# ✅ Good - rate over time window
sum(rate(autofill_policy_total[5m]))

# ❌ Bad - raw counter value
sum(autofill_policy_total)
```

### 2. Choose Appropriate Time Windows
```promql
# Short window (5m) for real-time monitoring
rate(metric[5m])

# Medium window (1h) for trends
rate(metric[1h])

# Long window (24h) for daily patterns
rate(metric[24h])
```

### 3. Use Labels Wisely
```promql
# ✅ Good - aggregate by meaningful dimension
sum by (segment) (rate(autofill_policy_total[1h]))

# ❌ Bad - too many labels creates high cardinality
sum by (segment, style_id, user_id, timestamp) (...)
```

### 4. Set Reasonable Alert Thresholds
- Start conservative (avoid alert fatigue)
- Tune based on historical data
- Use `for:` clause to avoid flapping
- Include actionable descriptions

### 5. Document Custom Metrics
- Add comments to metric definitions
- Include units in metric names
- Use consistent naming conventions
- Update this doc when adding new metrics

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Recording Rules](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/)
