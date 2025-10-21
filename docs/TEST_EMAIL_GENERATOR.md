# Test Email Generator for v3.1 Phishing Detection

## Overview

The test email generator creates deterministic fixtures that trigger all v3.1 phishing detection signals, making it easy to validate the pipeline and debug specific heuristics.

## Files

- **`scripts/generate_test_emails.py`** - Python script that generates and bulk-indexes test emails
- **`scripts/deploy_email_risk_v31.sh`** - Deployment script that uploads pipeline and runs generator

## Test Cases

The generator creates 7 test emails covering all v3.1 signals:

| ID | Signals Triggered | Expected Outcome |
|----|-------------------|------------------|
| `tc1-brand-mismatch` | Brand mention (Prometric) + non-canonical domain + risky phrases ("mini home office") | `suspicious=true`, high score |
| `tc2-replyto-mismatch` | Reply-To domain differs from From domain (proton.me) | Warning/suspicious (+15 pts) |
| `tc3-spf-dmarc-fail` | SPF=fail, DKIM=fail, DMARC=fail | `suspicious=true`, high score |
| `tc4-shortener-anchor-mismatch` | URL shorteners (bit.ly, lnkd.in) + anchor text mismatch | Warning/suspicious |
| `tc5-risky-attachments` | Risky attachments (.docm macro, .zip archive) | Suspicious (+20 pts) |
| `tc6-young-domain` | Newly-registered offbrand domain (requires enrichment) | Suspicious if enriched |
| `tc7-ok-control` | Clean corporate email from @prometric.com | **NOT suspicious** (control) |

## Usage

### Quick Start

```bash
# Set Elasticsearch URL
export ES_URL="http://localhost:9200"

# Deploy pipeline + generate tests (recommended)
bash scripts/deploy_email_risk_v31.sh

# Or run generator standalone
python scripts/generate_test_emails.py
```

### Environment Variables

```bash
ES_URL=http://localhost:9200          # Elasticsearch endpoint (default: localhost:9200)
ES_INDEX=gmail_emails-999999          # Target index (default: gmail_emails-999999)
ES_PIPELINE=applylens_emails_v3       # Pipeline name (default: applylens_emails_v3)
```

### Custom Index

```bash
# Generate into a different index
ES_URL=http://localhost:9200 ES_INDEX=gmail_emails python scripts/generate_test_emails.py
```

## Verification

### Kibana Discover

Open Kibana → Discover → Index: `gmail_emails-999999`

**High-risk emails:**
```kql
suspicion_score >= 40
```

**Reply-To mismatch:**
```kql
explanations : "Reply-To domain differs*"
```

**URL shorteners:**
```kql
explanations : "Uses link shortener*" OR body_text : ("bit.ly" OR "lnkd.in")
```

**Risky attachments:**
```kql
explanations : "Contains risky attachment*" OR attachments.filename : (*.docm OR *.zip OR *.exe)
```

**Control (should NOT be suspicious):**
```kql
_id : "tc7-ok-control"
```

### Expected Results

Run this query to see suspicious/not suspicious counts:

```bash
curl -X POST "http://localhost:9200/gmail_emails-999999/_search" \
  -H 'Content-Type: application/json' \
  -d '{
  "size": 0,
  "aggs": {
    "suspicious": {
      "terms": { "field": "suspicious" }
    }
  }
}'
```

Expected output:
```json
{
  "aggregations": {
    "suspicious": {
      "buckets": [
        { "key": true, "doc_count": 5 },   // tc1, tc3, tc5 definitely; tc2, tc4 likely
        { "key": false, "doc_count": 2 }   // tc7 definitely; tc6 if no enrichment
      ]
    }
  }
}
```

## Signal Breakdown

### tc1-brand-mismatch (105+ pts expected)
- ✅ Domain mismatch: "Prometric" in body but from `careers-finetunelearning.com` (+25)
- ✅ Risky phrase: "mini home office" (+15)
- ✅ PII request: "phone, location" (+15)
- ✅ Vague role: "executive team will assign" (+15)
- ✅ SPF neutral (+5)
- ✅ DMARC none (+10)
- ✅ Reply-To mismatch (+15)

### tc2-replyto-mismatch (15+ pts)
- ✅ Reply-To domain differs from From: `proton.me` vs `finetunelearning.com` (+15)
- All other auth signals pass

### tc3-spf-dmarc-fail (40+ pts)
- ✅ SPF fail (+10)
- ✅ DKIM fail (+10)
- ✅ DMARC fail (+15)

### tc4-shortener-anchor-mismatch (30+ pts)
- ✅ URL shortener: `bit.ly` (+8)
- ✅ URL shortener: `lnkd.in` (+8)
- ✅ Anchor mismatch: href=bit.ly but text="prometric.com" (+12)

### tc5-risky-attachments (20+ pts)
- ✅ .docm macro-enabled document (+20)
- ✅ .zip archive (+20)

### tc6-young-domain (15+ pts if enriched)
- ✅ Domain age < 30 days (+15, requires enrichment)
- ✅ PII request: "ID images" (+15)
- ✅ SPF neutral (+5)

### tc7-ok-control (0 pts - should be clean)
- ❌ All checks pass, no suspicious signals

## Domain Enrichment (Optional)

To test `tc6-young-domain` with full domain age detection:

```bash
# Seed enrichment index with young domain
curl -X PUT "http://localhost:9200/domain_enrich/_doc/new-hire-team-hr.com" \
  -H 'Content-Type: application/json' \
  -d '{
    "domain": "new-hire-team-hr.com",
    "age_days": 7,
    "created_at": "2025-10-14T00:00:00Z"
  }'

# Delete and re-index tc6 to pick up enrichment
curl -X DELETE "http://localhost:9200/gmail_emails-999999/_doc/tc6-young-domain"
ES_URL=http://localhost:9200 python scripts/generate_test_emails.py
```

After re-indexing, `tc6` should show:
- `suspicion_score` increased by +15
- `explanations` includes "Domain registered < 30 days ago"

## Troubleshooting

### Generator fails with "requests module not found"

```bash
pip install requests
# or
pip3 install requests
```

### No test emails appear in index

Check pipeline exists:
```bash
curl "http://localhost:9200/_ingest/pipeline/applylens_emails_v3?pretty"
```

Check index mapping:
```bash
curl "http://localhost:9200/gmail_emails-999999/_mapping?pretty"
```

### All emails flagged as suspicious (including tc7)

Check your v3.1 pipeline weights. Control email `tc7` should have:
- ✅ SPF=pass, DKIM=pass, DMARC=pass
- ✅ No shorteners or risky attachments
- ✅ Reply-To matches From domain
- ✅ No brand mentions outside domain
- Expected score: 0-10 pts

### Suspicion scores lower than expected

Verify pipeline has v3.1 processors:
```bash
curl "http://localhost:9200/_ingest/pipeline/applylens_emails_v3" | jq '.applylens_emails_v3.processors | length'
```

Should return `5` (v3.0 base + 4 new v3.1 processors).

## Integration with CI/CD

Add to your test suite:

```yaml
# .github/workflows/test.yml
- name: Test Email Risk Pipeline
  run: |
    ES_URL=http://elasticsearch:9200 bash scripts/deploy_email_risk_v31.sh
    # Verify tc7 is not suspicious
    curl -s "http://elasticsearch:9200/gmail_emails-999999/_doc/tc7-ok-control" | \
      jq -e '._source.suspicious == false'
    # Verify tc1 is suspicious
    curl -s "http://elasticsearch:9200/gmail_emails-999999/_doc/tc1-brand-mismatch" | \
      jq -e '._source.suspicious == true and ._source.suspicion_score > 40'
```

## Next Steps

1. **Run generator**: `bash scripts/deploy_email_risk_v31.sh`
2. **Verify in Kibana**: Query `gmail_emails-999999` with KQL filters above
3. **Set up enrichment**: Create domain_enrich worker for production
4. **Monitor feedback**: Track user feedback on test cases via API

## See Also

- [EMAIL_RISK_DETECTION_V3.md](./EMAIL_RISK_DETECTION_V3.md) - Full v3.1 architecture
- [EMAIL_RISK_V3.1_SUMMARY.md](./EMAIL_RISK_V3.1_SUMMARY.md) - Implementation details
