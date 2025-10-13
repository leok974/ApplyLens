# 🔥 SLO Burn Rate Alerts Added

**Date:** October 9, 2025  
**Status:** ✅ Complete

---

## 🚨 What Was Added

Added **2 production-grade SLO burn rate alerts** following Google SRE multi-window alerting patterns for a **99.9% availability SLO**.

These alerts detect when you're consuming your error budget too quickly, giving you early warning before SLO breaches.

---

## 📋 New Alert Rules

### 1. SLO Burn Rate Fast (1h > 14.4×)

**File:** `infra/grafana/provisioning/alerting/rules-applylens.yaml`

**Alert Details:**

- **UID:** `applens_burn_fast_1h`
- **Title:** SLO burn rate high (1h > 14.4x)
- **Severity:** critical 🔴
- **Window:** 1 hour
- **Threshold:** Burn rate > 14.4×
- **Duration:** Fires after 5 minutes
- **Purpose:** Quick detection of sharp spikes that will deplete error budget rapidly

**Query:**

```promql
(sum(rate(applylens_http_requests_total{status=~"5.."}[1h]))
 / sum(rate(applylens_http_requests_total[1h]))) / 0.001
```text

**What It Means:**

- **14.4× burn rate** = Consuming error budget 14.4 times faster than sustainable
- If sustained, **depletes 30-day budget in ~2 days**
- **Critical alert** - requires immediate investigation

**When It Fires:**

- Sustained 5xx error rate spike
- API returning errors for significant portion of traffic
- Incident requiring immediate response

---

### 2. SLO Burn Rate Slow (6h > 6×)

**File:** `infra/grafana/provisioning/alerting/rules-applylens.yaml`

**Alert Details:**

- **UID:** `applens_burn_slow_6h`
- **Title:** SLO burn rate high (6h > 6x)
- **Severity:** warning ⚠️
- **Window:** 6 hours
- **Threshold:** Burn rate > 6×
- **Duration:** Fires after 30 minutes
- **Purpose:** Catch sustained degradation; resistant to noise

**Query:**

```promql
(sum(rate(applylens_http_requests_total{status=~"5.."}[6h]))
 / sum(rate(applylens_http_requests_total[6h]))) / 0.001
```text

**What It Means:**

- **6× burn rate** = Consuming error budget 6 times faster than sustainable
- If sustained, **depletes 30-day budget in ~5 days**
- **Warning alert** - investigate and plan mitigation

**When It Fires:**

- Elevated error rates over hours (not just spike)
- Sustained degradation
- Potential systemic issue

---

## 🎯 Understanding Burn Rate Alerts

### Error Budget for 99.9% SLO

- **Uptime target:** 99.9% (3 nines)
- **Allowed downtime:** 0.1% = **43.2 minutes per 30 days**
- **Allowed error rate:** 0.001 (0.1%)

### What is Burn Rate?

Burn rate = **Current error rate ÷ Allowed error rate**

| Burn Rate | Error Rate | Budget Depletes In | Severity |
|-----------|------------|-------------------|----------|
| 1× | 0.1% | 30 days (on track) | ✅ Normal |
| 6× | 0.6% | 5 days | ⚠️ Warning |
| 14.4× | 1.44% | 2 days | 🔴 Critical |
| 100× | 10% | 7 hours | 🔥 Page immediately |

### Multi-Window Strategy

**Why use both 1h and 6h windows?**

```text
Fast Window (1h):
  ✅ Detects incidents quickly (within an hour)
  ❌ Sensitive to short spikes/noise
  ❌ Can cause false alarms

Slow Window (6h):
  ✅ Stable, resists false positives
  ✅ Confirms sustained issues
  ❌ Slower to detect new incidents

Best Practice: Use BOTH
  → 1h catches sharp spikes (page immediately)
  → 6h confirms sustained issues (investigate)
```text

---

## 🧮 Burn Rate Math

### Calculation

```text
Burn Rate = (Current Error Rate) / (Allowed Error Rate)

For 99.9% SLO:
  Allowed Error Rate = 0.001 (0.1%)

Example:
  If 5xx rate = 1.44% (0.0144)
  Burn Rate = 0.0144 / 0.001 = 14.4×
```text

### Threshold Selection

**14.4× (1h window):**

- At this rate, you deplete 30-day budget in **50 hours** (~2 days)
- Standard Google SRE threshold for fast-window paging
- Fires after 5 minutes to reduce false positives

**6× (6h window):**

- At this rate, you deplete 30-day budget in **5 days**
- Catches sustained issues before budget fully depleted
- Fires after 30 minutes for stability

### Budget Depletion Time

```text
Time to deplete = 30 days / burn_rate

Examples:
  6× burn   → 30 / 6   = 5 days
  14.4× burn → 30 / 14.4 = 2.08 days
  100× burn  → 30 / 100  = 0.3 days = 7.2 hours
```text

---

## 🧪 Testing the Alerts

### Test Setup

Make sure your webhook listener is running to see notifications:

```powershell
# Terminal 1: Start webhook listener
python D:\ApplyLens\tools\grafana_webhook.py
```text

### Test 1: Trigger Fast Burn Rate Alert (1h)

Generate sustained errors over 5+ minutes:

```powershell
# Terminal 2: Generate error burst
Write-Host "🔥 Generating high error rate (400 requests over 100 seconds)..." -ForegroundColor Yellow
1..400 | % { 
    try { 
        Invoke-WebRequest "http://localhost:8003/debug/500" -UseBasicParsing | Out-Null 
    } catch { }
    Start-Sleep -Milliseconds 250
    if ($_ % 40 -eq 0) { Write-Host "  Sent $_..." -ForegroundColor Gray }
}

Write-Host "`n✅ Error burst sent. Timeline:" -ForegroundColor Green
Write-Host "   T+1m: 1h burn rate panel starts climbing" -ForegroundColor Cyan
Write-Host "   T+5m: Fast burn alert fires (if rate sustained)" -ForegroundColor Red
Write-Host "   T+30m: Slow burn alert fires (if rate sustained)" -ForegroundColor Yellow
Write-Host "`nWatch:" -ForegroundColor Cyan
Write-Host "   • Dashboard: http://localhost:3000/d/applylens-overview" -ForegroundColor White
Write-Host "   • Alerts: http://localhost:3000/alerting/list" -ForegroundColor White
Write-Host "   • Webhook listener terminal for notifications`n" -ForegroundColor White
```text

**Expected Behavior:**

1. **Immediately:** 1h burn rate panel spikes
2. **After 5 min:** Fast burn rate alert goes to **Firing** (if sustained)
3. **Webhook listener:** Receives critical alert notification
4. **After 30 min:** Slow burn rate alert goes to **Firing** (if sustained)

### Test 2: Monitor Recovery

```powershell
# Stop generating errors
Write-Host "🛑 Stopped error generation" -ForegroundColor Green
Write-Host "⏳ Watch burn rate decay..." -ForegroundColor Cyan
Write-Host "   • 1h panel drops gradually as 1h window ages out errors" -ForegroundColor Gray
Write-Host "   • 6h panel drops slower (longer memory)" -ForegroundColor Gray
Write-Host "   • Alerts resolve when burn rate drops below threshold`n" -ForegroundColor Gray
```text

### Test 3: Check Alert States

```powershell
# Via API
$cred = New-Object PSCredential("admin",(ConvertTo-SecureString "admin" -AsPlainText -Force))
$rules = Invoke-RestMethod -Uri http://localhost:3000/api/v1/provisioning/alert-rules -Credential $cred
$rules | Where-Object { $_.title -like "*burn*" } | Select-Object title, uid, @{Name='Severity';Expression={$_.labels.severity}} | Format-Table

# Via Grafana UI
start http://localhost:3000/alerting/list
```text

---

## 🎨 Alert Dashboard Integration

Your dashboard now has **complete SLO monitoring**:

**Panels showing burn rate:**

- **Panel 9:** SLO Burn Rate (1h) timeseries
- **Panel 10:** SLO Burn Rate (6h) timeseries

**Alerts monitoring burn rate:**

- **Alert 5:** SLO burn rate high (1h > 14.4×) [critical]
- **Alert 6:** SLO burn rate high (6h > 6×) [warning]

**Workflow:**

1. **Dashboard panels** show real-time burn rate visualization
2. **Alerts** notify you when burn rate exceeds thresholds
3. **Webhook** receives notifications for on-call response

---

## 📊 Complete Alert Rules Overview

### Grafana Rules (6 Total)

1. ✅ ApplyLens API Down [critical]
2. ✅ High HTTP Error Rate [warning]
3. ✅ Backfill errors detected [warning]
4. ✅ Gmail disconnected (15m) [warning]
5. ✅ **SLO burn rate high (1h > 14.4×) [critical] - NEW!**
6. ✅ **SLO burn rate high (6h > 6×) [warning] - NEW!**

### Prometheus Rules (6 Total)

7. ✅ ApplyLensApiDown [critical]
8. ✅ HighHttpErrorRate [warning]
9. ✅ BackfillFailing [warning]
10. ✅ BackfillRateLimitedSpike [info]
11. ✅ GmailDisconnected [warning]
12. ✅ DependenciesDown [critical]

**Total: 12 alert rules** covering all critical aspects of your service!

---

## 🔧 Tuning Your Alerts

### Adjusting for Low Traffic

If you have low traffic, burn rate can be noisy. Consider:

```yaml
# Increase 'for' duration
for: 10m  # Instead of 5m for fast alert
for: 1h   # Instead of 30m for slow alert
```text

### Adjusting for Different SLO

**For 99.5% SLO:**

```yaml
# Change divisor from 0.001 to 0.005
expr: |
  (sum(rate(applylens_http_requests_total{status=~"5.."}[1h]))
   / sum(rate(applylens_http_requests_total[1h]))) / 0.005
```text

**For 99.95% SLO:**

```yaml
# Change divisor from 0.001 to 0.0005
expr: |
  (sum(rate(applylens_http_requests_total{status=~"5.."}[1h]))
   / sum(rate(applylens_http_requests_total[1h]))) / 0.0005
```text

### Adjusting Burn Rate Thresholds

Common thresholds for different SLOs:

| SLO | Fast Window | Slow Window |
|-----|-------------|-------------|
| 99% | 10× (1h) | 5× (6h) |
| 99.5% | 12× (1h) | 5.5× (6h) |
| 99.9% | 14.4× (1h) | 6× (6h) |
| 99.95% | 15× (1h) | 6.5× (6h) |

---

## 📚 SRE Resources

### Google SRE Books

- **Site Reliability Engineering:** Chapter on SLIs, SLOs, and Error Budgets
- **The Site Reliability Workbook:** Chapter 2 - Implementing SLOs
- **Alerting on SLOs:** <https://sre.google/workbook/alerting-on-slos/>

### Key Concepts

**Multi-window alerting:**

- Multiple time windows provide balance between speed and accuracy
- Fast window catches incidents quickly
- Slow window confirms sustained issues

**Burn rate vs. error rate:**

- Error rate: absolute percentage of errors
- Burn rate: relative to your SLO target
- Burn rate normalizes across different SLO targets

**Error budget policies:**

- Define actions at different budget consumption levels
- Example: 50% budget consumed → freeze feature launches
- Example: 10% budget remaining → all hands on reliability

---

## 🛠️ Next Steps

### 1. Set Up Error Budget Dashboard

Create a panel showing remaining error budget:

```promql
# Error budget remaining (days)
30 - (30 * (sum(increase(applylens_http_requests_total{status=~"5.."}[30d])) / sum(increase(applylens_http_requests_total[30d])) / 0.001))
```text

### 2. Add Latency-Based SLO

Track p99 latency SLO (e.g., 99% of requests < 500ms):

```yaml
- alert: LatencySLOBreach
  expr: |
    histogram_quantile(0.99, 
      sum(rate(applylens_http_request_duration_seconds_bucket[1h])) by (le)
    ) > 0.5
  for: 5m
```text

### 3. Create Runbook Links

Add runbook links to alert annotations:

```yaml
annotations:
  summary: "SLO burn rate high (fast window)"
  description: "1h burn rate > 14.4×. See runbook."
  runbook_url: "https://wiki.example.com/runbooks/slo-burn-rate"
```text

### 4. Set Up On-Call Integration

Configure PagerDuty or similar for critical alerts:

```yaml
# infra/grafana/provisioning/alerting/contact-points.yaml
- orgId: 1
  name: PagerDuty
  receivers:
    - uid: pagerduty_oncall
      type: pagerduty
      settings:
        integrationKey: <your-key>
```text

Then route critical severity to PagerDuty:

```yaml
# notification-policies.yaml
routes:
  - receiver: PagerDuty
    object_matchers:
      - [ "severity", "=", "critical" ]
```text

---

## 🎯 Success Metrics

Your SLO alerting system is successful when:

- ✅ Alerts fire **before** users complain
- ✅ Alerts provide **actionable** information
- ✅ False positive rate < 2% (tune thresholds if higher)
- ✅ Mean time to detect (MTTD) < 5 minutes for critical issues
- ✅ Team understands burn rate and can respond appropriately

---

## 📁 Files Modified

**1. infra/grafana/provisioning/alerting/rules-applylens.yaml**

- Added 2 burn rate alert rules
- Total Grafana rules: 6
- Both using multi-window SRE pattern

---

**✅ Production-grade SLO burn rate alerting is complete!**

You now have:

- 🎯 11 dashboard panels (7 original + 4 SLO panels)
- 🚨 12 alert rules (6 Grafana + 6 Prometheus)
- 📊 Multi-window burn rate monitoring (1h + 6h)
- 🔔 Burn rate alerts (fast + slow detection)
- 📚 Complete SRE-style monitoring stack

Your monitoring system now follows **Google SRE best practices** with:

- Error budget tracking
- Multi-window burn rate alerting
- Fast detection with noise resistance
- Clear severity levels and escalation paths

🎉 **Enterprise-grade SRE monitoring complete!**
