# PromQL Quick Reference for ApplyLens

Essential Prometheus queries for monitoring ApplyLens API metrics.

## Quick Testing in Prometheus

Open: <http://localhost:9090/graph>

Click the **Graph** tab to visualize time-series data.

---

## HTTP Request Metrics

### Request Rate (requests per second)

```promql
# Total request rate
sum(rate(applylens_http_requests_total[5m]))

# By method and status
sum by (method, status_code) (rate(applylens_http_requests_total[5m]))

# Only successful requests (2xx)
sum(rate(applylens_http_requests_total{status_code=~"2.."}[5m]))

# Only errors (5xx)
sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m]))
```text

### Error Rate

```promql
# 5xx error rate as percentage (last 5 minutes)
sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m])) 
/ ignoring(status_code) sum(rate(applylens_http_requests_total[5m]))

# 4xx client error rate
sum(rate(applylens_http_requests_total{status_code=~"4.."}[5m])) 
/ ignoring(status_code) sum(rate(applylens_http_requests_total[5m]))

# Total error rate (4xx + 5xx)
sum(rate(applylens_http_requests_total{status_code=~"[45].."}[5m])) 
/ ignoring(status_code) sum(rate(applylens_http_requests_total[5m]))
```text

### Request Latency

```promql
# p50 (median) latency
histogram_quantile(0.5, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))

# p90 latency
histogram_quantile(0.9, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))

# p95 latency
histogram_quantile(0.95, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))

# p99 latency
histogram_quantile(0.99, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))

# Average latency
rate(applylens_http_request_duration_seconds_sum[5m]) 
/ rate(applylens_http_request_duration_seconds_count[5m])

# Latency by endpoint
histogram_quantile(0.9, sum by (le, path) (rate(applylens_http_request_duration_seconds_bucket[5m])))
```text

### Top Endpoints by Traffic

```promql
# Top 10 endpoints by request count (last hour)
topk(10, sum by (path) (increase(applylens_http_requests_total[1h])))

# Slowest endpoints (p99 latency)
topk(5, histogram_quantile(0.99, sum by (le, path) (rate(applylens_http_request_duration_seconds_bucket[5m]))))
```text

### In-Flight Requests

```promql
# Current in-flight requests
sum(applylens_http_requests_in_progress)

# By method
sum by (method) (applylens_http_requests_in_progress)
```text

---

## Backfill Metrics

### Backfill Request Rate

```promql
# Backfill requests per minute
sum(rate(applylens_backfill_requests_total[5m])) * 60

# By outcome
sum by (result) (rate(applylens_backfill_requests_total[5m]))

# Success rate (percentage)
sum(rate(applylens_backfill_requests_total{result="ok"}[5m])) 
/ sum(rate(applylens_backfill_requests_total[5m]))
```text

### Backfill Outcomes

```promql
# Total backfill requests in last hour
sum by (result) (increase(applylens_backfill_requests_total[1h]))

# Rate-limited requests (last 15 minutes)
increase(applylens_backfill_requests_total{result="rate_limited"}[15m])

# Failed backfills (last 1 hour)
increase(applylens_backfill_requests_total{result="error"}[1h])

# Bad requests (last 1 hour)
increase(applylens_backfill_requests_total{result="bad_request"}[1h])
```text

### Email Insertion Rate

```promql
# Emails inserted per minute
rate(applylens_backfill_inserted_total[1m]) * 60

# Emails inserted per hour
rate(applylens_backfill_inserted_total[1h]) * 3600

# Total emails inserted (last 24 hours)
increase(applylens_backfill_inserted_total[24h])

# Average emails per successful backfill
increase(applylens_backfill_inserted_total[1h]) 
/ increase(applylens_backfill_requests_total{result="ok"}[1h])
```text

---

## System Health

### Database Status

```promql
# Database up (1) or down (0)
applylens_db_up

# Database uptime percentage (last hour)
avg_over_time(applylens_db_up[1h]) * 100
```text

### Elasticsearch Status

```promql
# Elasticsearch up (1) or down (0)
applylens_es_up

# Elasticsearch uptime percentage (last hour)
avg_over_time(applylens_es_up[1h]) * 100
```text

### Overall System Health

```promql
# Both DB and ES are up
min(applylens_db_up) and min(applylens_es_up)

# Any component down
(min(applylens_db_up) == 0) or (min(applylens_es_up) == 0)

# All systems operational (1 = yes, 0 = no)
min(applylens_db_up) * min(applylens_es_up)
```text

---

## Gmail Connection

### Connection Status

```promql
# Gmail connected (1) or disconnected (0)
applylens_gmail_connected

# By user email
applylens_gmail_connected{user_email="leoklemet.pa@gmail.com"}

# Count of connected users
sum(applylens_gmail_connected)

# Maximum connection status over last 10 minutes
max_over_time(applylens_gmail_connected[10m])
```text

---

## SLO/SLI Queries

### Availability

```promql
# API availability (percentage of successful requests)
sum(rate(applylens_http_requests_total{status_code=~"[23].."}[5m])) 
/ sum(rate(applylens_http_requests_total[5m])) * 100

# Uptime (based on successful scrapes)
avg_over_time(up{job="applylens-api"}[1h]) * 100
```text

### Latency SLO

```promql
# Percentage of requests under 500ms
sum(rate(applylens_http_request_duration_seconds_bucket{le="0.5"}[5m])) 
/ sum(rate(applylens_http_request_duration_seconds_count[5m])) * 100

# Percentage of requests under 1 second
sum(rate(applylens_http_request_duration_seconds_bucket{le="1.0"}[5m])) 
/ sum(rate(applylens_http_request_duration_seconds_count[5m])) * 100
```text

### Error Budget

```promql
# Error budget remaining (if SLO is 99.9% availability)
# Shows how much error budget is left (positive = good, negative = exceeded)
(0.999 - (
  sum(rate(applylens_http_requests_total{status_code=~"[23].."}[30d])) 
  / sum(rate(applylens_http_requests_total[30d]))
)) * 100
```text

---

## Alerting Queries

### High Error Rate Alert

```promql
# Alert if 5xx errors > 5% for 5 minutes
(sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m])) 
 / ignoring(status_code) sum(rate(applylens_http_requests_total[5m]))) > 0.05
```text

### High Latency Alert

```promql
# Alert if p99 latency > 2 seconds
histogram_quantile(0.99, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m]))) > 2
```text

### Backfill Failures

```promql
# Alert if any backfill errors in last 10 minutes
increase(applylens_backfill_requests_total{result="error"}[10m]) > 0
```text

### Gmail Disconnected

```promql
# Alert if Gmail disconnected for 15 minutes
max_over_time(applylens_gmail_connected[15m]) < 1
```text

### Dependencies Down

```promql
# Alert if DB or ES is down
(min(applylens_db_up) == 0) or (min(applylens_es_up) == 0)
```text

---

## Time-Based Aggregations

### Hourly Patterns

```promql
# Requests per hour (over last 24 hours)
sum(increase(applylens_http_requests_total[1h]))

# Peak hour (highest request count)
max_over_time(sum(rate(applylens_http_requests_total[1h]))[24h:1h])
```text

### Daily Patterns

```promql
# Total requests today
sum(increase(applylens_http_requests_total[1d]))

# Average daily request count (last 7 days)
avg_over_time(sum(increase(applylens_http_requests_total[1d]))[7d:1d])
```text

### Comparing Time Periods

```promql
# Compare current 5m rate vs 1 hour ago
sum(rate(applylens_http_requests_total[5m])) 
/ sum(rate(applylens_http_requests_total[5m] offset 1h))

# Compare today vs yesterday (same hour)
sum(increase(applylens_http_requests_total[1h])) 
/ sum(increase(applylens_http_requests_total[1h] offset 24h))
```text

---

## Advanced Queries

### Request Rate Anomaly Detection

```promql
# Alert if request rate deviates >50% from weekly average
abs(
  sum(rate(applylens_http_requests_total[5m])) 
  - avg_over_time(sum(rate(applylens_http_requests_total[5m]))[7d:5m])
) / avg_over_time(sum(rate(applylens_http_requests_total[5m]))[7d:5m]) > 0.5
```text

### Heatmap Data (for Grafana)

```promql
# Request duration histogram buckets
sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m]))
```text

### Cardinality Check

```promql
# Count unique label combinations for a metric
count(applylens_http_requests_total)

# Count unique paths
count(sum by (path) (applylens_http_requests_total))

# Count unique status codes
count(sum by (status_code) (applylens_http_requests_total))
```text

### Resource Usage Prediction

```promql
# Predict metric value in 1 hour using linear regression
predict_linear(applylens_backfill_inserted_total[1h], 3600)
```text

---

## Common Grafana Variables

Use these in Grafana dashboard variables for dynamic filtering:

### Instance Variable

```promql
# Query: label_values(applylens_http_requests_total, instance)
# Usage: {instance="$instance"}
```text

### Path Variable

```promql
# Query: label_values(applylens_http_requests_total, path)
# Usage: {path="$path"}
```text

### Status Code Variable

```promql
# Query: label_values(applylens_http_requests_total, status_code)
# Usage: {status_code="$status"}
```text

---

## Testing Queries in PowerShell

```powershell
# Function to query Prometheus
function Query-Prometheus {
    param([string]$Query)
    $encoded = [System.Web.HttpUtility]::UrlEncode($Query)
    $response = Invoke-RestMethod "http://localhost:9090/api/v1/query?query=$encoded"
    return $response.data.result
}

# Examples
Query-Prometheus "applylens_http_requests_total"
Query-Prometheus "rate(applylens_http_requests_total[5m])"
Query-Prometheus "histogram_quantile(0.95, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))"
```text

---

## Metric Naming Conventions

ApplyLens follows Prometheus best practices:

- **Counters**: End with `_total` (always increasing)
  - `applylens_backfill_requests_total`
  - `applylens_backfill_inserted_total`
  - `applylens_http_requests_total`

- **Gauges**: Can go up or down
  - `applylens_db_up`
  - `applylens_es_up`
  - `applylens_gmail_connected`

- **Histograms**: End with `_seconds`, `_bucket`, `_sum`, `_count`
  - `applylens_http_request_duration_seconds_bucket`
  - `applylens_http_request_duration_seconds_sum`
  - `applylens_http_request_duration_seconds_count`

---

## Query Performance Tips

1. **Use recording rules** for expensive queries that run frequently
2. **Limit time ranges** - shorter ranges = faster queries
3. **Aggregate before calculation** - `sum by (label) (rate())` not `rate(sum by (label))`
4. **Use instant queries** for current values, range queries for graphs
5. **Avoid high cardinality** - don't use user IDs or email addresses in labels

---

## Resources

- **PromQL Documentation**: <https://prometheus.io/docs/prometheus/latest/querying/basics/>
- **Query Examples**: <https://prometheus.io/docs/prometheus/latest/querying/examples/>
- **Functions Reference**: <https://prometheus.io/docs/prometheus/latest/querying/functions/>
- **Best Practices**: <https://prometheus.io/docs/practices/naming/>
