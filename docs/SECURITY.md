# Security Policy

## Data Handling

- Store only necessary email metadata in dev. Avoid PII in logs.
- Use read-only Gmail scopes for demos.
- Keep secrets out of repo; use GitHub Actions secrets.

## Reporting a Vulnerability

Please report security vulnerabilities to the repository maintainers privately through GitHub's security advisory feature.

## Security UI Quickstart

# Security UI - Quick Start Guide

## For Frontend Developers

### Using the Components

#### 1. Display Risk Badge in Email List

```typescript
import { RiskBadge } from "@/components/security/RiskBadge";

// In your email list item component:
<div className="email-item">
  <span>{email.subject}</span>
  {email.risk_score !== undefined && (
    <RiskBadge score={email.risk_score} quarantined={email.quarantined} />
  )}
</div>
```

#### 2. Add Security Panel to Email Details

```typescript
import { SecurityPanel } from "@/components/security/SecurityPanel";

// In your email details view:
<div className="email-details">
  <h1>{email.subject}</h1>
  <div>{email.body}</div>
  
  {email.risk_score !== undefined && (
    <SecurityPanel
      emailId={email.id}
      riskScore={email.risk_score}
      quarantined={email.quarantined}
      flags={email.flags}
      onRefresh={() => {
        // Refetch email data after rescan
        refetchEmail(email.id);
      }}
    />
  )}
</div>
```

#### 3. Add Security Settings Page

Already implemented at `/settings/security` route!

```typescript
// Just navigate users to:
<Link to="/settings/security">Security Settings</Link>
```

---

## For Backend Developers

### Required API Endpoints

#### 1. Email Security Data (ALREADY IMPLEMENTED ✅)

Your email API responses should include:

```json
{
  "id": "123",
  "subject": "Important Email",
  "from": "sender@example.com",
  "risk_score": 55,
  "quarantined": false,
  "flags": [
    {
      "signal": "DMARC_FAIL",
      "evidence": "auth=fail",
      "weight": 25
    },
    {
      "signal": "SPF_FAIL",
      "evidence": "ip=1.2.3.4",
      "weight": 15
    }
  ]
}
```

**Endpoints that should return this:**

- `GET /api/search/` → Array of emails with security data
- `GET /api/emails/` → Array of emails with security data
- `GET /api/search/by_id/{id}` → Single email with security data

#### 2. Rescan Endpoint (ALREADY IMPLEMENTED ✅)

```python
@router.post("/security/rescan/{email_id}")
def rescan_email(email_id: str, db: Session = Depends(get_db)):
    """Re-analyze email security."""
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Run security analysis
    analyzer = get_security_analyzer()
    result = analyzer.analyze(...)
    
    # Update database
    email.risk_score = result.risk_score
    email.flags = [f.dict() for f in result.flags]
    email.quarantined = result.quarantined
    db.commit()
    
    return {
        "status": "ok",
        "email_id": email_id,
        "risk_score": result.risk_score,
        "quarantined": result.quarantined,
        "flags": result.flags
    }
```

#### 3. Security Stats Endpoint (ALREADY IMPLEMENTED ✅)

```python
@router.get("/security/stats")
def get_security_stats(db: Session = Depends(get_db)):
    """Get aggregate security statistics."""
    quarantined = db.query(func.count(Email.id)).filter(Email.quarantined == True).scalar() or 0
    average_risk = db.query(func.avg(Email.risk_score)).filter(Email.risk_score.isnot(None)).scalar()
    average_risk = float(average_risk) if average_risk is not None else 0.0
    high_risk = db.query(func.count(Email.id)).filter(Email.risk_score >= 50).scalar() or 0
    
    return {
        "total_quarantined": quarantined,
        "average_risk_score": average_risk,
        "high_risk_count": high_risk
    }
```

#### 4. Policy Endpoints (TODO - NEEDS IMPLEMENTATION ⚠️)

**GET /api/policy/security**

```python
@router.get("/policy/security")
def get_security_policies(db: Session = Depends(get_db)):
    """Fetch security policy configuration."""
    # Option 1: Fetch from database
    policy = db.query(SecurityPolicy).first()
    if not policy:
        # Return defaults
        return {
            "autoQuarantineHighRisk": True,
            "autoArchiveExpiredPromos": True,
            "autoUnsubscribeInactive": {
                "enabled": False,
                "threshold": 10
            }
        }
    
    return {
        "autoQuarantineHighRisk": policy.auto_quarantine_high_risk,
        "autoArchiveExpiredPromos": policy.auto_archive_expired_promos,
        "autoUnsubscribeInactive": {
            "enabled": policy.auto_unsubscribe_enabled,
            "threshold": policy.auto_unsubscribe_threshold
        }
    }
```

**PUT /api/policy/security**

```python
@router.put("/policy/security")
def save_security_policies(
    policies: SecurityPoliciesInput,
    db: Session = Depends(get_db)
):
    """Save security policy configuration."""
    policy = db.query(SecurityPolicy).first()
    if not policy:
        policy = SecurityPolicy()
        db.add(policy)
    
    policy.auto_quarantine_high_risk = policies.autoQuarantineHighRisk
    policy.auto_archive_expired_promos = policies.autoArchiveExpiredPromos
    policy.auto_unsubscribe_enabled = policies.autoUnsubscribeInactive.enabled
    policy.auto_unsubscribe_threshold = policies.autoUnsubscribeInactive.threshold
    
    db.commit()
    
    # Optional: Trigger background job to apply policies
    # apply_policies_to_existing_emails.delay()
    
    return {"status": "ok"}
```

**Create the Pydantic models:**

```python
from pydantic import BaseModel

class AutoUnsubscribeConfig(BaseModel):
    enabled: bool
    threshold: int

class SecurityPoliciesInput(BaseModel):
    autoQuarantineHighRisk: bool
    autoArchiveExpiredPromos: bool
    autoUnsubscribeInactive: AutoUnsubscribeConfig
```

**Create the database model:**

```python
# In alembic migration or models.py
class SecurityPolicy(Base):
    __tablename__ = "security_policies"
    
    id = Column(Integer, primary_key=True)
    auto_quarantine_high_risk = Column(Boolean, default=True)
    auto_archive_expired_promos = Column(Boolean, default=True)
    auto_unsubscribe_enabled = Column(Boolean, default=False)
    auto_unsubscribe_threshold = Column(Integer, default=10)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## Testing

### Run E2E Tests

```bash
cd apps/web
pnpm exec playwright test tests/security-ui.spec.ts
```

### Manual Testing Checklist

1. **Email List**
   - [ ] Open `/search` or `/inbox-polished`
   - [ ] Verify risk badges appear on emails with `risk_score`
   - [ ] Check badge colors (red ≥80, amber 40-79, green <40)

2. **Email Details**
   - [ ] Click on an email
   - [ ] Security panel should appear (if email has risk_score)
   - [ ] Click "Why flagged?" → Evidence modal opens
   - [ ] Click "Rescan" → Loading state → Success toast

3. **Security Settings**
   - [ ] Navigate to `/settings/security`
   - [ ] Toggle switches work
   - [ ] Number input for threshold works
   - [ ] Save button triggers toast

4. **Dark Mode**
   - [ ] Toggle dark mode
   - [ ] All colors display correctly
   - [ ] Badges are readable
   - [ ] Modals have proper contrast

---

## Common Issues & Solutions

### Issue: Risk badges not showing

**Solution:** Make sure your API returns `risk_score` in the email object:

```typescript
// Check in browser console:
console.log(email.risk_score); // Should be a number
```

### Issue: SecurityPanel not appearing

**Cause:** SecurityPanel only renders if `risk_score !== undefined`

**Solution:** Ensure API includes `risk_score` field (can be 0)

### Issue: Rescan button doesn't work

**Possible causes:**

1. API endpoint not implemented
2. CORS issues (use `credentials: "include"`)
3. Email ID format mismatch (string vs number)

**Debug:**

```typescript
// Check network tab in browser DevTools
// POST /api/security/rescan/{id} should return 200
```

### Issue: Policy save fails with 404

**Cause:** Backend policy endpoints not implemented yet

**Solution:** Implement the endpoints above or use frontend with defaults (already handled gracefully)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (React)                    │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  EmailList    │  │ EmailDetails │  │   Settings   │ │
│  │  (RiskBadge)  │  │ (Security    │  │   Security   │ │
│  │               │  │  Panel)      │  │  (Policy     │ │
│  │               │  │              │  │   Panel)     │ │
│  └───────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│          │                 │                  │          │
│          └─────────────────┴──────────────────┘          │
│                            │                             │
│                    ┌───────▼────────┐                    │
│                    │  securityApi   │                    │
│                    │  - rescan()    │                    │
│                    │  - getStats()  │                    │
│                    │  - getPolicies│                    │
│                    └───────┬────────┘                    │
└────────────────────────────┼──────────────────────────────┘
                             │
                             │ HTTP/JSON
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                     │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │          /api/security/* endpoints                  │ │
│  │  - POST /rescan/{id}  ✅                           │ │
│  │  - GET /stats         ✅                           │ │
│  ├────────────────────────────────────────────────────┤ │
│  │          /api/policy/* endpoints                    │ │
│  │  - GET /security      ⚠️ TODO                      │ │
│  │  - PUT /security      ⚠️ TODO                      │ │
│  └───────────────┬────────────────────────────────────┘ │
│                  │                                        │
│          ┌───────▼─────────┐                            │
│          │ EmailRiskAnalyzer│                            │
│          │ - analyze()      │                            │
│          │ - 12 detections  │                            │
│          └───────┬──────────┘                            │
│                  │                                        │
└──────────────────┼─────────────────────────────────────┘
                   │
                   ▼
         ┌──────────────────┐
         │   PostgreSQL DB   │
         │  - emails table   │
         │    * risk_score   │
         │    * quarantined  │
         │    * flags (JSONB)│
         └───────────────────┘
```

---

## Performance Tips

### 1. Optimize Large Lists

If you have 1000+ emails with risk badges:

```typescript
import { memo } from 'react';

// Memoize the EmailRow component
export const EmailRow = memo(function EmailRow(props) {
  // ... component code
});
```

### 2. Lazy Load Evidence Modal

Already implemented! The modal only mounts when opened.

### 3. Cache Policy Data

```typescript
// In PolicyPanel component, add localStorage cache:
React.useEffect(() => {
  const cached = localStorage.getItem('security-policies');
  if (cached) {
    setPol(JSON.parse(cached));
  }
  getPolicies().then(p => {
    setPol(p);
    localStorage.setItem('security-policies', JSON.stringify(p));
  });
}, []);
```

### 4. Debounce Policy Input

```typescript
import { useDebouncedCallback } from 'use-debounce';

const debouncedSave = useDebouncedCallback(
  () => savePolicies(pol),
  1000
);
```

---

## Customization Examples

### Change Risk Level Thresholds

Edit `RiskBadge.tsx`:

```typescript
// Change from 80/40 to 70/30:
const level = score >= 70 ? "high" : score >= 30 ? "med" : "low";
```

### Add More Policy Options

Edit `PolicyPanel.tsx`:

```typescript
// Add new toggle:
<div className="flex items-center justify-between">
  <Label htmlFor="autoBlockSuspicious">Auto-block suspicious senders</Label>
  <Switch id="autoBlockSuspicious" checked={pol.autoBlockSuspicious}
          onCheckedChange={(v)=>update("autoBlockSuspicious", v)} />
</div>
```

Update types in `security.ts`:

```typescript
export type SecurityPolicies = {
  autoQuarantineHighRisk: boolean;
  autoArchiveExpiredPromos: boolean;
  autoUnsubscribeInactive: { enabled: boolean; threshold: number };
  autoBlockSuspicious: boolean; // New!
};
```

### Change Badge Colors

Edit `RiskBadge.tsx`:

```typescript
// Use your brand colors:
const color =
  level === "high" ? "bg-purple-500/20 text-purple-300 border-purple-600/40" :
  level === "med"  ? "bg-blue-500/20 text-blue-300 border-blue-600/40" :
                     "bg-green-500/20 text-green-300 border-green-600/40";
```

---

## Next Steps

1. ✅ Security UI is ready to use!
2. ⚠️ Implement policy backend endpoints (optional, has defaults)
3. 🚀 Deploy to production
4. 📊 Monitor user feedback
5. 🔄 Iterate based on usage patterns

For questions, see `SECURITY_UI_IMPLEMENTATION.md` for full documentation.


## Security Integration


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
- **API Docs:** <http://localhost:8003/docs> (FastAPI auto-generated)

---

**Last Updated:** October 12, 2025  
**Version:** 1.0.0  
**Author:** ApplyLens Security Team
