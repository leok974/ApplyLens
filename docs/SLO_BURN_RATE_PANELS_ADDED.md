# 🎯 Advanced SLO Monitoring Panels Added

**Date:** October 9, 2025  
**Status:** ✅ Complete

---

## 🚀 What Was Added

Added 4 advanced SLO monitoring panels to the ApplyLens dashboard, bringing the total to **11 panels** with comprehensive SRE-style monitoring.

---

## 📊 New Dashboard Panels

### 1. Last Alert Fired (minutes ago)

**Type:** Stat  
**Position:** Row 4, x=8, y=22 (8 units wide, 7 units tall)  
**Purpose:** Shows time elapsed since the most recent firing alert

**Query:**
```promql
(time() - max_over_time(timestamp(ALERTS{alertstate="firing"}[30d])))/60
```

**How It Works:**
- `ALERTS{alertstate="firing"}` - Prometheus meta-metric showing active alerts
- `timestamp()` - Get the timestamp when alert fired
- `max_over_time(...[30d])` - Find most recent alert in last 30 days
- `time() - ...` - Calculate time difference
- `/ 60` - Convert seconds to minutes

**Display:**
- Unit: minutes (m)
- Shows single stat value
- If no alerts have fired, may show NaN or empty

**Use Cases:**
- Quick visibility into recent alerting activity
- Verify alerting system is working
- Track time since last incident

---

### 2. SLO Burn Rate (1h, 99.9% SLO)

**Type:** Timeseries  
**Position:** Row 5, x=0, y=29 (12 units wide, 7 units tall)  
**Purpose:** Fast-moving burn rate for quick incident detection

**Query:**
```promql
(sum(rate(applylens_http_requests_total{status=~"5.."}[1h])) / 
 sum(rate(applylens_http_requests_total[1h]))) / 0.001
```

**Thresholds:**
- 🟢 **Green:** < 1× (within error budget)
- 🟠 **Orange:** 1× - 10× (consuming error budget faster than expected)
- 🔴 **Red:** > 10× (burning through error budget rapidly)

**How It Works:**
- Calculates error rate over 1 hour window
- Divides by allowed error rate (0.001 for 99.9% SLO)
- Burn rate = 1× means you're using error budget at exactly the expected rate
- Burn rate > 1× means you're using it faster (alert fatigue risk)
- Burn rate > 10× means you're depleting it very rapidly (urgent action needed)

**SRE Context:**
- 1h window provides **fast detection** of incidents
- Catches problems within an hour
- More sensitive to noise/spikes

---

### 3. SLO Burn Rate (6h, 99.9% SLO)

**Type:** Timeseries  
**Position:** Row 5, x=12, y=29 (12 units wide, 7 units tall)  
**Purpose:** Slower-moving burn rate that resists noise

**Query:**
```promql
(sum(rate(applylens_http_requests_total{status=~"5.."}[6h])) / 
 sum(rate(applylens_http_requests_total[6h]))) / 0.001
```

**Thresholds:**
- 🟢 **Green:** < 1× (within error budget)
- 🟠 **Orange:** 1× - 6× (elevated burn rate)
- 🔴 **Red:** > 6× (critical burn rate)

**How It Works:**
- Same calculation as 1h window, but over 6 hours
- Smoother, more stable view
- Less sensitive to temporary spikes

**SRE Context:**
- 6h window provides **stability** against false alarms
- Better for sustained issues
- Multi-window strategy: Use both 1h (fast) + 6h (stable)

**Multi-Window Alerting Pattern:**
```
If (1h burn > 14.4×) OR (6h burn > 6×):
  → Page on-call (critical SLO threat)

If (1h burn > 10×) AND (6h burn > 3×):
  → Create incident ticket (investigate)
```

---

### 4. API Uptime (last 1h)

**Type:** Gauge  
**Position:** Row 6, x=0, y=36 (8 units wide, 7 units tall)  
**Purpose:** Real-time uptime percentage for immediate health check

**Query:**
```promql
avg_over_time(up{job="applylens-api"}[1h]) * 100
```

**Thresholds:**
- 🔴 **Red:** < 95% (poor uptime)
- 🟠 **Orange:** 95% - 99.9% (acceptable)
- 🟢 **Green:** > 99.9% (excellent)

**How It Works:**
- `up` metric = 1 when Prometheus can scrape target
- Average over 1 hour window
- Multiply by 100 for percentage

**Use Cases:**
- **Immediate visibility** into current health
- Complements 30-day SLO gauge (long-term vs short-term)
- Quickly spot recent downtime

**Comparison with 30-day gauge:**
- **1h gauge:** "How are we doing right now?"
- **30d gauge:** "Did we meet our monthly SLO?"

---

## 📈 Complete Dashboard Overview

### All 11 Panels

**Row 1 - Traffic & Performance:**
1. HTTP req/s (by method & status)
2. HTTP latency (p50/p90/p99)

**Row 2 - Business Metrics:**
3. Backfill outcomes (1h bar gauge)
4. Emails inserted rate

**Row 3 - System Health:**
5. Subsystem health (DB + ES)
6. Gmail connected per user

**Row 4 - SLO & Alerting:**
7. API Uptime (last 30d) - long-term SLO
8. **Last Alert Fired - NEW!**

**Row 5 - SLO Burn Rate:**
9. **SLO Burn Rate (1h) - NEW!** (fast detection)
10. **SLO Burn Rate (6h) - NEW!** (noise-resistant)

**Row 6 - Short-term Health:**
11. **API Uptime (last 1h) - NEW!** (real-time health)

---

## 🎯 SRE Burn Rate Concepts

### What is Error Budget?

For a **99.9% SLO:**
- Allowed downtime: 0.1% = 43.2 minutes per 30 days
- This is your **error budget**

### What is Burn Rate?

Burn rate tells you **how fast** you're consuming that budget:

| Burn Rate | Meaning | Example | Action |
|-----------|---------|---------|--------|
| 0× | Perfect (no errors) | 0 errors/hour | ✅ All good |
| 1× | Normal consumption | Budget lasts exactly 30d | ✅ On track |
| 2× | Using budget 2× faster | Budget lasts 15 days | ⚠️ Monitor |
| 10× | Using budget 10× faster | Budget lasts 3 days | 🚨 Investigate |
| 100× | Rapid depletion | Budget lasts 7 hours | 🔥 Page on-call |

### Multi-Window Strategy

SRE teams use **multiple time windows** for different purposes:

```
Fast Window (1h):
  ✅ Catches incidents quickly
  ❌ Sensitive to noise/spikes
  
Slow Window (6h):
  ✅ Stable, reduces false positives
  ❌ Slower to detect new incidents

Best Practice: Use BOTH
  → 1h: Fast detection
  → 6h: Confirmation & stability
```

### Example Alert Rules (to add to Prometheus)

```yaml
# Fast burn - critical
- alert: HighErrorBudgetBurn_1h
  expr: |
    (sum(rate(applylens_http_requests_total{status=~"5.."}[1h])) / 
     sum(rate(applylens_http_requests_total[1h]))) / 0.001 > 14.4
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Fast error budget burn (1h window)"
    description: "Burning error budget 14.4× faster than sustainable rate"

# Slow burn - warning
- alert: ElevatedErrorBudgetBurn_6h
  expr: |
    (sum(rate(applylens_http_requests_total{status=~"5.."}[6h])) / 
     sum(rate(applylens_http_requests_total[6h]))) / 0.001 > 6
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "Sustained error budget burn (6h window)"
    description: "Burning error budget 6× faster over 6 hours"
```

**Burn rate thresholds explained:**
- **14.4× (1h):** If sustained, depletes 30-day budget in 2 days
- **6× (6h):** If sustained, depletes 30-day budget in 5 days

---

## 🧮 Burn Rate Math

### For 99.9% SLO (0.1% error budget):

**1× Burn Rate:**
- Error rate = 0.1% = 0.001
- Budget lasts: 30 days

**10× Burn Rate:**
- Error rate = 1% = 0.010
- Budget depleted in: 30 / 10 = 3 days

**100× Burn Rate:**
- Error rate = 10% = 0.100
- Budget depleted in: 30 / 100 = 0.3 days = 7.2 hours

### Why Divide by 0.001?

```promql
current_error_rate / allowed_error_rate = burn_rate

Example:
  5xx rate = 0.005 (0.5%)
  Allowed = 0.001 (0.1% for 99.9% SLO)
  Burn rate = 0.005 / 0.001 = 5×
```

---

## 📊 Testing the New Panels

### Test 1: Generate Errors to See Burn Rate

```powershell
# Generate burst of errors
Write-Host "🔥 Generating errors to test burn rate panels..." -ForegroundColor Yellow
1..500 | % { 
    try { Invoke-WebRequest "http://localhost:8003/debug/500" -UseBasicParsing | Out-Null } 
    catch { }
    if ($_ % 50 -eq 0) { Write-Host "  Sent $_..." -ForegroundColor Gray }
}

Write-Host "`n✅ Errors sent. Check dashboard:" -ForegroundColor Green
Write-Host "   • 1h burn rate should spike immediately" -ForegroundColor Cyan
Write-Host "   • 6h burn rate should gradually increase" -ForegroundColor Cyan
Write-Host "   • 1h uptime gauge should drop" -ForegroundColor Cyan
```

### Test 2: Monitor After Stopping API

```powershell
# Stop API and watch metrics
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop api
Write-Host "📊 Watch dashboard panels:" -ForegroundColor Cyan
Write-Host "   • 1h uptime drops to ~0%" -ForegroundColor Gray
Write-Host "   • Last Alert Fired updates when alert fires" -ForegroundColor Gray

Start-Sleep -Seconds 120

docker compose -f D:\ApplyLens\infra\docker-compose.yml start api
Write-Host "✅ API restarted - uptime recovering" -ForegroundColor Green
```

### Test 3: Check Last Alert Fired

```powershell
# Trigger an alert first (stop API for 70 seconds)
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop api
Start-Sleep -Seconds 70
docker compose -f D:\ApplyLens\infra\docker-compose.yml start api

# Wait a moment, then check
Start-Sleep -Seconds 10
Write-Host "📊 Check 'Last Alert Fired' panel in dashboard" -ForegroundColor Cyan
Write-Host "   Should show ~1-2 minutes ago" -ForegroundColor Gray
```

---

## 🎨 Panel Layout

```
┌─────────────────────────────────────────────────────┐
│ Row 1: Traffic & Performance                        │
│  [HTTP req/s          ] [HTTP latency p50/90/99   ] │
├─────────────────────────────────────────────────────┤
│ Row 2: Business Metrics                             │
│  [Backfill outcomes   ] [Emails inserted rate     ] │
├─────────────────────────────────────────────────────┤
│ Row 3: System Health                                │
│  [Subsystem health    ] [Gmail connected          ] │
├─────────────────────────────────────────────────────┤
│ Row 4: SLO & Alerting                               │
│  [API Uptime 30d      ] [Last Alert Fired    ] [?] │
├─────────────────────────────────────────────────────┤
│ Row 5: SLO Burn Rate (Multi-Window)                 │
│  [Burn Rate 1h        ] [Burn Rate 6h             ] │
├─────────────────────────────────────────────────────┤
│ Row 6: Short-term Health                            │
│  [API Uptime 1h       ]                             │
└─────────────────────────────────────────────────────┘
```

---

## 🔗 Resources & References

### Google SRE Books
- **The Site Reliability Workbook:** Chapter on SLOs and Error Budgets
- **Implementing SLOs:** Multi-window, multi-burn-rate alerting

### Alerting on SLOs
- https://sre.google/workbook/alerting-on-slos/
- Multi-window alerting strategy
- Burn rate thresholds

### PromQL for SLOs
- https://prometheus.io/docs/practices/histograms/
- https://grafana.com/blog/2022/05/10/how-to-visualize-prometheus-histograms-in-grafana/

---

## 🛠️ Next Steps

### 1. Add Burn Rate Alerts

Create alerts that fire when burn rate exceeds thresholds:

```yaml
# infra/prometheus/alerts.yml
- alert: FastBurnRate
  expr: |
    (sum(rate(applylens_http_requests_total{status=~"5.."}[1h])) / 
     sum(rate(applylens_http_requests_total[1h]))) / 0.001 > 14.4
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Critical error budget burn (14.4× in 1h)"

- alert: SustainedBurnRate
  expr: |
    (sum(rate(applylens_http_requests_total{status=~"5.."}[6h])) / 
     sum(rate(applylens_http_requests_total[6h]))) / 0.001 > 6
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "Sustained error budget burn (6× in 6h)"
```

### 2. Error Budget Tracking Panel

Add a panel showing remaining error budget:

```json
{
  "title": "Error Budget Remaining (30d)",
  "expr": "((0.001 * 30 * 24 * 60 * 60) - sum(increase(applylens_http_requests_total{status=~\"5..\"}[30d]))) / (sum(increase(applylens_http_requests_total[30d])) * 0.001) * 100"
}
```

### 3. Latency SLO

Add latency-based SLO (e.g., p99 < 500ms):

```json
{
  "title": "Latency SLO (p99 < 500ms)",
  "expr": "(histogram_quantile(0.99, sum(rate(applylens_http_request_duration_seconds_bucket[1h])) by (le)) < 0.5) * 100"
}
```

---

## 📚 Files Modified

**1. infra/grafana/provisioning/dashboards/json/applylens-overview.json**
- Added 4 new panels (total now: 11 panels)
- Added SLO burn rate monitoring (1h + 6h windows)
- Added last alert fired tracking
- Added short-term uptime gauge

---

**✅ Advanced SLO monitoring successfully deployed!**

Your dashboard now includes Google SRE-style multi-window burn rate alerting, giving you both fast detection (1h) and stable monitoring (6h) to balance speed and accuracy in incident response.

🎉 **Production-grade SRE monitoring is complete!**
