# Prometheus Metrics for ApplyLens

ApplyLens exposes Prometheus metrics at `/metrics` endpoint for monitoring and observability.

## Quick Start

### Access Metrics

```bash
curl http://localhost:8003/metrics
```

### Available Metrics

#### HTTP Request Metrics (Automatic)

These are automatically collected by the `starlette-exporter` middleware:

- **`applylens_http_requests_total`** (Counter)
  - Labels: `app_name`, `method`, `path`, `status_code`
  - Total HTTP requests processed by the API

- **`applylens_http_requests_in_progress`** (Gauge)
  - Labels: `app_name`, `method`
  - Currently in-flight HTTP requests

- **`applylens_http_request_duration_seconds`** (Histogram)
  - Labels: `app_name`, `method`, `path`, `status_code`
  - Request latency distribution with buckets: 0.005s, 0.01s, 0.025s, 0.05s, 0.075s, 0.1s, 0.25s, 0.5s, 0.75s, 1s, 2.5s, 5s, 7.5s, 10s

#### Custom Application Metrics

- **`applylens_backfill_requests_total`** (Counter)
  - Labels: `result` (ok, error, rate_limited, bad_request)
  - Total backfill requests by outcome
  - Example: `applylens_backfill_requests_total{result="ok"}` = 1

- **`applylens_backfill_inserted_total`** (Counter)
  - Total emails inserted during all backfill operations
  - Example: `applylens_backfill_inserted_total` = 32

- **`applylens_gmail_connected`** (Gauge)
  - Labels: `user_email`
  - Gmail connection status (1=connected, 0=disconnected)
  - Example: `applylens_gmail_connected{user_email="leoklemet.pa@gmail.com"}` = 1

- **`applylens_db_up`** (Gauge)
  - Database connectivity (1=up, 0=down)
  - Updated by `/readiness` endpoint

- **`applylens_es_up`** (Gauge)
  - Elasticsearch connectivity (1=up, 0=down)
  - Updated by `/readiness` endpoint

## Prometheus Server Configuration

### prometheus.yml Example

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'applylens'
    static_configs:
      - targets: ['localhost:8003']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### Docker Compose Example

To add Prometheus to your stack:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    ports:
      - "9090:9090"
    networks:
      - applylens_network
    restart: unless-stopped

volumes:
  prometheus_data:
```

## Grafana Dashboard

### Example PromQL Queries

**Request Rate (requests per minute):**

```promql
rate(applylens_http_requests_total[1m]) * 60
```

**Request Latency (p95):**

```promql
histogram_quantile(0.95, sum(rate(applylens_http_request_duration_seconds_bucket[5m])) by (le, path))
```

**Backfill Success Rate:**

```promql
rate(applylens_backfill_requests_total{result="ok"}[5m]) / 
rate(applylens_backfill_requests_total[5m])
```

**System Health:**

```promql
applylens_db_up + applylens_es_up  # Should be 2 when both healthy
```

**Gmail Connection Status:**

```promql
applylens_gmail_connected
```

**Emails Inserted Over Time:**

```promql
increase(applylens_backfill_inserted_total[1h])
```

### Sample Grafana Dashboard JSON

Create a new dashboard in Grafana and import this configuration:

```json
{
  "dashboard": {
    "title": "ApplyLens Monitoring",
    "panels": [
      {
        "title": "HTTP Request Rate",
        "targets": [
          {
            "expr": "rate(applylens_http_requests_total[1m]) * 60",
            "legendFormat": "{{method}} {{path}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Request Latency (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(applylens_http_request_duration_seconds_bucket[5m])) by (le))",
            "legendFormat": "p95"
          }
        ],
        "type": "graph"
      },
      {
        "title": "System Health",
        "targets": [
          {
            "expr": "applylens_db_up",
            "legendFormat": "Database"
          },
          {
            "expr": "applylens_es_up",
            "legendFormat": "Elasticsearch"
          }
        ],
        "type": "stat"
      },
      {
        "title": "Backfill Stats",
        "targets": [
          {
            "expr": "rate(applylens_backfill_requests_total[5m])",
            "legendFormat": "{{result}}"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
```

## Alerting Rules

### prometheus/alerts.yml Example

```yaml
groups:
  - name: applylens_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          rate(applylens_http_requests_total{status_code=~"5.."}[5m]) / 
          rate(applylens_http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API error rate"
          description: "Error rate is above 5% for 5 minutes"

      - alert: DatabaseDown
        expr: applylens_db_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failed"
          description: "Cannot connect to PostgreSQL"

      - alert: ElasticsearchDown
        expr: applylens_es_up == 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Elasticsearch connection failed"
          description: "Cannot connect to Elasticsearch"

      - alert: GmailDisconnected
        expr: applylens_gmail_connected == 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Gmail OAuth disconnected"
          description: "User {{$labels.user_email}} is not connected"

      - alert: HighBackfillRateLimit
        expr: |
          rate(applylens_backfill_requests_total{result="rate_limited"}[10m]) > 0.5
        for: 5m
        labels:
          severity: info
        annotations:
          summary: "High backfill rate limiting"
          description: "Backfill requests are being rate limited"
```

## Testing Metrics

### PowerShell Commands

```powershell
# 1. Check metrics endpoint
$metrics = (Invoke-WebRequest -Uri http://localhost:8003/metrics).Content
$metrics -split "`n" | Where-Object { $_ -match "^applylens_" }

# 2. Trigger operations to populate metrics
Invoke-RestMethod -Uri "http://localhost:8003/readiness"
Invoke-RestMethod -Uri "http://localhost:8003/gmail/status"
Invoke-RestMethod -Uri "http://localhost:8003/gmail/backfill?days=2" -Method POST

# 3. View specific metrics
$metrics -split "`n" | Where-Object { $_ -match "applylens_backfill" }
```

### Bash Commands

```bash
# Check metrics endpoint
curl http://localhost:8003/metrics | grep "^applylens_"

# Trigger operations
curl http://localhost:8003/readiness
curl http://localhost:8003/gmail/status
curl -X POST "http://localhost:8003/gmail/backfill?days=2"

# View specific metrics
curl -s http://localhost:8003/metrics | grep "applylens_backfill"
```

## Metrics Architecture

### Implementation Details

1. **Middleware**: `starlette-exporter` provides automatic HTTP metrics
2. **Custom Metrics**: Defined in `services/api/app/metrics.py`
3. **Instrumentation**:
   - `routes_gmail.py`: Backfill and connection status
   - `main.py`: Database and Elasticsearch health
4. **Export Format**: Prometheus text format (OpenMetrics compatible)

### File Structure

```
services/api/app/
├── metrics.py          # Centralized metric definitions
├── main.py             # Middleware setup + /metrics endpoint
└── routes_gmail.py     # Metric instrumentation
```

### Adding New Metrics

To add a new metric:

1. Define in `metrics.py`:

```python
from prometheus_client import Counter, Gauge, Histogram

MY_METRIC = Counter(
    "applylens_my_metric_total",
    "Description of metric",
    ["label1", "label2"]
)
```

2. Import in your route file:

```python
from .metrics import MY_METRIC

@router.get("/my-endpoint")
def my_endpoint():
    MY_METRIC.labels(label1="value1", label2="value2").inc()
    return {"ok": True}
```

3. Metrics will automatically appear at `/metrics`

## Production Deployment

### Security Considerations

1. **Restrict Access**: Metrics may contain sensitive information

   ```nginx
   # Nginx example - restrict /metrics to internal network
   location /metrics {
       allow 10.0.0.0/8;
       deny all;
       proxy_pass http://applylens-api:8003;
   }
   ```

2. **TLS**: Use HTTPS for Prometheus scraping in production

3. **Authentication**: Consider adding basic auth to `/metrics`

### Performance Impact

- Metrics collection has minimal overhead (<1ms per request)
- Memory usage increases with cardinality (unique label combinations)
- Retention in Prometheus can be configured (default: 15 days)

### Best Practices

1. Keep label cardinality low (avoid user IDs in labels)
2. Use consistent naming: `applylens_<component>_<metric>_<unit>`
3. Counter suffixes: `_total`
4. Histogram/Summary suffixes: `_seconds`, `_bytes`
5. Document all metrics in this file

## Troubleshooting

### Metrics Not Appearing

1. Check if API is running:

   ```bash
   curl http://localhost:8003/healthz
   ```

2. Check container logs:

   ```bash
   docker logs infra-api-1
   ```

3. Verify dependencies installed:

   ```bash
   docker exec infra-api-1 pip list | grep -E "prometheus|starlette-exporter"
   ```

### Stale Metrics

Gauges may show stale values if not updated. Call `/readiness` or relevant endpoints to refresh:

```bash
curl http://localhost:8003/readiness
curl http://localhost:8003/gmail/status
```

### Missing Labels

If labels show as "unknown", ensure the instrumentation code provides all label values:

```python
# BAD - missing required label
GMAIL_CONNECTED.set(1)

# GOOD - provides all labels
GMAIL_CONNECTED.labels(user_email=email).set(1)
```

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [starlette-exporter GitHub](https://github.com/stephenhillier/starlette_exporter)
- [prometheus_client Python](https://github.com/prometheus/client_python)
- [Grafana Prometheus Data Source](https://grafana.com/docs/grafana/latest/datasources/prometheus/)
