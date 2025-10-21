# Email Risk v3.1 - Post-Staging Verification Checklist

## Overview
Fast verification checklist to ensure all Email Risk v3.1 features are working correctly after staging deployment.

**Date:** October 21, 2025
**Version:** v3.1 (16-signal phishing detection)
**Environment:** Staging → Production

---

## ✅ 1. Risk Advice Endpoint - Cross-Index Queries

### Test direct index query
```powershell
curl -s "http://localhost:8003/emails/test-risk-v31-001/risk-advice?index=gmail_emails-999999" | jq
```

**Expected:**
- ✅ Returns JSON with `suspicion_score`, `suspicious`, `explanations`
- ✅ Score ≥ 40 for test email (multiple phishing signals)

### Test fallback search (no index param)
```powershell
curl -s "http://localhost:8003/emails/test-risk-v31-001/risk-advice" | jq
```

**Expected:**
- ✅ Returns same score as direct query
- ✅ Falls back to `gmail_emails-*` pattern search

### Verify alias configuration
```bash
docker exec applylens-es-prod curl -s "http://localhost:9200/_alias/gmail_emails" | jq
```

**Expected:**
- ✅ Alias includes `gmail_emails-999999` test index
- ✅ Alias includes production indices

---

## ✅ 2. Prometheus Metrics - Advice Served Counter

### Check metric increments
```powershell
# Baseline check
curl -s "http://localhost:8003/metrics" | Select-String "applylens_email_risk_served_total"

# Trigger 3 advice requests
1..3 | ForEach-Object {
    curl -s "http://localhost:8003/emails/test-risk-v31-001/risk-advice?index=gmail_emails-999999" | Out-Null
    Start-Sleep -Milliseconds 500
}

# Verify counter increased
curl -s "http://localhost:8003/metrics" | Select-String 'applylens_email_risk_served_total{level="suspicious"}'
```

**Expected:**
- ✅ Counter exists: `applylens_email_risk_served_total{level="suspicious"}`
- ✅ Counter increments by 3 after requests
- ✅ Labels include: `suspicious`, `warn`, `ok`

---

## ✅ 3. Domain Enrichment Backfill

### Check reindex task status
```bash
docker exec applylens-es-prod curl -s "http://localhost:9200/_tasks?actions=*reindex&detailed=true" | jq
```

**Expected:**
- ✅ Task shows `completed: true` or still running with progress
- ✅ No errors in task response

### Verify domain_age field populated
```bash
docker exec applylens-es-prod curl -s "http://localhost:9200/gmail_emails-999999/_search?size=3&_source_includes=from,domain_age_days,explanations" | jq '.hits.hits[]._source'
```

**Expected:**
- ✅ At least one email shows `domain_age_days` field
- ✅ "Domain age < 30 days" appears in `explanations` for young domains
- ✅ Test email from `careers-finetunelearning.com` shows domain age

---

## ✅ 4. Prime-Advice Endpoint (Background Caching)

### Test fire-and-forget priming
```powershell
curl -s -X POST "http://localhost:8003/emails/test-risk-v31-001/prime-advice?index=gmail_emails-999999" | jq
```

**Expected:**
- ✅ Returns `{"ok": true, "primed": "test-risk-v31-001"}`
- ✅ No errors in API logs: `docker logs applylens-api-prod --tail 20`
- ✅ Metrics counter increments (advice served in background)

### Verify UI integration point
```javascript
// From web UI EmailDetailPane.tsx - call on mount:
useEffect(() => {
  if (emailId) {
    fetch(`/api/emails/${emailId}/prime-advice`, { method: 'POST' })
      .catch(() => {}); // Silent fail
  }
}, [emailId]);
```

**Expected:**
- ✅ API call fires when email detail pane opens
- ✅ No console errors if endpoint unavailable

---

## ✅ 5. Kibana Data View Configuration

### Check data view pattern
Navigate to: http://localhost:5601/kibana → **Stack Management** → **Data Views**

**Expected:**
- ✅ Data view exists: `gmail_emails-*` or alias `gmail_emails`
- ✅ Time field: `received_at`
- ✅ Pattern matches both production and test indices

### Verify saved searches work
Navigate to: http://localhost:5601/kibana → **Discover**

Load each saved search:
1. **Risk v3.1 - High Suspicion (≥40)**
2. **Risk v3.1 - Auth Fails**
3. **Risk v3.1 - Reply-To Mismatch**
4. **Risk v3.1 - Young Domains**
5. **Risk v3.1 - Risky Attachments**
6. **Risk v3.1 - URL Shorteners**
7. **Risk v3.1 - User Confirmed Scams**

**Expected:**
- ✅ All searches return results (including test emails)
- ✅ No "index not found" errors
- ✅ At least 1 result from `gmail_emails-999999` test index

---

## ✅ 6. Smoke Test Script Execution

### Run automated smoke test
```powershell
cd d:\ApplyLens
.\scripts\smoke_risk_advice.ps1
```

**Expected:**
- ✅ Document indexes successfully through v3 pipeline
- ✅ Risk advice score ≥ 50 (multiple signals detected)
- ✅ Fallback search works without index param
- ✅ Prometheus metrics increment
- ✅ Prime-advice endpoint returns `{"ok": true}`
- ✅ Output: **"✅ PASS - All critical checks successful"**

---

## ✅ 7. Prometheus Alert Rules Integration

### Add alerts to Prometheus config
```bash
# Check if alerts are already loaded
curl -s "http://localhost:9090/api/v1/rules" | jq '.data.groups[] | select(.name=="applylens_email_risk_v31")'
```

**If not loaded:**
```bash
# Prometheus should auto-detect changes, or reload manually:
curl -X POST "http://localhost:9090/-/reload"
```

### Verify alerts are loaded
Navigate to: http://localhost:9090/alerts

**Expected:**
- ✅ Alert group: `applylens_email_risk_v31` visible
- ✅ 4 alerts defined:
  1. `EmailRiskAdviceSpikeHigh` (suspicious > 0.5/min)
  2. `EmailRiskAdviceDrop` (no advice for 30m)
  3. `EmailRiskFeedbackAnomaly` (surge in scam reports)
  4. `EmailRiskHighFalsePositives` (>15% legit on suspicious)
- ✅ All alerts show "Inactive" (no current issues)

### Test alert firing (optional)
```powershell
# Trigger spike: rapid advice requests
1..20 | ForEach-Object {
    curl -s "http://localhost:8003/emails/test-risk-v31-001/risk-advice?index=gmail_emails-999999" | Out-Null
    Start-Sleep -Milliseconds 100
}

# Wait 10 minutes, check if EmailRiskAdviceSpikeHigh fires
```

---

## ✅ 8. Rollback Plan Verification

### Confirm backup exists
```bash
ls -la d:\ApplyLens\infra\elasticsearch\pipelines\backup\emails_v2_backup_*.json
```

**Expected:**
- ✅ Backup file present with timestamp
- ✅ File size > 1KB (contains full v2 pipeline)

### Test rollback procedure
```bash
# Rollback command (DO NOT RUN unless needed):
docker exec applylens-es-prod curl -X PUT \
  "http://localhost:9200/_ingest/pipeline/applylens_emails_v3" \
  -H "Content-Type: application/json" \
  -d @/backup/emails_v2_backup_20251021_145540.json
```

**Expected:**
- ✅ Command documented in `STAGING_DEPLOYMENT_V31_SUMMARY.md`
- ✅ Backup file accessible from Docker container
- ✅ API restart command ready: `docker-compose -f docker-compose.prod.yml restart api`

---

## 📊 Production Readiness Summary

| Check | Status | Notes |
|-------|--------|-------|
| 1. Risk advice endpoint | ⬜ | Cross-index queries work |
| 2. Prometheus metrics | ⬜ | Counters increment correctly |
| 3. Domain enrichment | ⬜ | Backfill complete, domain_age populated |
| 4. Prime-advice endpoint | ⬜ | Background tasks working |
| 5. Kibana data view | ⬜ | Pattern matches all indices |
| 6. Smoke test script | ⬜ | All checks pass |
| 7. Alert rules | ⬜ | Loaded in Prometheus |
| 8. Rollback plan | ⬜ | Backup verified |

**Sign-off:** _______________ Date: _______________

---

## 🚨 Troubleshooting

### Issue: "Email not found" error
```bash
# Check alias configuration
docker exec applylens-es-prod curl -s "http://localhost:9200/_cat/aliases/gmail_emails?v"

# Verify document exists
docker exec applylens-es-prod curl -s "http://localhost:9200/gmail_emails-999999/_doc/test-risk-v31-001?_source=false"
```

### Issue: Metrics not incrementing
```bash
# Check API logs for errors
docker logs applylens-api-prod --tail 50 | grep -i "risk-advice\|error"

# Verify Prometheus scraping
curl -s "http://localhost:9090/api/v1/targets" | jq '.data.activeTargets[] | select(.labels.job=="applylens-api")'
```

### Issue: Domain enrichment not showing
```bash
# Check enrich policy status
docker exec applylens-es-prod curl -s "http://localhost:9200/_enrich/policy/domain_age_policy"

# Re-execute policy
docker exec applylens-es-prod curl -X POST "http://localhost:9200/_enrich/policy/domain_age_policy/_execute"
```

### Issue: Kibana searches return no results
```
1. Check data view time range (last 90 days)
2. Verify index pattern includes test indices
3. Refresh field list in data view settings
4. Check index exists: GET /_cat/indices/gmail_emails-*?v
```

---

## 📝 Next Steps After Sign-off

1. **Monitor for 24 hours** - Watch Prometheus dashboards and Kibana for anomalies
2. **Enable user feedback** - Update UI to show feedback buttons on risk banner
3. **Tune weights** - Adjust signal weights based on false positive rate
4. **Scale domain worker** - If backfill queue grows, increase worker replicas
5. **Document edge cases** - Add to runbook as patterns emerge

**Last updated:** 2025-10-21
**Owner:** Platform Team
**Review cycle:** After each v3.x deployment
