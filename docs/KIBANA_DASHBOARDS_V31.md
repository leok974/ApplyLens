# Kibana Dashboards v3.1 — Email Risk Detection

## Overview

Fast verification of v3.1 multi-signal phishing detection using **reliable, version-agnostic saved searches** and a lightweight dashboard skeleton. This approach avoids brittle Lens JSON exports; charts can be added in-app with a few clicks using the included KQL queries.

**What's included**:
- 📊 Data view for `gmail_emails-*` rollover pattern
- 🔍 6 saved searches covering key v3.1 signals
- 📈 Empty dashboard shell (add panels interactively)
- 🎯 KQL query library for common filters
- 🛠️ Lens chart recipes (build in 60 seconds)
- ✅ End-to-end validation path

## Architecture

```
┌─────────────────┐
│  Data View      │  gmail_emails-*
│  (aliased)      │  ─────────────────────┐
└─────────────────┘                       │
                                          │
┌─────────────────┐                       │
│ Saved Searches  │  6 KQL-based searches │
│  (v3.1 signals) │  ─────────────────────┤
└─────────────────┘                       │
                                          ▼
┌─────────────────┐              ┌──────────────┐
│   Dashboard     │  References  │   Discover   │
│     Shell       │◄─────────────┤  Analytics   │
└─────────────────┘              └──────────────┘
         │
         │ Add panels
         ▼
┌─────────────────┐
│ Lens Charts     │  Build interactively
│ (60s each)      │  (score over time,
└─────────────────┘   top reasons, etc.)
```

## Files

| File | Purpose | Objects |
|------|---------|---------|
| `dv_emails_aliased.ndjson` | Data view for `gmail_emails-*` | 1 index-pattern |
| `saved_searches_v31.ndjson` | 6 saved searches + data view | 1 index-pattern + 6 searches |
| `dashboard_shell_v31.ndjson` | Empty dashboard shell | 1 dashboard |

## 1. Data View (Discover Source)

**File**: `infra/kibana/dv_emails_aliased.ndjson`

Creates data view:
- **ID**: `applylens-emails-alias`
- **Title**: `gmail_emails-*` (rollover pattern)
- **Time field**: `received_at`
- **Name**: "ApplyLens Emails (all)"

Covers all email indices: `gmail_emails-000001`, `gmail_emails-000002`, `gmail_emails-999999` (test), etc.

**Alternative**: If you prefer the test index only, use the earlier `applylens-test-gmail-999999` data view or import both.

## 2. Saved Searches (Rock-Solid & Importable)

**File**: `infra/kibana/saved_searches_v31.ndjson`

Contains **6 saved searches** targeting v3.1 signals:

### Search 1: High Risk (score ≥ 40)
- **ID**: `al-highrisk-40`
- **Title**: "AL — High Risk (score ≥ 40)"
- **Query**: `suspicion_score >= 40`
- **Columns**: `received_at`, `from`, `subject`, `suspicion_score`, `suspicious`
- **Use case**: Daily review of flagged emails

### Search 2: Warnings (25 ≤ score < 40)
- **ID**: `al-warning-25-39`
- **Title**: "AL — Warnings (25 ≤ score < 40)"
- **Query**: `suspicion_score >= 25 and suspicion_score < 40`
- **Columns**: `received_at`, `from`, `subject`, `suspicion_score`
- **Use case**: Medium-risk emails for monitoring

### Search 3: SPF/DKIM/DMARC Fails
- **ID**: `al-spf-dkim-dmarc-fails`
- **Title**: "AL — SPF/DKIM/DMARC Fails"
- **Query**: `headers_authentication_results : ("spf=fail" or "dkim=fail" or "dmarc=fail")`
- **Columns**: `received_at`, `from`, `subject`, `headers_authentication_results`, `suspicion_score`
- **Use case**: Authentication failure analysis

### Search 4: Reply-To Mismatch
- **ID**: `al-replyto-mismatch`
- **Title**: "AL — Reply-To mismatch"
- **Query**: `explanations : "Reply-To domain differs"`
- **Columns**: `received_at`, `from`, `reply_to`, `subject`, `suspicion_score`
- **Use case**: Detect reply-to hijacking attempts

### Search 5: Young Domains (< 30 days)
- **ID**: `al-young-domains`
- **Title**: "AL — Young domains (< 30 days)"
- **Query**: `explanations : "Domain age < 30 days"`
- **Columns**: `received_at`, `from`, `from_domain`, `suspicion_score`
- **Use case**: Track domain enrichment worker effectiveness

### Search 6: Risky Attachments
- **ID**: `al-risky-attachments`
- **Title**: "AL — Risky attachments (.docm/.zip)"
- **Query**: `explanations : "Contains risky attachment"`
- **Columns**: `received_at`, `from`, `subject`, `attachments.filename`, `suspicion_score`
- **Use case**: Executable/macro file monitoring

**Why KQL-based searches?**
- ✅ Version-agnostic (safe across Kibana minor versions)
- ✅ Human-readable and auditable
- ✅ Easy to customize (edit query in Discover)
- ✅ Reliable references to pipeline `explanations[]` text
- ❌ Avoid brittle Lens JSON (breaks on schema changes)

## 3. Lightweight Dashboard Shell

**File**: `infra/kibana/dashboard_shell_v31.ndjson`

Creates empty dashboard:
- **ID**: `al-risk-v31-overview`
- **Title**: "ApplyLens — Email Risk v3.1 Overview"
- **Description**: "Overview shell; open saved searches and add visualizations in-app."
- **Panels**: Empty (add saved searches and Lens charts interactively)

**Import this, then**:
1. Open dashboard in Kibana
2. Click "Add panel" → "Add from library" → Select saved searches
3. Build Lens charts (see section 5) and add to dashboard

## 4. Import Commands

### PowerShell (Windows)

```powershell
$KBN = "http://localhost:5601/kibana"
$AUTH = "elastic:elasticpass"
$enc = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($AUTH))

function Import-NDJSON($path) {
  $boundary = [Guid]::NewGuid().ToString()
  $LF = "`r`n"
  $blob = Get-Content $path -Raw
  $body = "--$boundary$LF" +
  "Content-Disposition: form-data; name=`"file`"; filename=`"$([IO.Path]::GetFileName($path))`"$LF" +
  "Content-Type: application/ndjson$LF$LF" + $blob + "$LF--$boundary--$LF"
  Invoke-RestMethod -Uri "$KBN/api/saved_objects/_import?createNewCopies=false" `
    -Method POST -Headers @{ "kbn-xsrf"="true"; "Authorization"="Basic $enc"; "Content-Type"="multipart/form-data; boundary=$boundary" } -Body $body
}

Import-NDJSON "infra/kibana/dv_emails_aliased.ndjson"
Import-NDJSON "infra/kibana/saved_searches_v31.ndjson"
Import-NDJSON "infra/kibana/dashboard_shell_v31.ndjson"
```

### Bash (macOS/Linux)

```bash
KBN="http://localhost:5601/kibana"
AUTH="elastic:elasticpass"

curl -s -u "$AUTH" -H "kbn-xsrf: true" \
  -F "file=@infra/kibana/dv_emails_aliased.ndjson;type=application/ndjson" \
  "$KBN/api/saved_objects/_import?createNewCopies=false" | jq

curl -s -u "$AUTH" -H "kbn-xsrf: true" \
  -F "file=@infra/kibana/saved_searches_v31.ndjson;type=application/ndjson" \
  "$KBN/api/saved_objects/_import?createNewCopies=false" | jq

curl -s -u "$AUTH" -H "kbn-xsrf: true" \
  -F "file=@infra/kibana/dashboard_shell_v31.ndjson;type=application/ndjson" \
  "$KBN/api/saved_objects/_import?createNewCopies=false" | jq
```

**Expected output** (each import):
```json
{
  "success": true,
  "successCount": 1,
  "successResults": [
    {
      "type": "index-pattern",
      "id": "applylens-emails-alias",
      "meta": { "title": "gmail_emails-*" }
    }
  ]
}
```

## 5. Add Charts in 60 Seconds (In-App)

Build these **3 essential charts** directly in Kibana using Lens (no JSON export needed):

### Chart 1: Suspicion Score Over Time (Stacked Line)

**Steps**:
1. Analytics → Visualize Library → **Create visualization**
2. Select data view: **gmail_emails-\***
3. Chart type: **Line** (stacked)
4. Configuration:
   - **X-axis**: `@timestamp` (or `received_at`) → Histogram → Interval: **1 hour**
   - **Y-axis**: **Count**
   - **Break down by**: Filters:
     * Filter 1: `suspicion_score >= 40` → Label: **"High"**
     * Filter 2: `suspicion_score >= 25 and suspicion_score < 40` → Label: **"Warn"**
     * Filter 3: `suspicion_score < 25` → Label: **"Low"**
5. **Save as**: "AL — Suspicion Levels Over Time"

**Result**: Stacked line chart showing risk distribution over time (High/Warn/Low).

### Chart 2: Top Explanations (Last 7 Days)

**Steps**:
1. Analytics → Visualize Library → **Create visualization**
2. Select data view: **gmail_emails-\***
3. Chart type: **Bar** (horizontal)
4. Configuration:
   - **Y-axis**: **Count**
   - **X-axis**: **Top values** of `explanations.keyword` → Size: **10**
   - **Filter**: `@timestamp >= now-7d`
5. **Save as**: "AL — Top Reasons (7d)"

**Result**: Horizontal bar chart showing most common phishing signals (e.g., "Reply-To domain differs", "SPF/DKIM/DMARC fail").

### Chart 3: Top Sender Domains in High Risk

**Steps**:
1. Analytics → Visualize Library → **Create visualization**
2. Select data view: **gmail_emails-\***
3. Chart type: **Bar** (vertical)
4. Configuration:
   - **X-axis**: **Top values** of `from_domain.keyword` → Size: **10**
   - **Y-axis**: **Count**
   - **Filter**: `suspicion_score >= 40`
5. **Save as**: "AL — High Risk: Top Sender Domains"

**Result**: Vertical bar chart showing domains with most high-risk emails.

**Add to dashboard**:
1. Open dashboard: "ApplyLens — Email Risk v3.1 Overview"
2. Click **Edit** → **Add panel** → **Add from library**
3. Select all 3 saved visualizations
4. Arrange panels and **Save**

## 6. Handy KQL Snippets

Use these in Discover or as dashboard filters:

### Risk Levels

```kuery
# High risk
suspicion_score >= 40

# Warnings
suspicion_score >= 25 and suspicion_score < 40

# Low risk
suspicion_score < 25
```

### v3.1 Signals

```kuery
# SPF/DKIM/DMARC fails
headers_authentication_results : ("spf=fail" or "dkim=fail" or "dmarc=fail")

# Reply-To mismatch (v3.1 reason text)
explanations : "Reply-To domain differs"

# Link shorteners / anchor mismatch
body_text : ("bit.ly" or "lnkd.in" or "tinyurl") or explanations : "Anchor text and href domain differ"

# Risky attachments
explanations : "Contains risky attachment"

# Young domain signal
explanations : "Domain age < 30 days"

# Brand mention off-brand domain
explanations : "Brand mention on off-brand domain"
```

### Combined Queries

```kuery
# High risk with authentication failures
suspicion_score >= 40 and headers_authentication_results : ("spf=fail" or "dkim=fail" or "dmarc=fail")

# Young domains with high score
explanations : "Domain age < 30 days" and suspicion_score >= 40

# Attachments with shorteners (double red flag)
explanations : ("Contains risky attachment" and "Uses link shortener")
```

## 7. Quick ES CLI Spot-Checks (No UI)

Verify v3.1 signals directly via Elasticsearch API:

### Count by Suspicious Flag

```bash
ES_URL="http://localhost:9200"
curl -s "$ES_URL/gmail_emails-*/_search" -H 'Content-Type: application/json' -d '{
  "size": 0,
  "aggs": {
    "by_suspicious": {
      "terms": {
        "field": "suspicious"
      }
    }
  }
}' | jq '.aggregations.by_suspicious.buckets'
```

**Expected output**:
```json
[
  { "key": "false", "key_as_string": "false", "doc_count": 9432 },
  { "key": "true", "key_as_string": "true", "doc_count": 87 }
]
```

### Top Explanations

```bash
curl -s "$ES_URL/gmail_emails-*/_search" -H 'Content-Type: application/json' -d '{
  "size": 0,
  "aggs": {
    "ex": {
      "terms": {
        "field": "explanations.keyword",
        "size": 10
      }
    }
  }
}' | jq '.aggregations.ex.buckets'
```

**Expected output**:
```json
[
  { "key": "Reply-To domain differs from From domain", "doc_count": 42 },
  { "key": "SPF/DKIM/DMARC authentication failed", "doc_count": 38 },
  { "key": "Contains risky attachment (.docm, .zip)", "doc_count": 15 },
  { "key": "Brand mention on off-brand domain", "doc_count": 12 }
]
```

### Score Distribution

```bash
curl -s "$ES_URL/gmail_emails-*/_search" -H 'Content-Type: application/json' -d '{
  "size": 0,
  "aggs": {
    "score_ranges": {
      "range": {
        "field": "suspicion_score",
        "ranges": [
          { "key": "Low (0-24)", "to": 25 },
          { "key": "Warn (25-39)", "from": 25, "to": 40 },
          { "key": "High (40+)", "from": 40 }
        ]
      }
    }
  }
}' | jq '.aggregations.score_ranges.buckets'
```

## 8. End-to-End Validation Path

Follow this path to validate the complete v3.1 dashboard setup:

### Step 1: Seed Test Fixtures

```bash
ES_URL=http://localhost:9200 python scripts/generate_test_emails.py
```

**Expected**: 7 test emails indexed to `gmail_emails-999999`

### Step 2: Import Dashboard Objects

**PowerShell**:
```powershell
# Use Import-NDJSON function from section 4
Import-NDJSON "infra/kibana/dv_emails_aliased.ndjson"
Import-NDJSON "infra/kibana/saved_searches_v31.ndjson"
Import-NDJSON "infra/kibana/dashboard_shell_v31.ndjson"
```

**Bash**:
```bash
# Use curl commands from section 4
```

**Expected**: 3 successful imports (data view, 6 saved searches, 1 dashboard)

### Step 3: Open Saved Searches in Discover

Navigate to **Analytics** → **Discover** → **Open** → **Saved searches**

**Test each search**:

#### AL — High Risk (score ≥ 40)
- **Expected**: 5-6 emails visible
  * tc1-brand-mismatch (105+ pts)
  * tc3-spf-dmarc-fail (40+ pts)
  * tc4-shortener-anchor-mismatch (30+ pts)
  * tc5-risky-attachments (20+ pts)
  * tc6-young-domain (30+ pts with enrichment)
- **Not shown**: tc2-replyto-mismatch (15 pts), tc7-ok-control (0 pts)

#### AL — Reply-To mismatch
- **Expected**: 1 email visible
  * tc2-replyto-mismatch (from domain ≠ reply-to domain)

#### AL — Young domains (< 30 days)
- **Expected**: 1 email visible (if enrichment seeded)
  * tc6-young-domain (domain age 7 days)
- **Empty**: If domain enrichment worker hasn't run yet

#### AL — SPF/DKIM/DMARC Fails
- **Expected**: 1 email visible
  * tc3-spf-dmarc-fail (all auth headers fail)

#### AL — Risky attachments
- **Expected**: 1 email visible
  * tc5-risky-attachments (invoice.docm, archive.zip)

### Step 4: Build Lens Charts (60 seconds total)

Follow instructions in **section 5** to create:
1. AL — Suspicion Levels Over Time (stacked line)
2. AL — Top Reasons (7d) (horizontal bar)
3. AL — High Risk: Top Sender Domains (vertical bar)

**Expected**: 3 saved visualizations in Library

### Step 5: Add Panels to Dashboard

1. Open dashboard: "ApplyLens — Email Risk v3.1 Overview"
2. Click **Edit** → **Add panel** → **Add from library**
3. Add saved searches:
   - AL — High Risk (score ≥ 40)
   - AL — Warnings (25 ≤ score < 40)
   - AL — Reply-To mismatch
4. Add visualizations:
   - AL — Suspicion Levels Over Time
   - AL — Top Reasons (7d)
   - AL — High Risk: Top Sender Domains
5. **Save**

**Expected**: Dashboard with 6 panels (3 saved searches + 3 charts)

### Step 6: Verify Dashboard

**Visual checks**:
- ✅ Time series shows spike when fixtures were indexed
- ✅ Top Reasons shows "Brand mention on off-brand domain", "Reply-To domain differs", etc.
- ✅ Top Sender Domains shows test domains (new-hire-team-hr.com, suspicious-bank-alert.com, etc.)
- ✅ Saved searches display test emails

**CLI verification**:
```bash
# Count high-risk emails
curl -s "$ES_URL/gmail_emails-999999/_count?q=suspicion_score:>=40" | jq '.count'
# Expected: 5-6

# Check explanations
curl -s "$ES_URL/gmail_emails-999999/_search?size=10" | jq '.hits.hits[]._source | {id, suspicion_score, explanations}'
```

## Usage

### Daily Workflow

1. **Morning review**: Open "AL — High Risk (score ≥ 40)" saved search
2. **Triage**: Review flagged emails, click through to full details
3. **Feedback**: Use EmailRiskBanner buttons (Mark as Scam / Mark as Legit)
4. **Monitor trends**: Check dashboard for anomalies (spike in young domains, auth failures, etc.)

### Weekly Analysis

1. Open dashboard: "ApplyLens — Email Risk v3.1 Overview"
2. Adjust time range to **Last 7 days**
3. Review:
   - Suspicion levels over time (any spikes?)
   - Top reasons (which signals firing most?)
   - Top sender domains (repeat offenders?)
4. Export saved search to CSV for deeper analysis

### Monthly Tuning

1. Query false positives: `user_feedback_verdict="legit" and suspicious=true`
2. Query false negatives: `user_feedback_verdict="scam" and suspicious=false`
3. Adjust pipeline weights in `infra/elasticsearch/pipelines/emails_v3.json`
4. Re-test with test generator: `python scripts/generate_test_emails.py`

## Customization

### Add New Saved Search

**Example**: "AL — Link Shorteners"

1. Open **Discover** → Data view: `gmail_emails-*`
2. Query: `body_text : ("bit.ly" or "lnkd.in" or "tinyurl")`
3. Columns: `received_at`, `from`, `subject`, `body_text`, `suspicion_score`
4. **Save** → Title: "AL — Link Shorteners"
5. Add to dashboard via "Add from library"

### Modify Existing Search

1. Open saved search in **Discover**
2. Edit query (e.g., change threshold: `suspicion_score >= 60`)
3. Add/remove columns
4. **Save** → **Save as new** (to keep original)

### Export Saved Searches

**CLI export** (backup):
```bash
curl -s -u elastic:elasticpass \
  "http://localhost:5601/kibana/api/saved_objects/_export" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "search",
    "includeReferencesDeep": true
  }' > saved_searches_backup.ndjson
```

## Troubleshooting

### "Index pattern not found"

**Problem**: Data view `applylens-emails-alias` doesn't exist

**Solution**:
```bash
# Re-import data view
Import-NDJSON "infra/kibana/dv_emails_aliased.ndjson"
```

### "No results" in saved searches

**Problem**: No emails match query

**Solution**:
1. Check if emails exist: `curl "$ES_URL/gmail_emails-*/_count"`
2. Verify suspicion_score field: `curl "$ES_URL/gmail_emails-*/_search?size=1" | jq '.hits.hits[]._source.suspicion_score'`
3. Generate test emails: `python scripts/generate_test_emails.py`

### "Dashboard is empty"

**Problem**: Panels not added yet

**Solution**: This is expected! Dashboard shell is empty by design. Follow **section 5** to add charts.

### "Import failed: Conflict"

**Problem**: Objects already exist

**Solution**: Use `createNewCopies=true` in import URL:
```powershell
Invoke-RestMethod -Uri "$KBN/api/saved_objects/_import?createNewCopies=true" ...
```

Or delete existing objects:
```bash
curl -X DELETE -u elastic:elasticpass \
  "http://localhost:5601/kibana/api/saved_objects/dashboard/al-risk-v31-overview" \
  -H "kbn-xsrf: true"
```

## Performance Considerations

### Index Pattern Optimization

**Current**: `gmail_emails-*` (matches all rollover indices)

**Pros**: Covers all data, including test index
**Cons**: Can be slow on large datasets

**Optimization**: Create separate data views:
- Production: `gmail_emails-00*` (excludes test index 999999)
- Test: `gmail_emails-999999` (test fixtures only)

### Search Performance

**Saved searches use KQL**, which is optimized for:
- ✅ Keyword field matching (`explanations.keyword`)
- ✅ Range queries (`suspicion_score >= 40`)
- ✅ Boolean combinations (`and`, `or`)

**Slow queries** (avoid in production):
- ❌ Wildcard on text fields: `subject : *urgent*`
- ❌ Regex on large fields: `body_text : /https?:\/\/.*/`

**Optimization**: Use pipeline-generated fields instead of text matching:
- Instead of: `body_text : "bit.ly"`
- Use: `explanations : "Uses link shortener"`

## Next Steps

### Immediate (After Import)

1. ✅ Import 3 NDJSON files (data view, saved searches, dashboard)
2. ✅ Open saved searches in Discover
3. ✅ Verify test emails visible (run generator if needed)
4. ✅ Build 3 Lens charts (60 seconds each)
5. ✅ Add panels to dashboard

### Short-term (Week 1)

1. ⏳ Create production data view (exclude test index)
2. ⏳ Add more Lens visualizations:
   - Feedback breakdown (pie chart: scam/legit/unsure)
   - Auth failure trends (line chart over time)
   - Attachment types distribution (bar chart)
3. ⏳ Export dashboard to PDF (scheduled reports)
4. ⏳ Set up alerts (e.g., spike in young domains)

### Long-term (Month 1)

1. ⏳ ML integration (add ml_confidence_score field to charts)
2. ⏳ Advanced visualizations:
   - Heatmap: Risk by hour of day
   - Sankey diagram: Sender domain → Risk level → User verdict
   - Metric: False positive rate (user_feedback_verdict="legit" and suspicious=true)
3. ⏳ Automated dashboards (Kibana Canvas for executive reports)

## Related Documentation

- **Test Email Generator**: `docs/TEST_EMAIL_GENERATOR.md`
- **v3.1 Implementation**: `docs/EMAIL_RISK_V3.1_SUMMARY.md`
- **Domain Enrichment**: `docs/DOMAIN_ENRICHMENT_WORKER.md`
- **E2E Tests**: `apps/web/tests/e2e/README-email-risk.md`
- **Test Saved Search**: `docs/KIBANA_SAVED_SEARCH_TEST.md`

## Files Summary

| File | Objects | Size | Purpose |
|------|---------|------|---------|
| `dv_emails_aliased.ndjson` | 1 index-pattern | 1 line | Data view for gmail_emails-* |
| `saved_searches_v31.ndjson` | 1 index-pattern + 6 searches | 7 lines | v3.1 signal searches |
| `dashboard_shell_v31.ndjson` | 1 dashboard | 1 line | Empty dashboard shell |

**Total**: 9 Kibana objects (1 data view + 6 saved searches + 1 dashboard + 1 duplicate data view reference)

---

**Status**: 🟢 **Ready to Import**
**Approach**: Version-agnostic KQL + interactive Lens charts
**Maintenance**: Low (no brittle JSON, uses pipeline explanations)
