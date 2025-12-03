# Email Classification - Verification Guide

This guide covers how to verify the email classification system is working correctly in production.

## Table of Contents
1. [Health Check](#health-check)
2. [Classification Backfill](#classification-backfill)
3. [Database Verification](#database-verification)
4. [Opportunities Integration](#opportunities-integration)
5. [Bootstrap Training Labels](#bootstrap-training-labels)

---

## 1. Health Check

### Classifier Diagnostics Endpoint

Check classifier status and configuration:

```bash
curl http://localhost:8000/diagnostics/classifier/health | jq
```

Expected response (heuristic mode):
```json
{
  "ok": true,
  "status": "healthy",
  "mode": "heuristic",
  "model_version": "heuristic_v1",
  "has_model_artifacts": false,
  "uses_ml": false,
  "ml_model_loaded": false,
  "vectorizer_loaded": false,
  "message": "Classifier running in heuristic mode (heuristic-only)",
  "sample_prediction": {
    "category": "interview_invite",
    "is_real_opportunity": true,
    "confidence": 0.8,
    "source": "heuristic"
  },
  "error": null
}
```

---

## 2. Classification Backfill

### Overview

The backfill script classifies historical emails that don't have classification data yet.

### Dry Run (Preview Mode)

See what would be updated without making changes:

```bash
cd services/api
python -m scripts.backfill_email_classification --limit 500 --dry-run
```

### Real Backfill

Classify and persist results for unclassified emails:

```bash
# Backfill up to 1000 emails
python -m scripts.backfill_email_classification --limit 1000

# Backfill for specific user
python -m scripts.backfill_email_classification --user-id leo@applylens.app --limit 500

# Large backfill (gradual rollout)
python -m scripts.backfill_email_classification --limit 5000
```

### Verify Backfill Results

Check how many emails were classified:

```sql
SELECT
  category,
  is_real_opportunity,
  COUNT(*) AS n
FROM emails
WHERE is_real_opportunity IS NOT NULL
GROUP BY category, is_real_opportunity
ORDER BY n DESC
LIMIT 20;
```

Expected output after backfill:
```
         category         | is_real_opportunity |  n
--------------------------+---------------------+------
 newsletter_marketing     | false               | 1523
 recruiter_outreach       | true                | 342
 interview_invite         | true                | 89
 application_confirmation | true                | 67
 job_alert_digest         | false               | 54
 rejection                | false               | 41
 security_auth            | false               | 28
 receipt_invoice          | false               | 15
```

---

## 3. Database Verification

### Check Email Classification Fields

```sql
-- Check that opportunities endpoint respects is_real_opportunity field
SELECT
  e.subject,
  e.is_real_opportunity,
  e.category,
  e.category_confidence,
  a.company,
  a.status
FROM emails e
LEFT JOIN applications a ON a.thread_id = e.thread_id
WHERE e.is_real_opportunity = TRUE
  AND a.status NOT IN ('rejected', 'withdrawn', 'ghosted', 'closed')
LIMIT 20;
```

**Expected**: These should match what `/api/opportunities` returns.

---

### 1. Trigger Gmail Backfill

Option 1: Manual backfill (small test)
```bash
curl -X POST "http://localhost:8000/api/gmail/backfill?days=7" \
  -H "Authorization: Bearer <token>"
```

Option 2: Wait for scheduled backfill to run

### 2. Check Email Classification Fields

```sql
-- Verify emails are being classified
SELECT category,
       is_real_opportunity,
       classifier_version,
       COUNT(*) AS n
FROM emails
WHERE category IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY n DESC;
```

**Expected Results:**
- `classifier_version` should show `heuristic_v1` or similar
- Categories: `security_auth`, `receipt_invoice`, `application_confirmation`, `job_alert_digest`, `newsletter_marketing`, `personal_other`, etc.
- Mix of `is_real_opportunity = TRUE/FALSE`

### 3. Check Classification Events

```sql
-- Verify classification events are being logged
SELECT model_version,
       source,
       predicted_category,
       COUNT(*) AS n
FROM email_classification_events
GROUP BY 1, 2, 3
ORDER BY n DESC
LIMIT 20;
```

**Expected Results:**
- `source = 'heuristic'` (in current mode)
- `model_version = 'heuristic_v1'`
- Events created for every email processed

### 4. Sample Email Details

```sql
-- Inspect a few classified emails
SELECT id,
       subject,
       category,
       is_real_opportunity,
       category_confidence,
       classifier_version,
       received_at
FROM emails
WHERE category IS NOT NULL
ORDER BY received_at DESC
LIMIT 10;
```

## B. Run Bootstrap Script

### 1. Execute Bootstrap

```bash
cd services/api
python -m scripts.bootstrap_email_training_labels --limit 5000
```

**Expected Output:**
```
Inserted 487 training labels
```

(Actual number depends on your email corpus)

### 2. Check Training Labels Distribution

```sql
-- View label distribution
SELECT label_category,
       label_is_real_opportunity,
       label_source,
       COUNT(*) AS n
FROM email_training_labels
GROUP BY 1, 2, 3
ORDER BY n DESC;
```

**Expected Results:**

| Category | is_real_opportunity | Source | Count |
|----------|---------------------|--------|-------|
| security_auth | FALSE | bootstrap_rule_security_auth | ~150 |
| receipt_invoice | FALSE | bootstrap_rule_receipt_invoice | ~120 |
| application_confirmation | TRUE | bootstrap_rule_application_confirmation | ~80 |
| job_alert_digest | FALSE | bootstrap_rule_job_alert_digest | ~70 |
| interview_invite | TRUE | bootstrap_rule_interview_invite | ~40 |
| newsletter_marketing | FALSE | bootstrap_rule_newsletter_marketing | ~30 |

### 3. Confidence Distribution

```sql
-- Check confidence scores
SELECT label_category,
       AVG(confidence) AS avg_conf,
       MIN(confidence) AS min_conf,
       MAX(confidence) AS max_conf,
       COUNT(*) AS n
FROM email_training_labels
GROUP BY 1
ORDER BY avg_conf DESC;
```

**Expected Results:**
- `security_auth`: avg ~0.99 (highest confidence)
- `receipt_invoice`: avg ~0.97
- `interview_invite`: avg ~0.94
- `application_confirmation`: avg ~0.92
- `job_alert_digest`: avg ~0.90
- `newsletter_marketing`: avg ~0.88

### 4. Sample Training Labels

```sql
-- Inspect some labeled emails
SELECT e.subject,
       e.sender,
       tl.label_category,
       tl.label_is_real_opportunity,
       tl.confidence,
       tl.label_source
FROM email_training_labels tl
JOIN emails e ON e.id = tl.email_id
ORDER BY tl.confidence DESC
LIMIT 20;
```

## C. Health Check Diagnostics Endpoint

### 1. Test Classifier Health

```bash
curl http://localhost:8000/diagnostics/classifier/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "mode": "heuristic",
  "model_version": "heuristic_v1",
  "ml_model_loaded": false,
  "vectorizer_loaded": false,
  "test_classification": {
    "category": "recruiter_outreach",
    "confidence": 0.5,
    "is_real_opportunity": true,
    "source": "heuristic",
    "model_version": "heuristic_v1"
  }
}
```

## D. Common Issues & Troubleshooting

### Issue: No classification events being created

**Symptoms:**
```sql
SELECT COUNT(*) FROM email_classification_events;
-- Returns: 0
```

**Diagnosis:**
- Check if Gmail ingest is running
- Verify `classify_and_persist_email()` is being called in `gmail_service.py`
- Check logs for classification errors

**Fix:**
```bash
# Check server logs
docker logs applylens-api | grep -i "classification"

# Verify integration code
grep -n "classify_and_persist_email" app/gmail_service.py
```

### Issue: Bootstrap script finds 0 labels

**Symptoms:**
```bash
python -m scripts.bootstrap_email_training_labels --limit 5000
# Output: Inserted 0 training labels
```

**Diagnosis:**
- No emails in database matching rules
- All emails already labeled (script skips duplicates)

**Fix:**
```sql
-- Check total email count
SELECT COUNT(*) FROM emails;

-- Check if emails already labeled
SELECT COUNT(*) FROM email_training_labels;

-- View email content for rule matching
SELECT subject, body_text FROM emails LIMIT 10;
```

### Issue: Classification confidence always 0.5

**Symptoms:**
All emails get `category_confidence = 0.5`

**Diagnosis:**
- Heuristic fallback is kicking in (no strong signals)
- Rules need tuning for your email corpus

**Fix:**
- Add domain-specific keywords to classifier
- Adjust confidence thresholds
- Consider training ML model sooner

## E. Next Steps After Verification

Once all checks pass:

1. **✅ Step 2 Complete:** Training labels bootstrapped
2. **➡️ Step 3:** Train ML model
   ```bash
   python -m scripts.train_email_classifier
   ```
3. **➡️ Step 4:** Deploy in ml_shadow mode
   ```bash
   export EMAIL_CLASSIFIER_MODE=ml_shadow
   export EMAIL_CLASSIFIER_MODEL_VERSION=ml_v1
   # Restart server
   ```
4. **➡️ Step 5:** Build dbt analytics models
5. **➡️ Step 6:** Wire Opportunities page to use `is_real_opportunity`
6. **➡️ Step 7:** Monitor correction rate and drift
7. **➡️ Step 8:** Gradual rollout to ml_live

## F. Useful Monitoring Queries

### Daily classification volume
```sql
SELECT DATE(created_at) AS day,
       source,
       COUNT(*) AS classifications
FROM email_classification_events
GROUP BY 1, 2
ORDER BY 1 DESC;
```

### Category distribution over time
```sql
SELECT DATE(created_at) AS day,
       predicted_category,
       COUNT(*) AS n
FROM email_classification_events
GROUP BY 1, 2
ORDER BY 1 DESC, 3 DESC;
```

### High-confidence real opportunities
```sql
SELECT e.subject,
       e.sender,
       e.category,
       e.category_confidence,
       e.received_at
FROM emails e
WHERE e.is_real_opportunity = TRUE
  AND e.category_confidence > 0.85
ORDER BY e.received_at DESC
LIMIT 20;
```
