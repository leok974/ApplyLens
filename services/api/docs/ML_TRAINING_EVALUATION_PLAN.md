# ML Training & Evaluation Plan

Complete workflow for training and evaluating the email classifier ML model.

## Prerequisites

- ✅ Step 1 complete: Gmail ingest integration
- ✅ Step 2 complete: Bootstrap script created
- ⏳ Database with emails ingested

## Phase 1: Bootstrap Training Labels

### 1.1. Run Bootstrap Script

From `services/api`:

```bash
python -m scripts.bootstrap_email_training_labels --limit 5000
```

**Expected output:**
```
Inserted 487 training labels
```

(Actual number depends on your email corpus)

### 1.2. Inspect Label Distribution

```sql
SELECT label_category,
       label_is_real_opportunity,
       label_source,
       COUNT(*) AS n
FROM email_training_labels
GROUP BY 1, 2, 3
ORDER BY n DESC;
```

**Requirements for good training:**

✅ **Total labels:** At least 300 (ideally 1000+)

✅ **Class balance:**
- Both `TRUE` and `FALSE` for `is_real_opportunity`
- Aim for 30-70% split (not 95-5%)

✅ **Category diversity:**
- At least 3-4 different categories
- Not dominated by one category (e.g., not 90% security codes)

**If distribution is skewed:**

Option A: Add custom rules to bootstrap script
```python
# In infer_label_for_email(), add:
if any(k in text for k in ["recruiter", "talent team", "hiring manager"]):
    return ("recruiter_outreach", True, "bootstrap_rule_recruiter", 0.85)
```

Option B: Filter recent job-related emails
```sql
-- Find candidates for manual labeling
SELECT id, subject, sender, body_text
FROM emails
WHERE subject ILIKE '%interview%'
   OR subject ILIKE '%application%'
   OR subject ILIKE '%offer%'
ORDER BY received_at DESC
LIMIT 50;
```

Then manually insert into `email_training_labels`.

### 1.3. Check Confidence Distribution

```sql
SELECT label_category,
       AVG(confidence) AS avg_conf,
       MIN(confidence) AS min_conf,
       MAX(confidence) AS max_conf,
       COUNT(*) AS n
FROM email_training_labels
GROUP BY 1
ORDER BY avg_conf DESC;
```

**Expected ranges:**
- `security_auth`: ~0.99
- `receipt_invoice`: ~0.97
- `interview_invite`: ~0.94
- `application_confirmation`: ~0.92
- `job_alert_digest`: ~0.90
- `newsletter_marketing`: ~0.88

## Phase 2: Train ML Model (v1)

### 2.0. Inspect Training Data Quality

**Before training**, verify label distribution and quality.

⚠️ **Note**: This script requires database access. Run on production server or use SSH tunnel to production DB.

```bash
# On production server:
cd /app  # or wherever API code is deployed
python -m scripts.inspect_email_training_labels

# OR with SSH tunnel to production DB:
# ssh -L 5432:localhost:5432 user@db-server
# Then set DATABASE_URL=postgresql://user:pass@localhost:5432/applylens
# python -m scripts.inspect_email_training_labels
```

**Expected output:**
```
=== Email Training Labels Report ===

Total Labels: 487

Distribution by Category:
  security_auth                ████████████████████░  120 (24.6%)
  receipt_invoice              ████████████████░      98 (20.1%)
  application_confirmation     ██████████████░        87 (17.9%)
  newsletter_marketing         ███████████░           65 (13.3%)
  job_alert_digest             █████████░             54 (11.1%)
  interview_invite             ███████░               43 (8.8%)
  recruiter_outreach           ████░                  20 (4.1%)

Distribution by is_real_opportunity:
  TRUE    ████████████░  187 (38.4%)
  FALSE   ████████████████████  300 (61.6%)
  NULL    ░              0 (0.0%)

Class Balance Ratio: 1.60 (FALSE/TRUE)
✅ Class balance is healthy (1.0-3.0 range)

Confidence Statistics:
  Min: 0.80, Avg: 0.91, Max: 0.99
  High-confidence (≥0.8): 487 (100.0%)

Label Source Breakdown:
  bootstrap_rule_auth          120 (24.6%)
  bootstrap_rule_receipt       98 (20.1%)
  bootstrap_rule_confirmation  87 (17.9%)

Recommendations:
✅ Good label count (≥300)
✅ Healthy class balance
✅ High average confidence
✅ Ready for training!
```

**Requirements:**
- ✅ Total labels ≥ 300 (ideally 1000+)
- ✅ Class balance ratio between 1.0-3.0
- ✅ Average confidence ≥ 0.85
- ✅ No severe category skew (one category <80%)

**If issues found, re-run bootstrap with adjusted rules before training.**

### 2.1. Run Training Script

⚠️ **Note**: Requires database access with training labels. Run on production server.

```bash
cd /app  # or API deployment directory
python -m scripts.train_email_classifier
```

**What it does:**
1. Loads training labels with confidence ≥ 0.8
2. Builds TF-IDF features (50k vocab, 1-2 grams)
3. Trains LogisticRegression (balanced, LBFGS, 200 iter)
4. Performs 80/20 train/val split
5. Saves artifacts to `models/`

**Expected output:**
```
Training samples: 487
Validation samples: 122

Classification Report:
              precision    recall  f1-score   support
       False       0.89      0.92      0.90        65
        True       0.87      0.82      0.84        57

    accuracy                           0.88       122
   macro avg       0.88      0.87      0.87       122

Confidence distribution:
  0.5-0.6: 12 predictions
  0.6-0.7: 23 predictions
  0.7-0.8: 31 predictions
  0.8-0.9: 38 predictions
  0.9-1.0: 18 predictions

✅ Model saved: models/email_opp_model.joblib
✅ Vectorizer saved: models/email_opp_vectorizer.joblib
```

### 2.2. Record Metrics

Add to `docs/EMAIL_CLASSIFICATION_STATUS.md`:

```markdown
## ML Model v1 Training Results

**Date:** 2025-12-03
**Training set size:** 487 labels (confidence ≥ 0.8)
**Validation set size:** 122 labels (20% holdout)

### Validation Metrics (is_real_opportunity)

| Metric | Value |
|--------|-------|
| Precision (True) | 0.87 |
| Recall (True) | 0.82 |
| F1 (True) | 0.84 |
| Overall Accuracy | 0.88 |

### Category Distribution

| Category | Train Count | Val Count |
|----------|-------------|-----------|
| security_auth | 120 | 28 |
| receipt_invoice | 98 | 24 |
| application_confirmation | 87 | 19 |
| ... | ... | ... |
```

### 2.3. Threshold Analysis

If you want to tune the decision threshold (default 0.5):

```python
# In scripts/train_email_classifier.py, add after training:

from sklearn.metrics import precision_recall_curve
import matplotlib.pyplot as plt

y_proba = model.predict_proba(X_val)[:, 1]
precisions, recalls, thresholds = precision_recall_curve(y_val, y_proba)

# Plot precision/recall vs threshold
plt.figure(figsize=(10, 6))
plt.plot(thresholds, precisions[:-1], label='Precision')
plt.plot(thresholds, recalls[:-1], label='Recall')
plt.xlabel('Threshold')
plt.ylabel('Score')
plt.legend()
plt.title('Precision-Recall vs Threshold')
plt.savefig('threshold_analysis.png')

# Find threshold for 90% precision
target_precision = 0.90
idx = np.argmin(np.abs(precisions - target_precision))
optimal_threshold = thresholds[idx]
print(f"\nFor precision ≥ {target_precision}: threshold = {optimal_threshold:.3f}")
```

If you need higher precision (fewer false positives), increase threshold.

## Phase 3: Create Golden Set for Honest Evaluation

### 3.1. Manual Labeling

Pick ~50-100 diverse emails and hand-label them:

```sql
-- Find candidates from different categories
SELECT id, subject, sender, received_at
FROM emails
WHERE (
    subject ILIKE '%interview%' OR
    subject ILIKE '%application%' OR
    subject ILIKE '%offer%' OR
    subject ILIKE '%rejection%' OR
    labels @> ARRAY['INBOX']
)
AND received_at >= NOW() - INTERVAL '90 days'
ORDER BY RANDOM()
LIMIT 100;
```

For each email, inspect and manually classify:

```sql
INSERT INTO email_golden_labels
  (email_id, golden_category, golden_is_real_opportunity, labeler)
VALUES
  (12345, 'interview_invite', TRUE, 'leo'),
  (12346, 'job_alert_digest', FALSE, 'leo'),
  (12347, 'application_confirmation', TRUE, 'leo'),
  (12348, 'security_auth', FALSE, 'leo'),
  (12349, 'receipt_invoice', FALSE, 'leo');
  -- ... continue for all 50-100 emails
```

**Tips for labeling:**
- Mix of `TRUE` and `FALSE` for `is_real_opportunity`
- Include edge cases (unclear emails)
- Diverse senders and subjects
- Recent emails (last 3 months)

### 3.2. Run Golden Set Evaluation

```bash
python -m scripts.eval_email_classifier_on_golden
```

**Expected output:**
```
=== Email Classifier Golden Set Evaluation ===

✓ Found 87 golden labels

✓ Loaded classifier: mode=heuristic, version=heuristic_v1

============================================================
BINARY CLASSIFICATION: is_real_opportunity
============================================================
              precision    recall  f1-score   support

Not Opportunity    0.891     0.943     0.916        53
    Opportunity    0.912     0.838     0.873        34

       accuracy                          0.897        87

Confusion Matrix (is_real_opportunity):
                  Predicted
                  False  True
Actual False         50     3
       True           6    28

============================================================
CATEGORY CLASSIFICATION
============================================================
                        precision    recall  f1-score   support

application_confirmation    0.857     0.750     0.800        12
    interview_invite        0.900     0.818     0.857        11
    job_alert_digest        0.933     0.933     0.933        15
newsletter_marketing        0.750     0.857     0.800         7
    receipt_invoice         0.933     0.933     0.933        15
      security_auth         0.944     1.000     0.971        17

           accuracy                          0.908        87

============================================================
SUMMARY
============================================================
Golden set size:           87
Binary accuracy:           0.897
Category accuracy:         0.908
Classifier mode:           heuristic
Model version:             heuristic_v1
```

### 3.3. Compare Heuristic vs ML

After training ml_v1:

```bash
# Switch to ML mode
export EMAIL_CLASSIFIER_MODE=ml_live
export EMAIL_CLASSIFIER_MODEL_VERSION=ml_v1
export EMAIL_CLASSIFIER_MODEL_PATH=/app/models/email_opp_model.joblib
export EMAIL_CLASSIFIER_VECTORIZER_PATH=/app/models/email_opp_vectorizer.joblib

# Re-run evaluation
python -m scripts.eval_email_classifier_on_golden
```

**Decision criteria:**

| Metric | Heuristic | ml_v1 | Decision |
|--------|-----------|-------|----------|
| Binary F1 | 0.87 | **0.92** | ✅ Switch to ml_v1 |
| Category Accuracy | 0.91 | **0.94** | ✅ Switch to ml_v1 |
| Precision (True) | 0.91 | 0.89 | ⚠️ Slight drop acceptable |

**Switch to ml_live if:**
- ✅ ML F1 improves by ≥3 points
- ✅ Category accuracy improves
- ✅ Precision drop <5 points (to avoid false positives)

## Phase 4: Deploy ML Model in Shadow Mode

### 4.1. Bake Artifacts into API Image

**Option A: Docker build** (recommended)
```dockerfile
# In Dockerfile
COPY models/email_opp_model.joblib /app/models/
COPY models/email_opp_vectorizer.joblib /app/models/
```

**Option B: Volume mount**
```yaml
# docker-compose.yml
volumes:
  - ./models:/app/models:ro
```

### 4.2. Set Environment Variables

```env
EMAIL_CLASSIFIER_MODE=ml_shadow
EMAIL_CLASSIFIER_MODEL_VERSION=ml_v1
EMAIL_CLASSIFIER_MODEL_PATH=/app/models/email_opp_model.joblib
EMAIL_CLASSIFIER_VECTORIZER_PATH=/app/models/email_opp_vectorizer.joblib
```

### 4.3. Verify Shadow Mode

```bash
# Check diagnostics endpoint
curl http://localhost:8000/diagnostics/classifier/health

# Expected response:
{
  "status": "healthy",
  "mode": "ml_shadow",
  "model_version": "ml_v1",
  "ml_model_loaded": true,
  "vectorizer_loaded": true,
  "test_classification": {
    "category": "recruiter_outreach",
    "confidence": 0.87,
    "is_real_opportunity": true,
    "source": "ml",
    "model_version": "ml_v1"
  }
}
```

### 4.4. Monitor Shadow Predictions

```sql
-- Check both heuristic and ML are logging
SELECT source, model_version, COUNT(*) AS n
FROM email_classification_events
WHERE created_at >= NOW() - INTERVAL '1 day'
GROUP BY 1, 2;

-- Expected:
-- heuristic | heuristic_v1 | 487
-- ml_shadow | ml_v1        | 487
```

## Phase 5: Shadow Mode Analysis (1-2 weeks)

### 5.1. Agreement Rate

```sql
WITH heuristic_preds AS (
    SELECT email_id,
           predicted_is_real_opportunity AS heur_pred
    FROM email_classification_events
    WHERE source = 'heuristic'
    AND created_at >= NOW() - INTERVAL '7 days'
),
ml_preds AS (
    SELECT email_id,
           predicted_is_real_opportunity AS ml_pred
    FROM email_classification_events
    WHERE source = 'ml_shadow'
    AND created_at >= NOW() - INTERVAL '7 days'
)
SELECT
    COUNT(*) AS total_emails,
    COUNT(CASE WHEN h.heur_pred = m.ml_pred THEN 1 END) AS agreements,
    COUNT(CASE WHEN h.heur_pred = m.ml_pred THEN 1 END)::float / COUNT(*) AS agreement_rate
FROM heuristic_preds h
JOIN ml_preds m ON h.email_id = m.email_id;
```

**Target:** Agreement rate ≥85%

### 5.2. Disagreement Analysis

```sql
-- Find emails where heuristic and ML disagree
SELECT e.id,
       e.subject,
       e.sender,
       h.predicted_category AS heur_category,
       m.predicted_category AS ml_category,
       h.predicted_is_real_opportunity AS heur_opp,
       m.predicted_is_real_opportunity AS ml_opp,
       h.confidence AS heur_conf,
       m.confidence AS ml_conf
FROM emails e
JOIN email_classification_events h ON e.id = h.email_id AND h.source = 'heuristic'
JOIN email_classification_events m ON e.id = m.email_id AND m.source = 'ml_shadow'
WHERE h.predicted_is_real_opportunity != m.predicted_is_real_opportunity
AND h.created_at >= NOW() - INTERVAL '7 days'
ORDER BY ABS(h.confidence - m.confidence) DESC
LIMIT 20;
```

Manually review these disagreements - which one is correct?

### 5.3. User Correction Rate

```sql
-- Correction rate by model
WITH corrections AS (
    SELECT
        DATE(c.created_at) AS correction_date,
        COUNT(*) AS correction_count
    FROM email_category_corrections c
    GROUP BY 1
),
classifications AS (
    SELECT
        DATE(e.created_at) AS classification_date,
        source,
        COUNT(*) AS classification_count
    FROM email_classification_events e
    WHERE source IN ('heuristic', 'ml_shadow')
    GROUP BY 1, 2
)
SELECT
    c.correction_date,
    cl.source,
    c.correction_count,
    cl.classification_count,
    c.correction_count::float / cl.classification_count AS correction_rate
FROM corrections c
JOIN classifications cl ON c.correction_date = cl.classification_date
WHERE c.correction_date >= CURRENT_DATE - 14
ORDER BY c.correction_date DESC;
```

**Target:** Correction rate <10%

## Phase 6: Switch to ml_live

### 6.1. Decision Criteria

Switch to `ml_live` when **ALL** are true:

- ✅ Agreement rate with heuristic ≥85%
- ✅ Correction rate <10%
- ✅ Golden set F1 ≥0.90
- ✅ No significant drift in category distribution
- ✅ 1-2 weeks of shadow mode data

### 6.2. Deploy ml_live

```env
EMAIL_CLASSIFIER_MODE=ml_live  # Changed from ml_shadow
EMAIL_CLASSIFIER_MODEL_VERSION=ml_v1
EMAIL_CLASSIFIER_MODEL_PATH=/app/models/email_opp_model.joblib
EMAIL_CLASSIFIER_VECTORIZER_PATH=/app/models/email_opp_vectorizer.joblib
```

Restart API server.

### 6.3. Verify ml_live

```bash
curl http://localhost:8000/diagnostics/classifier/health
# mode should be "ml_live"
```

```sql
-- Check that emails are using ML predictions
SELECT category, is_real_opportunity, classifier_version, COUNT(*)
FROM emails
WHERE received_at >= NOW() - INTERVAL '1 hour'
GROUP BY 1, 2, 3;

-- classifier_version should be "ml_v1"
```

## Phase 7: Ongoing Monitoring & Retraining

### 7.1. Weekly Monitoring

Run these queries weekly:

```sql
-- 1. Correction rate trend
SELECT DATE(created_at) AS day,
       COUNT(*) AS corrections
FROM email_category_corrections
WHERE created_at >= CURRENT_DATE - 7
GROUP BY 1
ORDER BY 1;

-- 2. Category distribution drift
SELECT predicted_category,
       COUNT(*) AS n
FROM email_classification_events
WHERE created_at >= NOW() - INTERVAL '7 days'
AND source = 'ml_live'
GROUP BY 1
ORDER BY 2 DESC;

-- 3. Low confidence predictions
SELECT DATE(created_at) AS day,
       AVG(confidence) AS avg_conf,
       COUNT(CASE WHEN confidence < 0.6 THEN 1 END) AS low_conf_count
FROM email_classification_events
WHERE source = 'ml_live'
AND created_at >= CURRENT_DATE - 7
GROUP BY 1
ORDER BY 1;
```

### 7.2. Monthly Retraining

**Triggers for retraining:**
- Correction rate increases >5 points
- New email patterns emerge (new ATS, new recruiters)
- Golden set F1 drops below 0.88
- 30 days since last training

**Retraining workflow:**
1. Run bootstrap again with higher limit:
   ```bash
   python -m scripts.bootstrap_email_training_labels --limit 10000
   ```
2. Add user corrections to training set:
   ```sql
   INSERT INTO email_training_labels
     (email_id, thread_id, label_category, label_is_real_opportunity, label_source, confidence)
   SELECT
     email_id,
     thread_id,
     new_category,
     new_is_real_opportunity,
     'user_correction',
     1.0
   FROM email_category_corrections;
   ```
3. Re-train:
   ```bash
   python -m scripts.train_email_classifier
   ```
4. Evaluate on golden set
5. Deploy as `ml_v2` in shadow mode
6. Compare to `ml_v1`
7. Switch to live if better

## Summary Checklist

- [ ] Phase 1: Bootstrap ≥300 training labels
- [ ] Phase 2: Train ml_v1, record metrics
- [ ] Phase 3: Create 50-100 golden labels
- [ ] Phase 4: Deploy ml_shadow mode
- [ ] Phase 5: Monitor for 1-2 weeks
- [ ] Phase 6: Switch to ml_live
- [ ] Phase 7: Set up weekly monitoring
- [ ] Retrain monthly or when drift detected
