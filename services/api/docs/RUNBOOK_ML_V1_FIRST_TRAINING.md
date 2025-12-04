# Runbook: First Production ML Training (ml_v1)

**Purpose**: Step-by-step instructions for training the first production email opportunity classifier on the production server.

**Audience**: DevOps, ML engineers with production server SSH access

**Prerequisites**:
- SSH access to production server (`ssh user@applylens-api-server`)
- Production database has `email_training_labels` table populated (~195+ labels)
- Docker installed on production server
- Access to push Docker images (if deploying via container registry)

**Estimated Time**: 30-45 minutes

---

## Phase 1: Pre-flight Checks

### 1.1 SSH to Production Server

```bash
ssh user@applylens-api-server
cd /app/services/api
```

### 1.2 Verify Training Labels Exist

```bash
python -m scripts.inspect_email_training_labels
```

**Expected output:**
```
Total training labels: 195
Labels by is_real_opportunity:
  TRUE  (opportunities)          65 (33.3%)
  FALSE (not opportunities)     130 (66.7%)
```

**Action if labels missing:**
```bash
# Bootstrap from heuristic classifications
python -m scripts.bootstrap_email_training_labels --dry-run=false --limit=500
```

**Decision point**: If total < 100 labels, consider:
- Waiting for more user activity
- Running bootstrap on more emails
- Accepting lower initial accuracy

Minimum viable: **50+ labels with both classes present**

### 1.3 Check Current Classifier Mode

```bash
curl http://localhost:8000/diagnostics/classifier/health | jq '.mode'
```

Should return: `"heuristic"` (ML not yet enabled)

---

## Phase 2: Train ml_v1 Model

### 2.1 Run Training Script

```bash
cd /app/services/api
python -m scripts.train_email_classifier
```

**What to watch for:**
- Training set size (should match label count from Phase 1)
- Class balance (opportunities vs non-opportunities)
- Validation metrics (precision, recall, F1 for both classes)
- No errors during joblib save

**Example output:**
```
=== Email Opportunity Classifier Training ===

Loading training data from database...
✓ Loaded 195 labeled emails
  - Positive (opportunities): 65 (33.3%)
  - Negative (not opportunities): 130 (66.7%)

Splitting data (80/20 train/validation)...
  - Training set: 156 examples
  - Validation set: 39 examples

Building TF-IDF features...
✓ Feature matrix shape: (156, 4832)
  - Vocabulary size: 4832

Training Logistic Regression classifier...
✓ Training complete

=== Validation Results ===
              precision    recall  f1-score   support

     Not Opp      0.923     0.960     0.941        25
 Opportunity      0.929     0.867     0.897        15

    accuracy                          0.923        39
   macro avg      0.926     0.913     0.919        39
weighted avg      0.925     0.923     0.923        39

📊 Binary Metrics (Opportunity class):
   Precision: 0.929
   Recall:    0.867
   F1-Score:  0.897

💾 Saving model artifacts...
✓ Saved model to: /app/models/email_classifier_v1.joblib
✓ Saved vectorizer to: /app/models/email_vectorizer_v1.joblib
```

### 2.2 Document Training Results

Copy the output above and paste into `docs/EMAIL_CLASSIFICATION_STATUS.md`:

```markdown
## ml_v1 Training (First Production Run)

**Date**: 2025-12-03
**Trained by**: [Your name]
**Git commit**: [commit hash]

### Training Data
- Total labels: 195
- Opportunities: 65 (33.3%)
- Non-opportunities: 130 (66.7%)
- Training set: 156 examples
- Validation set: 39 examples

### Model Configuration
- Vectorizer: TF-IDF (max_features=50000, ngram_range=(1,2))
- Classifier: LogisticRegression (class_weight='balanced', solver='lbfgs')
- Vocabulary size: 4832 features

### Validation Performance
| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| Not Opp | 0.923 | 0.960 | 0.941 | 25 |
| Opportunity | 0.929 | 0.867 | 0.897 | 15 |
| **Overall** | **0.925** | **0.923** | **0.923** | **39** |

### Artifacts
- Model: `/app/models/email_classifier_v1.joblib` (~45KB)
- Vectorizer: `/app/models/email_vectorizer_v1.joblib` (~280KB)

### Notes
- Initial bootstrap-only labels (no manual corrections yet)
- Expect improvement after golden set labeling and corrections
- Ready for shadow mode deployment
```

Commit this to git:

```bash
cd /app
git add docs/EMAIL_CLASSIFICATION_STATUS.md
git commit -m "docs(ml): Document ml_v1 training results"
git push origin main
```

---

## Phase 3: Evaluate on Golden Set (Optional)

**Skip this section if you haven't created `email_golden_labels` table yet.**

### 3.1 Run Golden Set Evaluation

```bash
cd /app/services/api
python -m scripts.eval_email_classifier_on_golden
```

**Expected output:**
```
=== Email Classifier Evaluation (Golden Set) ===

Golden set size: 87 emails

Heuristic Classifier:
  Accuracy: 0.816
  Precision (opp): 0.741
  Recall (opp): 0.870
  F1 (opp): 0.800

ML Classifier (ml_v1):
  Accuracy: 0.897
  Precision (opp): 0.889
  Recall (opp): 0.870
  F1 (opp): 0.879

ML vs Heuristic:
  Accuracy improvement: +8.1%
  F1 improvement: +7.9%
```

### 3.2 Document Golden Set Results

Add to `docs/EMAIL_CLASSIFICATION_STATUS.md`:

```markdown
### Golden Set Evaluation

**Date**: 2025-12-03
**Golden set size**: 87 hand-labeled emails

| Metric | Heuristic | ML (ml_v1) | Improvement |
|--------|-----------|------------|-------------|
| Accuracy | 81.6% | 89.7% | +8.1% |
| Precision (opp) | 74.1% | 88.9% | +14.8% |
| Recall (opp) | 87.0% | 87.0% | 0.0% |
| F1 (opp) | 80.0% | 87.9% | +7.9% |

**Conclusion**: ML model shows significant precision improvement over heuristic baseline while maintaining recall.
```

---

## Phase 4: Build Docker Image with ml_v1

### 4.1 Verify Artifacts Are Included in Build

Check `services/api/Dockerfile`:

```dockerfile
# Should have this line:
COPY models/ /app/models/
```

If missing, add it before the `CMD` instruction.

### 4.2 Build Image

```bash
cd /app
docker build -t leoklemet/applylens-api:0.8.3-ml_v1 services/api
```

**What to watch:**
- No errors during build
- Image size reasonable (~300-500MB)
- Model files copied into `/app/models/`

### 4.3 Test Image Locally (Before Deploy)

```bash
# Stop current API container (if running in Docker)
docker compose -f docker-compose.prod.yml stop applylens-api-prod

# Run new image with heuristic mode (safe test)
docker run --rm \
  -p 8000:8000 \
  -e APPLYLENS_EMAIL_CLASSIFIER_MODE=heuristic \
  -e DATABASE_URL=$DATABASE_URL \
  leoklemet/applylens-api:0.8.3-ml_v1 \
  uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal, test health endpoint
curl http://localhost:8000/diagnostics/classifier/health | jq
```

**Expected response:**
```json
{
  "mode": "heuristic",
  "has_model_artifacts": true,
  "model_version": "v1",
  "model_loaded_at": null,
  "uses_ml": false
}
```

✅ **Key validation**: `has_model_artifacts: true` (model files are baked in)

Stop the test container: `Ctrl+C`

### 4.4 Push Image to Registry (If Using Docker Hub)

```bash
docker push leoklemet/applylens-api:0.8.3-ml_v1
```

---

## Phase 5: Deploy to Production (Heuristic Mode)

**Strategy**: Deploy image with ML artifacts, but keep mode=heuristic initially.

### 5.1 Update docker-compose.prod.yml

```yaml
services:
  applylens-api-prod:
    image: leoklemet/applylens-api:0.8.3-ml_v1  # ← Updated
    environment:
      # Keep heuristic for now - we'll switch to ml_shadow later
      APPLYLENS_EMAIL_CLASSIFIER_MODE: heuristic
      APPLYLENS_EMAIL_CLASSIFIER_MODEL_VERSION: ml_v1
      APPLYLENS_EMAIL_CLASSIFIER_MODEL_PATH: /app/models/email_classifier_v1.joblib
      APPLYLENS_EMAIL_CLASSIFIER_VECTORIZER_PATH: /app/models/email_vectorizer_v1.joblib
      # ... other env vars
```

### 5.2 Deploy Updated Container

```bash
cd /app
docker compose -f docker-compose.prod.yml up -d applylens-api-prod
```

### 5.3 Verify Deployment

```bash
# Wait for container to start (check logs)
docker compose -f docker-compose.prod.yml logs -f applylens-api-prod

# Test health endpoint
curl https://api.applylens.app/diagnostics/classifier/health | jq
```

**Expected:**
```json
{
  "mode": "heuristic",
  "has_model_artifacts": true,
  "model_version": "ml_v1",
  "uses_ml": false
}
```

✅ **Success criteria:**
- `has_model_artifacts: true` (ML files loaded)
- `mode: "heuristic"` (not using ML yet)
- No errors in logs
- API responds normally

---

## Phase 6: Enable ML Shadow Mode

**Wait 24-48 hours** after Phase 5 to ensure stability, then:

### 6.1 Update Environment to Shadow Mode

Edit `docker-compose.prod.yml`:

```yaml
APPLYLENS_EMAIL_CLASSIFIER_MODE: ml_shadow  # ← Changed from heuristic
```

### 6.2 Redeploy

```bash
docker compose -f docker-compose.prod.yml up -d applylens-api-prod
```

### 6.3 Verify Shadow Mode Active

```bash
curl https://api.applylens.app/diagnostics/classifier/health | jq
```

**Expected:**
```json
{
  "mode": "ml_shadow",
  "has_model_artifacts": true,
  "model_version": "ml_v1",
  "uses_ml": true,
  "sample_prediction": {
    "heuristic_result": "opportunity",
    "ml_result": "opportunity",
    "agreement": true
  }
}
```

### 6.4 Monitor Shadow Mode Metrics

Query database for agreement rate:

```sql
-- Shadow mode agreement over last 7 days
SELECT
    COUNT(*) as total_classifications,
    SUM(CASE WHEN heuristic_result = ml_result THEN 1 ELSE 0 END) as agreements,
    ROUND(100.0 * SUM(CASE WHEN heuristic_result = ml_result THEN 1 ELSE 0 END) / COUNT(*), 2) as agreement_pct
FROM email_classifications
WHERE classified_at >= NOW() - INTERVAL '7 days'
  AND ml_result IS NOT NULL;
```

**Target**: >85% agreement rate before promoting to `ml_live`

### 6.5 Check for Disagreements

```sql
-- Find emails where heuristic and ML disagree
SELECT
    e.id,
    e.subject,
    e.sender,
    ec.heuristic_result,
    ec.ml_result,
    ec.ml_confidence
FROM email_classifications ec
JOIN emails e ON e.id = ec.email_id
WHERE ec.heuristic_result != ec.ml_result
  AND ec.classified_at >= NOW() - INTERVAL '7 days'
ORDER BY ec.ml_confidence DESC
LIMIT 20;
```

Review these manually to identify:
- False positives (ML says opportunity, heuristic says no)
- False negatives (ML says no, heuristic says opportunity)
- Patterns suggesting model improvement opportunities

---

## Phase 7: Promote to ML Live (After Monitoring)

**Criteria for promotion:**
- Shadow mode running ≥7 days
- Agreement rate ≥85%
- No critical bugs or user complaints
- Manual review shows ML quality ≥ heuristic

### 7.1 Update to ML Live

Edit `docker-compose.prod.yml`:

```yaml
APPLYLENS_EMAIL_CLASSIFIER_MODE: ml_live  # ← Final promotion
```

### 7.2 Deploy

```bash
docker compose -f docker-compose.prod.yml up -d applylens-api-prod
```

### 7.3 Monitor Closely

- Check error rates
- User-reported misclassifications
- Database metrics (classification distribution changes)

**Rollback plan** if issues arise:

```bash
# Emergency: revert to heuristic
docker compose -f docker-compose.prod.yml exec applylens-api-prod \
  sh -c 'export APPLYLENS_EMAIL_CLASSIFIER_MODE=heuristic && pkill -HUP uvicorn'
```

---

## Troubleshooting

### Model files not found

**Symptom**: `has_model_artifacts: false`

**Fix**:
```bash
# Verify files exist in container
docker compose -f docker-compose.prod.yml exec applylens-api-prod ls -lh /app/models/

# If missing, rebuild image with correct COPY command
cd /app
docker build -t leoklemet/applylens-api:0.8.3-ml_v1 services/api
docker compose -f docker-compose.prod.yml up -d applylens-api-prod
```

### Training fails with "No labels found"

**Fix**:
```bash
# Bootstrap labels from existing heuristic classifications
python -m scripts.bootstrap_email_training_labels --dry-run=false --limit=500
```

### Low validation accuracy (<80%)

**Possible causes**:
- Insufficient training data (need 100+ labels)
- Highly imbalanced classes (>90% one class)
- Poor quality bootstrap labels

**Fix**:
1. Collect more labels (wait for user activity or bootstrap more emails)
2. Add golden set for validation
3. Review and correct bootstrap labels manually

### High disagreement in shadow mode (>30%)

**Actions**:
1. Review disagreement examples (query from Phase 6.5)
2. Check if ML is consistently wrong on specific categories
3. Retrain with corrected labels
4. Consider staying in shadow longer or reverting to heuristic

---

## Rollback Procedure

If ML deployment causes issues:

### Immediate (Emergency)

```bash
# Switch back to heuristic mode
docker compose -f docker-compose.prod.yml exec applylens-api-prod \
  sh -c 'export APPLYLENS_EMAIL_CLASSIFIER_MODE=heuristic && pkill -HUP uvicorn'
```

### Controlled (Planned)

```bash
# Update compose file
nano docker-compose.prod.yml  # Change mode to heuristic

# Redeploy
docker compose -f docker-compose.prod.yml up -d applylens-api-prod

# Verify
curl https://api.applylens.app/diagnostics/classifier/health | jq '.mode'
# Should return: "heuristic"
```

---

## Post-Deployment Checklist

- [ ] Training metrics documented in `EMAIL_CLASSIFICATION_STATUS.md`
- [ ] Docker image built and pushed: `leoklemet/applylens-api:0.8.3-ml_v1`
- [ ] Deployed with `mode: heuristic` initially
- [ ] Health endpoint shows `has_model_artifacts: true`
- [ ] Waited 24-48 hours for stability
- [ ] Enabled `ml_shadow` mode
- [ ] Monitored agreement rate ≥7 days
- [ ] Agreement rate ≥85%
- [ ] Reviewed disagreement examples
- [ ] Promoted to `ml_live` (if criteria met)
- [ ] Monitoring dashboards updated
- [ ] Team notified of ML deployment

---

## Next Steps After ml_v1

1. **Golden Set Labeling**: Hand-label 50-100 diverse emails for evaluation
2. **Model Retraining**: Retrain monthly or when new labels reach +50
3. **Feature Engineering**: Experiment with additional features (sender patterns, time-of-day)
4. **Model Comparison**: Try alternative algorithms (Random Forest, SVM)
5. **Active Learning**: Identify uncertain predictions for manual labeling
6. **A/B Testing**: Compare ml_v1 vs ml_v2 in production

See `docs/ML_TRAINING_EVALUATION_PLAN.md` for long-term roadmap.
