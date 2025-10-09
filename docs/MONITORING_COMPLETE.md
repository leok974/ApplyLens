# 🎯 Prometheus + Grafana Setup Complete!

## ✅ What's Been Deployed

### Infrastructure Added
- **Prometheus v2.55.1** - Metrics collection and alerting
- **Grafana 11.1.0** - Visualization and dashboards
- **Alert Rules** - 5 production-ready alerts configured

### Services Running
```
✅ infra-prometheus  → http://localhost:9090
✅ infra-grafana     → http://localhost:3000 (admin/admin)
✅ infra-api-1       → http://localhost:8003/metrics
```

### Configuration Files Created
```
infra/
├── docker-compose.yml              (updated - added prometheus + grafana)
└── prometheus/
    ├── prometheus.yml              (scrape config - 30s interval)
    ├── alerts.yml                  (5 alert rules)
    └── grafana-dashboard.json      (7-panel dashboard)

docs/
├── MONITORING_SETUP.md             (complete setup guide - 500+ lines)
├── PROMETHEUS_METRICS.md           (metrics documentation - 600+ lines)
└── PROMQL_RECIPES.md               (query cookbook - 400+ lines)
```

---

## 🚀 Quick Access

### Open Monitoring Tools
```powershell
# Prometheus
start http://localhost:9090/graph

# Grafana
start http://localhost:3000

# API Metrics (raw)
start http://localhost:8003/metrics
```

### Import Grafana Dashboard
1. Open Grafana: http://localhost:3000
2. Login: `admin` / `admin`
3. Click **+** → **Import dashboard**
4. Upload: `D:\ApplyLens\infra\prometheus\grafana-dashboard.json`
5. Select **Prometheus** data source
6. Click **Import**

---

## 📊 Dashboard Panels

Your imported dashboard shows:

1. **HTTP req/s** - Request rate by method/status
2. **HTTP latency (p50/p90/p99)** - Response time percentiles
3. **Backfill outcomes** - Success/error/rate-limited counts (last 1h)
4. **Emails inserted** - Insertion rate (per minute)
5. **Subsystem health** - DB and ES status (green=up, red=down)
6. **Gmail connected** - OAuth connection status by user
7. **HTTP Error Rate** - 5xx error percentage over 5m

---

## 🔔 Alert Rules Configured

### Critical Alerts
- **ApplyLensApiDown** - API unreachable >1 min
- **DependenciesDown** - DB or ES down >2 min

### Warning Alerts
- **HighHttpErrorRate** - 5xx errors >5% for 5 min
- **BackfillFailing** - Backfill errors in last 10 min
- **GmailDisconnected** - Gmail disconnected >15 min

View alerts: http://localhost:9090/alerts

---

## 📈 Essential Queries

### System Health
```promql
# All systems up (should be 1)
min(applylens_db_up) * min(applylens_es_up)

# Gmail connected
applylens_gmail_connected{user_email="leoklemet.pa@gmail.com"}
```

### API Performance
```promql
# Request rate (per second)
sum(rate(applylens_http_requests_total[5m]))

# p95 latency
histogram_quantile(0.95, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))

# Error rate (percentage)
sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m])) 
/ ignoring(status_code) sum(rate(applylens_http_requests_total[5m]))
```

### Backfill Activity
```promql
# Backfill outcomes (last hour)
sum by (result) (increase(applylens_backfill_requests_total[1h]))

# Emails inserted per minute
rate(applylens_backfill_inserted_total[1m]) * 60
```

---

## 🧪 Test the Setup

### 1. Generate Some Traffic
```powershell
# Trigger health checks
Invoke-RestMethod "http://localhost:8003/readiness"
Invoke-RestMethod "http://localhost:8003/gmail/status"

# Run backfill
Invoke-RestMethod -Uri "http://localhost:8003/gmail/backfill?days=2" -Method POST

# Check multiple times to populate metrics
1..5 | ForEach-Object { 
    Invoke-RestMethod "http://localhost:8003/healthz"
    Start-Sleep -Seconds 2
}
```

### 2. Wait for Scrape (30 seconds)
```powershell
Start-Sleep -Seconds 35
```

### 3. Query Prometheus
```powershell
# View all ApplyLens metrics
$query = "{__name__=~`"applylens_.*`"}"
$response = Invoke-RestMethod "http://localhost:9090/api/v1/query?query=$query"
$response.data.result | ForEach-Object { 
    Write-Host "$($_.metric.__name__): $($_.value[1])" 
}
```

### 4. Check Grafana Dashboard
- Open: http://localhost:3000
- Navigate to imported "ApplyLens API Overview" dashboard
- See real-time metrics updating

---

## 📚 Documentation Guide

### For Operations
- **MONITORING_SETUP.md** - Complete deployment and troubleshooting guide
  - Prometheus/Grafana configuration
  - Alert setup and notification channels
  - Production deployment checklist
  - Troubleshooting common issues

### For Developers
- **PROMETHEUS_METRICS.md** - Metric definitions and usage
  - All available metrics explained
  - How to add new metrics
  - Best practices and anti-patterns
  - Security considerations

### For Analysis
- **PROMQL_RECIPES.md** - Query cookbook
  - 50+ ready-to-use PromQL queries
  - SLO/SLI calculations
  - Alerting query patterns
  - Performance optimization tips

---

## 🔧 Common Operations

### View Logs
```powershell
# Prometheus logs
docker logs infra-prometheus --tail 50

# Grafana logs
docker logs infra-grafana --tail 50

# API logs (metrics endpoint)
docker logs infra-api-1 | Select-String "metrics"
```

### Restart Services
```powershell
# Restart Prometheus (after config change)
docker compose -f D:\ApplyLens\infra\docker-compose.yml restart prometheus

# Restart Grafana
docker compose -f D:\ApplyLens\infra\docker-compose.yml restart grafana

# Restart both
docker compose -f D:\ApplyLens\infra\docker-compose.yml restart prometheus grafana
```

### Validate Configuration
```powershell
# Check Prometheus config
docker exec infra-prometheus promtool check config /etc/prometheus/prometheus.yml

# Check alert rules
docker exec infra-prometheus promtool check rules /etc/prometheus/alerts.yml

# View targets status
Invoke-RestMethod "http://localhost:9090/api/v1/targets" | 
    Select-Object -ExpandProperty data | 
    Select-Object -ExpandProperty activeTargets
```

---

## 🎨 Customization Ideas

### Additional Dashboard Panels

**Add to Grafana dashboard:**

1. **Top Endpoints by Traffic**
   - Query: `topk(10, sum by (path) (increase(applylens_http_requests_total[1h])))`
   - Type: Bar gauge

2. **Request Rate Trend**
   - Query: `deriv(sum(increase(applylens_http_requests_total[5m]))[30m:5m])`
   - Type: Graph (shows if traffic is increasing/decreasing)

3. **Backfill Success Rate**
   - Query: `sum(rate(applylens_backfill_requests_total{result="ok"}[5m])) / sum(rate(applylens_backfill_requests_total[5m]))`
   - Type: Gauge (0-1 range, thresholds: <0.9 red, >0.95 green)

4. **Total Emails in System**
   - Query: `applylens_backfill_inserted_total`
   - Type: Stat

### Custom Alert Rules

Add to `prometheus/alerts.yml`:

```yaml
- alert: HighTrafficSpike
  expr: |
    rate(applylens_http_requests_total[5m]) > 
    avg_over_time(rate(applylens_http_requests_total[5m])[1h:5m]) * 2
  for: 10m
  labels: { severity: info }
  annotations:
    summary: "Traffic spike detected"
    description: "Request rate is 2x the hourly average"

- alert: SlowEndpoints
  expr: |
    histogram_quantile(0.95, sum by (le, path) (rate(applylens_http_request_duration_seconds_bucket[5m]))) > 1
  for: 10m
  labels: { severity: warning }
  annotations:
    summary: "Endpoint p95 latency > 1s"
    description: "{{$labels.path}} is slow (p95: {{$value}}s)"
```

---

## 🚨 What to Monitor

### Daily Checks
- [ ] All targets up: http://localhost:9090/targets
- [ ] No critical alerts: http://localhost:9090/alerts
- [ ] Grafana dashboard loads without errors

### Weekly Reviews
- [ ] Error rate trend (should be <1%)
- [ ] Latency trend (p95 should be <500ms)
- [ ] Backfill success rate (should be >95%)
- [ ] Storage usage (Prometheus data)

### Monthly Tasks
- [ ] Review and update alert thresholds
- [ ] Check for high-cardinality metrics
- [ ] Verify alert notification channels work
- [ ] Update Grafana dashboards based on usage patterns

---

## 🎓 Learning Resources

### Prometheus
- Official Docs: https://prometheus.io/docs/
- Query Language: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Best Practices: https://prometheus.io/docs/practices/naming/

### Grafana
- Documentation: https://grafana.com/docs/grafana/latest/
- Dashboard Examples: https://grafana.com/grafana/dashboards/
- Provisioning: https://grafana.com/docs/grafana/latest/administration/provisioning/

### PromQL Learning
- PromLabs: https://promlabs.com/promql-cheat-sheet/
- Query Examples: https://github.com/infinityworks/prometheus-example-queries
- Interactive Tutorial: https://prometheus.io/docs/prometheus/latest/querying/examples/

---

## 🔒 Production Checklist

Before deploying to production:

### Security
- [ ] Change Grafana admin password
- [ ] Restrict /metrics endpoint (IP allowlist or basic auth)
- [ ] Enable HTTPS for Prometheus and Grafana
- [ ] Configure secure credential storage

### Performance
- [ ] Set Prometheus retention period based on storage
- [ ] Configure recording rules for expensive queries
- [ ] Add persistent volumes for both services
- [ ] Monitor Prometheus memory usage

### Reliability
- [ ] Configure alerting channels (Slack, PagerDuty, email)
- [ ] Test alert notification delivery
- [ ] Set up backup for Grafana dashboards
- [ ] Document runbooks for each alert

### Observability
- [ ] Add business metrics (user signups, conversion rates)
- [ ] Create SLO dashboards (99.9% uptime, p95 < 500ms)
- [ ] Set up long-term storage (Thanos, Cortex, or VictoriaMetrics)
- [ ] Configure federation if running multiple Prometheus servers

---

## 🎉 Success Metrics

Your monitoring is working when:

✅ **Prometheus scrapes metrics** every 30 seconds
✅ **Grafana dashboard** updates in real-time
✅ **Alerts evaluate** and show in Prometheus UI
✅ **Queries respond** in <1 second
✅ **Metrics persist** after container restarts

---

## 🆘 Support

If you encounter issues:

1. **Check logs** first:
   ```powershell
   docker logs infra-prometheus --tail 100
   docker logs infra-grafana --tail 100
   docker logs infra-api-1 | Select-String "metrics"
   ```

2. **Verify network connectivity**:
   ```powershell
   # From Prometheus to API
   docker exec infra-prometheus wget -O- http://api:8003/metrics
   
   # From Grafana to Prometheus
   docker exec infra-grafana wget -O- http://prometheus:9090/api/v1/query?query=up
   ```

3. **Check configuration syntax**:
   ```powershell
   # Prometheus config
   docker exec infra-prometheus promtool check config /etc/prometheus/prometheus.yml
   
   # Alert rules
   docker exec infra-prometheus promtool check rules /etc/prometheus/alerts.yml
   ```

4. **Review documentation**:
   - `docs/MONITORING_SETUP.md` - Troubleshooting section
   - `docs/PROMETHEUS_METRICS.md` - Metrics definitions
   - `docs/PROMQL_RECIPES.md` - Query examples

---

## 📍 Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                     ApplyLens API                        │
│                   (Port 8003)                            │
│                                                          │
│  Endpoints:                                              │
│  • /metrics       → Prometheus text format              │
│  • /readiness     → Sets DB_UP, ES_UP gauges           │
│  • /gmail/status  → Sets GMAIL_CONNECTED gauge          │
│  • /gmail/backfill → Increments counters                │
└────────────┬─────────────────────────────────────────────┘
             │
             │ Scrape every 30s
             ↓
┌──────────────────────────────────────────────────────────┐
│                    Prometheus                            │
│                   (Port 9090)                            │
│                                                          │
│  • Collects metrics from /metrics                       │
│  • Evaluates alert rules (alerts.yml)                   │
│  • Stores time-series data (15 days default)            │
│  • Exposes PromQL query API                             │
└────────────┬─────────────────────────────────────────────┘
             │
             │ Query metrics via PromQL
             ↓
┌──────────────────────────────────────────────────────────┐
│                     Grafana                              │
│                   (Port 3000)                            │
│                                                          │
│  • Visualizes metrics in dashboards                     │
│  • Shows 7-panel ApplyLens overview                     │
│  • Real-time updates (10s refresh)                      │
│  • Alert annotations on graphs                          │
└──────────────────────────────────────────────────────────┘
```

---

## 🎯 Next Steps

1. ✅ **Monitoring Setup Complete** - Prometheus and Grafana running
2. ✅ **Metrics Flowing** - API exposing metrics, Prometheus scraping
3. ✅ **Dashboard Created** - 7 panels showing key metrics
4. ✅ **Alerts Configured** - 5 production-ready alert rules

### Recommended Actions

**Immediate (Today):**
- [ ] Import Grafana dashboard from `grafana-dashboard.json`
- [ ] Change Grafana admin password
- [ ] Test alerts by stopping a service
- [ ] Bookmark monitoring URLs

**This Week:**
- [ ] Set up Slack/email alert notifications
- [ ] Create custom dashboard for your workflow
- [ ] Add business-specific metrics
- [ ] Configure Prometheus retention period

**This Month:**
- [ ] Review alert thresholds based on real traffic
- [ ] Add SLO/SLI dashboards
- [ ] Set up Grafana user accounts for team
- [ ] Document runbooks for each alert

---

**You now have production-grade monitoring for ApplyLens!** 🚀

All metrics, alerts, and dashboards are configured and running. Check the docs for advanced queries and customization options.
