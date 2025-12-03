# Local ML Demo - Email Opportunity Classifier 🧪

**Purpose**: Test the complete ML classification pipeline locally without production database access.

This "offline lab" uses synthetic training data to generate real model artifacts, allowing you to:
- Exercise the full ML inference path (load → vectorize → predict → surface)
- Test shadow mode and diagnostics endpoints
- Validate classifier integration without touching production

---

## Quick Start

### 1. Generate Demo Model Artifacts

```bash
cd services/api
python -m scripts.train_local_demo
```

**Output:**
```
✓ Generated 60 training examples
  - Positive (opportunities): 25 (41.7%)
  - Negative (not opportunities): 35 (58.3%)
✓ Training complete
💾 Saved model to: models/email_classifier_v1.joblib
💾 Saved vectorizer to: models/email_vectorizer_v1.joblib
```

**What this creates:**
- `models/email_classifier_v1.joblib` - Trained LogisticRegression classifier
- `models/email_vectorizer_v1.joblib` - Fitted TF-IDF vectorizer (861 features)
- Small synthetic dataset: 25 opportunity emails, 35 non-opportunities
- Achieves 100% accuracy on validation split (demo only - overfits on purpose)

---

## 2. Use Demo Model Locally

### Configuration

The `.env.dev` file is pre-configured for ML shadow mode:

```env
# Note: AgentSettings uses APPLYLENS_ prefix (see app/config.py)
APPLYLENS_EMAIL_CLASSIFIER_MODE=ml_shadow
APPLYLENS_EMAIL_CLASSIFIER_MODEL_VERSION=ml_v1_demo
APPLYLENS_EMAIL_CLASSIFIER_MODEL_PATH=models/email_classifier_v1.joblib
APPLYLENS_EMAIL_CLASSIFIER_VECTORIZER_PATH=models/email_vectorizer_v1.joblib
```

### Start API Server

```bash
# Standard dev server (uses .env.dev)
python -m uvicorn app.main:app --reload --port 8000

# Or with start script
.\start_server.ps1
```

### Verify ML Loading

```bash
curl http://localhost:8000/diagnostics/classifier/health | jq
```

**Expected Response:**
```json
{
  "mode": "ml_shadow",
  "has_model_artifacts": true,
  "uses_ml": true,
  "model_version": "ml_v1_demo",
  "model_loaded_at": "2025-12-03T...",
  "sample_prediction": {
    "text": "Hello! I'm reaching out about a Software Engineer opportunity...",
    "heuristic_result": "opportunity",
    "ml_result": "opportunity",
    "ml_confidence": 0.892,
    "agreement": true
  }
}
```

✅ **Success indicators:**
- `has_model_artifacts: true`
- `uses_ml: true`
- `sample_prediction` shows ML inference working
- No errors in server logs about missing files

---

## 3. Test Classification Endpoints

### Diagnose a Single Email

```bash
curl -X POST http://localhost:8000/diagnostics/classifier/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hi! I found your profile and wanted to discuss a Senior Python Developer role at our startup. Competitive salary and equity. Are you open to a quick chat?",
    "true_label": "opportunity"
  }' | jq
```

**Response:**
```json
{
  "heuristic": {
    "classification": "opportunity",
    "confidence": 0.75,
    "matched_signals": ["job_title_mention", "role_discussion"]
  },
  "ml": {
    "classification": "opportunity",
    "confidence": 0.91,
    "model_version": "ml_v1_demo"
  },
  "agreement": true,
  "true_label": "opportunity",
  "correct": {
    "heuristic": true,
    "ml": true
  }
}
```

### Run Backfill in Shadow Mode (Dry Run)

```bash
# Process 50 emails from local DB (if any exist)
python -m scripts.backfill_email_classification --limit 50 --dry-run
```

**What this tests:**
- Bulk classification workflow
- ML classifier invocation at scale
- Shadow mode comparison logic
- No database writes (dry-run)

---

## 4. File Structure

```
services/api/
├── app/
│   └── classification/
│       └── email_classifier.py          # Loads models from config paths
├── models/                               # ← Demo artifacts live here
│   ├── email_classifier_v1.joblib       # Trained classifier (25KB)
│   └── email_vectorizer_v1.joblib       # TF-IDF vectorizer (120KB)
├── scripts/
│   └── train_local_demo.py              # Generates demo artifacts
└── .env.dev                              # ML shadow mode config
```

**Path Resolution:**
- **Dev**: `config.py` defaults to `models/email_classifier_v1.joblib`
- **Prod**: Override via `EMAIL_CLASSIFIER_MODEL_PATH=/app/models/email_classifier_v1.joblib`
- Paths are relative to `services/api/` working directory

---

## 5. What the Demo Model Knows

The synthetic training data includes:

### Opportunities (25 examples):
- Recruiter outreach mentioning roles/positions
- Company hiring messages with job details
- LinkedIn InMail about opportunities
- Headhunter emails with "your profile caught my eye"
- Career opportunity messages with compensation details

### Non-Opportunities (35 examples):
- Security verification codes
- Purchase receipts and order confirmations
- Newsletter subscriptions
- Social media notifications
- Password reset emails
- Calendar invites
- Marketing campaigns
- Automated alerts
- Forum digest emails

**Training Details:**
- **Vectorization**: TF-IDF with 50,000 max features, 1-2 word n-grams
- **Model**: Logistic Regression, LBFGS solver, class_weight='balanced'
- **Validation**: 80/20 train/test split
- **Performance**: 100% accuracy on 12-sample validation set (intentionally overfit)

---

## 6. Docker Integration (Optional)

To use demo model in Docker dev environment:

### Dockerfile (already configured)

The `Dockerfile` copies model artifacts:

```dockerfile
# Copy model artifacts for ML classification
COPY models/ /app/models/
```

### docker-compose.dev.api.yml

```yaml
services:
  api:
    environment:
      EMAIL_CLASSIFIER_MODE: "ml_shadow"
      EMAIL_CLASSIFIER_MODEL_VERSION: "ml_v1_demo"
      EMAIL_CLASSIFIER_MODEL_PATH: "/app/models/email_classifier_v1.joblib"
      EMAIL_CLASSIFIER_VECTORIZER_PATH: "/app/models/email_vectorizer_v1.joblib"
```

Then:

```bash
docker-compose -f docker-compose.dev.api.yml up --build
```

---

## 7. Limitations & Caveats

⚠️ **This model is NOT for production use:**

| Aspect | Demo Model | Production Model |
|--------|-----------|------------------|
| Training Data | 60 synthetic emails | 195+ real labeled emails |
| Data Source | Hard-coded strings | Production PostgreSQL |
| Accuracy | 100% (overfit on tiny set) | ~88-92% (realistic) |
| Vocabulary | 861 features | ~5,000-10,000 features |
| Purpose | Test infrastructure | Actual classification |
| Update Frequency | Manual re-run | Scheduled retraining |

**Use this model to:**
- ✅ Verify ML loading/inference pipeline works
- ✅ Test diagnostics endpoints locally
- ✅ Experiment with shadow mode configuration
- ✅ Validate backfill scripts without prod DB

**DO NOT use for:**
- ❌ Production classification decisions
- ❌ Performance benchmarking
- ❌ Feature engineering evaluation
- ❌ Real accuracy metrics

---

## 8. Transition to Production

When ready to train on **real data** (requires production DB access):

```bash
# SSH to production server
ssh user@applylens-api-server

# Run actual training script
cd /app
python -m scripts.train_email_classifier

# Artifacts written to:
# - models/email_classifier_v1.joblib
# - models/email_vectorizer_v1.joblib
```

Then update production env:

```env
EMAIL_CLASSIFIER_MODE=ml_shadow        # Start in shadow mode
EMAIL_CLASSIFIER_MODEL_VERSION=ml_v1   # Real model version
```

Monitor shadow mode agreement rate, then promote to `ml_live` when confident.

See [ML_TRAINING_EVALUATION_PLAN.md](./ML_TRAINING_EVALUATION_PLAN.md) for full production workflow.

---

## 9. Troubleshooting

### Model files not found

**Error:** `FileNotFoundError: models/email_classifier_v1.joblib`

**Fix:**
```bash
# Re-run training script
python -m scripts.train_local_demo

# Verify files exist
ls models/
```

### Health endpoint shows `has_model_artifacts: false`

**Check:**
1. Model files exist in `models/` directory
2. Paths in `.env.dev` are correct (relative, not absolute)
3. Working directory is `services/api` when starting server
4. No typos in env var names (`EMAIL_CLASSIFIER_MODEL_PATH`)

### Predictions seem random

**This is expected** - demo model is trained on 60 synthetic examples. It will:
- Work perfectly on text similar to training data
- Behave unpredictably on real production emails
- Show high confidence even when wrong (overfit)

**Solution:** Use for testing infrastructure only, not prediction quality.

---

## 10. Next Steps

After validating local demo:

1. **Test Shadow Mode Monitoring** - Check agreement metrics in logs
2. **Run Evaluation Script** - `python -m scripts.evaluate_email_classifier` (requires real labels)
3. **Document Findings** - Note any bugs or improvements needed
4. **Plan Production Training** - Schedule training run on prod server with real data
5. **Deploy ML Model** - Follow production deployment workflow in `EMAIL_CLASSIFICATION_STATUS.md`

---

## Teaching Use Case

The `train_local_demo.py` script also serves as **educational material** for understanding:
- TF-IDF vectorization parameters
- Scikit-learn training pipeline
- Model serialization with joblib
- Validation metrics interpretation
- Feature engineering for email text

See inline comments in the script for detailed explanations of each step.
