# 🚀 Auto-Provisioned Monitoring - Quick Reference

## ⚡ Quick Commands

### Access Services

```powershell
start http://localhost:9090          # Prometheus
start http://localhost:3000          # Grafana (admin/admin)
start http://localhost:8003/metrics  # API metrics (raw)
```

### Hot Reload Prometheus (No Restart!)

```powershell
# 1. Edit config
notepad D:\ApplyLens\infra\prometheus\alerts.yml

# 2. Validate
docker exec infra-prometheus promtool check rules /etc/prometheus/alerts.yml

# 3. Hot reload (instant!)
Invoke-WebRequest -Method POST http://localhost:9090/-/reload
```

### Generate Test Traffic

```powershell
1..5 | % { 
    curl http://localhost:8003/healthz | Out-Null
    curl http://localhost:8003/readiness | Out-Null
    Start-Sleep -Milliseconds 200
}
```

### Check Target Health

```powershell
$t = (irm http://localhost:9090/api/v1/targets).data.activeTargets | ? {$_.labels.job -eq "applylens-api"}
$t | select scrapeUrl, health, lastError | ft
```

### Query Metrics

```powershell
# Request rate
$q = "sum(rate(applylens_http_requests_total[5m]))"
(irm "http://localhost:9090/api/v1/query?query=$q").data.result[0].value[1]

# System health
irm "http://localhost:9090/api/v1/query?query=applylens_db_up" | % data | % result | % value
irm "http://localhost:9090/api/v1/query?query=applylens_es_up" | % data | % result | % value
```

---

## 📊 Dashboard Quick Access

**Direct URL:** <http://localhost:3000/d/applylens-overview>

**Or navigate:** Dashboards → ApplyLens → ApplyLens API Overview

**Panels:**

1. HTTP req/s (by method & status)
2. HTTP latency (p50/p90/p99)
3. Backfill outcomes (1h bar gauge)
4. Emails inserted rate
5. Subsystem health (DB + ES)
6. Gmail connected per user

---

## 🚨 Alert Rules

**View:** <http://localhost:9090/alerts>

**6 Rules:**

- **ApplyLensApiDown** (critical) - API down >1m
- **HighHttpErrorRate** (warning) - 5xx >5% for 5m
- **BackfillFailing** (warning) - Errors in last 10m
- **BackfillRateLimitedSpike** (info) - >10 rate-limits in 15m
- **GmailDisconnected** (warning) - Disconnected >15m
- **DependenciesDown** (critical) - DB/ES down >2m

---

## 🔧 Common Operations

### Restart Services

```powershell
docker compose -f D:\ApplyLens\infra\docker-compose.yml restart prometheus grafana
```

### View Logs

```powershell
docker logs infra-prometheus --tail 50
docker logs infra-grafana --tail 50
```

### Verify Provisioning

```powershell
# Check alert rules loaded
(irm http://localhost:9090/api/v1/rules).data.groups | ? name -eq "applylens" | % rules | % name

# Check Grafana dashboard
$cred = New-Object PSCredential("admin", (ConvertTo-SecureString "admin" -AsPlainText -Force))
irm http://localhost:3000/api/search -Credential $cred | ? title -match "ApplyLens" | select title, folderTitle
```

---

## 📁 File Locations

```
infra/
├── docker-compose.yml                                    # Updated (lifecycle flag)
├── prometheus/
│   ├── prometheus.yml                                    # Scrape config
│   └── alerts.yml                                        # 6 alert rules
└── grafana/
    └── provisioning/
        ├── datasources/prom.yml                          # Auto datasource
        └── dashboards/
            ├── applylens.yml                             # Provider config
            └── json/applylens-overview.json              # Dashboard JSON
```

---

## 💡 Key Features

✅ **Auto-Provisioning**

- Datasource automatically configured on startup
- Dashboard auto-loads in "ApplyLens" folder
- No manual Grafana UI configuration needed

✅ **Hot Reload**

- Edit `alerts.yml` or `prometheus.yml`
- POST to `http://localhost:9090/-/reload`
- Changes apply instantly without restart

✅ **Pre-installed Plugins**

- grafana-piechart-panel
- Add more: `GF_INSTALL_PLUGINS=plugin1,plugin2` in docker-compose.yml

✅ **Fast Scraping**

- 15-second interval (was 30s)
- Near real-time metrics in dashboard

---

## 📚 Documentation

- **MONITORING_AUTO_SETUP_COMPLETE.md** - Complete summary
- **AUTO_PROVISIONED_MONITORING.md** - Provisioning guide
- **MONITORING_SETUP.md** - Detailed deployment
- **PROMQL_RECIPES.md** - Query examples

---

## 🎯 Success Checklist

- [x] Prometheus scraping API (health: up)
- [x] 6 alert rules loaded
- [x] Grafana datasource auto-configured
- [x] Dashboard auto-loaded in "ApplyLens" folder
- [x] Hot reload enabled
- [x] System health metrics (DB=1, ES=1)
- [ ] Change Grafana password
- [ ] Test hot reload
- [ ] Explore dashboard
- [ ] Set up alert notifications

---

**Everything is ready!** Open <http://localhost:3000> and explore your dashboard. 🎉
