# 🚀 ApplyLens Prometheus - Quick Start Queries

**Test these in Prometheus Graph UI:** http://localhost:9090/graph

---

## 🏃 Copy & Paste These First

### System Health Check
```promql
applylens_db_up
```
Should show: **1** (database is up)

```promql
applylens_es_up
```
Should show: **1** (Elasticsearch is up)

```promql
applylens_gmail_connected{user_email="leoklemet.pa@gmail.com"}
```
Should show: **1** (Gmail connected)

---

### HTTP Request Rate
```promql
sum(rate(applylens_http_requests_total[5m]))
```
Shows: **Requests per second** (over last 5 minutes)

```promql
sum by (status_code) (rate(applylens_http_requests_total[5m]))
```
Shows: **Requests per second by status code** (200, 404, 500, etc.)

---

### Response Time (Latency)
```promql
histogram_quantile(0.95, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))
```
Shows: **p95 latency in seconds** (95% of requests are faster than this)

```promql
histogram_quantile(0.99, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))
```
Shows: **p99 latency** (99% of requests are faster than this)

---

### Backfill Activity
```promql
sum by (result) (increase(applylens_backfill_requests_total[1h]))
```
Shows: **Backfill requests in last hour** (ok, rate_limited, error, bad_request)

```promql
rate(applylens_backfill_inserted_total[5m]) * 60
```
Shows: **Emails inserted per minute**

---

## 📊 Grafana Dashboard Import

1. Open: http://localhost:3000
2. Login: `admin` / `admin`
3. Click **+** (left sidebar) → **Import dashboard**
4. Click **Upload JSON file**
5. Select: `D:\ApplyLens\infra\prometheus\grafana-dashboard.json`
6. Choose data source: **Prometheus**
7. Click **Import**

**Result:** 7-panel dashboard with all key metrics

---

## 🔍 Advanced Queries

### Error Rate (Percentage)
```promql
sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m])) 
/ ignoring(status_code) sum(rate(applylens_http_requests_total[5m])) * 100
```
Shows: **5xx error rate as percentage**

### Top Endpoints by Traffic
```promql
topk(5, sum by (path) (increase(applylens_http_requests_total[1h])))
```
Shows: **Top 5 endpoints by request count (last hour)**

### All Systems Operational
```promql
min(applylens_db_up) * min(applylens_es_up)
```
Shows: **1 if all up, 0 if any down**

---

## 🧪 Generate Test Traffic

Run this in PowerShell to populate metrics:

```powershell
# Generate traffic
1..10 | ForEach-Object {
    Invoke-RestMethod "http://localhost:8003/healthz"
    Invoke-RestMethod "http://localhost:8003/readiness"
    Invoke-RestMethod "http://localhost:8003/gmail/status"
    Start-Sleep -Milliseconds 500
}

# Wait for Prometheus to scrape
Start-Sleep -Seconds 35

# Now run queries in Prometheus UI
```

---

## 📈 Watch Metrics Update Live

In Prometheus Graph UI:

1. Enter query: `applylens_http_requests_total`
2. Click **Execute**
3. Switch to **Graph** tab
4. Set refresh: **5s** (dropdown at top)
5. Generate traffic (run PowerShell commands above)
6. Watch graph update in real-time!

---

## 🚨 View Active Alerts

http://localhost:9090/alerts

**You should see:**
- ApplyLensApiDown (inactive - API is up ✅)
- HighHttpErrorRate (inactive - no errors ✅)
- BackfillFailing (inactive - no failures ✅)
- GmailDisconnected (inactive - connected ✅)
- DependenciesDown (inactive - all up ✅)

---

## 💡 Pro Tips

1. **Use the Graph tab** - Much easier to see trends over time
2. **Adjust time range** - Top-right dropdown (Last 1h, Last 6h, etc.)
3. **Enable auto-refresh** - Dropdown next to time range
4. **Stack graphs** - Add multiple queries, click "Add Query"
5. **Use legends** - Shows exact values on hover

---

## 🎯 Success Checklist

- [x] Prometheus is running (http://localhost:9090)
- [x] Grafana is running (http://localhost:3000)
- [x] API target shows as "UP" (http://localhost:9090/targets)
- [x] Metrics are flowing (queries return data)
- [ ] Dashboard imported in Grafana
- [ ] Grafana password changed from default
- [ ] All 5 alerts showing as inactive

---

## 📚 Full Documentation

For deep dive:
- **MONITORING_COMPLETE.md** - Complete setup summary
- **MONITORING_SETUP.md** - Detailed deployment guide
- **PROMETHEUS_METRICS.md** - All metrics explained
- **PROMQL_RECIPES.md** - 50+ query examples

---

**You're all set!** 🎉 Start with the basic queries above, then explore the docs for advanced monitoring.
