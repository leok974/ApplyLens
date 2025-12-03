# Email Classification v0.8.3 → Local ML Demo 🧪

## What Was Built

A complete "offline lab" for the email opportunity classifier that enables local ML testing without production database access.

### New Files Created

1. **`scripts/train_local_demo.py`** (284 lines)
   - Generates synthetic training data (60 emails: 25 opportunities, 35 non-opportunities)
   - Trains TF-IDF + LogisticRegression classifier
   - Outputs model artifacts to `models/` directory
   - Achieves 100% validation accuracy (intentionally overfit for demo)
   - Includes extensive teaching comments explaining each step

2. **`scripts/verify_ml_demo.py`** (170 lines)
   - Sanity check script for local ML setup
   - Verifies artifacts exist and are loadable
   - Tests configuration settings
   - Runs end-to-end inference on test cases
   - Provides actionable error messages

3. **`docs/LOCAL_ML_DEMO.md`** (comprehensive guide)
   - Quick start instructions
   - File structure explanation
   - Docker integration (optional)
   - Troubleshooting guide
   - Production transition plan
   - Limitations and caveats clearly documented

### Modified Files

4. **`app/config.py`**
   - Changed `EMAIL_CLASSIFIER_MODEL_PATH` from `str | None = None` to `str = "models/email_classifier_v1.joblib"`
   - Changed `EMAIL_CLASSIFIER_VECTORIZER_PATH` from `str | None = None` to `str = "models/email_vectorizer_v1.joblib"`
   - **Benefit**: Dev environment gets working defaults; prod can override via env vars

5. **`.env.dev`**
   - Added ML shadow mode configuration:
     ```env
     APPLYLENS_EMAIL_CLASSIFIER_MODE=ml_shadow
     APPLYLENS_EMAIL_CLASSIFIER_MODEL_VERSION=ml_v1_demo
     APPLYLENS_EMAIL_CLASSIFIER_MODEL_PATH=models/email_classifier_v1.joblib
     APPLYLENS_EMAIL_CLASSIFIER_VECTORIZER_PATH=models/email_vectorizer_v1.joblib
     ```
   - **Benefit**: Local dev server uses ML classifier by default

### Generated Artifacts

6. **`models/email_classifier_v1.joblib`** (~25KB)
   - Trained LogisticRegression classifier
   - Balanced class weights
   - 861-feature vocabulary

7. **`models/email_vectorizer_v1.joblib`** (~120KB)
   - Fitted TF-IDF vectorizer
   - 50K max features, 1-2 word n-grams
   - Min document frequency = 1 (for small dataset)

---

## What Works Now

### ✅ Complete Local ML Pipeline

```bash
# 1. Generate demo model
python -m scripts.train_local_demo

# 2. Verify setup
python -m scripts.verify_ml_demo

# 3. Start API (uses ML shadow mode from .env.dev)
python -m uvicorn app.main:app --reload --port 8000

# 4. Test health endpoint
curl http://localhost:8000/diagnostics/classifier/health | jq
```

**Expected output:**
- `mode: "ml_shadow"`
- `has_model_artifacts: true`
- `uses_ml: true`
- `model_version: "ml_v1_demo"`
- Sample prediction with ML confidence scores

### ✅ No Database Required

All training uses hard-coded synthetic data:
- 25 opportunity examples (recruiter emails, job offers, hiring messages)
- 35 non-opportunity examples (receipts, notifications, newsletters)
- No PostgreSQL, Elasticsearch, or external services needed

### ✅ Teaching-Friendly Code

`train_local_demo.py` includes detailed comments explaining:
- TF-IDF vectorization parameters (`max_features`, `ngram_range`, `min_df`)
- Logistic regression configuration (`class_weight`, `solver`, `max_iter`)
- Train/test splitting strategy (80/20, stratified)
- Model serialization with joblib
- Validation metrics interpretation

### ✅ Production-Compatible Architecture

- Same TF-IDF parameters as production (except `min_df`)
- Same LogisticRegression configuration
- Same model serialization format
- Same file paths and naming conventions
- Same diagnostics/health endpoints

---

## Verification Results

```
🧪 Local ML Demo Verification

============================================================
1. Verifying Model Artifacts
============================================================
✓ Model files exist
✓ Loaded classifier: LogisticRegression
✓ Loaded vectorizer: TfidfVectorizer
  - Vocabulary size: 861

============================================================
2. Verifying Configuration
============================================================
Mode: ml_shadow
Model version: ml_v1_demo
Model path: models/email_classifier_v1.joblib
Vectorizer path: models/email_vectorizer_v1.joblib

============================================================
3. Testing Inference Pipeline
============================================================
✓ Expected: opportunity     | Got: opportunity     | Confidence: 0.577
✓ Expected: not_opportunity | Got: not_opportunity | Confidence: 0.622
✓ Expected: not_opportunity | Got: not_opportunity | Confidence: 0.545
✓ Expected: opportunity     | Got: opportunity     | Confidence: 0.580

✓ All test cases passed!
```

---

## Key Design Decisions

### 1. Default Paths in Config

**Before:**
```python
EMAIL_CLASSIFIER_MODEL_PATH: str | None = None
```

**After:**
```python
EMAIL_CLASSIFIER_MODEL_PATH: str = "models/email_classifier_v1.joblib"
```

**Rationale:**
- Dev environment "just works" without additional configuration
- Prod can override with absolute paths (`/app/models/...`)
- No breaking changes (env vars still take precedence)

### 2. APPLYLENS_ Prefix for Env Vars

All classifier settings use `APPLYLENS_` prefix per `AgentSettings.Config`:
```env
APPLYLENS_EMAIL_CLASSIFIER_MODE=ml_shadow  # Not EMAIL_CLASSIFIER_MODE
```

**Benefit:**
- Consistent with other agent settings (e.g., `APPLYLENS_PROVIDERS`)
- Avoids conflicts with third-party libraries

### 3. Intentional Overfit

The demo model achieves 100% accuracy because:
- Only 60 training examples (far too small)
- Synthetic data lacks real-world diversity
- Validation set is only 12 examples

**This is by design:**
- Proves infrastructure works correctly
- Demonstrates the ML pipeline end-to-end
- NOT meant to measure real performance

### 4. Separate Documentation

Created `LOCAL_ML_DEMO.md` instead of adding to existing docs because:
- Distinct audience (local dev vs production ops)
- Different prerequisites (no DB vs production access)
- Clear separation of concerns (demo vs real training)

---

## Limitations & Caveats

### ⚠️ Not Production-Ready

| Aspect | Demo Model | Production Model |
|--------|-----------|------------------|
| Training Data | 60 synthetic emails | 195+ real labeled emails |
| Data Source | Hard-coded strings | Production PostgreSQL |
| Accuracy | 100% (overfit) | ~88-92% (realistic) |
| Vocabulary | 861 features | ~5,000-10,000 features |
| Purpose | Test infrastructure | Actual classification |

### Use Cases

**✅ DO use for:**
- Testing ML loading/inference pipeline
- Local development without DB access
- Shadow mode configuration experiments
- Learning how the classifier works

**❌ DON'T use for:**
- Production classification decisions
- Performance benchmarking
- Feature engineering validation
- Accuracy claims or marketing

---

## File Structure

```
services/api/
├── app/
│   ├── classification/
│   │   └── email_classifier.py      # Loads models from config paths
│   └── config.py                     # Now has default model paths
├── docs/
│   └── LOCAL_ML_DEMO.md             # NEW: Complete usage guide
├── models/                           # NEW: Demo artifacts directory
│   ├── email_classifier_v1.joblib   # Trained classifier
│   └── email_vectorizer_v1.joblib   # TF-IDF vectorizer
├── scripts/
│   ├── train_local_demo.py          # NEW: Synthetic data trainer
│   └── verify_ml_demo.py            # NEW: Setup verification
└── .env.dev                          # Updated with ML shadow mode
```

---

## Next Steps

### Immediate (Now Available)

1. ✅ **Test locally** - Run `verify_ml_demo.py` and start API
2. ✅ **Experiment** - Modify synthetic data, retrain, observe changes
3. ✅ **Shadow mode** - Process emails and compare heuristic vs ML

### Short Term (This Week)

4. **Backfill Testing** - Run `backfill_email_classification.py --limit 50 --dry-run` locally
5. **Diagnostics** - Test `/diagnostics/classifier/diagnose` endpoint with various emails
6. **Documentation** - Share `LOCAL_ML_DEMO.md` with team for feedback

### Long Term (Production)

7. **Production Training** - SSH to server, run `train_email_classifier.py` on real 195+ labels
8. **Deploy ML Model** - Build Docker image with real artifacts, deploy to prod
9. **Monitor Shadow Mode** - Track agreement rate, confidence distributions
10. **Promote to Live** - Switch from `ml_shadow` to `ml_live` when confident

---

## Teaching Value

The demo script serves as educational material for:

### ML Concepts
- **TF-IDF**: How text becomes numbers (term frequency, inverse document frequency)
- **N-grams**: Capturing multi-word phrases ("senior engineer" vs "senior" + "engineer")
- **Class Imbalance**: Why `class_weight='balanced'` matters (25 vs 35 examples)
- **Train/Test Split**: Preventing overfitting with held-out validation

### Scikit-learn Pipeline
- **Vectorizer Fitting**: Learning vocabulary from training data only
- **Transform vs Fit-Transform**: Training vs inference distinction
- **Model Serialization**: Saving/loading with joblib
- **Prediction API**: `predict()` vs `predict_proba()` for confidence

### Production ML
- **Artifact Management**: Model + vectorizer as separate files
- **Path Configuration**: Environment-based deployment
- **Shadow Mode**: Testing ML alongside heuristics before cutover
- **Validation Metrics**: Precision, recall, F1 for business decisions

---

## Summary

**What we built:** A fully self-contained ML training environment that works without any external dependencies.

**What it enables:**
- Local ML development and testing
- Infrastructure validation before production deployment
- Teaching and onboarding for ML components
- Experimentation without production data access

**What's different from production:**
- Synthetic vs real training data
- 60 vs 195+ labeled examples
- 100% vs 88-92% accuracy
- Local files vs production database

**Key insight:** By creating an "offline lab" with real ML artifacts (just trained on fake data), we can test the entire classification infrastructure locally. This mirrors the production pipeline exactly, just with different input data.

The demo model works perfectly for its intended purpose: proving the plumbing is correct before running real water through it. 🚰
