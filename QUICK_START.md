# Email Risk v3.1 — Quick Start Guide

**⚡ Fast-track deployment in 5 steps**

---

## Step 1: Restart API (Load Feature Flags Router)

```powershell
cd d:\ApplyLens
docker-compose -f docker-compose.prod.yml restart api

# Wait 30 seconds for startup
Start-Sleep -Seconds 30
```

---

## Step 2: Verify Feature Flags Endpoint

```powershell
# List all flags
curl http://localhost:8003/flags/ | jq

# Expected output:
# {
#   "EmailRiskBanner": { "enabled": true, "rollout_percent": 10 },
#   "EmailRiskDetails": { "enabled": true, "rollout_percent": 10 },
#   "EmailRiskAdvice": { "enabled": true, "rollout_percent": 100 }
# }
```

---

## Step 3: Reload Prometheus (Load Alert Rules)

```powershell
# Reload Prometheus config
curl -X POST http://localhost:9090/-/reload

# Verify alerts loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name=="email_risk_v31")'
```

---

## Step 4: Import Kibana Saved Searches (Manual - 2 minutes)

1. Open http://localhost:5601
2. Navigate to **Stack Management** → **Saved Objects**
3. Click **Import**
4. Select file: `d:\ApplyLens\infra\kibana\saved_searches_v31.ndjson`
5. Click **Import** (allow overwrite if prompted)
6. Verify 8 searches + 1 dashboard imported

---

## Step 5: Execute Soft Launch (10% Rollout)

```powershell
# Ramp EmailRiskBanner to 10%
curl -X POST 'http://localhost:8003/flags/EmailRiskBanner/ramp?to=10' | jq

# Expected output:
# {
#   "flag": "EmailRiskBanner",
#   "from_percent": 10,
#   "to_percent": 10,
#   "timestamp": "2025-10-21T..."
# }

# View audit log
curl http://localhost:8003/flags/EmailRiskBanner/audit | jq
```

---

## Monitoring (First 6 Hours)

### Grafana Dashboard
**URL:** http://localhost:3000/d/email-risk-v31

**Watch for:**
- ✅ P95 Latency < 300ms (green zone)
- ✅ Error Rate < 0.1%
- ✅ Request Rate increasing gradually
- ⚠️ Any red zones or alerts

### Prometheus Metrics
**URL:** http://localhost:9090/graph

**Key queries:**
```promql
# P95 latency
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{path=~".*/risk-advice"}[5m])))

# Error rate
sum(rate(http_requests_total{code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# Risk advice served
rate(applylens_email_risk_served_total[5m])
```

### API Logs
```powershell
# Watch for ramp events and errors
docker logs applylens-api-prod --tail 50 -f | Select-String -Pattern "flag_ramp|risk-advice|Error"
```

---

## Staged Rollout Schedule

| Stage | Percentage | When | Hold Time | Go/No-Go Criteria |
|-------|-----------|------|-----------|-------------------|
| **Stage 1** | 10% | Now | 6 hours | P95 < 300ms, Error rate < 0.1% |
| **Stage 2** | 25% | T+24h | 12 hours | No P1 incidents, metrics stable |
| **Stage 3** | 50% | T+72h | 24 hours | User feedback < 10% negative |
| **Stage 4** | 100% | T+168h (Day 7) | Ongoing | All SLOs met for 48h |

### Ramp Commands

```powershell
# Stage 2 (after 24h)
curl -X POST 'http://localhost:8003/flags/EmailRiskBanner/ramp?to=25' | jq

# Stage 3 (after 72h)
curl -X POST 'http://localhost:8003/flags/EmailRiskBanner/ramp?to=50' | jq

# Stage 4 (after 7 days)
curl -X POST 'http://localhost:8003/flags/EmailRiskBanner/ramp?to=100' | jq
```

---

## Emergency Rollback

**If P95 > 500ms or Error Rate > 1%:**

```powershell
# IMMEDIATE: Disable feature flag (< 1 minute)
curl -X POST 'http://localhost:8003/flags/EmailRiskBanner/disable' | jq

# Verify disabled
curl http://localhost:8003/flags/EmailRiskBanner | jq

# Check impact (should see request rate drop)
curl http://localhost:8003/metrics | Select-String -Pattern "applylens_email_risk_served_total"
```

**Then:** Follow rollback procedure in `RELEASE_CHECKLIST.md` → Rollback Procedure section.

---

## Health Checks (Every 30 Minutes)

```powershell
# Quick health check script
$p95 = (curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,sum(rate(http_request_duration_seconds_bucket{path=~".*risk-advice"}[5m]))by(le))' | ConvertFrom-Json).data.result[0].value[1]
$errors = (curl -s "http://localhost:8003/metrics" | Select-String -Pattern 'applylens_email_risk_served_total{level="error"}' | Select-Object -First 1).ToString()

Write-Host "P95 Latency: $p95 ms" -ForegroundColor $(if ([double]$p95 -lt 0.3) { "Green" } else { "Red" })
Write-Host "Errors: $errors" -ForegroundColor $(if ($errors -match " 0\.0") { "Green" } else { "Red" })
```

---

## Weight Tuning (Weekly)

**After 7 days of 100% rollout:**

```powershell
cd d:\ApplyLens

# Run weight analysis
python scripts/analyze_weights.py --since 7d --output docs/WEIGHT_TUNING_ANALYSIS_WEEK1.md

# Review recommendations
notepad docs/WEIGHT_TUNING_ANALYSIS_WEEK1.md

# If approved, create PR with weight changes
git checkout -b weight-tuning-week1
# Update weights in services/api/app/lib/email_risk.py
git add services/api/app/lib/email_risk.py
git commit -m "Apply week 1 weight tuning recommendations"
git push origin weight-tuning-week1
```

---

## Troubleshooting

### Problem: Flags endpoint returns 404

**Solution:**
```powershell
# Restart API to load flags router
docker-compose -f docker-compose.prod.yml restart api
Start-Sleep -Seconds 30
curl http://localhost:8003/flags/ | jq
```

### Problem: P95 latency spiking

**Check:**
1. Elasticsearch query performance: `curl http://localhost:9200/_cat/indices?v`
2. API container resources: `docker stats applylens-api-prod`
3. Recent ramp events: `curl http://localhost:8003/flags/audit/all | jq`

**Action:**
- If spike correlates with ramp, consider rolling back to previous percentage
- Check ES slow query logs
- Review Grafana dashboard for anomalies

### Problem: High false positive rate

**Check:**
1. User feedback in weight analysis
2. Signal distribution: Which signals are triggering most?
3. Review `docs/WEIGHT_TUNING_ANALYSIS_*.md` for recommendations

**Action:**
- Run early weight tuning: `python scripts/analyze_weights.py --since 48h`
- Consider temporary weight reductions for high-FP signals
- Monitor precision metric in Grafana

---

## Success Confirmation

**✅ Soft launch successful if after 6 hours:**
- [ ] P95 latency < 300ms sustained
- [ ] Error rate < 0.1%
- [ ] No P1 incidents
- [ ] User feedback < 5% negative
- [ ] Grafana dashboard shows healthy metrics

**Then:** Proceed to Stage 2 (25% rollout) after 24 hours.

---

## Support

- **Grafana:** http://localhost:3000/d/email-risk-v31
- **Prometheus:** http://localhost:9090/graph
- **Kibana:** http://localhost:5601
- **API Docs:** http://localhost:8003/docs
- **Runbook:** `RELEASE_CHECKLIST.md`
- **Full Status:** `EMAIL_RISK_V31_COMPLETE.md`

---

**🚀 Ready to launch!** Execute Step 1 when approved.
