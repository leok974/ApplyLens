# 🚀 Auto-Provisioned Monitoring Stack - Complete Setup

## ✅ What's Been Deployed

### Services Running

- ✅ **Prometheus v2.55.1** - <http://localhost:9090>
  - Hot reload enabled: `POST http://localhost:9090/-/reload`
  - Scraping API every 15 seconds
  - 6 alert rules active

- ✅ **Grafana 11.1.0** - <http://localhost:3000> (admin/admin)
  - Auto-provisioned Prometheus datasource
  - Auto-provisioned "ApplyLens API Overview" dashboard
  - Pre-installed plugin: grafana-piechart-panel

### Configuration Structure

```
infra/
├── docker-compose.yml                    ✅ Updated with lifecycle & volumes
├── prometheus/
│   ├── prometheus.yml                    ✅ Scrape config (15s interval)
│   └── alerts.yml                        ✅ 6 alert rules
└── grafana/
    └── provisioning/
        ├── datasources/
        │   └── prom.yml                  ✅ Auto-wired Prometheus datasource
        └── dashboards/
            ├── applylens.yml             ✅ Dashboard provider config
            └── json/
                └── applylens-overview.json ✅ 6-panel dashboard
```

---

## 📊 Dashboard Panels (Auto-Loaded)

The **"ApplyLens API Overview"** dashboard includes:

1. **HTTP req/s** - Request rate by method and status code (timeseries)
2. **HTTP latency (p50/p90/p99)** - Response time percentiles (timeseries)
3. **Backfill outcomes (1h)** - Success/error/rate-limited counts (bar gauge)
4. **Emails inserted (rate)** - Insertion rate per second (timeseries)
5. **Subsystem health** - DB and ES status with color thresholds (stat panel)
6. **Gmail connected (per user)** - OAuth connection status table

**Location in Grafana:** Dashboards → ApplyLens folder → ApplyLens API Overview

---

## 🚨 Alert Rules (6 Total)

### Critical Alerts

1. **ApplyLensApiDown**
   - Fires if API is unreachable for >1 minute
   - Expression: `(1 - up{job="applylens-api"}) == 1`

2. **DependenciesDown**
   - Fires if DB or ES is down for >2 minutes
   - Expression: `(min(applylens_db_up) == 0) or (min(applylens_es_up) == 0)`

### Warning Alerts

3. **HighHttpErrorRate**
   - Fires if 5xx errors >5% for 5 minutes
   - Expression: `sum(rate(...{status_code=~"5.."}[5m])) / sum(rate(...[5m])) > 0.05`

4. **BackfillFailing**
   - Fires if any backfill errors in last 10 minutes
   - Expression: `increase(applylens_backfill_requests_total{result="error"}[10m]) > 0`

5. **GmailDisconnected**
   - Fires if Gmail disconnected for >15 minutes
   - Expression: `max_over_time(applylens_gmail_connected[15m]) < 1`

### Info Alerts

6. **BackfillRateLimitedSpike**
   - Fires if >10 rate-limited backfills in 15 minutes
   - Expression: `increase(applylens_backfill_requests_total{result="rate_limited"}[15m]) > 10`

**View Alerts:** <http://localhost:9090/alerts>

---

## 🔧 Hot Reload Feature

Prometheus supports live configuration reload (no restart needed):

### After Editing Alert Rules

```powershell
# Edit alerts
notepad D:\ApplyLens\infra\prometheus\alerts.yml

# Validate syntax
docker exec infra-prometheus promtool check rules /etc/prometheus/alerts.yml

# Hot reload (no downtime!)
Invoke-WebRequest -Method POST http://localhost:9090/-/reload

# Verify rules reloaded
Invoke-RestMethod http://localhost:9090/api/v1/rules
```

### After Editing Prometheus Config

```powershell
# Edit config
notepad D:\ApplyLens\infra\prometheus\prometheus.yml

# Validate syntax
docker exec infra-prometheus promtool check config /etc/prometheus/prometheus.yml

# Hot reload
Invoke-WebRequest -Method POST http://localhost:9090/-/reload

# Check targets
Invoke-RestMethod http://localhost:9090/api/v1/targets
```

---

## 📈 Quick Sanity Checks

### 1. Check Prometheus Target Health

```powershell
$response = Invoke-RestMethod "http://localhost:9090/api/v1/targets"
$target = $response.data.activeTargets | Where-Object { $_.labels.job -eq "applylens-api" }
$target | Select-Object scrapeUrl, health, lastError | Format-Table
```

**Expected:** `scrapeUrl: http://api:8003/metrics`, `health: up`

### 2. Query Metrics

```powershell
# Total request rate
$query = "sum(rate(applylens_http_requests_total[5m]))"
$response = Invoke-RestMethod "http://localhost:9090/api/v1/query?query=$query"
Write-Host "Request rate: $($response.data.result[0].value[1]) req/s"

# System health
$db = (Invoke-RestMethod "http://localhost:9090/api/v1/query?query=applylens_db_up").data.result[0].value[1]
$es = (Invoke-RestMethod "http://localhost:9090/api/v1/query?query=applylens_es_up").data.result[0].value[1]
Write-Host "DB: $db, ES: $es (1=up, 0=down)"
```

### 3. Generate Test Traffic

```powershell
# Generate 20 requests
1..5 | ForEach-Object {
    Invoke-RestMethod "http://localhost:8003/healthz" | Out-Null
    Invoke-RestMethod "http://localhost:8003/readiness" | Out-Null
    Invoke-RestMethod "http://localhost:8003/gmail/status" | Out-Null
    Start-Sleep -Milliseconds 200
}

# Wait for scrape (15s interval)
Start-Sleep -Seconds 20

# View in Prometheus Graph UI
start "http://localhost:9090/graph?g0.expr=sum(rate(applylens_http_requests_total%5B5m%5D))&g0.tab=0"
```

### 4. Verify Grafana Provisioning

```powershell
# Check datasource
$datasources = Invoke-RestMethod -Uri "http://localhost:3000/api/datasources" -Credential (New-Object PSCredential("admin", (ConvertTo-SecureString "admin" -AsPlainText -Force)))
$datasources | Where-Object { $_.name -eq "Prometheus" } | Select-Object name, type, url, isDefault

# Check dashboards
$dashboards = Invoke-RestMethod -Uri "http://localhost:3000/api/search" -Credential (New-Object PSCredential("admin", (ConvertTo-SecureString "admin" -AsPlainText -Force)))
$dashboards | Where-Object { $_.title -match "ApplyLens" } | Select-Object title, folderTitle, uid
```

**Expected:** Prometheus datasource exists, "ApplyLens API Overview" dashboard in "ApplyLens" folder

---

## 🎯 Access Your Monitoring

### Prometheus UI

```powershell
start http://localhost:9090
```

**Try these queries:**

- `applylens_http_requests_total` - See all HTTP requests
- `rate(applylens_http_requests_total[5m])` - Request rate per second
- `histogram_quantile(0.95, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))` - p95 latency
- `sum by (result) (increase(applylens_backfill_requests_total[1h]))` - Backfill outcomes

### Grafana Dashboards

```powershell
start http://localhost:3000
```

1. Login: `admin` / `admin`
2. Navigate: Dashboards → ApplyLens → ApplyLens API Overview
3. Dashboard auto-refreshes every 10 seconds
4. Time range default: Last 1 hour

### Alerts Page

```powershell
start http://localhost:9090/alerts
```

All 6 alerts should show as **inactive** (green) when system is healthy.

---

## 🔄 Common Operations

### Restart Services

```powershell
# Restart both (preserves data)
docker compose -f D:\ApplyLens\infra\docker-compose.yml restart prometheus grafana

# Restart just Prometheus
docker compose -f D:\ApplyLens\infra\docker-compose.yml restart prometheus
```

### View Logs

```powershell
# Prometheus logs
docker logs infra-prometheus --tail 50

# Grafana logs
docker logs infra-grafana --tail 50

# Follow logs (real-time)
docker logs -f infra-prometheus
```

### Validate Configuration

```powershell
# Check Prometheus config syntax
docker exec infra-prometheus promtool check config /etc/prometheus/prometheus.yml

# Check alert rules syntax
docker exec infra-prometheus promtool check rules /etc/prometheus/alerts.yml

# Output:
# SUCCESS: 6 rules found
```

---

## 🎨 Customizing Dashboards

### Add New Panel to Existing Dashboard

1. Open dashboard in Grafana
2. Click **Add panel** (top-right)
3. Choose panel type (Graph, Stat, Table, etc.)
4. Add query (e.g., `rate(applylens_backfill_inserted_total[5m])`)
5. Configure visualization options
6. Click **Apply**
7. Click **Save dashboard** (top-right)

### Create New Dashboard from Scratch

1. Click **+** → **Dashboard**
2. Click **Add visualization**
3. Select data source: **Prometheus**
4. Add queries and configure panels
5. Click **Save dashboard** (top-right)
6. Choose folder: **ApplyLens**

### Export Dashboard JSON

1. Open dashboard
2. Click **Share** (top-right)
3. Click **Export** tab
4. Click **Save to file**
5. Save to `infra/grafana/provisioning/dashboards/json/`

Next time Grafana restarts, it will load the new dashboard automatically.

---

## 🚨 Adding Custom Alerts

### 1. Edit Alert Rules File

```powershell
notepad D:\ApplyLens\infra\prometheus\alerts.yml
```

### 2. Add New Alert

```yaml
  - alert: HighLatency
    expr: |
      histogram_quantile(0.99, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m]))) > 2
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "API p99 latency > 2s"
      description: "99th percentile latency is {{$value}}s for 10 minutes"
```

### 3. Validate & Reload

```powershell
# Validate syntax
docker exec infra-prometheus promtool check rules /etc/prometheus/alerts.yml

# Hot reload (no restart!)
Invoke-WebRequest -Method POST http://localhost:9090/-/reload

# Verify new alert appears
start http://localhost:9090/alerts
```

---

## 🔒 Security Hardening (For Production)

### 1. Change Grafana Password

Update `docker-compose.yml`:

```yaml
grafana:
  environment:
    - GF_SECURITY_ADMIN_USER=admin
    - GF_SECURITY_ADMIN_PASSWORD=YourSecurePassword123!  # Change this!
```

Or set via environment variable:

```powershell
$env:GRAFANA_ADMIN_PASSWORD = "SecurePassword123!"
docker compose -f D:\ApplyLens\infra\docker-compose.yml up -d grafana
```

### 2. Restrict /metrics Endpoint

Add basic auth or IP allowlist. Example with nginx:

```nginx
location /metrics {
    # Only allow Prometheus server
    allow 10.0.0.0/8;      # Internal network
    allow 172.16.0.0/12;   # Docker networks
    deny all;
    
    proxy_pass http://api:8003;
}
```

Or in FastAPI with basic auth:

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

### 3. Use Docker Networks

Update `docker-compose.yml` to isolate services:

```yaml
services:
  prometheus:
    networks:
      - monitoring
  
  grafana:
    networks:
      - monitoring
  
  api:
    networks:
      - monitoring
      - public

networks:
  monitoring:
    internal: true  # No external access
  public:
```

---

## 📚 PromQL Query Examples

### HTTP Metrics

```promql
# Request rate by endpoint
sum by (path) (rate(applylens_http_requests_total[5m]))

# Error rate percentage
sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m])) 
/ ignoring(status_code) sum(rate(applylens_http_requests_total[5m])) * 100

# p95 latency by endpoint
histogram_quantile(0.95, sum by (le, path) (rate(applylens_http_request_duration_seconds_bucket[5m])))

# Top 5 slowest endpoints
topk(5, histogram_quantile(0.99, sum by (le, path) (rate(applylens_http_request_duration_seconds_bucket[5m]))))
```

### Backfill Metrics

```promql
# Backfill success rate
sum(rate(applylens_backfill_requests_total{result="ok"}[5m])) 
/ sum(rate(applylens_backfill_requests_total[5m]))

# Emails per minute
rate(applylens_backfill_inserted_total[1m]) * 60

# Rate-limited requests (last hour)
increase(applylens_backfill_requests_total{result="rate_limited"}[1h])
```

### System Health

```promql
# All systems up (should equal 1)
min(applylens_db_up) * min(applylens_es_up)

# Any system down
(min(applylens_db_up) == 0) or (min(applylens_es_up) == 0)

# Uptime percentage (last 24h)
avg_over_time(up{job="applylens-api"}[24h]) * 100
```

---

## 🎓 Learning Resources

### Prometheus

- **Query Language:** <https://prometheus.io/docs/prometheus/latest/querying/basics/>
- **Alerting Rules:** <https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/>
- **Recording Rules:** <https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/>

### Grafana

- **Provisioning:** <https://grafana.com/docs/grafana/latest/administration/provisioning/>
- **Dashboard JSON:** <https://grafana.com/docs/grafana/latest/dashboards/json-model/>
- **Variable Templates:** <https://grafana.com/docs/grafana/latest/variables/>

### Best Practices

- **Naming Conventions:** <https://prometheus.io/docs/practices/naming/>
- **Metric Types:** <https://prometheus.io/docs/concepts/metric_types/>
- **Instrumentation:** <https://prometheus.io/docs/practices/instrumentation/>

---

## 🆘 Troubleshooting

### Problem: Target shows as "DOWN"

```powershell
# Check API is running and responding
curl http://localhost:8003/metrics

# Check Prometheus can reach API container
docker exec infra-prometheus wget -O- http://api:8003/metrics

# Check Prometheus logs
docker logs infra-prometheus --tail 50
```

### Problem: Dashboard not appearing in Grafana

```powershell
# Check provisioning logs
docker logs infra-grafana --tail 100 | Select-String "provision"

# Verify files exist
Test-Path D:\ApplyLens\infra\grafana\provisioning\dashboards\json\applylens-overview.json

# Restart Grafana
docker compose -f D:\ApplyLens\infra\docker-compose.yml restart grafana
```

### Problem: Alerts not firing

```powershell
# Check alert rules are loaded
Invoke-RestMethod http://localhost:9090/api/v1/rules | ConvertTo-Json -Depth 10

# Check alert evaluation
start http://localhost:9090/alerts

# View Prometheus logs for errors
docker logs infra-prometheus | Select-String "error|warn"
```

### Problem: Metrics showing as 0

```powershell
# Trigger endpoints to populate metrics
Invoke-RestMethod http://localhost:8003/readiness
Invoke-RestMethod http://localhost:8003/gmail/status

# Wait for scrape (15s)
Start-Sleep -Seconds 20

# Query again
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=applylens_db_up"
```

---

## ✅ Success Checklist

- [x] Prometheus running and scraping API target
- [x] Grafana running with auto-provisioned datasource
- [x] Dashboard auto-loaded in "ApplyLens" folder
- [x] 6 alert rules loaded and evaluating
- [x] Hot reload enabled for configuration changes
- [x] Metrics flowing (db_up=1, es_up=1)
- [ ] Change Grafana admin password
- [ ] Test alerts by stopping a service
- [ ] Create custom dashboard panels
- [ ] Set up alert notification channels

---

## 🎉 You're All Set

Your monitoring stack is **fully auto-provisioned** and ready for production use:

- ✅ No manual datasource configuration needed
- ✅ Dashboard automatically appears in Grafana
- ✅ Hot reload for quick iteration
- ✅ 6 production-ready alerts configured
- ✅ Complete observability of ApplyLens API

**Next:** Open Grafana (<http://localhost:3000>), login, and explore the "ApplyLens API Overview" dashboard!
