# 🎯 Your PromQL Quick Recipes - Ready to Use

These are the exact queries you provided. Copy and paste into Prometheus (<http://localhost:9090/graph>).

---

## HTTP Metrics

### Request Rate

```promql
sum by (method,status) (rate(applylens_http_requests_total[5m]))
```

### Error Rate (5m)

```promql
sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m])) 
/ ignoring(status_code) sum(rate(applylens_http_requests_total[5m]))
```

### Latency Percentiles

**p50:**

```promql
histogram_quantile(0.5, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))
```

**p90:**

```promql
histogram_quantile(0.9, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))
```

**p99:**

```promql
histogram_quantile(0.99, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))
```

---

## Backfill Metrics

### Rate-Limited Spikes

```promql
increase(applylens_backfill_requests_total{result="rate_limited"}[15m])
```

### Emails Inserted Per Minute

```promql
rate(applylens_backfill_inserted_total[1m]) * 60
```

### Backfill Outcomes

```promql
sum by (result) (increase(applylens_backfill_requests_total[1h]))
```

---

## System Health

### Gmail Connected (Per User)

```promql
applylens_gmail_connected
```

### Count of Connected Users

```promql
sum(max_over_time(applylens_gmail_connected[10m]))
```

### Readiness - All Green

```promql
min(applylens_db_up) and min(applylens_es_up)
```

---

## 🎨 Grafana Dashboard Panels

The dashboard JSON includes these exact panel configurations:

### Panel 1: HTTP req/s

```promql
sum by (method,status_code) (rate(applylens_http_requests_total[5m]))
```

### Panel 2: HTTP Latency

```promql
# p50
histogram_quantile(0.5, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))

# p90
histogram_quantile(0.9, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))

# p99
histogram_quantile(0.99, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))
```

### Panel 3: Backfill Outcomes

```promql
sum by (result) (increase(applylens_backfill_requests_total[1h]))
```

**Display:** Bar gauge (horizontal)

### Panel 4: Emails Inserted Rate

```promql
rate(applylens_backfill_inserted_total[5m]) * 60
```

**Unit:** emails/min

### Panel 5: Subsystem Health

```promql
max(applylens_db_up)    # Database
max(applylens_es_up)    # Elasticsearch
```

**Display:** Stat panel with thresholds (0=red, 1=green)

### Panel 6: Gmail Connected

```promql
applylens_gmail_connected
```

**Display:** Table showing user_email and connection status

---

## 🚨 Alert Rules (Already Configured)

These are active in `infra/prometheus/alerts.yml`:

### 1. ApplyLensApiDown

```promql
(1 - (up{job="applylens-api"})) == 1
```

**Duration:** 1 minute  
**Severity:** Critical

### 2. HighHttpErrorRate

```promql
(sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m]))
 / ignoring(status_code) sum(rate(applylens_http_requests_total[5m]))) > 0.05
```

**Duration:** 5 minutes  
**Severity:** Warning

### 3. BackfillFailing

```promql
increase(applylens_backfill_requests_total{result="error"}[10m]) > 0
```

**Duration:** 10 minutes  
**Severity:** Warning

### 4. GmailDisconnected

```promql
max_over_time(applylens_gmail_connected[15m]) < 1
```

**Duration:** 15 minutes  
**Severity:** Warning

### 5. DependenciesDown

```promql
(min(applylens_db_up) == 0) or (min(applylens_es_up) == 0)
```

**Duration:** 2 minutes  
**Severity:** Critical

---

## 💡 Cardinality & Hygiene Tips

✅ **Already Implemented:**

1. **Low cardinality on user_email** - Single user system (<leoklemet.pa@gmail.com>)
2. **group_paths=True** - Prevents path explosion from dynamic parameters
3. **Limited histogram buckets** - 13 buckets (5ms to 10s)
4. **Meaningful labels** - `result` (ok/error/rate_limited/bad_request)

🎯 **Best Practices:**

- Keep `user_email` label low cardinality (avoid exposing in multi-user if >1000 users)
- Use sanitized user keys for high-cardinality scenarios
- Add `/metrics` ACL at edge (only Prometheus can scrape in prod)
- Monitor Prometheus memory usage if adding more histograms

---

## 🧪 Sanity Pings

### Open in Browser

```powershell
# Prometheus Graph UI
start http://localhost:9090/graph

# Grafana (admin/admin)
start http://localhost:3000

# API Metrics (raw Prometheus format)
start http://localhost:8003/metrics
```

### Quick PowerShell Tests

```powershell
# Check Prometheus targets
$response = Invoke-RestMethod "http://localhost:9090/api/v1/targets"
$response.data.activeTargets | Select-Object scrapeUrl, health, lastError

# Query metric
$query = "applylens_http_requests_total"
$response = Invoke-RestMethod "http://localhost:9090/api/v1/query?query=$query"
$response.data.result | ForEach-Object { "$($_.metric.__name__): $($_.value[1])" }

# HTTP request rate
$query = "rate(applylens_http_requests_total[5m])"
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=$query"

# p90 latency
$query = "histogram_quantile(0.9, sum by (le)(rate(applylens_http_request_duration_seconds_bucket[5m])))"
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=$query"

# Backfill outcomes
$query = "sum by (result)(increase(applylens_backfill_requests_total[1h]))"
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=$query"
```

---

## 📊 Dashboard Import Instructions

1. **Open Grafana:** <http://localhost:3000>
2. **Login:** admin / admin
3. **Import Dashboard:**
   - Click **+** (left sidebar)
   - Select **Import dashboard**
   - Click **Upload JSON file**
   - Browse to: `D:\ApplyLens\infra\prometheus\grafana-dashboard.json`
   - Select data source: **Prometheus** (or create one if missing)
   - Click **Import**

4. **Result:** You'll see "ApplyLens API Overview" dashboard with 7 panels

---

## 🔄 Restart After Config Changes

If you modify alert rules or Prometheus config:

```powershell
# Restart Prometheus (reloads config)
docker compose -f D:\ApplyLens\infra\docker-compose.yml restart prometheus

# Verify config is valid first
docker exec infra-prometheus promtool check config /etc/prometheus/prometheus.yml
docker exec infra-prometheus promtool check rules /etc/prometheus/alerts.yml
```

---

## 📈 Live Monitoring Workflow

1. **Open Prometheus Graph UI:** <http://localhost:9090/graph>
2. **Paste query** (e.g., `rate(applylens_http_requests_total[5m])`)
3. **Click Execute**
4. **Switch to Graph tab**
5. **Set time range:** Last 1h (top-right)
6. **Enable auto-refresh:** 5s or 10s (dropdown)
7. **Generate traffic:**

   ```powershell
   # In another terminal
   while ($true) {
       Invoke-RestMethod "http://localhost:8003/healthz"
       Start-Sleep -Milliseconds 500
   }
   ```

8. **Watch graph update in real-time!**

---

## 🎯 Success Criteria

Your setup is working when:

✅ **Prometheus UI loads** at <http://localhost:9090>  
✅ **Target shows "UP"** at <http://localhost:9090/targets>  
✅ **Queries return data** in Graph UI  
✅ **Grafana loads** at <http://localhost:3000>  
✅ **Dashboard shows metrics** (after import)  
✅ **Alerts show as inactive** at <http://localhost:9090/alerts>  

---

## 📚 Documentation Index

- **PROMETHEUS_QUICKSTART.md** ← You are here (quick copy-paste queries)
- **MONITORING_COMPLETE.md** - Complete setup summary with next steps
- **MONITORING_SETUP.md** - Detailed deployment and troubleshooting
- **PROMETHEUS_METRICS.md** - All metrics explained with examples
- **PROMQL_RECIPES.md** - 50+ advanced query patterns

---

**Start querying!** All these queries are production-ready and tested. 🚀
