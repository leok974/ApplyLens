# Prometheus & Grafana Monitoring Stack

Complete monitoring setup for ApplyLens with Prometheus metrics collection and Grafana visualization.

## Quick Start

### 1. Start Prometheus and Grafana

```powershell
cd D:\ApplyLens\infra
docker compose up -d prometheus grafana
```

Wait ~10 seconds for services to start, then access:

- **Prometheus**: <http://localhost:9090>
- **Grafana**: <http://localhost:3000> (admin/admin)

### 2. Import Grafana Dashboard

1. Open Grafana at <http://localhost:3000>
2. Login with username: `admin`, password: `admin`
3. Click **+** → **Import dashboard**
4. Click **Upload JSON file** and select: `D:\ApplyLens\infra\prometheus\grafana-dashboard.json`
5. Select **Prometheus** as the data source
6. Click **Import**

You'll see the "ApplyLens API Overview" dashboard with 7 panels showing real-time metrics.

### 3. Add Prometheus Data Source (if needed)

If Prometheus data source doesn't exist:

1. Go to **Configuration** → **Data Sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Set URL: `http://prometheus:9090`
5. Click **Save & Test**

## Dashboard Panels

The imported dashboard includes:

1. **HTTP req/s** - Request rate by method and status code
2. **HTTP latency (p50/p90/p99)** - Response time percentiles
3. **Backfill outcomes (last 1h)** - Success/error/rate-limited counts
4. **Emails inserted (rate)** - Email insertion rate per minute
5. **Subsystem health** - Database and Elasticsearch status (1=up, 0=down)
6. **Gmail connected (per user)** - OAuth connection status
7. **HTTP Error Rate (5m)** - 5xx error percentage

## PromQL Quick Recipes

### HTTP Metrics

**Request rate (per second):**

```promql
sum by (method,status_code) (rate(applylens_http_requests_total[5m]))
```

**Error rate (5xx as percentage):**

```promql
sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m])) 
/ ignoring(status_code) sum(rate(applylens_http_requests_total[5m]))
```

**Latency percentiles:**

```promql
# p50
histogram_quantile(0.5, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))

# p90
histogram_quantile(0.9, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))

# p99
histogram_quantile(0.99, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))
```

### Backfill Metrics

**Rate-limited spikes (last 15m):**

```promql
increase(applylens_backfill_requests_total{result="rate_limited"}[15m])
```

**Emails inserted per minute:**

```promql
rate(applylens_backfill_inserted_total[1m]) * 60
```

**Backfill outcomes (last hour):**

```promql
sum by (result) (increase(applylens_backfill_requests_total[1h]))
```

### System Health

**Gmail connection status:**

```promql
applylens_gmail_connected
```

**Count of connected users:**

```promql
sum(max_over_time(applylens_gmail_connected[10m]))
```

**All systems operational (DB + ES):**

```promql
min(applylens_db_up) and min(applylens_es_up)
```

**Any system down:**

```promql
(min(applylens_db_up) == 0) or (min(applylens_es_up) == 0)
```

## Alerting Rules

Alerts are configured in `infra/prometheus/alerts.yml`:

### Active Alerts

1. **ApplyLensApiDown** (Critical)
   - Triggers when API is unreachable for >1 minute
   - Check: API container running, network connectivity

2. **HighHttpErrorRate** (Warning)
   - Triggers when 5xx errors exceed 5% for 5 minutes
   - Check: Application logs, database connectivity

3. **BackfillFailing** (Warning)
   - Triggers when backfill operations fail
   - Check: Gmail OAuth token, API quota

4. **GmailDisconnected** (Warning)
   - Triggers when Gmail connection is down for 15 minutes
   - Check: OAuth token expiration, refresh token validity

5. **DependenciesDown** (Critical)
   - Triggers when DB or Elasticsearch is unreachable for 2 minutes
   - Check: Container status, network connectivity

### View Alerts

1. Open Prometheus: <http://localhost:9090/alerts>
2. See active alerts and their status (pending, firing, resolved)

### Configure Alert Notifications

To send alerts to Slack, email, or other channels:

1. Create `infra/prometheus/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h

receivers:
  - name: 'default'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
        title: 'ApplyLens Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}: {{ .Annotations.description }}{{ end }}'
```

2. Add Alertmanager to `docker-compose.yml`:

```yaml
alertmanager:
  image: prom/alertmanager:v0.27.0
  container_name: infra-alertmanager
  volumes:
    - ./prometheus/alertmanager.yml:/etc/alertmanager/alertmanager.yml
  ports: ["9093:9093"]
```

3. Update `prometheus.yml`:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

## Testing Queries in Prometheus

### 1. Open Prometheus Graph UI

```powershell
start http://localhost:9090/graph
```

### 2. Try These Queries

**All ApplyLens metrics:**

```promql
{__name__=~"applylens_.*"}
```

**HTTP requests in last 5 minutes:**

```promql
rate(applylens_http_requests_total[5m])
```

**Current system health:**

```promql
applylens_db_up
applylens_es_up
```

**Backfill activity:**

```promql
sum by (result) (increase(applylens_backfill_requests_total[1h]))
```

### 3. Switch to Graph View

- Click the **Graph** tab to see time-series visualization
- Adjust time range with the dropdown (Last 1h, Last 6h, etc.)
- Enable auto-refresh for live updates

## Architecture

```
┌─────────────┐
│  ApplyLens  │  Exposes /metrics endpoint
│     API     │  Port 8003
└──────┬──────┘
       │
       │ scrapes every 30s
       ↓
┌─────────────┐
│ Prometheus  │  Collects & stores metrics
│             │  Port 9090
│             │  Evaluates alert rules
└──────┬──────┘
       │
       │ queries metrics
       ↓
┌─────────────┐
│   Grafana   │  Visualizes dashboards
│             │  Port 3000
└─────────────┘
```

### File Structure

```
infra/
├── docker-compose.yml           # Added prometheus + grafana services
└── prometheus/
    ├── prometheus.yml           # Scrape config
    ├── alerts.yml               # Alert rules
    └── grafana-dashboard.json   # Pre-configured dashboard
```

## Performance & Cardinality

### Current Label Cardinality (Low Risk)

✅ **Good cardinality:**

- `user_email` label: Single user (<leoklemet.pa@gmail.com>)
- `result` label: 4 values (ok, error, rate_limited, bad_request)
- `method` label: ~5 HTTP methods
- `path` label: ~10 API paths (grouped by `group_paths=True`)

### Best Practices

1. **Keep user labels low cardinality**
   - Current: 1 user ✅
   - If multi-user: Use user ID hash, not email

2. **Group dynamic paths**
   - Already configured: `group_paths=True` ✅
   - Prevents explosion from path parameters

3. **Limit histogram buckets**
   - Current: 13 buckets (5ms to 10s) ✅
   - Reasonable for API latency tracking

4. **Secure /metrics endpoint**
   - Development: Open access ✅
   - Production: Add ACL or basic auth

### Memory Usage

Prometheus memory scales with:

- **Active time series**: ~100 currently
- **Retention period**: 15 days (default)
- **Scrape interval**: 30 seconds

Estimated memory: **~200MB** for ApplyLens metrics alone.

## Production Deployment

### 1. Secure Metrics Endpoint

Add nginx rule to restrict `/metrics`:

```nginx
location /metrics {
    # Only allow Prometheus server
    allow 10.0.0.0/8;      # Internal network
    deny all;
    
    proxy_pass http://api:8003;
}
```

Or add basic auth in FastAPI:

```python
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from secrets import compare_digest

security = HTTPBasic()

@app.get("/metrics")
def metrics(credentials: HTTPBasicCredentials = Depends(security)):
    if not (compare_digest(credentials.username, "prometheus") and
            compare_digest(credentials.password, os.getenv("METRICS_PASSWORD"))):
        raise HTTPException(status_code=401)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### 2. Persistent Storage

Add volumes to docker-compose.yml:

```yaml
prometheus:
  volumes:
    - ./prometheus:/etc/prometheus
    - prometheus_data:/prometheus    # Persist metrics

grafana:
  volumes:
    - grafana_data:/var/lib/grafana  # Persist dashboards

volumes:
  prometheus_data:
  grafana_data:
```

### 3. Configure Retention

Update Prometheus command in docker-compose.yml:

```yaml
prometheus:
  command:
    - --config.file=/etc/prometheus/prometheus.yml
    - --storage.tsdb.retention.time=30d    # Keep 30 days
    - --storage.tsdb.retention.size=10GB   # Max 10GB
```

### 4. External Access

Update Grafana environment for production:

```yaml
grafana:
  environment:
    - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER}
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    - GF_SERVER_ROOT_URL=https://grafana.yourdomain.com
    - GF_AUTH_ANONYMOUS_ENABLED=false
```

## Troubleshooting

### Prometheus Can't Scrape API

**Symptom:** Target shows as "DOWN" in <http://localhost:9090/targets>

**Check:**

```powershell
# 1. Verify API /metrics endpoint
curl http://localhost:8003/metrics

# 2. Check Prometheus can reach API
docker exec infra-prometheus wget -O- http://api:8003/metrics

# 3. View Prometheus logs
docker logs infra-prometheus
```

**Fix:** Ensure API container is running and on same network.

### No Data in Grafana

**Symptom:** Dashboard panels show "No data"

**Check:**

```powershell
# 1. Test Prometheus data source in Grafana
# Settings → Data Sources → Prometheus → Save & Test

# 2. Query Prometheus directly
start http://localhost:9090/graph
# Run: applylens_http_requests_total

# 3. Check time range in Grafana (top-right)
```

**Fix:** Ensure Prometheus is scraping successfully (check /targets page).

### Metrics Showing Old Values

**Symptom:** Gauges not updating (e.g., `applylens_db_up` stuck at 0)

**Trigger metric updates:**

```powershell
# Call readiness endpoint to update DB_UP and ES_UP
curl http://localhost:8003/readiness

# Call status to update GMAIL_CONNECTED
curl http://localhost:8003/gmail/status

# Run backfill to update counters
Invoke-RestMethod -Uri "http://localhost:8003/gmail/backfill?days=2" -Method POST
```

### Alerts Not Firing

**Check alert evaluation:**

```powershell
# 1. Open Prometheus alerts page
start http://localhost:9090/alerts

# 2. Check alert rules loaded
docker exec infra-prometheus promtool check rules /etc/prometheus/alerts.yml

# 3. View Prometheus logs
docker logs infra-prometheus --tail 50
```

**Fix:** Ensure `alerts.yml` syntax is correct and referenced in `prometheus.yml`.

## Useful Commands

### Start/Stop Services

```powershell
# Start monitoring stack
docker compose -f D:\ApplyLens\infra\docker-compose.yml up -d prometheus grafana

# Stop monitoring stack
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop prometheus grafana

# Restart Prometheus (after config change)
docker compose -f D:\ApplyLens\infra\docker-compose.yml restart prometheus

# View logs
docker logs infra-prometheus --tail 50
docker logs infra-grafana --tail 50
```

### Validate Configuration

```powershell
# Check Prometheus config syntax
docker exec infra-prometheus promtool check config /etc/prometheus/prometheus.yml

# Check alert rules syntax
docker exec infra-prometheus promtool check rules /etc/prometheus/alerts.yml

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | ConvertFrom-Json
```

### Query Metrics via API

```powershell
# Instant query
$query = "applylens_http_requests_total"
curl "http://localhost:9090/api/v1/query?query=$query"

# Range query (last 1 hour)
curl "http://localhost:9090/api/v1/query_range?query=$query&start=$(Get-Date -UFormat %s -Date (Get-Date).AddHours(-1))&end=$(Get-Date -UFormat %s)&step=60s"
```

### Export/Import Dashboards

```powershell
# Export current dashboard from Grafana UI
# Dashboard → Share → Export → Save to file

# Import via CLI (requires Grafana API key)
$headers = @{ "Authorization" = "Bearer YOUR_API_KEY" }
Invoke-RestMethod -Uri "http://localhost:3000/api/dashboards/db" -Method POST -Headers $headers -ContentType "application/json" -InFile "dashboard.json"
```

## Next Steps

1. ✅ **Monitoring Setup Complete**
   - Prometheus scraping API metrics every 30s
   - Grafana dashboard showing 7 key metrics
   - 5 alert rules configured

2. 🎯 **Recommended Actions**
   - Create Grafana account (change admin password)
   - Set up Slack/email notifications for critical alerts
   - Add custom dashboard panels for specific workflows
   - Configure Prometheus retention based on storage

3. 📊 **Advanced Monitoring**
   - Add PostgreSQL exporter for DB metrics
   - Add Elasticsearch exporter for cluster health
   - Create SLO/SLI dashboards (99.9% uptime, p99 < 500ms)
   - Set up recording rules for expensive queries

## Resources

- **Prometheus Documentation**: <https://prometheus.io/docs/>
- **Grafana Documentation**: <https://grafana.com/docs/>
- **PromQL Tutorial**: <https://prometheus.io/docs/prometheus/latest/querying/basics/>
- **Grafana Dashboard Gallery**: <https://grafana.com/grafana/dashboards/>
- **ApplyLens Metrics Guide**: `D:\ApplyLens\docs\PROMETHEUS_METRICS.md`
