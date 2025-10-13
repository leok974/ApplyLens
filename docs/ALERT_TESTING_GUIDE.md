# 🧪 Alert Testing & Verification Guide

## Quick Verification Commands

### 1. Check Prometheus Target Health

```powershell
# Verify Prometheus can scrape the API
Invoke-RestMethod http://localhost:9090/api/v1/targets `
| % data | % activeTargets `
| ? {$_.labels.job -eq "applylens-api"} `
| Format-Table scrapeUrl, lastScrape, health, lastError
```

**Expected Output:**

```
scrapeUrl               lastScrape                    health lastError
---------               ----------                    ------ ---------
http://api:8003/metrics 2025-10-09T14:10:46.753...    up
```

### 2. Check Grafana Alert Rules

```powershell
# Verify rules are loaded via Grafana API
$cred = New-Object PSCredential("admin",(ConvertTo-SecureString "admin" -AsPlainText -Force))

# List all provisioned alert rules
Invoke-RestMethod -Uri http://localhost:3000/api/v1/provisioning/alert-rules -Credential $cred `
| Select-Object title, folderUID, @{Name='Severity';Expression={$_.labels.severity}} `
| Format-Table
```

### 3. Check Alert Rule States

```powershell
# Check current alert states (Normal/Pending/Firing)
$cred = New-Object PSCredential("admin",(ConvertTo-SecureString "admin" -AsPlainText -Force))
Invoke-RestMethod -Uri http://localhost:3000/api/prometheus/grafana/api/v1/rules -Credential $cred `
| % data | % groups | % rules `
| Select-Object name, state, @{Name='Health';Expression={$_.health}} `
| Format-Table
```

### 4. Force Prometheus Reload (No Restart)

```powershell
# Hot reload Prometheus configuration after editing alerts.yml
Invoke-WebRequest -Method POST http://localhost:9090/-/reload
Write-Host "✅ Prometheus configuration reloaded" -ForegroundColor Green
```

### 5. Check Grafana Contact Points

```powershell
# List all contact points
$cred = New-Object PSCredential("admin",(ConvertTo-SecureString "admin" -AsPlainText -Force))
Invoke-RestMethod http://localhost:3000/api/v1/provisioning/contact-points -Credential $cred `
| Select-Object name, type, uid `
| Format-Table
```

### 6. Check Notification Policies

```powershell
# View notification routing policy
$cred = New-Object PSCredential("admin",(ConvertTo-SecureString "admin" -AsPlainText -Force))
Invoke-RestMethod http://localhost:3000/api/v1/provisioning/policies -Credential $cred `
| ConvertTo-Json -Depth 5
```

---

## 🧪 Testing Alerts

### Test 1: API Down Alert (Critical)

**Trigger:** Stop the API service  
**Duration:** Fires after 1 minute  
**Severity:** Critical

```powershell
# Stop API
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop api

# Wait for alert to fire (>1 minute)
Write-Host "⏳ Waiting 70 seconds for alert to fire..." -ForegroundColor Yellow
Start-Sleep -Seconds 70

# Check alert status in Grafana
start http://localhost:3000/alerting/list

# Restart API
docker compose -f D:\ApplyLens\infra\docker-compose.yml start api
Write-Host "✅ API restarted - alert should resolve" -ForegroundColor Green
```

**Expected:**

- Alert goes to **Pending** after ~15 seconds (first failed scrape)
- Alert goes to **Firing** after 1 minute
- Notification sent to webhook
- Alert **Resolves** when API comes back up

---

### Test 2: High HTTP Error Rate Alert (Warning)

**Trigger:** Generate burst of 5xx errors  
**Duration:** Fires after 5 minutes of >5% error rate  
**Severity:** Warning

#### Option A: Using Debug Endpoint (Recommended)

```powershell
# Generate 200 errors quickly
Write-Host "🔥 Generating 200 HTTP 500 errors..." -ForegroundColor Yellow
1..200 | % { 
    try { 
        Invoke-WebRequest "http://localhost:8003/debug/500" -UseBasicParsing -ErrorAction SilentlyContinue | Out-Null 
    } catch { }
    if ($_ % 20 -eq 0) { Write-Host "  Sent $_ requests..." -ForegroundColor Gray }
}

Write-Host "`n✅ Error burst sent. Wait ~5 minutes for alert." -ForegroundColor Green
Write-Host "📊 Check metrics:" -ForegroundColor Cyan
Write-Host "   http://localhost:9090/graph?g0.expr=rate(applylens_http_requests_total%7Bstatus%3D~%225..%22%7D%5B5m%5D)&g0.tab=0" -ForegroundColor Gray

# Optional: Keep generating errors to sustain high rate
Write-Host "`n🔁 (Optional) Run this to sustain errors:" -ForegroundColor Yellow
Write-Host '   1..300 | % { try { Invoke-WebRequest "http://localhost:8003/debug/500" -UseBasicParsing | Out-Null } catch {}; Start-Sleep -Milliseconds 500 }' -ForegroundColor Gray
```

#### Option B: Stop API While Sending Requests

```powershell
# Start background job sending requests
$job = Start-Job { 
    1..300 | % { 
        try { 
            Invoke-WebRequest http://localhost:8003/healthz -UseBasicParsing | Out-Null 
        } catch { }
        Start-Sleep -Milliseconds 900 
    } 
}

# Wait a bit, then stop API (causes connection errors)
Start-Sleep -Seconds 5
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop api

# Wait 10 seconds
Start-Sleep -Seconds 10

# Restart API
docker compose -f D:\ApplyLens\infra\docker-compose.yml start api

# Clean up job
Receive-Job $job | Out-Null
Remove-Job $job
```

**Expected:**

- Error rate metric shows >5% for 5 minutes
- Alert goes to **Firing** after 5 minutes
- Notification sent to webhook

---

### Test 3: Backfill Errors Alert (Warning)

**Trigger:** Backfill request fails due to ES being down  
**Duration:** Fires after 10 minutes of errors  
**Severity:** Warning

```powershell
# Stop Elasticsearch
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop es
Write-Host "🛑 Elasticsearch stopped" -ForegroundColor Yellow

# Wait for ES to be fully down
Start-Sleep -Seconds 5

# Attempt backfill (will fail without ES)
Write-Host "📧 Attempting backfill (will fail)..." -ForegroundColor Cyan
try { 
    Invoke-WebRequest "http://localhost:8003/gmail/backfill?days=2" `
        -Method POST `
        -UseBasicParsing `
        -ErrorAction Stop 
} catch {
    Write-Host "✓ Backfill failed as expected: $($_.Exception.Message)" -ForegroundColor Gray
}

# Check the backfill error metric
Start-Sleep -Seconds 2
$errorMetric = Invoke-RestMethod "http://localhost:9090/api/v1/query?query=applylens_backfill_requests_total{result=`"error`"}"
Write-Host "`n📊 Backfill errors: $($errorMetric.data.result[0].value[1])" -ForegroundColor Cyan

# Restart Elasticsearch
docker compose -f D:\ApplyLens\infra\docker-compose.yml start es
Write-Host "`n✅ Elasticsearch restarted" -ForegroundColor Green
Write-Host "⏳ Alert will fire after 10 minutes of sustained errors" -ForegroundColor Yellow
```

**Expected:**

- Backfill request returns error
- `applylens_backfill_requests_total{result="error"}` increments
- Alert fires after 10 minutes if errors persist

---

## 🎧 Webhook Listener Setup

### Start the Webhook Listener

```powershell
# Start the listener (keeps running)
python D:\ApplyLens\tools\grafana_webhook.py
```

**Output:**

```
======================================================================
🎧 GRAFANA WEBHOOK LISTENER
======================================================================

✓ Listening on http://0.0.0.0:9000/webhook
✓ Health check: http://localhost:9000/

Configured in Grafana contact point as:
  http://host.docker.internal:9000/webhook

Press Ctrl+C to stop
======================================================================
```

### Test the Webhook from Grafana

1. Keep the webhook listener running
2. Open Grafana: <http://localhost:3000/alerting/notifications>
3. Click **Default** contact point
4. Click **Test** button
5. Check your terminal - you should see the test alert payload

**Example Output:**

```
======================================================================
🚨 GRAFANA ALERT RECEIVED - 2025-10-09 14:30:15
======================================================================

🔥 Status: FIRING

📊 Alerts (1):

  Alert #1:
    Labels: {"alertname": "TestAlert", "severity": "info"}
    Annotations: {"summary": "Test notification"}
    Status: firing
    Started: 2025-10-09T14:30:15Z

📦 Full Payload:
{
  "status": "firing",
  "alerts": [...]
}
======================================================================
```

### Test with Real Alert

```powershell
# In one terminal: Start webhook listener
python D:\ApplyLens\tools\grafana_webhook.py

# In another terminal: Trigger an alert
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop api
Start-Sleep -Seconds 70

# Watch webhook listener terminal for notification
# Then restart API
docker compose -f D:\ApplyLens\infra\docker-compose.yml start api
```

---

## 📊 Useful PromQL Queries

### HTTP Request Rate

```promql
# Overall request rate
sum(rate(applylens_http_requests_total[5m]))

# By status code
sum by (status_code) (rate(applylens_http_requests_total[5m]))

# Error rate percentage
(sum(rate(applylens_http_requests_total{status=~"5.."}[5m]))
 / sum(rate(applylens_http_requests_total[5m]))) * 100
```

### Backfill Metrics

```promql
# Backfill request rate by result
sum by (result) (rate(applylens_backfill_requests_total[5m]))

# Total errors in last 10 minutes
increase(applylens_backfill_requests_total{result="error"}[10m])

# Success rate
rate(applylens_backfill_requests_total{result="success"}[5m])
```

### System Health

```promql
# Database status
applylens_db_up

# Elasticsearch status
applylens_es_up

# Gmail connected users
sum(applylens_gmail_connected)
```

---

## 🔧 Advanced Testing

### Simulate Alert Flapping

```powershell
# Rapidly start/stop API to test alert behavior
1..5 | % {
    Write-Host "Cycle $_/5" -ForegroundColor Cyan
    docker compose -f D:\ApplyLens\infra\docker-compose.yml stop api
    Start-Sleep -Seconds 30
    docker compose -f D:\ApplyLens\infra\docker-compose.yml start api
    Start-Sleep -Seconds 45
}
```

### Generate Mixed Traffic

```powershell
# Mix of successful and failed requests
$job = Start-Job {
    1..500 | % {
        # Successful request
        if ($_ % 3 -ne 0) {
            try { Invoke-WebRequest "http://localhost:8003/healthz" -UseBasicParsing | Out-Null } catch {}
        }
        # Failed request
        else {
            try { Invoke-WebRequest "http://localhost:8003/debug/500" -UseBasicParsing | Out-Null } catch {}
        }
        Start-Sleep -Milliseconds 200
    }
}

Write-Host "🔁 Generating mixed traffic (500 requests over ~100 seconds)..." -ForegroundColor Cyan
Write-Host "   ~67% success, ~33% errors" -ForegroundColor Gray
Wait-Job $job | Out-Null
Receive-Job $job | Out-Null
Remove-Job $job
Write-Host "✅ Traffic generation complete" -ForegroundColor Green
```

### Check Alert Evaluation Timing

```powershell
# See when alerts last evaluated
$cred = New-Object PSCredential("admin",(ConvertTo-SecureString "admin" -AsPlainText -Force))
Invoke-RestMethod -Uri http://localhost:3000/api/prometheus/grafana/api/v1/rules -Credential $cred `
| % data | % groups | % rules `
| Select-Object name, state, evaluationTime, lastEvaluation `
| Format-Table
```

---

## 🔍 Troubleshooting

### Alert Not Firing

```powershell
# Check if metric exists
$metric = "applylens_http_requests_total"
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=$metric" `
| % data | % result

# Check alert rule expression
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=up{job=`"applylens-api`"}" `
| % data | % result | % value
```

### Webhook Not Receiving Notifications

```powershell
# Test webhook manually
$payload = @{
    status = "firing"
    alerts = @(
        @{
            labels = @{ alertname = "TestAlert"; severity = "info" }
            annotations = @{ summary = "Manual test" }
        }
    )
} | ConvertTo-Json

Invoke-WebRequest -Method POST `
    -Uri "http://localhost:9000/webhook" `
    -ContentType "application/json" `
    -Body $payload
```

### Check Grafana Alerting Logs

```powershell
# View recent alerting activity
docker logs infra-grafana --tail 50 2>&1 | Select-String "alert|notif|eval"

# Follow logs in real-time
docker logs infra-grafana --follow 2>&1 | Select-String "alert|notif|eval"
```

### Verify Contact Point Configuration

```powershell
# Check contact point details
$cred = New-Object PSCredential("admin",(ConvertTo-SecureString "admin" -AsPlainText -Force))
Invoke-RestMethod http://localhost:3000/api/v1/provisioning/contact-points -Credential $cred `
| ConvertTo-Json -Depth 10
```

---

## 🛡️ Hardening for Production

### 1. Change Grafana Admin Password

**Option A: Environment Variable (docker-compose.yml)**

```yaml
grafana:
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=your-secure-password-here
```

**Option B: Via Grafana UI**

```
1. Login: http://localhost:3000 (admin/admin)
2. Click profile → Change password
3. Enter new password
```

### 2. Restrict Metrics Endpoint

Add authentication to `/metrics` endpoint (in production):

```python
# services/api/app/main.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

def verify_metrics_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify metrics endpoint credentials"""
    correct_username = secrets.compare_digest(credentials.username, "prometheus")
    correct_password = secrets.compare_digest(credentials.password, os.getenv("METRICS_PASSWORD", "changeme"))
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

@app.get("/metrics", dependencies=[Depends(verify_metrics_auth)])
def metrics():
    """Expose Prometheus metrics (authenticated)"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

Then update Prometheus config:

```yaml
# infra/prometheus/prometheus.yml
scrape_configs:
  - job_name: applylens-api
    static_configs:
      - targets: ['api:8003']
    basic_auth:
      username: prometheus
      password: your-secure-password
```

### 3. Reduce Label Cardinality

For multi-user systems, hash or use internal user IDs instead of emails:

```python
# Instead of:
GMAIL_CONNECTED.labels(user_email=user.email).set(1)

# Use:
import hashlib
user_hash = hashlib.sha256(user.email.encode()).hexdigest()[:8]
GMAIL_CONNECTED.labels(user_id=user_hash).set(1)
```

### 4. Set Up HTTPS for Grafana

```yaml
# infra/docker-compose.yml
grafana:
  environment:
    - GF_SERVER_PROTOCOL=https
    - GF_SERVER_CERT_FILE=/etc/grafana/ssl/cert.pem
    - GF_SERVER_CERT_KEY=/etc/grafana/ssl/key.pem
  volumes:
    - ./grafana/ssl:/etc/grafana/ssl:ro
```

### 5. Configure Real Notification Channels

Replace webhook with production channels (see `GRAFANA_ALERTING_SETUP.md`):

- **Slack:** Use Incoming Webhooks
- **Email:** Configure SMTP settings
- **PagerDuty:** For critical alerts
- **Microsoft Teams:** For team notifications

---

## 📚 Reference URLs

- **Prometheus Targets:** <http://localhost:9090/targets>
- **Prometheus Rules:** <http://localhost:9090/rules>
- **Prometheus Graph:** <http://localhost:9090/graph>
- **Grafana Alerts:** <http://localhost:3000/alerting/list>
- **Grafana Contact Points:** <http://localhost:3000/alerting/notifications>
- **Grafana Notification Policies:** <http://localhost:3000/alerting/routes>
- **API Metrics:** <http://localhost:8003/metrics>
- **API Health:** <http://localhost:8003/healthz>
- **API Readiness:** <http://localhost:8003/readiness>
- **Debug 500:** <http://localhost:8003/debug/500> (testing only)

---

## 🎯 Quick Test Checklist

- [ ] Prometheus scraping API (`/api/v1/targets`)
- [ ] Grafana rules loaded (`/api/v1/provisioning/alert-rules`)
- [ ] Webhook listener running (`python tools/grafana_webhook.py`)
- [ ] Test contact point in Grafana UI (should see webhook payload)
- [ ] Trigger API Down alert (stop/start API)
- [ ] Trigger High Error Rate alert (spam `/debug/500`)
- [ ] Trigger Backfill Errors alert (stop ES, call backfill)
- [ ] Verify notifications arrive at webhook
- [ ] Check alerts resolve when conditions clear
- [ ] Test Prometheus hot reload (`POST /-/reload`)

---

**✅ All verification and testing tools are ready!**

Run `python D:\ApplyLens\tools\grafana_webhook.py` to start receiving alert notifications locally! 🎉
