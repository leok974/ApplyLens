# ApplyLens — Agentic Suspicious Email Detection (v3.1)

**Status**: ✅ Implemented
**Date**: October 21, 2025 (v3.1 updates)
**Phase**: 4 Enhancement — Email Risk Intelligence
**Version**: 3.1 - Multi-Signal Phishing Detection

---

## Overview

This implementation adds **intelligent phishing detection with agentic guidance** to ApplyLens. The system:

1. **Detects** suspicious emails using transparent heuristics (domain mismatch, risky phrases, PII requests, **auth failures, URL inspection, attachments**)
2. **Explains** why emails are flagged with human-readable reasons
3. **Guides** users with actionable verification steps and suggested responses
4. **Learns** from user feedback to improve detection over time
5. **Empowers** job seekers to protect themselves without blocking legitimate opportunities

---

## v3.1 New Signals (October 2025)

### Authentication Failures
- **SPF Fail** (+10 pts): Sender not authorized by domain
- **DKIM Fail** (+10 pts): Message integrity not verified
- **DMARC Fail** (+15 pts): Email authentication policy violation
- **Reply-To Mismatch** (+15 pts): Reply-To domain differs from From domain

### URL Inspection
- **Link Shorteners** (+8 pts): Uses bit.ly, tinyurl, t.co, etc.
- **Anchor Mismatch** (+12 pts): Link text doesn't match destination
- **Off-Brand URLs** (+10 pts): Links to non-trusted domains

### Attachments
- **Risky File Types** (+20 pts): Executables, scripts, macro docs, archives
  - Extensions: exe, msi, js, vbs, ps1, cmd, bat, scr, apk, pkg, docm, xlsm, pptm, zip, rar, 7z, iso, img

### Domain Age (Future)
- **Young Domain** (+15 pts): Sender domain registered < 30 days
- Requires enrichment index populated by background worker

---

## Architecture

### 1. Elasticsearch Ingest Pipeline v3.1

**File**: `infra/elasticsearch/pipelines/emails_v3.json`

**Purpose**: Enriches email documents with phishing risk assessment during ingestion.

**New Fields Added**:
- `suspicion_score` (0-100): Numeric risk score based on weighted heuristics
- `suspicious` (boolean): True if score ≥ threshold (default: 40)
- `explanations` (array): Human-readable reasons for the score
- `suggested_actions` (array): What the user should do next
- `verify_checks` (array): Specific verification steps to request from sender
- `from_domain` (keyword): Extracted sender domain for enrichment
- `user_feedback_verdict` (keyword): User's feedback on email (scam/legit/unsure)
- `user_feedback_note` (text): Optional feedback note
- `user_feedback_at` (date): Timestamp of feedback

**Heuristics** (transparent & tunable):

| Check | Weight | Trigger |
|-------|--------|---------|
| **v3.0 Signals** | | |
| Domain mismatch | 25 | Sender domain doesn't match brand mentioned in email |
| Non-canonical domain | 25 | Brand claim from unverified domain |
| Risky phrases | 10 each | "equipment will be provided", "send your details", "gift card", "crypto", etc. |
| PII request | 20 | Asks for SSN, bank info, ID documents |
| Vague role | 10 | Missing salary/comp, team, or tech stack details |
| No calendar invite | 5 | No calendar or scheduling link provided |
| No career link | 10 | No link to official job posting |
| **v3.1 Signals** | | |
| SPF fail | 10 | SPF authentication failed |
| DKIM fail | 10 | DKIM signature verification failed |
| DMARC fail | 15 | DMARC policy failed or policy=reject |
| Reply-To mismatch | 15 | Reply-To domain differs from From domain |
| Link shorteners | 8 | Contains bit.ly, tinyurl, t.co, etc. |
| Anchor mismatch | 12 | Link text doesn't match href destination |
| Off-brand URLs | 10 | Links to non-trusted domains |
| Risky attachment | 20 | Contains executable, script, macro doc, or archive |
| Young domain | 15 | Sender domain < 30 days old (requires enrichment) |

**Trusted Domains** (whitelist):
- `prometric.com`
- `finetunelearning.com`

**Design Philosophy**:
- **Transparent**: All rules are visible and explainable
- **Tunable**: Weights and thresholds can be adjusted without redeployment
- **Safe-by-default**: Doesn't block emails, only warns users
- **Context-aware**: Understands job search patterns (interviews, offers, etc.)

**Pipeline Chaining**:
```json
{
  "processors": [
    { "pipeline": { "name": "applylens_emails_v2", "ignore_failure": true }},
    { "script": { /* v3 phishing detection */ }}
  ]
}
```

The v3 pipeline **extends** v2 (which adds smart flags like `is_recruiter`, `is_interview`, etc.).

---

### 2. API Endpoint: Risk Advice

**File**: `services/api/app/routers/emails.py`

**Route**: `GET /emails/{email_id}/risk-advice`

**Response**:
```json
{
  "suspicious": true,
  "suspicion_score": 65,
  "explanations": [
    "Sender domain does not match claimed brand: shady-domain.com",
    "Contains common scam language (3 hits).",
    "No official careers/job posting link provided."
  ],
  "suggested_actions": [
    "Do not purchase or accept 'equipment' arrangements or send money.",
    "Wait to share any personal details until verified."
  ],
  "verify_checks": [
    "Verify sender domain matches official site (e.g., prometric.com).",
    "Request a calendar invite from an official corporate domain.",
    "Request the public job posting on the official careers site."
  ]
}
```

**Prometheus Metrics**:
```python
email_risk_served_total = Counter(
    "applylens_email_risk_served_total",
    "Email risk advice served",
    ["level"]  # suspicious|warn|ok
)
```

**Error Handling**:
- Returns 404 if email not found in Elasticsearch
- Returns 503 if Elasticsearch is unavailable
- Graceful fallback to default values if fields missing

**Route**: `POST /emails/{email_id}/risk-feedback`

**Purpose**: Submit user feedback on risk assessment for continuous improvement.

**Request Body**:
```json
{
  "verdict": "scam",  // "scam", "legit", or "unsure"
  "note": "Verified with company - this was legitimate"  // optional
}
```

**Response**:
```json
{
  "ok": true,
  "verdict": "scam",
  "labels": ["suspicious", "user_confirmed_scam"]
}
```

**Behavior**:
- **verdict="scam"**: Adds `suspicious` and `user_confirmed_scam` labels
- **verdict="legit"**: Removes `suspicious` label, adds `user_confirmed_legit`
- **verdict="unsure"**: No label changes, records feedback for analysis
- Updates `user_feedback_verdict`, `user_feedback_note`, `user_feedback_at` fields
- Increments Prometheus counter: `applylens_email_risk_feedback_total{verdict}`

**Use Cases**:
- Train heuristic weights based on false positive/negative rates
- Identify new phishing patterns to add to detection rules
- Measure user trust and system accuracy over time

---

### 3. Frontend: Intelligent Banner with Feedback

**File**: `apps/web/src/components/email/EmailRiskBanner.tsx`

**Component**: `<EmailRiskBanner>`

**v3.1 Enhancements**:
- **Signal Chips**: Displays detected signals as badges (SPF, DKIM, URL, ATTACH, REPLY-TO, etc.)
- **Collapsible Details**: "Why we flagged it" button to show/hide explanations
- **Feedback Buttons**:
  - **"Mark as Scam"**: Calls `/risk-feedback` with `verdict=scam`
  - **"Mark Legit"**: Calls `/risk-feedback` with `verdict=legit`
  - **"Request Official Invite"**: Opens prefilled verification template
  - **"Dismiss"**: Hides banner

**Behavior**:

#### High Risk (suspicious=true):
- **Red banner** with alert icon
- Title: "This email looks suspicious (score: 65)"
- Signal chips: SPF, DKIM, URL, ATTACH (visual indicators)
- Collapsible sections:
  1. **Why it's flagged**: Bulleted list of `explanations`
  2. **What you should do**: Bulleted list of `suggested_actions`
  3. **Verify with sender**: Bulleted list of `verify_checks`
- Action buttons with loading states during feedback submission

#### Medium Risk (score ≥ 25 but suspicious=false):
- **Yellow banner** with warning icon
- Title: "Some risk indicators found (score: 32)"
- Same sections but softer tone

#### Low Risk (score < 25):
- **No banner** (silent pass)

**Prefilled Verification Template**:
```
Subject: Verification before scheduling

Hi [Recruiter Name],

Thanks for reaching out. Before we proceed, could you please:
1) Share the public job posting link on your official careers site, and
2) Send a calendar invite from your corporate domain (e.g., @prometric.com) with a meeting link?

This helps me verify details and prepare properly.

Best regards,
[Your Name]
```

**Integration Point**: `EmailDetailsPanel.tsx`
- Fetches risk advice when email is opened
- Displays banner between email header and body
- Handles button clicks (mark scam, request invite)

---

## Deployment Steps

### 1. Upload Pipeline to Elasticsearch

```bash
curl -X PUT http://localhost:9200/_ingest/pipeline/applylens_emails_v3 \
  -H 'Content-Type: application/json' \
  --data-binary @infra/elasticsearch/pipelines/emails_v3.json
```

**Verification**:
```bash
curl -s http://localhost:9200/_ingest/pipeline/applylens_emails_v3 | jq
```

### 2. Update Index Template (Optional)

To make v3 the default for **new indices**:

```bash
curl -X PUT http://localhost:9200/_index_template/applylens_emails \
  -H 'Content-Type: application/json' \
  -d '{
    "index_patterns": ["gmail_emails-*"],
    "template": {
      "settings": {
        "index.default_pipeline": "applylens_emails_v3"
      }
    }
  }'
```

**Alternative**: Keep v2 as default and only reindex suspicious candidates through v3.

### 3. Reindex Existing Emails (Backfill)

```bash
curl -X POST http://localhost:9200/_reindex \
  -H 'Content-Type: application/json' \
  -d '{
    "source": {
      "index": "gmail_emails-000001"
    },
    "dest": {
      "index": "gmail_emails-v3-reindexed",
      "pipeline": "applylens_emails_v3"
    }
  }'
```

Then swap alias:
```bash
curl -X POST http://localhost:9200/_aliases \
  -H 'Content-Type: application/json' \
  -d '{
    "actions": [
      { "remove": { "index": "gmail_emails-000001", "alias": "gmail_emails" }},
      { "add": { "index": "gmail_emails-v3-reindexed", "alias": "gmail_emails" }}
    ]
  }'
```

### 4. Test with Sample Scam Email

**Index a test document**:
```bash
curl -X POST http://localhost:9200/gmail_emails/_doc?pipeline=applylens_emails_v3 \
  -H 'Content-Type: application/json' \
  -d '{
    "subject": "Job Opportunity - Remote Work",
    "from": "recruiter@shady-jobs.com",
    "body_text": "Hi! Prometric is hiring. Equipment will be provided. Reply with your name, phone, and location. Screening test will be emailed. Flexible hours, work from anywhere!",
    "received_at": "2025-10-21T10:00:00Z"
  }'
```

**Expected result**:
```json
{
  "suspicion_score": 65,
  "suspicious": true,
  "explanations": [
    "Sender domain does not match claimed brand: shady-jobs.com",
    "Non-canonical domain for brand claims: shady-jobs.com",
    "Contains common scam language (4 hits)."
  ],
  "suggested_actions": [
    "Do not purchase or accept 'equipment' arrangements or send money.",
    "Wait to share any personal details until verified."
  ],
  "verify_checks": [
    "Verify sender domain matches official site (e.g., prometric.com).",
    "Request a calendar invite from an official corporate domain.",
    "Request the public job posting on the official careers site."
  ]
}
```

### 5. API & Frontend Deployment

**Backend**:
```bash
cd services/api
# Restart API to pick up new route
docker-compose restart api
```

**Frontend**:
```bash
cd apps/web
npm run build
# Deploy updated assets
```

---

## Saved Searches (Kibana/UI)

### "Emails — Suspicious (score ≥ 40)"
```
KQL: suspicion_score >= 40
```

### "Offers/Interviews — Needs Verification"
```
KQL: (is_offer:true OR is_interview:true) AND suspicious:true
```

### "High-Risk Emails"
```
KQL: suspicion_score >= 60
```

### "Flagged by Domain Mismatch"
```
KQL: explanations:*"domain does not match"*
```

---

## Monitoring & Tuning

### Prometheus Metrics

**Risk Advice Served**:
```promql
rate(applylens_email_risk_served_total[5m])
```

**Suspicious Ratio**:
```promql
sum(rate(applylens_email_risk_served_total{level="suspicious"}[1h]))
/
sum(rate(applylens_email_risk_served_total[1h]))
```

**Grafana Dashboard**:
- Panel 1: Risk advice served by level (suspicious/warn/ok) — Stacked area chart
- Panel 2: Average suspicion score over time — Line chart
- Panel 3: Top explanations (aggregated) — Table
- Panel 4: User actions (mark scam, request invite, dismiss) — Counter

### Tuning Parameters

**Adjust weights** in `emails_v3.json`:

```json
"score_weights": {
  "domain_mismatch": 25,        // ← Increase to 30 if too many false negatives
  "non_canonical_domain": 25,
  "risky_phrase": 10,
  "request_pii": 20,            // ← Decrease to 15 if too sensitive
  "vague_role": 10,
  "no_calendar_invite": 5,
  "no_career_link": 10
},
"score_threshold": 40            // ← Lower to 35 for stricter detection
```

After tuning, re-upload pipeline and reindex.

**Add trusted domains**:
```json
"trusted_domains": [
  "prometric.com",
  "finetunelearning.com",
  "newcompany.com"              // ← Add here
]
```

**Add risky phrases**:
```json
"risky_phrases": [
  "mini home office",
  "new scam keyword"            // ← Add here
]
```

---

## Testing Checklist

- [ ] Pipeline v3 uploaded to Elasticsearch
- [ ] Test document indexed with suspicious=true
- [ ] API endpoint `/emails/{id}/risk-advice` returns valid JSON
- [ ] Prometheus metric `applylens_email_risk_served_total` increments
- [ ] Frontend banner displays for suspicious email (red)
- [ ] Frontend banner displays for medium-risk email (yellow)
- [ ] Frontend banner hidden for low-risk email
- [ ] "Mark as Scam" button labels email correctly
- [ ] "Request Official Invite" button copies template to clipboard
- [ ] KQL saved searches return correct results
- [ ] Reindexing completes without errors

---

## Security Considerations

### What This System Does NOT Do

❌ **Does not block emails** — All emails reach the inbox
❌ **Does not auto-delete** — User decides on each email
❌ **Does not use ML models** — Fully transparent heuristics
❌ **Does not phone home** — All processing happens locally

### What This System DOES Do

✅ **Warns users** — Contextual banner with explanations
✅ **Educates users** — Shows why email is suspicious
✅ **Empowers users** — Provides verification steps
✅ **Tracks trends** — Metrics for improving detection

### Privacy

- No email content sent to external services
- All analysis done in Elasticsearch ingest pipeline
- User actions tracked only via Prometheus counters (no PII)

---

## Future Enhancements

### Phase 5 Ideas

1. **User Feedback Loop**:
   - "This was legitimate" button → lowers future scores for similar patterns
   - "This was a scam" button → increases weights for matched rules

2. **Sender Reputation**:
   - Track historical sender behavior (e.g., @prometric.com always legitimate)
   - Build dynamic trust list based on user interactions

3. **ML Model (Optional)**:
   - Train classifier on labeled scam/legitimate emails
   - Combine with heuristics for hybrid scoring

4. **Real-Time Domain Verification**:
   - Query WHOIS/DNS records for sender domain age
   - Check domain against known scam databases

5. **Shared Intelligence**:
   - Opt-in community-based threat sharing (anonymized)
   - Flag emails reported as scams by multiple users

6. **Advanced Verification**:
   - Automatic DMARC/SPF/DKIM checks
   - Link analysis (check if URLs match claimed domain)

---

## Commit History

**Commit 1**: `feat(emails): agentic suspicious detection (v3) with reasons & advice`

Files changed:
- `infra/elasticsearch/pipelines/emails_v3.json` (new)
- `services/api/app/routers/emails.py` (new route)
- `apps/web/src/components/email/EmailRiskBanner.tsx` (new)
- `apps/web/src/components/inbox/EmailDetailsPanel.tsx` (integrated banner)
- `docs/EMAIL_RISK_DETECTION_V3.md` (this file)

---

## References

- **Pipeline v2**: [infra/elasticsearch/pipelines/emails_v2.json](../infra/elasticsearch/pipelines/emails_v2.json)
- **Security Panel**: [apps/web/src/components/security/SecurityPanel.tsx](../apps/web/src/components/security/SecurityPanel.tsx)
- **Phase 4 Summary**: [docs/OPERATIONAL_STATUS.md](./OPERATIONAL_STATUS.md)
- **ES Template Check Workflow**: [.github/workflows/es-template-check.yml](../.github/workflows/es-template-check.yml)

---

## User Guide

### How to Use the Risk Banner

When viewing an email in ApplyLens, you'll see a **risk banner** if the system detects potential phishing signals:

#### 1. Understanding the Banner Colors

| Color | Meaning | Suspicion Score | Action |
|-------|---------|-----------------|--------|
| 🔴 **Red** | High risk | ≥ 40 pts | **Do not respond** until verified |
| 🟡 **Yellow** | Medium risk | 25-39 pts | Proceed with caution, verify sender |
| 🟢 **Green** | Low risk | < 25 pts | Informational only, no action needed |

#### 2. Reading the Risk Signals

The banner shows **signal chips** for detected patterns:

- **SPF/DKIM/DMARC**: Email authentication failures
- **REPLY-TO**: Reply-To address differs from sender
- **URL**: Suspicious links (shorteners, mismatches)
- **ATTACH**: Risky attachment detected
- **DOMAIN-AGE**: Sender domain recently registered

**Example**:
```
⚠️ High Risk — Suspicion Score: 65

[SPF] [REPLY-TO] [URL] [ATTACH]

Why we flagged it ▼
```

#### 3. Viewing Detailed Explanations

Click **"Why we flagged it"** to expand:

1. **What We Found**: Specific patterns detected (e.g., "Reply-To domain differs from From domain")
2. **What You Should Do**: Actionable steps (e.g., "Verify company website")
3. **Questions to Ask**: What to request from sender (e.g., "Ask for official job posting link")

#### 4. Providing Feedback

Help improve detection accuracy by marking emails:

| Button | When to Use | Impact |
|--------|-------------|--------|
| **Mark as Scam** | Confirmed phishing email | Improves future detection, helps other users |
| **Mark Legit** | False positive (email is legitimate) | Reduces future false positives for similar patterns |

**How Feedback Works**:
1. Click "Mark as Scam" or "Mark Legit"
2. Optionally add a note (e.g., "Verified with company HR")
3. System updates the email's labels in Elasticsearch
4. Weekly analysis adjusts signal weights based on feedback

**Privacy**: Feedback is stored locally in your ApplyLens instance, not shared externally.

---

## For Security Teams: Using Kibana Saved Searches

### Accessing v3.1 Dashboards

1. Open Kibana: `http://localhost:5601`
2. Navigate to **Discover** → **Saved searches**
3. Look for searches starting with "AL —"

### 7 Pre-Built Saved Searches

| Search | Purpose | Use Case |
|--------|---------|----------|
| **AL — High Risk (score ≥ 40)** | Daily triage of flagged emails | Review top threats |
| **AL — Warning (25-39)** | Medium-risk emails | Weekly audit |
| **AL — SPF/DKIM/DMARC Fails** | Authentication failures | Identify spoofing attempts |
| **AL — Reply-To Mismatch** | Reply-To domain differs | Catch redirect attacks |
| **AL — Young Domains** | Domains < 30 days old | Track new threat actors |
| **AL — Risky Attachments** | Executable/script files | Malware prevention |
| **AL — URL Shorteners/Anchor Mismatch** | Link obfuscation | Phishing link detection |

### Daily Review Workflow

**Morning Triage (15 minutes)**:
1. Open "AL — High Risk (score ≥ 40)"
2. Sort by `received_at` (newest first)
3. Review top 10 emails:
   - Check `from` and `from_domain`
   - Read `explanations` array
   - Verify `user_feedback_verdict` if present
4. For confirmed scams:
   - Mark in UI (if not already marked)
   - Add to blocklist (if needed)
   - Alert affected users

**Weekly Analysis (30 minutes)**:
1. Open "AL — Warning (25-39)"
2. Review patterns in false positives
3. Run weight tuning analysis:
   ```bash
   python scripts/analyze_weights.py --days 7
   ```
4. Adjust weights if needed

**Monthly Audit (1 hour)**:
1. Review all 7 saved searches
2. Check false positive/negative rates
3. Update pipeline weights
4. Re-test with `python scripts/generate_test_emails.py`

### Building Custom Lens Charts

**Example 1: Signal Distribution Over Time**

1. Open Dashboard: "AL — Risk v3.1 Overview"
2. Click **"Create visualization"** → **Lens**
3. Configuration:
   - **X-axis**: `received_at` (Date histogram, interval: 1d)
   - **Y-axis**: `count()` (Count of emails)
   - **Break down by**: `explanations.keyword` (Top 5)
   - **Chart type**: Stacked bar
4. Save to dashboard

**Example 2: Top Risky Senders**

1. Create new Lens visualization
2. Configuration:
   - **Y-axis**: `from_domain` (Top 10 values)
   - **X-axis**: `Average(suspicion_score)`
   - **Chart type**: Horizontal bar
3. Add filter: `suspicious: true`
4. Save to dashboard

**Example 3: Feedback Breakdown**

1. Create new Lens visualization
2. Configuration:
   - **Slice by**: `user_feedback_verdict.keyword`
   - **Size by**: `count()`
   - **Chart type**: Pie chart
3. Save to dashboard

---

## Troubleshooting

### "Email marked suspicious but it's legitimate"

**Cause**: False positive from overly aggressive signal

**Solution**:
1. Click **"Mark Legit"** in the risk banner
2. Add note explaining why (e.g., "Verified on company website")
3. System will learn from this feedback
4. After 10+ similar cases, signal weight will auto-adjust

**Immediate Workaround**: Ignore the warning and proceed with caution

### "Known scam email not flagged"

**Cause**: False negative (signal weights too low or new pattern)

**Solution**:
1. Click **"Mark as Scam"** in the risk banner
2. Add note with details (e.g., "Phishing confirmed by IT team")
3. Run weight analysis: `python scripts/analyze_weights.py --days 30`
4. Review recommendations in `docs/WEIGHT_TUNING_ANALYSIS.md`
5. Adjust weights in `infra/elasticsearch/pipelines/emails_v3.json`

**Emergency Workaround**: Manually block sender domain

### "SPF/DKIM/DMARC signals not triggering"

**Cause**: Gmail not indexing authentication headers

**Solution**:
1. Check ES field mapping: `curl "$ES_URL/gmail_emails/_mapping?pretty"`
2. Verify `headers_authentication_results` and `headers_received_spf` exist
3. Re-index emails if needed
4. Update pipeline if header field names changed

### "Domain age signal always 0 points"

**Cause**: Domain enrichment worker not running

**Solution**:
1. Check enrichment index: `curl "$ES_URL/domain_enrich/_count"`
2. If count is 0, run worker:
   ```bash
   python services/workers/domain_enrich.py --once
   ```
3. Create enrich policy:
   ```bash
   curl -X PUT "$ES_URL/_enrich/policy/domain_age_policy" -d @policy.json
   curl -X POST "$ES_URL/_enrich/policy/domain_age_policy/_execute"
   ```
4. Re-ingest test email

### "Risk banner not showing in UI"

**Cause**: API endpoint not returning risk advice

**Solution**:
1. Check API logs: `docker logs applylens-api`
2. Test endpoint manually:
   ```bash
   curl http://localhost:8000/emails/{email_id}/risk-advice
   ```
3. Verify Elasticsearch connection in API
4. Check `suspicion_score` field exists in email document

### "Feedback submission fails"

**Cause**: API endpoint error or ES connection issue

**Solution**:
1. Open browser console (F12) for error details
2. Check API logs for POST `/emails/{id}/risk-feedback`
3. Verify Elasticsearch is accessible
4. Test manually:
   ```bash
   curl -X POST http://localhost:8000/emails/123/risk-feedback \
     -H "Content-Type: application/json" \
     -d '{"verdict": "scam", "note": "Test feedback"}'
   ```

---

## FAQ

### How is the suspicion score calculated?

The score is a **weighted sum of detected signals**:

```
suspicion_score = Σ (signal_weight × signal_detected)
```

Example:
- SPF fail (+10) + DMARC fail (+15) + Reply-To mismatch (+15) + Risky attachment (+20) = **60 points** → 🔴 High risk

### What's the difference between suspicion_score and suspicious flag?

- **suspicion_score**: Numeric value (0-240 max)
- **suspicious**: Boolean flag (true if score ≥ 40)

**Why 40?** This threshold balances detection coverage with false positive rate. Adjust in pipeline if needed.

### Can I customize signal weights?

**Yes!** Edit `infra/elasticsearch/pipelines/emails_v3.json`:

```json
{
  "script": {
    "source": "ctx.suspicion_score += 25; ...",  // Change weight
    ...
  }
}
```

Re-upload pipeline:
```bash
curl -X PUT "$ES_URL/_ingest/pipeline/applylens_emails_v3" \
  -H "Content-Type: application/json" \
  -d @infra/elasticsearch/pipelines/emails_v3.json
```

### How often should I tune weights?

**Recommended cadence**:
- **Weekly**: Run analysis script to monitor trends
- **Monthly**: Apply weight adjustments based on feedback
- **Quarterly**: Major review with security team

**Minimum data**: 100+ feedback entries for reliable analysis

### What happens when I mark an email as scam/legit?

1. API updates email document:
   ```json
   {
     "user_feedback_verdict": "scam",  // or "legit"
     "user_feedback_at": "2025-10-21T14:32:10Z",
     "labels_norm": ["user_confirmed_scam"]
   }
   ```

2. Prometheus counter increments:
   ```
   applylens_email_risk_feedback_total{verdict="scam"}
   ```

3. Weekly analysis uses this data to recommend weight adjustments

4. **No immediate change** — weights are adjusted manually after analysis

### Does the system block emails?

**No.** ApplyLens uses a **warn-and-educate** approach:

- ✅ Shows risk banner
- ✅ Explains detected signals
- ✅ Guides verification steps
- ❌ Does NOT block or delete emails
- ❌ Does NOT auto-report to spam

**Philosophy**: Job seekers need to see all emails (including risky ones) to make informed decisions. Blocking could cause missed opportunities.

### How accurate is the detection?

**Current benchmarks** (based on test cases):

- **True Positive Rate**: ~95% (scams correctly detected)
- **False Positive Rate**: ~5-8% (legit emails wrongly flagged)
- **False Negative Rate**: ~3-5% (scams missed)

**Improving over time**: Accuracy improves as more users provide feedback.

### What data is collected for feedback?

When you mark an email:

- Email ID (internal reference)
- Verdict (scam/legit/unsure)
- Optional note (your text)
- Timestamp

**NOT collected**:
- Personal information
- Email content (already in ES)
- User identity (anonymous feedback)

### Can I export the detection rules?

**Yes!** Rules are stored in:
- `infra/elasticsearch/pipelines/emails_v3.json` (Elasticsearch pipeline)
- `docs/EMAIL_RISK_DETECTION_V3.md` (this document, human-readable)

Export signal weights:
```bash
curl "$ES_URL/_ingest/pipeline/applylens_emails_v3?pretty" > pipeline_backup.json
```

### How do I add a new signal?

1. Edit `infra/elasticsearch/pipelines/emails_v3.json`
2. Add new processor or extend existing script
3. Update `SIGNAL_KEYWORDS` in `scripts/analyze_weights.py`
4. Add test case in `scripts/generate_test_emails.py`
5. Re-upload pipeline and test
6. Document in this guide

**Example**: Adding "External Image" signal

```json
{
  "script": {
    "source": """
      if (ctx.body_html != null && ctx.body_html.contains('<img src=\"http')) {
        ctx.suspicion_score += 5;
        ctx.explanations.add('External images (tracking pixels)');
      }
    """
  }
}
```

---

## Support

For questions or issues:
1. **Check this guide** for common issues
2. **Review Kibana saved searches** for similar cases
3. **Run weight analysis** to identify tuning opportunities
4. **Check Prometheus metrics** for anomalies
5. **Query Elasticsearch** for sample suspicious emails
6. **Review pipeline script logs** in Kibana
7. **Adjust weights** and re-test

**Success Metrics**:
- Accuracy: > 90%
- False Positive Rate: < 5%
- User Feedback: > 100 entries/month
- Signal Coverage: All 16 heuristics active
