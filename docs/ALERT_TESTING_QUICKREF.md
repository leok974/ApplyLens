# 🚨 Alert Testing Quick Reference

## ⚡ Instant Verification (30 seconds)

```powershell
# Check everything is working
Write-Host "`n🔍 Quick Health Check`n" -ForegroundColor Cyan

# 1. Prometheus → API
$target = (irm http://localhost:9090/api/v1/targets).data.activeTargets | ? {$_.labels.job -eq "applylens-api"}
Write-Host "Prometheus → API: " -NoNewline; if ($target.health -eq "up") { Write-Host "✅ UP" -ForegroundColor Green } else { Write-Host "❌ DOWN" -ForegroundColor Red }

# 2. Alert rules loaded
$ruleCount = (docker logs infra-grafana 2>&1 | Select-String "rule_uid=applens").Count
Write-Host "Alert Rules: " -NoNewline; Write-Host "✅ $ruleCount evaluating" -ForegroundColor Green

# 3. Debug endpoint
try { iwr http://localhost:8003/debug/500 -UseBasicParsing 2>$null } catch { if ($_.Exception.Response.StatusCode -eq 500) { Write-Host "Debug /500: ✅ Working" -ForegroundColor Green } }

Write-Host "`n✅ All systems ready for testing!`n" -ForegroundColor Green
```

---

## 🎧 Start Webhook Listener (NEW)

**In a separate terminal:**

```powershell
python D:\ApplyLens\tools\grafana_webhook.py
```

**What it does:**

- Listens on port 9000
- Receives alert notifications from Grafana
- Pretty-prints alert payloads to console
- Perfect for testing contact points

---

## 🧪 Test Alerts (3 Quick Tests)

### Test 1: API Down Alert (90 seconds)

```powershell
# Stop → Wait → Check → Restart
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop api
Start-Sleep -Seconds 70
start http://localhost:3000/alerting/list
docker compose -f D:\ApplyLens\infra\docker-compose.yml start api
```

**Expected:** Alert fires after 1 minute, webhook receives notification

---

### Test 2: High Error Rate Alert (NEW - 7 minutes)

```powershell
# Generate 200 errors using new debug endpoint
1..200 | % { 
    curl http://localhost:8003/debug/500 2>$null 
    if ($_ % 40 -eq 0) { Write-Host "Sent $_..." }
}
Write-Host "✅ Errors sent. Wait ~5 minutes for alert." -ForegroundColor Green
```

**Expected:** Alert fires after 5 minutes of sustained >5% error rate

---

### Test 3: Backfill Errors Alert (12 minutes)

```powershell
# Stop ES → Call backfill → Restart ES
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop es
Start-Sleep -Seconds 5
try { iwr "http://localhost:8003/gmail/backfill?days=2" -Method POST -UseBasicParsing } catch { Write-Host "✓ Failed as expected" }
docker compose -f D:\ApplyLens\infra\docker-compose.yml start es
Write-Host "✅ Error recorded. Wait ~10 minutes for alert." -ForegroundColor Green
```

**Expected:** Alert fires after 10 minutes of errors detected

---

## 🔥 Rapid Fire Test (All 3 at Once)

```powershell
# Start webhook listener first!
# Then run this in another terminal:

Write-Host "🔥 RAPID FIRE ALERT TEST`n" -ForegroundColor Red

# 1. Backfill errors (fire in 10m)
Write-Host "1️⃣  Triggering backfill error..." -ForegroundColor Yellow
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop es
Start-Sleep -Seconds 3
try { iwr "http://localhost:8003/gmail/backfill?days=2" -Method POST -UseBasicParsing } catch {}
docker compose -f D:\ApplyLens\infra\docker-compose.yml start es

# 2. HTTP error rate (fire in 5m)
Write-Host "`n2️⃣  Generating HTTP 5xx burst..." -ForegroundColor Yellow
1..200 | % { curl http://localhost:8003/debug/500 2>$null }

# 3. API down (fire in 1m)
Write-Host "`n3️⃣  Stopping API..." -ForegroundColor Yellow
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop api
Start-Sleep -Seconds 70

Write-Host "`n✅ Restarting API..." -ForegroundColor Green
docker compose -f D:\ApplyLens\infra\docker-compose.yml start api

Write-Host "`n📊 Expected timeline:" -ForegroundColor Cyan
Write-Host "   • T+1m:  API Down alert fires 🔥" -ForegroundColor Gray
Write-Host "   • T+5m:  High Error Rate alert fires 🔥" -ForegroundColor Gray
Write-Host "   • T+10m: Backfill Errors alert fires 🔥" -ForegroundColor Gray
Write-Host "`nWatch: http://localhost:3000/alerting/list`n" -ForegroundColor White
```

---

## 📞 Test Contact Point (No Alert Needed)

```powershell
# 1. Start webhook listener
python D:\ApplyLens\tools\grafana_webhook.py

# 2. In browser, go to:
start http://localhost:3000/alerting/notifications

# 3. Click "Default" → "Test" button
# 4. Check webhook terminal for payload
```

---

## 📊 Check Metrics in Real-Time

```powershell
# HTTP request rate
irm "http://localhost:9090/api/v1/query?query=rate(applylens_http_requests_total[5m])" | % data | % result | % value

# Error rate percentage
$errorRate = irm "http://localhost:9090/api/v1/query?query=(sum(rate(applylens_http_requests_total%7Bstatus=~%225..%22%7D%5B5m%5D))/sum(rate(applylens_http_requests_total%5B5m%5D)))*100"
Write-Host "Error Rate: $([math]::Round($errorRate.data.result[0].value[1], 2))%" -ForegroundColor Yellow

# Backfill errors
irm "http://localhost:9090/api/v1/query?query=applylens_backfill_requests_total{result=`"error`"}" | % data | % result | % value
```

---

## 🔄 Hot Reload (No Restart!)

```powershell
# Edit alert rules
notepad D:\ApplyLens\infra\prometheus\alerts.yml

# Reload (instant)
iwr -Method POST http://localhost:9090/-/reload
Write-Host "✅ Prometheus reloaded" -ForegroundColor Green
```

---

## 🛠️ New Tools Added

| Tool | Location | Purpose |
|------|----------|---------|
| **Debug /500 endpoint** | `GET /debug/500` | Generate 500 errors for testing |
| **Webhook listener** | `tools/grafana_webhook.py` | Receive & display alert notifications |
| **Testing guide** | `ALERT_TESTING_GUIDE.md` | Complete testing documentation |
| **This card** | `ALERT_TESTING_QUICKREF.md` | Quick copy-paste commands |

---

## 🔗 Essential URLs

```
Prometheus:          http://localhost:9090
Grafana Alerts:      http://localhost:3000/alerting/list
Contact Points:      http://localhost:3000/alerting/notifications
Notification Routes: http://localhost:3000/alerting/routes
API Metrics:         http://localhost:8003/metrics
Debug 500 Endpoint:  http://localhost:8003/debug/500
```

---

## 🎯 One-Liner Tests

```powershell
# Test API Down
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop api; Start-Sleep -Seconds 70; docker compose -f D:\ApplyLens\infra\docker-compose.yml start api

# Test High Error Rate
1..200 | % { curl http://localhost:8003/debug/500 2>$null }

# Test Backfill Errors
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop es; try { iwr "http://localhost:8003/gmail/backfill?days=2" -Method POST } catch {}; docker compose -f D:\ApplyLens\infra\docker-compose.yml start es

# Check all alert states
(irm http://localhost:9090/api/v1/rules).data.groups.rules | ? name -like "ApplyLens*" | select name, state, health | ft
```

---

**Ready to test!** Start the webhook listener, then trigger alerts! 🚀
