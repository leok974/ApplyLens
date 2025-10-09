# 🎉 Gmail Alert & SLO Panel - Added Successfully

**Date:** October 9, 2025  
**Status:** ✅ Complete

---

## What Was Added

### 1. Gmail Disconnected Alert Rule

**File:** `infra/grafana/provisioning/alerting/rules-applylens.yaml`

**Alert Details:**
- **UID:** `applens_gmail_disconnected`
- **Title:** Gmail disconnected (15m)
- **Severity:** warning
- **Condition:** `max_over_time(applylens_gmail_connected[15m]) < 1`
- **Duration:** Fires after 15 minutes
- **Description:** Alerts when `applylens_gmail_connected` has been 0 for the last 15 minutes

**How It Works:**
- Uses `max_over_time()` to check if Gmail was connected at any point in the last 15 minutes
- If the max value is less than 1 (meaning always 0), the alert fires
- Evaluates every 1 minute (interval: 1m)
- Uses Grafana's reduce + threshold expression model

**Query Chain:**
1. **Query A:** `max_over_time(applylens_gmail_connected[15m])` - Get max value over 15m window
2. **Expression B:** Reduce to last value
3. **Expression C:** Threshold check if < 1

---

### 2. API Uptime SLO Panel (30 days)

**File:** `infra/grafana/provisioning/dashboards/json/applylens-overview.json`

**Panel Details:**
- **Type:** Gauge
- **Title:** API Uptime (last 30d)
- **Position:** Row 4, x=0, y=22, 8 units wide, 7 units tall
- **Query:** `avg_over_time(up{job="applylens-api"}[30d]) * 100`
- **Unit:** Percent (%)
- **Range:** 0-100%

**Thresholds:**
- 🔴 **Red:** < 95% (Poor uptime)
- 🟠 **Orange:** 95% - 99.9% (Good uptime)
- 🟢 **Green:** > 99.9% (Excellent uptime, 3 nines SLO)

**How It Works:**
- The `up` metric is 1 when Prometheus can successfully scrape the API
- `avg_over_time()` calculates the average over 30 days
- Multiply by 100 to get percentage
- Example: 0.9995 * 100 = 99.95% uptime

**SLO Interpretation:**
- **99.9% (3 nines)** = ~43 minutes downtime per month
- **99.95%** = ~21 minutes downtime per month
- **99.99% (4 nines)** = ~4 minutes downtime per month

---

## Updated Monitoring Stack

### Alert Rules (10 Total)

**Grafana Rules (4):**
1. ✅ ApplyLens API Down [critical] - API unreachable >1m
2. ✅ High HTTP Error Rate [warning] - 5xx >5% for 5m
3. ✅ Backfill errors detected [warning] - Errors in last 10m
4. ✅ **Gmail disconnected (15m) [warning] - NEW!**

**Prometheus Rules (6):**
5. ✅ ApplyLensApiDown [critical] - API down >1m
6. ✅ HighHttpErrorRate [warning] - 5xx >5% for 5m
7. ✅ BackfillFailing [warning] - Backfill errors >10m
8. ✅ BackfillRateLimitedSpike [info] - >10 rate-limits in 15m
9. ✅ GmailDisconnected [warning] - Gmail down >15m
10. ✅ DependenciesDown [critical] - DB or ES down >2m

### Dashboard Panels (7 Total)

1. ✅ HTTP req/s (by method & status)
2. ✅ HTTP latency (p50/p90/p99)
3. ✅ Backfill outcomes (1h bar gauge)
4. ✅ Emails inserted rate
5. ✅ Subsystem health (DB + ES)
6. ✅ Gmail connected per user
7. ✅ **API Uptime (last 30d) SLO Gauge - NEW!**

---

## Testing the Gmail Disconnected Alert

### Scenario 1: No Users Connected

If no users have connected Gmail yet, the alert will fire after 15 minutes:

```promql
# Check current Gmail connected status
applylens_gmail_connected
```

If no results or all values are 0, the alert will fire.

### Scenario 2: User Disconnects Gmail

When a user revokes OAuth access or disconnects:

1. The `/gmail/status` endpoint sets `GMAIL_CONNECTED.labels(user_email=...).set(0)`
2. After 15 minutes of disconnected state, alert fires
3. Webhook receives notification

### Scenario 3: Test the Alert (Manual)

You can't easily simulate this without actually disconnecting OAuth, but you can check the metric:

```powershell
# Check Gmail connected metrics
$gmailMetric = Invoke-RestMethod "http://localhost:9090/api/v1/query?query=applylens_gmail_connected"
$gmailMetric.data.result | ForEach-Object {
    Write-Host "User: $($_.metric.user_email) - Connected: $($_.value[1])"
}

# Check the alert query
$alertQuery = "max_over_time(applylens_gmail_connected[15m])"
$result = Invoke-RestMethod "http://localhost:9090/api/v1/query?query=$alertQuery"
Write-Host "Max Gmail connected over 15m: $($result.data.result[0].value[1])"
```

---

## Verifying the Changes

### Check Alert Rules in Grafana

```powershell
# Via API
$cred = New-Object PSCredential("admin",(ConvertTo-SecureString "admin" -AsPlainText -Force))
$rules = Invoke-RestMethod -Uri http://localhost:3000/api/v1/provisioning/alert-rules -Credential $cred
$rules | Where-Object { $_.uid -eq "applens_gmail_disconnected" } | Select-Object title, uid, folderUID
```

**Or via UI:**
- http://localhost:3000/alerting/list
- Look for "Gmail disconnected (15m)" in the ApplyLens folder

### Check Dashboard Panel

**Via UI:**
- http://localhost:3000/d/applylens-overview
- Scroll to bottom row
- Look for "API Uptime (last 30d)" gauge panel
- Should show ~100% if API has been running continuously

**Note:** For new installations, the 30-day average may not be meaningful until you have 30 days of data. It will show the average of available data.

---

## SLO Best Practices

### Understanding Your SLO

The 30-day uptime gauge helps you:
- Track your availability SLO at a glance
- Quickly identify if you're meeting SLA commitments
- Spot trends in service reliability

### Common SLO Targets

| SLO | Downtime/Month | Use Case |
|-----|----------------|----------|
| 99% | 7.2 hours | Development/testing |
| 99.5% | 3.6 hours | Internal tools |
| 99.9% (3 nines) | 43 minutes | Standard production |
| 99.95% | 21 minutes | High availability |
| 99.99% (4 nines) | 4 minutes | Mission critical |

### Setting Up Error Budgets

Based on your SLO, you can calculate error budget:

```promql
# Error budget remaining (if SLO is 99.9%)
(avg_over_time(up{job="applylens-api"}[30d]) - 0.999) * 100
```

If this is positive, you're meeting your SLO.  
If negative, you've exhausted your error budget.

---

## Files Modified

1. **infra/grafana/provisioning/alerting/rules-applylens.yaml**
   - Added Gmail Disconnected alert rule (4th rule)

2. **infra/grafana/provisioning/dashboards/json/applylens-overview.json**
   - Added API Uptime (30d) SLO gauge panel (7th panel)

---

## Next Steps

### Optional Enhancements

1. **Add more SLO panels:**
   - Request latency SLO (e.g., p95 < 500ms)
   - Error rate SLO (e.g., <1% errors)
   - Backfill success rate SLO

2. **Create SLO alerts:**
   ```yaml
   - alert: SLOBreach
     expr: avg_over_time(up{job="applylens-api"}[30d]) < 0.999
     for: 1h
     annotations:
       summary: "30-day SLO breached (< 99.9%)"
   ```

3. **Add error budget burn rate alerts:**
   - Alert when consuming error budget too fast
   - Helps prevent SLO breaches

4. **Create monthly SLO reports:**
   - Export uptime metrics
   - Generate SLO compliance reports
   - Track SLO trends over time

---

## Troubleshooting

### Gmail Alert Not Firing

```powershell
# Check if metric exists
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=applylens_gmail_connected"

# Check alert evaluation
docker logs infra-grafana 2>&1 | Select-String "applens_gmail_disconnected"
```

### SLO Panel Showing No Data

```powershell
# Check if 'up' metric exists
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=up{job=`"applylens-api`"}"

# For shorter time range (if 30d is too long)
# Edit dashboard panel query to: avg_over_time(up{job="applylens-api"}[7d]) * 100
```

### Panel Not Appearing

- Refresh browser (Ctrl+F5)
- Check panel gridPos doesn't overlap
- Verify dashboard JSON syntax is valid
- Restart Grafana: `docker compose -f D:\ApplyLens\infra\docker-compose.yml restart grafana`

---

**✅ All changes successfully applied and verified!**

Your monitoring stack now includes:
- 10 alert rules (4 Grafana + 6 Prometheus)
- 7 dashboard panels (including new SLO gauge)
- Comprehensive alerting for API health, errors, backfill, and Gmail connectivity
- SLO tracking for service reliability

🎉 **Monitoring is production-ready!**
