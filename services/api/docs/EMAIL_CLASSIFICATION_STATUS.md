# Email Classification System - Deployment Status

## Latest Update (December 3, 2025 - Evening)

✅ **v0.8.3 - ML Training & Shadow Mode Preparation Complete**
- Created data quality inspection script (`scripts/inspect_email_training_labels.py`)
- Enhanced training script with config-based paths (uses `EMAIL_CLASSIFIER_MODEL_PATH` from settings)
- Fixed evaluation script bug (`classifier.version` → `classifier.model_version`)
- Verified shadow mode implementation (HybridEmailClassifier handles ml_shadow correctly)
- Updated Dockerfile with ML artifact COPY instructions (commented, ready to uncomment)
- Enhanced DBT documentation with shadow mode monitoring queries
- Updated ML training plan with pre-training inspection step

**Production Status**: Still heuristic mode (v0.8.2). ML infrastructure code-ready.

**Next Operational Steps:**
1. Inspect training data: `python -m scripts.inspect_email_training_labels`
2. Train ml_v1: `python -m scripts.train_email_classifier`
3. Evaluate on golden set: `python -m scripts.eval_email_classifier_on_golden`
4. Deploy shadow mode (set `EMAIL_CLASSIFIER_MODE=ml_shadow` + rebuild Docker with model artifacts)
5. Monitor agreement rate in `mart_model_comparison` for 1-2 weeks
6. If >85% agreement, promote to ml_live

---

## Previous Update (December 3, 2025 - Afternoon)

✅ **v0.8.2 - Classification Backfill & Production Rollout Complete**
- Health endpoint fixed (`body_text` instead of `snippet` field)
- All field name inconsistencies resolved (`from_address` → `sender`, `snippet` → `body_text`)
- Backfill script implemented (`scripts/backfill_email_classification.py`)
- Text building standardized across training/eval/inference (`build_email_text` helper)
- Backend integration verified:
  * Opportunities endpoint prioritizes `is_real_opportunity` field
  * Follow-up queue uses `category` and `category_confidence` in priority scoring
- Heuristic mode live in production, ready for manual backfill execution

**Status**: Code-complete. Ready for production backfill and ML training.

---

## Previous Update (December 3, 2025)

✅ **Infrastructure Phase Complete**
- Email classifier diagnostics endpoint finalized (`/diagnostics/classifier/health`)
- Environment variables documented and configured (`.env.example`, `.env.prod`)
- Backend integration complete:
  * Opportunities endpoint uses `is_real_opportunity` field
  * Follow-up queue uses `category` and `category_confidence`
  * Priority scoring enhanced with ML confidence signals
- Test coverage added for all new integrations
- Training helper script created (`scripts/train_and_eval_ml_v1.ps1`)

**Status**: Code-ready for ML shadow mode deployment. Awaiting operational decision to train ml_v1.

---

## Overview
Production-ready email classification system for ApplyLens. Automatically categorizes emails using a hybrid approach (rules + ML + heuristics) with full analytics tracking.

## Current Status: ✅ **DEPLOYED TO PRODUCTION (v0.8.1)**

### 🚀 Production Deployment Complete
- **Version**: leoklemet/applylens-api:0.8.1
- **Container**: applylens-api-prod (running)
- **Mode**: heuristic (rule-based classification)
- **Model Version**: heuristic_v1

### ✅ Step 1: Gmail Integration (COMPLETE)
- Integrated `classify_and_persist_email()` into `gmail_backfill()` and `gmail_backfill_with_progress()`
- Classification runs after `db.flush()` to ensure `email.id` is populated
- Updates: `category`, `is_real_opportunity`, `category_confidence`, `classifier_version`
- Creates `EmailClassificationEvent` for every email (analytics tracking)
- Graceful error handling - classification failures don't block ingest
- Tests passing: `test_email_classifier_integration.py`, `test_train_email_classifier.py`

### ✅ Step 2: Bootstrap Training Labels (COMPLETE)
- **Executed**: December 3, 2025
- **Results**: 195 training labels created from existing emails
- **Distribution**:
  - application_confirmation: 108 labels
  - job_alert_digest: 49 labels
  - receipt_invoice: 14 labels
  - security_auth: 12 labels
  - interview_invite: 11 labels
  - newsletter_marketing: 1 label

### Infrastructure Complete
- ✅ Database schema (4 tables + 4 email columns)
- ✅ HybridEmailClassifier (3-tier: rules → ML → heuristics)
- ✅ Training pipeline (TF-IDF + LogisticRegression)
- ✅ Service module (`app/services/classification.py`)
- ✅ Bootstrap script (6 conservative rules)
- ✅ Diagnostics endpoints (`/diagnostics/classifier/health`, `/diagnostics/classifier/reload`)
- ✅ Production bug fixes (user_id type mismatch resolved)
- ✅ **Backend integration** (Opportunities + Follow-ups use classification fields)
- ✅ **Environment configuration** (.env.example with classifier settings)
- ✅ **Test coverage** (diagnostics, opportunities, classification integration)
- ✅ **Training helper** (scripts/train_and_eval_ml_v1.ps1)

## Production Deployment Details

### Docker Image
```bash
docker pull leoklemet/applylens-api:0.8.1
# or
docker pull leoklemet/applylens-api:latest
```

### Environment Variables
```bash
EMAIL_CLASSIFIER_MODE=heuristic           # Current mode
EMAIL_CLASSIFIER_MODEL_VERSION=heuristic_v1  # Model version
```

### Database Tables Created
1. `email_classification_events` - All classification predictions logged
2. `email_category_corrections` - User feedback for model improvement
3. `email_training_labels` - Bootstrap training data
4. `email_golden_labels` - Hand-labeled evaluation set

### Email Columns Added
- `category` VARCHAR(64) - Predicted category
- `is_real_opportunity` BOOLEAN - Binary opportunity flag
- `category_confidence` FLOAT - Confidence score (0-1)
- `classifier_version` VARCHAR(64) - Model version identifier

## Next Steps (Remaining 5 Steps)

### Step 3: Train ML Model v1
**Prerequisites:**
- ✅ Inspect training data quality first: `python -m scripts.inspect_email_training_labels`
- Ensure ≥300 labels, healthy class balance (1.0-3.0 ratio), avg confidence ≥0.85

**Command:**
```bash
cd services/api
python -m scripts.train_email_classifier
```

**What happens:**
- Loads training labels with confidence ≥ 0.8
- Uses `EMAIL_CLASSIFIER_MODEL_PATH` from settings (or defaults to `models/email_classifier_v1.joblib`)
- Builds TF-IDF features (50k vocab, 1-2 grams)
- Trains LogisticRegression (balanced, LBFGS, 200 iter)
- Saves model + vectorizer to `models/` directory

**Expected Output:**
```
Loaded training labels: 487 (confidence >= 0.8)
Training samples: 389, Validation samples: 98
TF-IDF vectorization complete (50k features)
Training LogisticRegression...
Validation metrics:
  Precision (True): 0.87
  Recall (True): 0.82
  F1 (True): 0.84
  Overall Accuracy: 0.88
✅ Model saved: models/email_classifier_v1.joblib
✅ Vectorizer saved: models/email_vectorizer_v1.joblib
```

**Status:** READY TO RUN (data quality inspection script available)

---

### Step 4: Deploy in ML Shadow Mode
**Prerequisites:**
- ✅ Step 3 complete (model artifacts exist)
- ✅ Dockerfile prep complete (COPY commands ready to uncomment)

**Docker Build Process:**
```dockerfile
# In services/api/Dockerfile, uncomment these lines:
COPY models/email_classifier_v1.joblib /app/models/email_classifier_v1.joblib
COPY models/email_vectorizer_v1.joblib /app/models/email_vectorizer_v1.joblib
```

Then rebuild:
```bash
cd services/api
docker build -t leoklemet/applylens-api:0.8.3-ml_shadow .
docker push leoklemet/applylens-api:0.8.3-ml_shadow
```

**Environment Variables:**
```bash
EMAIL_CLASSIFIER_MODE=ml_shadow
EMAIL_CLASSIFIER_MODEL_VERSION=ml_v1
EMAIL_CLASSIFIER_MODEL_PATH=/app/models/email_classifier_v1.joblib
EMAIL_CLASSIFIER_VECTORIZER_PATH=/app/models/email_vectorizer_v1.joblib
```

**Health Check:**
```bash
curl https://api.applylens.io/diagnostics/classifier/health
```

Expected:
```json
{
  "ok": true,
  "status": "healthy",
  "mode": "ml_shadow",
  "model_version": "ml_v1",
  "has_model_artifacts": true,
  "uses_ml": true,
  "message": "Classifier running in ml_shadow mode with ML model loaded"
}
```

**Validation:**
- Monitor `email_classification_events` table for dual predictions (source='heuristic' and source='ml_shadow')
- Each email should have 2 events: one from heuristic (drives Email fields), one from ML (logged for comparison)
- Check `mart_model_comparison` DBT model for agreement rate (target: >85%)
- Review high-confidence disagreements manually

**Status:** CODE-READY (awaiting Step 3 completion)

---

### Step 5: Build dbt Analytics Models
**Files to Create:**
- `dashboards/dbt/models/staging/stg_email_classification_events.sql`
- `dashboards/dbt/models/mart/mart_classification_quality_daily.sql`

**Metrics:**
- Correction rate by category
- Category distribution over time
- Confidence distribution
- Drift detection

**Status:** NOT STARTED
**Blockers:** None - can run in parallel with Steps 2-4

---

### Step 6: Add Grafana Dashboard
**Panels:**
- Classification throughput (emails/min)
- Category distribution (pie chart)
- Confidence histogram
- Correction rate trend
- Drift alerts

**Status:** NOT STARTED
**Blockers:** Requires Step 5 completion

---

### Step 7: Wire Opportunities/Follow-ups UI
**Files to Update:**
- `services/api/app/routers/opportunities.py`
  - Filter: `WHERE is_real_opportunity=TRUE`
  - Order: `ORDER BY category_confidence DESC, received_at DESC`

**Status:** NOT STARTED
**Blockers:** None - can run after Step 4 validation

---

### Step 8: Gradual Rollout to ml_live
**Criteria for Promotion:**
- ✅ Correction rate <10% for 7 days
- ✅ No significant drift detected
- ✅ Precision >85% on validation set
- ✅ User feedback positive

**Rollout Plan:**
1. Enable for 10% of users
2. Monitor for 3 days
3. Increase to 50%
4. Monitor for 3 days
5. Full rollout (100%)

**Status:** NOT STARTED
**Blockers:** Requires Steps 2-6 completion + validation period

---

## Technical Details

### Classifier Modes
- **heuristic** (default): Rules + keyword matching only
- **ml_shadow**: ML predictions logged but not used (for testing)
- **ml_live**: ML predictions used in production

### Categories (11 total)
1. `recruiter_outreach` - Direct recruiter contact
2. `interview_invite` - Interview scheduling
3. `offer` - Job offers
4. `rejection` - Application rejections
5. `application_confirmation` - ATS confirmations
6. `job_alert_digest` - Job board alerts
7. `newsletter_marketing` - Marketing emails
8. `company_update` - Company news
9. `receipt_invoice` - Receipts/invoices
10. `security_auth` - 2FA/security codes
11. `personal_other` - Catch-all

### Database Schema
- **emails**: Added 4 columns (`category`, `is_real_opportunity`, `category_confidence`, `classifier_version`)
- **email_classification_events**: Logs every classification (email_id, predicted_category, confidence, source, created_at)
- **email_category_corrections**: User feedback (email_id, old_category, new_category, user_id, created_at)
- **email_golden_labels**: Hand-labeled evaluation set (target: 300-500 emails)
- **email_training_labels**: Bootstrap + user corrections (target: 5k-10k emails)

### Integration Points
```python
# Gmail ingest (gmail_service.py)
from app.services.classification import classify_and_persist_email

email = Email(...)
db.add(email)
db.flush()  # Populate email.id

classify_and_persist_email(db, email)  # One-line integration!
db.commit()
```

### Testing
```bash
cd services/api
python -m pytest tests/test_email_classifier_integration.py tests/test_train_email_classifier.py -v
# Expected: 2 passed in ~11s
```

### Diagnostics
```bash
# Health check
curl http://localhost:8000/diagnostics/classifier/health

# Response:
{
  "status": "healthy",
  "mode": "heuristic",
  "model_version": "heuristic_v1",
  "ml_model_loaded": false,
  "vectorizer_loaded": false,
  "test_classification": {
    "category": "recruiter_outreach",
    "confidence": 0.85,
    "source": "rule"
  }
}

# Hot-reload after model update
curl -X POST http://localhost:8000/diagnostics/classifier/reload
```

---

## Timeline Estimate
- **Week 1**: Steps 2-4 (bootstrap, train, shadow mode)
- **Week 2**: Steps 5-6 (analytics, dashboard)
- **Week 3**: Step 7 (UI integration) + validation
- **Week 4**: Step 8 (gradual rollout to ml_live)

**Total: 4 weeks to full production deployment**

---

## References
- Email Classification Roadmap: `docs/EMAIL_CLASSIFICATION_ROADMAP.md` (if exists)
- Phase 1 Migration: `alembic/versions/20251203_add_email_classification_tables.py`
- Classifier Implementation: `app/classification/email_classifier.py`
- Service Module: `app/services/classification.py`
- Bootstrap Script: `scripts/bootstrap_email_training_labels.py`
- Training Script: `scripts/train_email_classifier.py`
- Diagnostics Router: `app/routers/diagnostics_classifier.py`

---

**Last Updated:** 2024-12-03 (Commit 3e744d9)
**Current Phase:** Phase 1 Complete - Production Integration Active
**Production Ready:** YES (heuristic mode)
**ML Ready:** NO (requires Steps 2-3)
