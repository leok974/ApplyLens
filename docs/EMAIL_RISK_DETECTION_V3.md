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

## Support

For questions or issues:
1. Check Prometheus metrics for anomalies
2. Query Elasticsearch for sample suspicious emails
3. Review pipeline script logs in Kibana
4. Adjust weights and re-test

**Success Metric**: < 5% false positive rate (legitimate emails flagged as suspicious)
