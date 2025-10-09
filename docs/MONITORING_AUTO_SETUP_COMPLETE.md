# 🎯 Complete Auto-Provisioned Monitoring Setup Summary

## ✅ What Was Implemented

### Infrastructure Changes

**1. Updated `infra/docker-compose.yml`:**
- Added `--web.enable-lifecycle` flag to Prometheus for hot reload
- Added `GF_INSTALL_PLUGINS=grafana-piechart-panel` to Grafana
- Added Grafana provisioning volume mount: `./grafana/provisioning:/etc/grafana/provisioning`

**2. Created Grafana Auto-Provisioning Structure:**
```
infra/grafana/
└── provisioning/
    ├── datasources/
    │   └── prom.yml                    # Auto-wired Prometheus datasource
    └── dashboards/
        ├── applylens.yml               # Dashboard provider config
        └── json/
            └── applylens-overview.json # 6-panel dashboard
```

**3. Updated Prometheus Configuration:**
- `prometheus.yml`: Standardized scrape interval to 15s (was 30s)
- `alerts.yml`: Added 6th alert rule: **BackfillRateLimitedSpike** (info severity)

---

## 📊 Auto-Provisioned Dashboard

**Dashboard Name:** "ApplyLens API Overview"  
**Location:** Dashboards → ApplyLens folder  
**UID:** applylens-overview  
**Auto-refresh:** 10 seconds  
**Time range:** Last 1 hour

### Panels (6 Total)

1. **HTTP req/s** (Timeseries)
   - Query: `sum by (method,status_code) (rate(applylens_http_requests_total[5m]))`
   - Shows request rate by HTTP method and status code
   - Position: Top-left (12 units wide)

2. **HTTP latency (p50/p90/p99)** (Timeseries)
   - Queries:
     - p50: `histogram_quantile(0.5, sum by (le) (rate(...[5m])))`
     - p90: `histogram_quantile(0.9, sum by (le) (rate(...[5m])))`
     - p99: `histogram_quantile(0.99, sum by (le) (rate(...[5m])))`
   - Unit: seconds
   - Position: Top-right (12 units wide)

3. **Backfill outcomes (1h)** (Bar Gauge)
   - Query: `sum by (result) (increase(applylens_backfill_requests_total[1h]))`
   - Shows ok/error/rate_limited/bad_request counts
   - Orientation: Horizontal
   - Position: Middle-left (8 units wide)

4. **Emails inserted (rate)** (Timeseries)
   - Query: `rate(applylens_backfill_inserted_total[5m])`
   - Shows emails/second insertion rate
   - Position: Middle-center (8 units wide)

5. **Subsystem health** (Stat Panel)
   - Queries:
     - `max(applylens_db_up)` (Database)
     - `max(applylens_es_up)` (Elasticsearch)
   - Color thresholds: 0=red (down), 1=green (up)
   - Position: Middle-right (8 units wide)

6. **Gmail connected (per user)** (Table)
   - Query: `applylens_gmail_connected`
   - Shows user_email and connection status
   - Position: Bottom (full width)

---

## 🚨 Alert Rules (6 Total)

### Critical (2)
1. **ApplyLensApiDown**
   - Expression: `(1 - up{job="applylens-api"}) == 1`
   - Duration: 1 minute
   - Fixed: Changed from `(1 - (up{...}))` to `(1 - up{...})` (removed extra parentheses)

2. **DependenciesDown**
   - Expression: `(min(applylens_db_up) == 0) or (min(applylens_es_up) == 0)`
   - Duration: 2 minutes

### Warning (3)
3. **HighHttpErrorRate**
   - Expression: 5xx error rate > 5%
   - Duration: 5 minutes

4. **BackfillFailing**
   - Expression: `increase(applylens_backfill_requests_total{result="error"}[10m]) > 0`
   - Duration: 10 minutes

5. **GmailDisconnected**
   - Expression: `max_over_time(applylens_gmail_connected[15m]) < 1`
   - Duration: 15 minutes

### Info (1)
6. **BackfillRateLimitedSpike** (NEW)
   - Expression: `increase(applylens_backfill_requests_total{result="rate_limited"}[15m]) > 10`
   - Duration: 5 minutes
   - Fires when >10 rate-limited backfills in 15 minutes

---

## 🔧 New Features

### 1. Hot Reload (Prometheus)
No restart needed after config changes!

**Usage:**
```powershell
# Edit alerts or prometheus.yml
notepad D:\ApplyLens\infra\prometheus\alerts.yml

# Validate
docker exec infra-prometheus promtool check rules /etc/prometheus/alerts.yml

# Hot reload (instant!)
Invoke-WebRequest -Method POST http://localhost:9090/-/reload
```

**Enabled by:** `--web.enable-lifecycle` flag in docker-compose.yml

### 2. Auto-Provisioned Datasource
Grafana automatically connects to Prometheus on startup. No manual configuration needed!

**Configuration:** `infra/grafana/provisioning/datasources/prom.yml`
```yaml
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
```

### 3. Auto-Provisioned Dashboard
Dashboard loads automatically in "ApplyLens" folder on Grafana startup.

**Configuration:** `infra/grafana/provisioning/dashboards/applylens.yml`
```yaml
providers:
  - name: 'ApplyLens'
    folder: 'ApplyLens'
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards/json
```

### 4. Grafana Plugins
Pre-installed plugin: `grafana-piechart-panel`

**Enabled by:** `GF_INSTALL_PLUGINS=grafana-piechart-panel` in docker-compose.yml

---

## 🚀 Quick Access

### Services
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin/admin)
- **API Metrics:** http://localhost:8003/metrics

### Direct Links
- **Prometheus Alerts:** http://localhost:9090/alerts
- **Prometheus Targets:** http://localhost:9090/targets
- **Grafana Dashboard:** http://localhost:3000/d/applylens-overview
- **Prometheus Graph (HTTP rate):** http://localhost:9090/graph?g0.expr=sum(rate(applylens_http_requests_total[5m]))&g0.tab=0

---

## 📈 Verification Commands

### Check Prometheus Target
```powershell
$response = Invoke-RestMethod "http://localhost:9090/api/v1/targets"
$target = $response.data.activeTargets | Where-Object { $_.labels.job -eq "applylens-api" }
$target | Select-Object scrapeUrl, health, lastError | Format-Table
```
**Expected:** `health: up`

### Check Alert Rules
```powershell
$response = Invoke-RestMethod "http://localhost:9090/api/v1/rules"
$rules = $response.data.groups | Where-Object { $_.name -eq "applylens" }
Write-Host "Found $($rules.rules.Count) alert rules"
$rules.rules | ForEach-Object { "  • $($_.name) [$($_.labels.severity)]" }
```
**Expected:** 6 rules (2 critical, 3 warning, 1 info)

### Check Grafana Dashboard
```powershell
$cred = New-Object PSCredential("admin", (ConvertTo-SecureString "admin" -AsPlainText -Force))
$dashboards = Invoke-RestMethod -Uri "http://localhost:3000/api/search" -Credential $cred
$dashboards | Where-Object { $_.title -match "ApplyLens" } | Select-Object title, folderTitle, uid
```
**Expected:** "ApplyLens API Overview" in "ApplyLens" folder

### Generate Test Traffic
```powershell
# Generate 15 requests
1..5 | ForEach-Object {
    Invoke-RestMethod "http://localhost:8003/healthz" | Out-Null
    Invoke-RestMethod "http://localhost:8003/readiness" | Out-Null
    Invoke-RestMethod "http://localhost:8003/gmail/status" | Out-Null
    Start-Sleep -Milliseconds 200
}

# Wait for scrape (15s interval)
Start-Sleep -Seconds 20

# View metrics
$query = "sum(rate(applylens_http_requests_total[5m]))"
$response = Invoke-RestMethod "http://localhost:9090/api/v1/query?query=$query"
Write-Host "Request rate: $($response.data.result[0].value[1]) req/s"
```

---

## 📁 File Structure

```
D:\ApplyLens\
├── infra/
│   ├── docker-compose.yml                           ✅ Updated (lifecycle + plugins)
│   ├── prometheus/
│   │   ├── prometheus.yml                           ✅ Updated (15s scrape)
│   │   └── alerts.yml                               ✅ Updated (6 rules)
│   └── grafana/
│       └── provisioning/
│           ├── datasources/
│           │   └── prom.yml                         ✅ NEW (auto datasource)
│           └── dashboards/
│               ├── applylens.yml                    ✅ NEW (provider config)
│               └── json/
│                   └── applylens-overview.json      ✅ NEW (6-panel dashboard)
└── docs/
    ├── AUTO_PROVISIONED_MONITORING.md               ✅ NEW (this guide)
    ├── MONITORING_SETUP.md                          ✅ Existing
    ├── PROMETHEUS_METRICS.md                        ✅ Existing
    └── PROMQL_RECIPES.md                            ✅ Existing
```

---

## 🎯 Key Differences from Previous Setup

### Before (Manual Setup)
- ❌ Manual datasource configuration in Grafana UI
- ❌ Manual dashboard import via JSON upload
- ❌ No hot reload (restart required for config changes)
- ❌ 5 alert rules only

### After (Auto-Provisioned)
- ✅ Datasource auto-wired on startup
- ✅ Dashboard auto-loaded in "ApplyLens" folder
- ✅ Hot reload enabled (`POST /-/reload`)
- ✅ 6 alert rules (added BackfillRateLimitedSpike)
- ✅ Grafana plugins pre-installed
- ✅ Zero manual configuration needed

---

## 🔒 Security Recommendations

### For Production Deployment

**1. Change Grafana Credentials:**
```yaml
# In docker-compose.yml
grafana:
  environment:
    - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER}
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
```

**2. Restrict /metrics Endpoint:**
- Add IP allowlist at reverse proxy (nginx/Caddy)
- Or add basic auth to FastAPI `/metrics` endpoint
- Only Prometheus server should access metrics

**3. Use Docker Networks:**
```yaml
# In docker-compose.yml
networks:
  monitoring:
    internal: true  # No external access

services:
  prometheus:
    networks: [monitoring]
  grafana:
    networks: [monitoring]
  api:
    networks: [monitoring, public]
```

**4. Enable TLS:**
- Configure Grafana with TLS certificate
- Use reverse proxy (Caddy auto-TLS, nginx with Let's Encrypt)

---

## 🆘 Troubleshooting

### Dashboard Not Appearing in Grafana

**Check provisioning logs:**
```powershell
docker logs infra-grafana | Select-String "provisioning|dashboard"
```

**Expected output:**
```
logger=provisioning.dashboard level=info msg="starting to provision dashboards"
logger=provisioning.dashboard level=info msg="finished to provision dashboards"
```

**If dashboard missing:**
```powershell
# Verify file exists
Test-Path D:\ApplyLens\infra\grafana\provisioning\dashboards\json\applylens-overview.json

# Restart Grafana
docker compose -f D:\ApplyLens\infra\docker-compose.yml restart grafana
```

### Hot Reload Not Working

**Verify flag is set:**
```powershell
docker inspect infra-prometheus | ConvertFrom-Json | 
    Select-Object -ExpandProperty Args | 
    Where-Object { $_ -match "lifecycle" }
```

**Expected:** `--web.enable-lifecycle`

**Test hot reload:**
```powershell
Invoke-WebRequest -Method POST http://localhost:9090/-/reload
# Should return 200 OK
```

### Alerts Not Evaluating

**Check rule syntax:**
```powershell
docker exec infra-prometheus promtool check rules /etc/prometheus/alerts.yml
```

**Expected:** `SUCCESS: 6 rules found`

**View alert status:**
```powershell
start http://localhost:9090/alerts
```

---

## ✅ Success Checklist

- [x] Prometheus running with hot reload enabled
- [x] Grafana running with auto-provisioning
- [x] Datasource automatically configured
- [x] Dashboard auto-loaded in "ApplyLens" folder
- [x] 6 alert rules active
- [x] All alerts showing as inactive (system healthy)
- [x] Metrics flowing (db_up=1, es_up=1)
- [ ] Change Grafana admin password
- [ ] Test hot reload by editing alerts.yml
- [ ] Explore dashboard panels
- [ ] Set up alert notification channels (Slack/email)

---

## 🎓 Next Steps

### Immediate Actions
1. **Open Grafana:** http://localhost:3000
2. **Login:** admin / admin
3. **Navigate:** Dashboards → ApplyLens → ApplyLens API Overview
4. **Explore:** Click on panels, adjust time ranges, see metrics update

### This Week
1. **Test Hot Reload:**
   ```powershell
   # Add a test alert to alerts.yml
   notepad D:\ApplyLens\infra\prometheus\alerts.yml
   # Reload without restart
   Invoke-WebRequest -Method POST http://localhost:9090/-/reload
   ```

2. **Customize Dashboard:**
   - Add new panel showing total emails in system
   - Add panel for backfill success rate percentage
   - Create alert annotations on graphs

3. **Set Up Notifications:**
   - Configure Slack webhook for critical alerts
   - Add email notifications for warnings
   - Test alert delivery

### This Month
1. Create custom dashboards for specific workflows
2. Add recording rules for expensive queries
3. Configure Prometheus retention period
4. Set up Grafana user accounts for team members
5. Document runbooks for each alert

---

## 📚 Documentation Index

1. **AUTO_PROVISIONED_MONITORING.md** ← You are here
   - Complete setup summary
   - Auto-provisioning details
   - Hot reload instructions

2. **MONITORING_SETUP.md**
   - Detailed deployment guide
   - Production checklist
   - Troubleshooting section

3. **PROMETHEUS_METRICS.md**
   - All metrics explained
   - How to add new metrics
   - Best practices

4. **PROMQL_RECIPES.md**
   - 50+ query examples
   - SLO/SLI calculations
   - Alerting patterns

---

## 🎉 You're Ready!

Your monitoring stack is now **fully auto-provisioned** with:

✅ **Zero manual configuration** - Everything loads automatically  
✅ **Hot reload** - Edit alerts without restart  
✅ **Production-ready** - 6 alerts covering all critical scenarios  
✅ **Beautiful dashboards** - 6 panels showing key metrics  
✅ **Comprehensive docs** - 4 guides covering all aspects  

**Access your dashboard now:** http://localhost:3000/d/applylens-overview

**Happy monitoring!** 📊🚀
