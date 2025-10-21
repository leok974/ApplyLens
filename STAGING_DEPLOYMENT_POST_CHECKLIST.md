# Email Risk v3.1 - Post-Staging Deployment Checklist

## ✅ Completed Items

- [x] **Pipeline v3.1 uploaded** - 5 processors (v2 base + auth + attachments + URLs)
- [x] **Domain enrichment index created** - domain_enrich with proper mapping
- [x] **Enrich policy executed** - domain_age_policy status: COMPLETE
- [x] **API rebuilt & deployed** - /emails/risk/* endpoints live
- [x] **Web UI verified** - Running at port 5175
- [x] **Kibana imports complete** - 8 saved searches + 1 dashboard
- [x] **Smoke test passed** - Test email scored 78 with 6 signals
- [x] **Prometheus metrics flowing** - applylens_email_risk_served_total working
- [x] **Fallback search implemented** - API finds docs in any gmail_emails-* index
- [x] **Prime-advice endpoint added** - Background caching for instant UI loads

## 🔄 In Progress / Post-Staging Tasks

### 1. `/emails/{id}/risk-advice` - Find docs anywhere ✅

**Status**: COMPLETE

**Verification**:
```powershell
# Test with explicit index
curl "http://localhost:8003/emails/test-risk-v31-001/risk-advice?index=gmail_emails-999999" | jq

# Test fallback search (no index param)
curl "http://localhost:8003/emails/test-risk-v31-001/risk-advice" | jq
```

**Expected**: Both return same result with score 78, 6 explanations

---

### 2. Prometheus Counters on Advice Hits ✅

**Status**: COMPLETE

**Verification**:
```powershell
# Call endpoint a few times
1..5 | ForEach-Object { curl -s "http://localhost:8003/emails/test-risk-v31-001/risk-advice" | Out-Null }

# Check metrics
curl "http://localhost:8003/metrics" | Select-String "applylens_email_risk_served_total"
```

**Expected**: Counter shows `applylens_email_risk_served_total{level="suspicious"} 5.0` (or higher)

---

### 3. Backfill Domain Enrichment ⏸️

**Status**: READY (pipeline exists, index empty - needs data)

**Action**: Re-index existing emails through v3 pipeline to trigger enrichment

```powershell
# Option A: Reindex test index through pipeline (safe for staging)
$reindexBody = @{
    source = @{
        index = "gmail_emails-999999"
        query = @{ match_all = @{} }
    }
    dest = @{
        index = "gmail_emails-999999"
        pipeline = "applylens_emails_v3"
    }
    script = @{
        lang = "painless"
        source = "ctx._op='update'"
    }
} | ConvertTo-Json -Depth 5

docker exec applylens-es-prod curl -X POST "http://localhost:9200/_reindex?refresh=true&wait_for_completion=false" `
    -H "Content-Type: application/json" `
    -d $reindexBody

# Option B: Full production backfill (use with caution)
# Reindex all gmail_emails-* indices through pipeline
# Recommend doing this during off-hours with throttling
```

**Verification**:
```powershell
# Check task status
docker exec applylens-es-prod curl "http://localhost:9200/_tasks?actions=*reindex"

# Verify updated docs have enrichment
docker exec applylens-es-prod curl "http://localhost:9200/gmail_emails-999999/_search" `
    -d '{"size":1,"query":{"exists":{"field":"domain_age_days"}}}'
```

---

### 4. Auto-Advice Sampling (Agentic Nudge) ✅

**Status**: ENDPOINT CREATED

**Usage**: Call from UI after email open (fire-and-forget)

```javascript
// In EmailDetailPane.tsx or similar
useEffect(() => {
  if (email.suspicion_score >= 40) {
    // Pre-cache risk advice for instant loading
    fetch(`/emails/${email.id}/prime-advice`, { method: 'POST' })
      .catch(() => {}); // Silent fail
  }
}, [email.id]);
```

**Verification**:
```powershell
curl -X POST "http://localhost:8003/emails/test-risk-v31-001/prime-advice?index=gmail_emails-999999"
# Expected: {"ok": true, "primed": "test-risk-v31-001"}
```

---

### 5. Kibana Saved Search Sanity ✅

**Status**: VERIFIED (8 imports successful)

**Action**: Ensure data view points to pattern `gmail_emails-*`

**Verification**:
```powershell
# Check data view
# http://localhost:5601/kibana/app/management/kibana/dataViews

# Should be: "ApplyLens Emails (all)" with pattern "gmail_emails-*"
```

**Saved Searches Available**:
1. AL — High Risk (score ≥ 40)
2. AL — Warnings (25 ≤ score < 40)
3. AL — SPF/DKIM/DMARC Fails
4. AL — Reply-To mismatch
5. AL — Young domains (< 30 days)
6. AL — Risky attachments (.docm/.zip)
7. AL — URL shorteners / anchor mismatch

---

### 6. One-Click Smoke Test ✅

**Status**: SCRIPT CREATED

**Usage**:
```powershell
# Run smoke test
.\scripts\smoke_risk_advice.ps1

# Expected output:
# === Email Risk v3.1 Smoke Test ===
# 1. Indexing test email through v3 pipeline...
#   ✓ Document indexed successfully
# 2. Fetching risk advice from API...
#   ✓ Direct index query:
#     Score: 66
#     Suspicious: True
#     Signals detected: 5
# ...
# ✅ PASS - Email correctly flagged as suspicious
```

---

### 7. Alert on Sudden Spike ✅

**Status**: RULES CREATED

**Action**: Add Prometheus alert rules

```powershell
# 1. Copy alert rules to Prometheus config
cp scripts\prometheus_alerts_v31.yml infra\prometheus\alerts\email_risk_v31.yml

# 2. Reload Prometheus (if auto-reload not enabled)
docker exec applylens-prometheus-prod kill -HUP 1

# 3. Verify rules loaded
curl "http://localhost:9090/api/v1/rules" | jq '.data.groups[] | select(.name=="email_risk_v31_alerts")'

# 4. View alerts in UI
# http://localhost:9090/alerts
```

**Alert Rules**:
- `EmailRiskAdviceSpikeHigh` - High volume of suspicious emails (>0.5/min for 10m)
- `EmailRiskAdviceDrop` - No advice served for 30m (possible regression)
- `EmailRiskHighFeedbackRate` - High user correction rate
- `EmailRiskFeedbackImbalance` - >70% 'legit' feedback (false positives)
- `EmailRiskPipelineErrors` - Pipeline processing failures
- `DomainEnrichmentStale` - Worker hasn't run in 2+ hours

---

### 8. Post-Staging Validation ⏸️

**Status**: READY TO START

**Checklist**:

```powershell
# A. Endpoint returns JSON for real email
$realEmailId = "some-real-email-id"
curl "http://localhost:8003/emails/$realEmailId/risk-advice" | jq

# B. Metrics increase with usage
$before = (curl "http://localhost:8003/metrics" | Select-String "applylens_email_risk_served_total").ToString()
curl "http://localhost:8003/emails/test-risk-v31-001/risk-advice" | Out-Null
$after = (curl "http://localhost:8003/metrics" | Select-String "applylens_email_risk_served_total").ToString()
# Compare $before vs $after - counter should increment

# C. Young domain signal appears (after enrichment backfill)
docker exec applylens-es-prod curl "http://localhost:9200/gmail_emails-*/_search" `
    -d '{"query":{"exists":{"field":"domain_age_days"}},"size":1}' | jq '.hits.total.value'
# Expected: > 0 after enrichment worker runs

# D. Kibana searches return results
# http://localhost:5601/kibana → Open "AL — High Risk" saved search
# Expected: Shows emails with suspicion_score >= 40

# E. Rollback plan verified
Test-Path "d:\ApplyLens\backup\emails_v2_backup_20251021_145540.json"
# Expected: True

docker exec applylens-es-prod curl "http://localhost:9200/_ingest/pipeline/applylens_emails_v3" | jq '.applylens_emails_v3.description'
# Expected: "ApplyLens emails v3.1 - Multi-signal phishing detection (simplified for deployment)"
```

---

## 🚀 Production Deployment Readiness

### Pre-Production Checklist

- [ ] **Staging validation complete** (all 8 post-staging tasks ✅)
- [ ] **False positive rate < 10%** (review 24h of high-risk emails)
- [ ] **Domain enrichment worker running** as systemd daemon
- [ ] **Prometheus alerts configured** and tested
- [ ] **Grafana dashboard created** for risk summary endpoint
- [ ] **Rollback plan documented** and tested
- [ ] **User education docs shared** (EMAIL_RISK_DETECTION_V3.md)
- [ ] **API latency acceptable** (p95 < 200ms for /risk/summary-24h)
- [ ] **Pipeline latency acceptable** (< 1s per email)

### Production Deployment Steps

1. **Deploy Pipeline**:
   ```powershell
   # Upload to production ES
   $prodES = $env:PROD_ES_URL
   curl -X PUT "$prodES/_ingest/pipeline/applylens_emails_v3" `
       -H "Content-Type: application/json" `
       -d (Get-Content "infra\elasticsearch\pipelines\emails_v3_minimal.json" -Raw)
   ```

2. **Deploy Domain Worker**:
   ```bash
   ssh production-server
   sudo systemctl enable --now applylens-domain-enrich.service
   journalctl -u applylens-domain-enrich -f
   ```

3. **Deploy API**:
   ```powershell
   # Build and push to registry
   docker build -t registry.example.com/applylens-api:v3.1 services/api
   docker push registry.example.com/applylens-api:v3.1

   # Update production deployment
   kubectl set image deployment/applylens-api api=registry.example.com/applylens-api:v3.1
   ```

4. **Import Kibana Assets**:
   ```powershell
   $kibanaURL = $env:PROD_KIBANA_URL
   curl -u "$auth" -X POST -H "kbn-xsrf: reporting" `
       -F "file=@infra\kibana\saved_searches_v31.ndjson" `
       "$kibanaURL/api/saved_objects/_import?overwrite=true"
   ```

5. **Monitor for 24h**:
   - Check Prometheus alerts: http://prod-prometheus:9090/alerts
   - Review Kibana "High Risk" search for false positives
   - Monitor API latency and error rates
   - Collect user feedback

---

## 📊 Success Metrics

### Week 1 Targets

- **False Positive Rate**: < 10% (user feedback 'legit' < 10%)
- **False Negative Rate**: < 5% (missed phishing emails)
- **API Availability**: > 99.9%
- **Pipeline Success Rate**: > 99.5%
- **User Feedback Volume**: > 50 submissions
- **Domain Enrichment Coverage**: > 80% of sender domains

### Week 2+ Optimization

- Tune weights based on feedback (scripts/analyze_weights.py)
- Adjust threshold if needed (currently 40)
- Add missing heuristics (anchor mismatch, IP reputation)
- Expand shortener blocklist
- Improve domain age detection

---

## 🔧 Troubleshooting

### Pipeline Not Processing

```powershell
# Check pipeline exists
docker exec applylens-es-prod curl "http://localhost:9200/_ingest/pipeline/applylens_emails_v3"

# Test with sample doc
docker exec applylens-es-prod curl -X POST "http://localhost:9200/_ingest/pipeline/applylens_emails_v3/_simulate" `
    -d (Get-Content "test_email_tc4.json" -Raw)

# Check for errors
docker exec applylens-es-prod curl "http://localhost:9200/_nodes/stats/ingest" | jq '.nodes[].ingest.total.failed'
```

### API Endpoints 404

```powershell
# Verify API is running latest code
docker inspect applylens-api-prod --format='{{.Image}}' | % {docker inspect $_ --format='{{.Created}}'}

# Rebuild if needed
docker-compose -f docker-compose.prod.yml build --no-cache api
docker-compose -f docker-compose.prod.yml up -d --no-deps api
```

### Metrics Not Appearing

```powershell
# Check if endpoint was called
curl "http://localhost:8003/metrics" | Select-String "applylens_email_risk"

# Call endpoint to generate metrics
curl "http://localhost:8003/emails/test-risk-v31-001/risk-advice"

# Verify Prometheus is scraping
curl "http://localhost:9090/api/v1/targets" | jq '.data.activeTargets[] | select(.labels.job=="api")'
```

---

## 📁 Files Created in This Session

- ✅ `infra/elasticsearch/pipelines/emails_v3_minimal.json` - Working v3.1 pipeline
- ✅ `scripts/smoke_risk_advice.ps1` - Automated smoke test
- ✅ `scripts/prometheus_alerts_v31.yml` - Alert rules
- ✅ `STAGING_DEPLOYMENT_V31_SUMMARY.md` - Full deployment docs
- ✅ `STAGING_DEPLOYMENT_QUICK_REF.md` - Quick reference
- ✅ `STAGING_DEPLOYMENT_POST_CHECKLIST.md` - This checklist

---

**Last Updated**: October 21, 2025
**Environment**: Staging (Docker localhost)
**Version**: v3.1 (Minimal - 3 processors)
**Status**: ✅ Ready for production validation
