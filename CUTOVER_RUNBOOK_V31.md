# Email Risk v3.1 — 15‑Minute Production Cutover Runbook (Final)

> **Known‑Good Values (Prod)**
> - **Alias (read/search):** `gmail_emails`
> - **Write alias / pattern:** `gmail_emails-*`
> - **Default ingest pipeline id:** `applylens_emails_v3` (contents = v3.1)
> - **New pipeline payload file:** `pipelines/emails_v3.1.json` (or `emails_v3_minimal.json`)
> - **Previous (rollback) payload file:** `pipelines/emails_v3.0.json` ← **not** a v2 file
> - **Kibana data view:** `gmail_emails` (time field: `received_at`)
> - **Test doc id:** `test-risk-v31-001` (expected score **78/100**, signals **6**, `suspicious=true`)
> - **Feature flag:** `EmailRiskBanner`

---

## Pre‑conditions (quick check)

**Elasticsearch health** is `green` or `yellow`:
```bash
docker exec applylens-es-prod curl -s http://localhost:9200/_cluster/health | \
  jq '{status, number_of_nodes, initializing_shards, unassigned_shards}'
```

**Prometheus** healthy:
```bash
curl -s http://localhost:9090/-/healthy
# Expected: "Prometheus Server is Healthy."
```

**API live**:
```bash
curl -s http://localhost:8003/health | jq
# Expected: {"status": "healthy"}
```

**Docs & scripts present:**
- `CUTOVER_RUNBOOK_V31.md`
- `PRE_FLIGHT_CHECKLIST_V31.md`
- `STAGING_POST_CHECKLIST_V31.md`
- `scripts/smoke_risk_advice.ps1`

> **Path note:** Any `-d @/…` payload paths refer to files **inside containers** (e.g., the Elasticsearch container at `/pipelines/`). Host‑side checks may show `d:\ApplyLens\infra\elasticsearch\pipelines\…`; that's expected. Files must be copied into containers before use.

**Pre-requisites:**
- ✅ All 8 staging improvements verified
- ✅ Smoke test passing (`.\scripts\smoke_risk_advice.ps1`)
- ✅ Prometheus alerts configured
- ✅ Rollback plan documented
- ✅ Team notification sent

---

## ⏱️ Cutover Timeline (15 minutes)

```
T+0  → Lock templates + pipeline (2m)
T+2  → Switch default pipeline (2m)
T+4  → Sanity check doc shape (2m)
T+6  → API verification (3m)
T+9  → Prometheus reload (2m)
T+11 → Kibana validation (2m)
T+13 → Feature flag ramp (2m)
──────────────────────────
T+15 → CUTOVER COMPLETE ✅
```

---

## 📋 Step-by-Step Execution

### Step 1: Lock Templates + Pipeline Default (T+0)

**Objective:** Ensure the canonical pipeline id remains `applylens_emails_v3` while the **contents** are v3.1. This avoids client/config churn.

**Commands:**
```bash
# 1a. Copy pipeline file into ES container (if not already present)
docker cp d:\ApplyLens\infra\elasticsearch\pipelines\emails_v3_minimal.json \
  applylens-es-prod:/pipelines/emails_v3.1.json

# 1b. Upload index template (if changed)
docker exec applylens-es-prod curl -s -X PUT \
  "http://localhost:9200/_index_template/applylens_emails" \
  -H 'Content-Type: application/json' \
  -d @/templates/applylens_emails.v31.json | jq

# 1c. Upload the v3.1 content under the canonical pipeline id applylens_emails_v3
docker exec applylens-es-prod curl -s -X PUT \
  "http://localhost:9200/_ingest/pipeline/applylens_emails_v3" \
  -H 'Content-Type: application/json' \
  -d @/pipelines/emails_v3.1.json | jq
```

**Expected Output:**
```json
{
  "acknowledged": true
}
```

**Validation:**
```bash
# Verify pipeline shows v3.1 description
docker exec applylens-es-prod curl -s \
  "http://localhost:9200/_ingest/pipeline/applylens_emails_v3" | \
  jq '.applylens_emails_v3.description'
```

**Expected:** `"ApplyLens emails v3.1 - Multi-signal phishing detection (simplified for deployment)"`

**Success Criteria:**
- ✅ Template `acknowledged: true`
- ✅ Pipeline GET shows v3.1 fields: `domain_age_days`, `verify_checks`, `suspicion_score`
- ✅ Pipeline description mentions "v3.1"

**Rollback:** Re-upload previous v3.0 pipeline (see Rollback section)

---

### Step 2: Switch Default Pipeline for Writes (T+2)

**Objective:** Ensure all new emails are processed with v3.1 pipeline

**Note:** Since we uploaded v3.1 content to the canonical id `applylens_emails_v3`, no additional changes are needed. The template already references this pipeline id.

**Validation:**
```bash
# Confirm template uses applylens_emails_v3 as default pipeline
docker exec applylens-es-prod curl -s \
  "http://localhost:9200/_index_template/applylens_emails" | \
  jq '.index_templates[0].index_template.template.settings.index.default_pipeline'
```

**Expected:** `"applylens_emails_v3"`

**Success Criteria:**
- ✅ Template points to `applylens_emails_v3` (which now has v3.1 content)
- ✅ New writes automatically pass through v3.1 processors

---

### Step 3: Sanity Check New Doc Shape (T+4)

**Objective:** Verify newly ingested documents have v3.1 fields

**Option A - Query Recent Live Document:**
```bash
# Find most recent document with v3.1 fields
docker exec applylens-es-prod curl -s \
  "http://localhost:9200/gmail_emails-*/_search?q=_exists_:suspicion_score&size=1&sort=received_at:desc" | \
  jq '.hits.hits[0]._source | {
    suspicion_score,
    suspicious,
    domain_age_days,
    verify_checks,
    explanations
  }'
```

**Expected Output:**
```json
{
  "suspicion_score": 15,
  "suspicious": false,
  "domain_age_days": 3650,
  "verify_checks": [
    "Check sender domain is official",
    "Verify via phone/official website"
  ],
  "explanations": []
}
```

**Success Criteria:**
- ✅ `suspicion_score` field exists (number 0-100)
- ✅ `suspicious` field exists (boolean)
- ✅ `domain_age_days` populated (or null if no enrichment data)
- ✅ `verify_checks` array present
- ✅ No pipeline errors in response

**Troubleshooting:**
```bash
# Check pipeline execution errors
docker exec applylens-es-prod curl -s \
  "http://localhost:9200/_nodes/stats/ingest?filter_path=nodes.*.ingest.pipelines.applylens_emails_v3" | jq
```

---

### Step 4: API & Router Verification (T+6)

**Objective:** Confirm API endpoints work with cross-index fallback

**4a. Test Alias-Only Query (BadRequest → Fallback Path):**
```powershell
# Should trigger fallback search to gmail_emails-*
curl -s "http://localhost:8003/emails/test-risk-v31-001/risk-advice" | `
  jq '{score:.suspicion_score, suspicious, signals:(.explanations|length)}'
```

**Expected:**
```json
{
  "score": 78,
  "suspicious": true,
  "signals": 6
}
```

**4b. Test Direct Index Query (No Fallback):**
```powershell
# Should hit specific index directly
curl -s "http://localhost:8003/emails/test-risk-v31-001/risk-advice?index=gmail_emails-999999" | `
  jq '{score:.suspicion_score, suspicious}'
```

**Expected:**
```json
{
  "score": 78,
  "suspicious": true
}
```

**4c. Test Prime-Advice Endpoint:**
```powershell
curl -s -X POST "http://localhost:8003/emails/test-risk-v31-001/prime-advice?index=gmail_emails-999999" | jq
```

**Expected:**
```json
{
  "ok": true,
  "primed": "test-risk-v31-001"
}
```

**Success Criteria:**
- ✅ Alias query returns score via fallback
- ✅ Direct query returns same score
- ✅ Prime-advice returns `ok: true`
- ✅ No 404 or 500 errors
- ✅ Response time < 300ms (check logs)

**Validation - Check API Logs:**
```powershell
docker logs applylens-api-prod --tail 20 2>&1 | `
  Select-String -Pattern "risk-advice|Error" | `
  Select-Object -Last 10
```

---

### Step 5: Prometheus & Grafana (T+9)

**Objective:** Reload Prometheus alerts and verify metrics flowing

**5a. Reload Prometheus Config:**
```bash
# Reload to pick up new alert rules
curl -s -X POST "http://localhost:9090/-/reload"
```

**Expected:** HTTP 200 (empty response)

**5b. Verify Alert Rules Loaded:**
```bash
# Check for Email Risk v3.1 alert group
curl -s "http://localhost:9090/api/v1/rules" | `
  jq '.data.groups[] | select(.name=="applylens_email_risk_v31") | {name, rules: (.rules | map(.name))}'
```

**Expected:**
```json
{
  "name": "applylens_email_risk_v31",
  "rules": [
    "EmailRiskAdviceSpikeHigh",
    "EmailRiskAdviceDrop",
    "EmailRiskFeedbackAnomaly",
    "EmailRiskHighFalsePositives"
  ]
}
```

**5c. Spot-Check Metrics:**
```powershell
# Check risk advice counter
curl -s http://localhost:8003/metrics | `
  Select-String 'applylens_email_risk_served_total|applylens_crypto_decrypt_error_total'
```

**Expected Output:**
```
applylens_email_risk_served_total{level="ok"} 0.0
applylens_email_risk_served_total{level="suspicious"} 2.0
applylens_email_risk_served_total{level="warn"} 0.0
applylens_crypto_decrypt_error_total{error_type="..."} 0.0
```

**Success Criteria:**
- ✅ Prometheus reload successful
- ✅ 4 Email Risk v3.1 alerts loaded
- ✅ `applylens_email_risk_served_total` > 0
- ✅ `applylens_crypto_decrypt_error_total` = 0
- ✅ All alerts show "Inactive" status

**5d. Grafana Dashboard (Optional):**
Navigate to: http://localhost:3000/dashboards

Create quick Email Risk panel:
- Query: `rate(applylens_email_risk_served_total[5m])`
- Visualization: Time series
- Legend: `{{level}}`

---

### Step 6: Kibana Validation (T+11)

**Objective:** Verify Kibana searches and dashboards work

**6a. Verify Data View:**
Navigate to: http://localhost:5601/kibana → **Stack Management** → **Data Views**

**Checks:**
- ✅ Data view: `gmail_emails-*` or `gmail_emails` alias
- ✅ Time field: `received_at`
- ✅ Pattern matches test indices

**6b. Test High Risk Saved Search:**
Navigate to: http://localhost:5601/kibana → **Discover**

Load: **"AL — High Risk (≥40)"**

**Spot-Check 5 Documents:**
1. Click first 5 results
2. Verify each has:
   - ✅ `suspicion_score` ≥ 40
   - ✅ `suspicious: true`
   - ✅ `explanations` array with signals
   - ✅ `verify_checks` populated

**6c. Dashboard Validation:**
Navigate to: **Dashboard** → **"Email Risk v3.1 Overview"**

**Checks:**
- ✅ Renders without errors
- ✅ High/Warn/Low counts populate
- ✅ Top signals chart shows data
- ✅ No manual filters required

**Success Criteria:**
- ✅ Data view configured correctly
- ✅ Saved search returns results (including test emails)
- ✅ All 5 spot-checked docs have complete v3.1 fields
- ✅ Dashboard renders with real data

---

### Step 7: Feature Flag Ramp (T+13)

**Objective:** Gradually roll out EmailRiskBanner to users

**7a. Initial Ramp (10% Users):**

If using LaunchDarkly/ConfigCat:
```javascript
// apps/web/src/config/featureFlags.ts
export const EMAIL_RISK_BANNER_ROLLOUT = {
  enabled: true,
  percentage: 10, // Start at 10%
  targeting: {
    environments: ['production'],
    users: [] // Random sampling
  }
}
```

If using environment variable:
```bash
# Update docker-compose.prod.yml or .env
EMAIL_RISK_BANNER_ENABLED=true
EMAIL_RISK_BANNER_PERCENTAGE=10
```

**7b. Monitor for 24 Hours:**

Watch these metrics:
- `applylens_email_risk_served_total{level="suspicious"}` - Should rise gradually
- `applylens_email_risk_feedback_total{verdict="legit"}` - False positive indicator
- `applylens_http_requests_total{path="/emails/:id/risk-advice"}` - Load

**7c. Ramp to 100% (After 24h if SLOs Hold):**

Update percentage:
```javascript
percentage: 100 // Full rollout
```

**Success Criteria:**
- ✅ 10% of users see EmailRiskBanner
- ✅ No spike in error rates
- ✅ API response time P95 < 300ms
- ✅ False positive rate < 10%

---

## 🚨 Rollback Procedure (< 5 minutes)

**Trigger Conditions:**
- Alerts firing (EmailRiskAdviceSpikeHigh, EmailRiskAdviceDrop)
- False positive rate > 15%
- `applylens_crypto_decrypt_error_total` > 0
- API errors > 5% for 5 minutes

### Rollback Step 1: Frontend (30 seconds)

**Option A - Feature Flag:**
```javascript
// Set percentage to 0
EMAIL_RISK_BANNER_PERCENTAGE=0
```

**Option B - Environment Variable:**
```bash
EMAIL_RISK_BANNER_ENABLED=false
```

### Rollback Step 2: API (2 minutes)

**Revert to last good image:**
```bash
# Find previous working image
docker images applylens-api | head -3

# Roll back to specific image SHA
docker tag applylens-api:sha256-abc123... applylens-api:latest
docker-compose -f docker-compose.prod.yml up -d --no-deps api

# Verify
curl -s http://localhost:8003/health | jq
```

### Rollback Step 3: Elasticsearch Pipeline (2 minutes)

**Point default back to v3.0:**
```bash
# Copy v3.0 pipeline file into container (if not already present)
docker cp d:\ApplyLens\infra\elasticsearch\pipelines\emails_v3.0.json \
  applylens-es-prod:/pipelines/emails_v3.0.json

# Restore v3.0 content to canonical pipeline id
docker exec applylens-es-prod curl -s -X PUT \
  "http://localhost:9200/_ingest/pipeline/applylens_emails_v3" \
  -H 'Content-Type: application/json' \
  -d @/pipelines/emails_v3.0.json | jq

# Verify rollback
docker exec applylens-es-prod curl -s \
  "http://localhost:9200/_ingest/pipeline/applylens_emails_v3" | \
  jq '.applylens_emails_v3.description'
```

**Expected:** `"ApplyLens emails v3.0 - ..."` (v3.0 description, not v3.1)

**Important:** Pipeline ID stays `applylens_emails_v3` (canonical), but content reverts to **v3.0** (previous stable version)

### Rollback Validation

```bash
# 1. Check API health
curl -s http://localhost:8003/health | jq

# 2. Verify 5xx error rate dropped (note the two dots for 3-digit codes)
curl -s http://localhost:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m]))' | \
  jq '.data.result[0].value[1]'

# 3. Check Prometheus alerts cleared
curl -s http://localhost:9090/api/v1/alerts | \
  jq '.data.alerts[] | select(.labels.alertname | startswith("EmailRisk")) | {alert: .labels.alertname, state: .state}'
```

**Success Criteria:**
- ✅ API health endpoint returns 200
- ✅ Error rate drops below 1%
- ✅ Email Risk alerts clear within 5 minutes
- ✅ No data loss (new emails continue processing with v3.0)

---

## 📊 Monitoring Checklist (First 24 Hours)

### Critical Metrics (Watch Continuously)

| Metric | Threshold | Action |
|--------|-----------|--------|
| `applylens_crypto_decrypt_error_total{error_type}` | = 0 | **Alert immediately if > 0** |
| `applylens_email_risk_served_total{level="suspicious"}` | Rising gradually | Alert if spike |
| API error rate | < 1% | Rollback if > 5% |
| **P50 latency** `/emails/:id/risk-advice` | **< 300ms** | Investigate if > 500ms |
| **P95 latency** `/emails/:id/risk-advice` | **< 300ms** | **Critical - rollback if > 500ms** |
| False positive rate (manual spot-check) | < 10% | Tune weights if > 15% |

**Note:** P95 latency is critical - it reveals tail latencies that P50 may hide. A P95 > 300ms indicates performance degradation for 5% of users.

### Prometheus Queries

```promql
# Error rate (note: "5.." matches 5xx codes - two dots for 3-digit status codes)
sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m]))
  / sum(rate(applylens_http_requests_total[5m]))

# Advice served rate by level
rate(applylens_email_risk_served_total[5m])

# Rate limit ratio
sum(rate(applylens_rate_limit_exceeded_total[5m]))
  / (sum(rate(applylens_rate_limit_allowed_total[5m]))
     + sum(rate(applylens_rate_limit_exceeded_total[5m])))

# P50 latency (if histogram buckets available)
histogram_quantile(0.50,
  rate(http_request_duration_seconds_bucket{path="/emails/:id/risk-advice"}[5m]))

# P95 latency (CRITICAL - add to Grafana dashboard)
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket{path="/emails/:id/risk-advice"}[5m]))
```

### Manual Spot-Checks (Every 6 Hours)

**Run Smoke Test:**
```powershell
cd d:\ApplyLens
.\scripts\smoke_risk_advice.ps1
```

**Kibana Precision Check:**
1. Open "High Risk (≥40)" search
2. Sample 20 random emails
3. Count false positives
4. Calculate: `(false_positives / 20) * 100%`
5. **Target:** < 10% false positive rate

**Alert Status:**
```bash
curl -s http://localhost:9090/api/v1/alerts | `
  jq '.data.alerts[] | select(.state=="firing") | {alert: .labels.alertname, severity: .labels.severity}'
```

---

## 🎯 Success Criteria

### Immediate (T+15)
- [x] All 7 cutover steps completed
- [x] No errors in validation checks
- [x] Feature flag ramped to 10%
- [x] Monitoring dashboards updated

### 24 Hours
- [ ] Zero `applylens_crypto_decrypt_error_total`
- [ ] `applylens_email_risk_served_total` rising smoothly
- [ ] False positive rate < 10% (manual check)
- [ ] Rate limit ratio < 1%
- [ ] **P50 latency < 300ms AND P95 latency < 300ms** (both critical)
- [ ] No Email Risk alerts firing
- [ ] Feature flag ramped to 100%

### 7 Days
- [ ] User feedback collected (>50 responses)
- [ ] Weight tuning completed (if FP > 10%)
- [ ] Domain enrichment backlog < 1000 emails
- [ ] Grafana dashboard finalized
- [ ] Runbook updated with lessons learned

---

## 🛠️ Nice-to-Have Enhancements (Post-Cutover)

### 1. Automated Smoke Testing
```powershell
# Schedule via Task Scheduler
schtasks /create /tn "ApplyLens Email Risk Smoke Test" `
  /tr "powershell.exe -File d:\ApplyLens\scripts\smoke_risk_advice.ps1" `
  /sc hourly /st 00:00
```

### 2. Prime Advice UX Enhancement
```javascript
// apps/web/src/components/EmailDetailPane.tsx
useEffect(() => {
  if (emailId) {
    setPriming(true);
    fetch(`/api/emails/${emailId}/prime-advice`, { method: 'POST' })
      .then(() => setPriming(false))
      .catch(() => setPriming(false));
  }
}, [emailId]);

// Show subtle indicator:
{priming && <Badge color="blue">⚡ Priming...</Badge>}
```

### 3. Alias Hygiene
```python
# Prefer direct index on known single-document queries
# services/api/app/routers/emails.py

def get_email_by_id(email_id: str, index: str = "gmail_emails-000001"):
    """Use specific index for GET-by-ID to avoid alias BadRequest"""
    return es.get(index=index, id=email_id)
```

### 4. Anomaly Detection Panel
```promql
# Grafana stat panel: "Suspicious % vs 7-day median"
(rate(applylens_email_risk_served_total{level="suspicious"}[1h])
 / rate(applylens_email_risk_served_total[1h]))
/
(rate(applylens_email_risk_served_total{level="suspicious"}[7d] offset 7d)
 / rate(applylens_email_risk_served_total[7d] offset 7d))
```

---

## 📞 Contact & Escalation

**Runbook Owner:** Platform Engineering Team
**On-Call:** [PagerDuty rotation]
**Slack Channel:** #email-risk-v31
**Documentation:** `d:\ApplyLens\STAGING_ENHANCEMENTS_COMPLETE.md`

**Escalation Path:**
1. **L1:** Run rollback procedure (< 5 min)
2. **L2:** Check logs, metrics, alert platform team
3. **L3:** Engage security team for false positive analysis

---

## 🤖 Post-Cutover Copilot Tasks

These tasks enhance the v3.1 deployment with automated testing, CI integration, and improved observability:

### Task 1: Unit Test for BadRequest Fallback
**Priority:** High
**File:** `services/api/tests/test_email_risk.py`

```python
def test_risk_advice_multi_index_alias_fallback(client, mock_es):
    """Test BadRequestError triggers fallback to search query"""
    from elasticsearch import BadRequestError

    # Mock ES.get to raise BadRequestError (alias with multiple indices)
    mock_es.get.side_effect = BadRequestError(
        400, "alias [gmail_emails] has more than one index", {}
    )

    # Mock ES.search to return document via fallback
    mock_es.search.return_value = {
        "hits": {"hits": [{"_source": {"suspicion_score": 78, "suspicious": True}}]}
    }

    response = client.get("/emails/test-123/risk-advice")

    assert response.status_code == 200
    assert response.json()["suspicion_score"] == 78
    assert mock_es.search.called  # Fallback triggered
```

### Task 2: Smoke Script CI Integration
**Priority:** Medium
**File:** `scripts/smoke_risk_advice.ps1`

**Update:** Exit with non-zero code on any check failure for CI/CD pipeline integration.

```powershell
# At end of script, track failures
$failCount = 0
if ($testEmailResponse.StatusCode -ne 200) { $failCount++ }
if ($directQueryResponse.score -ne 78) { $failCount++ }
if ($fallbackResponse.score -ne 78) { $failCount++ }
if ($metricsValue -lt 1) { $failCount++ }
if ($primeResponse.ok -ne $true) { $failCount++ }

if ($failCount -gt 0) {
    Write-Host "❌ SMOKE TEST FAILED: $failCount checks failed" -ForegroundColor Red
    exit 1  # Non-zero exit for CI failure
} else {
    Write-Host "✅ SMOKE TEST PASSED" -ForegroundColor Green
    exit 0  # Success
}
```

### Task 3: Grafana P95 Latency Panel
**Priority:** High
**File:** `infra/grafana/provisioning/dashboards/email_risk_v31.json`

Add panel to Email Risk dashboard:

```json
{
  "title": "Email Risk Advice Latency (P50 & P95)",
  "targets": [
    {
      "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket{path=\"/emails/:id/risk-advice\"}[5m]))",
      "legendFormat": "P50"
    },
    {
      "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{path=\"/emails/:id/risk-advice\"}[5m]))",
      "legendFormat": "P95"
    }
  ],
  "thresholds": [
    {"value": 300, "color": "orange", "label": "Target: 300ms"}
  ],
  "yAxisLabel": "Latency (ms)"
}
```

### Task 4: Kibana Data View Import Validation
**Priority:** Low
**Commands:**

```bash
# Export current data view to verify it's correct
curl -s -X GET "http://localhost:5601/api/data_views/data_view/gmail_emails" \
  -H 'kbn-xsrf: true' | jq '.' > data_view_gmail_emails_export.json

# Verify time field and pattern
jq '.data_view | {title, timeFieldName, fieldFormatMap}' data_view_gmail_emails_export.json

# Re-import to test (idempotent)
curl -s -X POST "http://localhost:5601/api/data_views/data_view" \
  -H 'kbn-xsrf: true' -H 'Content-Type: application/json' \
  -d @data_view_gmail_emails_export.json | jq '.data_view.id'
```

### Task 5: Feature Flag Percentage Rollout Support
**Priority:** Medium
**File:** `apps/web/src/hooks/useFeatureFlag.ts`

Ensure `EmailRiskBanner` flag supports gradual percentage rollout:

```typescript
export function useFeatureFlag(flagName: string): boolean {
  const user = useCurrentUser();

  const flags = {
    EmailRiskBanner: {
      enabled: true,
      percentage: 10, // Start at 10%, ramp to 100%
      targetUsers: [] // Empty = random sampling by userId hash
    }
  };

  const flag = flags[flagName];
  if (!flag?.enabled) return false;

  // Hash userId to deterministic 0-99
  const userHash = hashCode(user.id) % 100;
  return userHash < flag.percentage;
}
```

---

## 📝 Post-Cutover Checklist

- [ ] Update status page: "Email Risk v3.1 deployed"
- [ ] Send team notification: "Cutover complete, monitoring for 24h"
- [ ] Schedule retrospective: Review FP rate, latency, user feedback
- [ ] Document lessons learned
- [ ] Archive runbook execution logs
- [ ] Update production deployment guide
- [ ] Complete Copilot tasks (unit test, CI integration, Grafana panel, feature flag)

---

**Cutover Executed By:** _______________ Date: _______________
**Rollback Required:** ☐ Yes ☐ No
**Issues Encountered:** _____________________________________________
**Notes:** _____________________________________________________________

---

**Last Updated:** October 21, 2025
**Version:** v3.1 Production Cutover
**Next Review:** Post-cutover retrospective (T+7 days)
