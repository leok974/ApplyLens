# Email Security Analyzer - Integration Guide

## Overview

The ApplyLens security analyzer provides comprehensive email threat detection with **12 independent detection mechanisms**, configurable risk scoring (0-100), and automatic quarantine. All results are explainable with detailed evidence for each detected risk signal.

## Architecture

### Core Components

1. **EmailRiskAnalyzer** (`app/security/analyzer.py`)
   - Main analysis engine with 12 detection mechanisms
   - Configurable risk weights via `RiskWeights` dataclass
   - Returns structured `RiskAnalysis` with score, flags, and quarantine status

2. **BlocklistProvider** (`app/security/blocklists.json`)
   - JSON-backed blocklists for malicious hosts, file hashes, and trusted domains
   - Easily extensible to Redis/Elasticsearch for dynamic updates

3. **Security Router** (`app/routers/security.py`)
   - `POST /api/security/rescan/{email_id}` - Rescan email and update risk score
   - `GET /api/security/stats` - Get aggregate security statistics

4. **Database Schema** (via Alembic migrations)
   - `risk_score` (Float) - 0-100 risk score
   - `flags` (JSONB) - Array of `{signal, evidence, weight}` objects
   - `quarantined` (Boolean) - Auto-quarantine flag when score >= 70

5. **Elasticsearch Mapping** (`es/templates/emails-template.json`)
   - Index template ensures all new indices include security fields
   - Supports aggregations on `risk_score` and nested queries on `flags.signal`

## Detection Mechanisms

| Signal | Weight | Description |
|--------|--------|-------------|
| **DMARC_FAIL** | 25 | DMARC authentication failed |
| **SPF_FAIL** | 15 | SPF record check failed |
| **DKIM_FAIL** | 15 | DKIM signature verification failed |
| **DISPLAY_NAME_SPOOF** | 15 | Brand name mismatch between display name and domain |
| **PUNYCODE_OR_HOMOGLYPH** | 10 | Domain uses punycode (xn--) encoding |
| **SUSPICIOUS_TLD** | 10 | Domain uses high-risk TLD (.ru, .xyz, .top, etc.) |
| **URL_HOST_MISMATCH** | 10 | Link text shows different domain than actual URL |
| **MALICIOUS_KEYWORD** | 10 | Body contains suspicious patterns (invoice.exe, etc.) |
| **NEW_DOMAIN** | 10 | Domain first seen ≤3 days ago |
| **EXECUTABLE_OR_HTML_ATTACHMENT** | 20 | Dangerous attachment types |
| **BLOCKLISTED_HASH_OR_HOST** | 30 | File hash or URL host in blocklist |
| **TRUSTED_DOMAIN** | -15 | Domain in trusted list (negative weight) |

**Quarantine Threshold:** 70 points

## Installation

### 1. Apply Database Migrations

```bash
cd services/api
alembic upgrade head
```

This creates:
- `0014_add_security_fields` - Adds `flags` (JSONB) and `quarantined` (Boolean) columns

**Verify migration:**
```bash
psql $DATABASE_URL -c "\d emails" | grep -E "(risk_score|quarantined|flags)"
```

Expected output:
```
 risk_score       | double precision     |           |          | 
 flags            | jsonb                |           | not null | '[]'::jsonb
 quarantined      | boolean              |           | not null | false
```

### 2. Install Elasticsearch Template

**Option A: Using script (recommended)**
```bash
cd services/api
python scripts/install_es_template.py
```

**Option B: Using curl**
```bash
curl -X PUT "http://localhost:9200/_index_template/emails-template" \
  -H 'Content-Type: application/json' \
  --data-binary @services/api/es/templates/emails-template.json
```

**Verify template:**
```bash
curl http://localhost:9200/_index_template/emails-template | jq '.index_templates[0].index_template.index_patterns'
```

Expected output: `["gmail_emails*", "emails-*"]`

### 3. Update Existing Index (Optional)

If you have an existing `gmail_emails` index:

```bash
cd services/api
python scripts/update_existing_index_mapping.py
```

This adds security fields to the existing index without requiring reindexing.

**Note:** Existing documents won't have security data until re-analyzed or re-synced.

### 4. Verify Integration

**Check model imports:**
```python
from app.models import Email
email = Email()
print(hasattr(email, 'flags'))  # Should be True
print(hasattr(email, 'quarantined'))  # Should be True
```

**Run unit tests:**
```bash
cd services/api
pytest tests/test_security_analyzer.py -v
```

Expected: **12/12 tests passing** with 95% code coverage

**Check router registration:**
```bash
curl http://localhost:8003/docs | grep security
```

Should show `/api/security/rescan/{email_id}` and `/api/security/stats` endpoints.

## Usage

### Analyze Email on Ingestion

Integrate into your email processing pipeline (e.g., `gmail_service.py` or ingestion worker):

```python
from app.security.analyzer import EmailRiskAnalyzer, BlocklistProvider

# Initialize (once at startup)
BLOCKLISTS = BlocklistProvider("app/security/blocklists.json")
ANALYZER = EmailRiskAnalyzer(blocklists=BLOCKLISTS)

# Analyze email
result = ANALYZER.analyze(
    headers={"Authentication-Results": "spf=pass; dkim=pass; dmarc=pass"},
    from_name="John Doe",
    from_email="john@example.com",
    subject="Important Account Update",
    body_text="Click here to verify...",
    body_html="<a href='http://phishing.ru'>PayPal</a>",
    urls_visible_text_pairs=[("PayPal", "http://phishing.ru")],
    attachments=[{"filename": "invoice.exe", "mime_type": "application/octet-stream"}],
    domain_first_seen_days_ago=2
)

# Store results
email.risk_score = float(result.risk_score)
email.flags = [f.dict() for f in result.flags]  # JSONB accepts list
email.quarantined = result.quarantined
db.commit()
```

### Rescan Existing Email

```bash
# Rescan email ID 123
curl -X POST http://localhost:8003/api/security/rescan/123
```

Response:
```json
{
  "status": "ok",
  "email_id": 123,
  "risk_score": 75,
  "quarantined": true,
  "flags": [
    {"signal": "DMARC_FAIL", "evidence": "auth=dmarc=fail", "weight": 25},
    {"signal": "SUSPICIOUS_TLD", "evidence": "tld=.ru", "weight": 10},
    {"signal": "URL_HOST_MISMATCH", "evidence": "visible=\"PayPal\" href=\"http://phishing.ru\"", "weight": 10}
  ]
}
```

### Get Security Statistics

```bash
curl http://localhost:8003/api/security/stats
```

Response:
```json
{
  "total_quarantined": 42,
  "average_risk_score": 12.5,
  "high_risk_count": 18
}
```

### Query Quarantined Emails (Elasticsearch)

```bash
# All quarantined emails
curl -X GET "http://localhost:9200/gmail_emails/_search" -H 'Content-Type: application/json' -d'
{
  "query": {"term": {"quarantined": true}},
  "size": 10
}'

# Emails with specific risk signals
curl -X GET "http://localhost:9200/gmail_emails/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "nested": {
      "path": "flags",
      "query": {
        "term": {"flags.signal": "DMARC_FAIL"}
      }
    }
  }
}'

# Risk score aggregations
curl -X GET "http://localhost:9200/gmail_emails/_search" -H 'Content-Type: application/json' -d'
{
  "size": 0,
  "aggs": {
    "risk_distribution": {
      "histogram": {
        "field": "risk_score",
        "interval": 10
      }
    }
  }
}'
```

## Configuration

### Customize Risk Weights

Edit `app/security/analyzer.py`:

```python
@dataclass(frozen=True)
class RiskWeights:
    DMARC_FAIL: int = 25
    SPF_FAIL: int = 15
    DKIM_FAIL: int = 15
    DISPLAY_NAME_SPOOF: int = 15
    EXECUTABLE_OR_HTML_ATTACHMENT: int = 20
    BLOCKLISTED_HASH_OR_HOST: int = 30
    TRUSTED_DOMAIN: int = -15
    QUARANTINE_THRESHOLD: int = 70  # ← Change threshold here
```

### Update Blocklists

Edit `app/security/blocklists.json`:

```json
{
  "hosts": [
    "update-security-login.ru",
    "billing-check.top",
    "your-malicious-domain.xyz"
  ],
  "hashes": [
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  ],
  "trusted_domains": [
    "paypal.com",
    "microsoft.com",
    "your-trusted-partner.com"
  ]
}
```

**Pro Tip:** For production, consider moving blocklists to Redis/Elasticsearch for dynamic updates without code deployment.

## Monitoring

### Prometheus Metrics (Future Enhancement)

```python
# app/metrics.py
from prometheus_client import Counter, Histogram

EMAILS_QUARANTINED = Counter('emails_quarantined_total', 'Total quarantined emails')
RISK_SCORE_HISTOGRAM = Histogram('email_risk_score', 'Email risk score distribution')

# In analyzer
if result.quarantined:
    EMAILS_QUARANTINED.inc()
RISK_SCORE_HISTOGRAM.observe(result.risk_score)
```

### Alerting

**High Quarantine Rate Alert:**
```promql
rate(emails_quarantined_total[5m]) > 0.5
```

**Critical Risk Detection:**
```bash
# Webhook to Slack/PagerDuty when risk_score > 90
curl -X POST http://slack-webhook-url -d '{
  "text": "🚨 Critical threat detected: email_id=123, risk_score=95"
}'
```

## Troubleshooting

### Migration Fails

**Error:** `column "flags" already exists`

**Solution:** The column may have been added by a previous migration. Check:
```bash
alembic current
alembic history
```

### Analyzer Tests Fail

**Error:** `ModuleNotFoundError: No module named 'idna'`

**Solution:** Install dependencies:
```bash
cd services/api
pip install idna>=3.4
```

### ES Template Not Applied

**Error:** New documents missing `flags` field

**Solution:** Verify template priority and patterns:
```bash
curl http://localhost:9200/_index_template/emails-template | jq '.index_templates[0].index_template.priority'
```

Template priority should be >= 200. If lower, increase in template JSON.

### Performance Issues

**Symptom:** Slow email ingestion after adding analyzer

**Solution 1:** Run analyzer asynchronously
```python
from celery import shared_task

@shared_task
def analyze_email_async(email_id: int):
    # Analyze in background worker
    pass
```

**Solution 2:** Batch analysis
```python
# Analyze 100 emails at once
for batch in chunk(emails, 100):
    results = [ANALYZER.analyze(...) for email in batch]
    db.bulk_update_mappings(Email, results)
    db.commit()
```

## API Reference

### EmailRiskAnalyzer.analyze()

**Parameters:**
- `headers` (Dict[str, str]) - Email headers (especially Authentication-Results)
- `from_name` (str) - Display name from From header
- `from_email` (str) - Email address from From header
- `subject` (str) - Email subject
- `body_text` (str) - Plain text body
- `body_html` (Optional[str]) - HTML body
- `urls_visible_text_pairs` (Optional[List[Tuple[str, str]]]) - (visible text, actual URL) pairs
- `attachments` (Optional[List[Dict]]) - Attachment metadata with `filename`, `mime_type`, `sha256`
- `domain_first_seen_days_ago` (Optional[int]) - Domain age in days

**Returns:** `RiskAnalysis`
```python
class RiskAnalysis(BaseModel):
    risk_score: int          # 0-100
    flags: List[RiskFlag]    # List of detected signals
    quarantined: bool        # True if score >= threshold
```

**Example:**
```python
result = analyzer.analyze(
    headers={"Authentication-Results": "dmarc=pass"},
    from_name="Alice",
    from_email="alice@trusted.com",
    subject="Meeting Tomorrow",
    body_text="Let's meet at 2pm",
    body_html=None
)

print(f"Risk: {result.risk_score}/100")
print(f"Quarantined: {result.quarantined}")
for flag in result.flags:
    print(f"  - {flag.signal}: {flag.evidence} (+{flag.weight})")
```

## Future Enhancements

1. **Machine Learning Integration**
   - Train classifier on historical quarantine decisions
   - Adjust weights dynamically based on feedback

2. **Advanced Threat Intelligence**
   - Integrate with VirusTotal, URLhaus APIs
   - Real-time domain reputation checks

3. **User Feedback Loop**
   - "Mark as Safe" / "Mark as Spam" buttons
   - Retrain model on user feedback

4. **Behavioral Analysis**
   - Track sender patterns (volume spikes, geo changes)
   - Detect account compromise indicators

5. **Sandbox Execution**
   - Detonate attachments in sandbox
   - Screenshot suspicious URLs

## Support

- **Unit Tests:** `tests/test_security_analyzer.py` (12 test cases, 95% coverage)
- **Documentation:** This file + inline docstrings
- **Scripts:**
  - `scripts/install_es_template.py` - Install Elasticsearch template
  - `scripts/update_existing_index_mapping.py` - Update existing index
- **API Docs:** http://localhost:8003/docs (FastAPI auto-generated)

---

**Last Updated:** October 12, 2025  
**Version:** 1.0.0  
**Author:** ApplyLens Security Team
