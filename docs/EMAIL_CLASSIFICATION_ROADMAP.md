# Email Classification & Analytics Roadmap

> **Goal**: Make ApplyLens way smarter about what's actually a *real opportunity* vs "noise," and wire it into analytics so you can actually see the improvement.

This document outlines a multi-phase plan to upgrade both **analytics** and the **classification model** for email categorization in ApplyLens.

---

## Phase 0 – Clarify taxonomy & success metrics

Before we touch code, lock in *what the model is supposed to do* and how we'll measure "better".

### 0.1 Taxonomy (thread-level label)

Define a **canonical thread category**, one label per thread (multi-label later if you want). For job-search flows you probably want at least:

* `recruiter_outreach`
* `interview_invite` (phone/technical/onsite)
* `offer`
* `rejection`
* `application_confirmation` (ATS "we received your application")
* `job_alert_digest` (LinkedIn/Indeed drip emails)
* `newsletter_marketing` (blogs, generic marketing)
* `company_update` (non-job related)
* `receipt_invoice`
* `security_auth` (2FA, password reset)
* `personal_other`

Plus a boolean `is_real_opportunity` that captures "should show up on the **Opportunities** page".

> This gives you: a multi-class category + a binary "opportunity or not" flag.

### 0.2 Metrics

Define concrete offline metrics:

* **Per-class precision / recall / F1** (especially for `recruiter_outreach`, `interview_invite`, `offer`, `job_alert_digest`, `newsletter_marketing`).
* **Overall accuracy** is less important than:
  * "What fraction of Hot/Warm opportunities are actually real leads?" (precision)
  * "What fraction of real leads end up in Hot/Warm?" (recall)

And online/product metrics:

* **Manual reclassification rate**: user changes category or marks something as "not an opportunity".
* **Opportunity click-through**: how often user interacts with Hot/Warm cards.
* **Time-to-act**: time from email arrival → first user interaction for different classes.

---

## Phase 1 – Instrumentation & analytics

Right now the model is "not good" but you don't have a clean feedback loop. First step: **see** what it's doing.

### 1.1 Log every classification event

When you ingest or re-index an email thread, log a `classification_event` row:

Table `email_classification_events` (Postgres):

* `id`
* `thread_id`
* `email_id` (nullable; but thread is primary)
* `model_version` (e.g. `"heuristic_v1"`, `"ml_v0"`)
* `predicted_category`
* `predicted_is_real_opportunity` (bool)
* `confidence` (0–1)
* `source` (`"heuristic" | "ml" | "hybrid"`)
* `created_at`

And a correction table:

`email_category_corrections`:

* `id`
* `thread_id`
* `old_category`
* `new_category`
* `user_id`
* `created_at`

Hook this into:

* Gmail ingest/backfill worker
* Any "reclassify thread" API
* Opportunities / Follow-ups pages when user edits the category.

### 1.2 Analytics wiring

You already have BigQuery+dbt & Grafana/Datadog patterns. Extend them:

* **dbt models**:
  * `fct_classification_events`: base events
  * `fct_category_corrections`: manual corrections
  * `mart_classification_quality_daily`: per day & per category
    * events
    * corrections
    * correction-rate (`corrections / events`)

* **Dashboards**:
  * Panel: "Correction rate by category (7d rolling)"
  * Panel: "Share of inbox by category"
  * Panel: "Opportunity list composition: share of Hot/Warm from each category"

This will tell you where the pain is (e.g. `job_alert_digest` being mis-tagged as `recruiter_outreach`).

---

## Phase 2 – Build a proper labeled dataset

You can't fix the model without data. Let's create a **golden set** and a **training set**.

### 2.1 Golden set (for evaluation only)

* Sample **N threads** (start with 300–500, aim for 1–2k later) from:
  * Hot/Warm opportunities currently shown
  * Threads with high correction rate
  * A random slice of inbox

* Label them manually (you + a friend + future UI):
  * `golden_category`
  * `golden_is_real_opportunity`

* Store in `email_golden_labels`:
  * `thread_id`, `golden_category`, `golden_is_real_opportunity`, `labeler`, `labeled_at`

Never train on this table. It's for **offline evaluation** only.

### 2.2 Training set from heuristics + signals

Bootstrap training data from:

* Existing heuristics (`is_real_opportunity` function, current category fields)
* Gmail labels (Primary, Social, Promotions, Updates, custom labels)
* High-precision rules:
  * `security_auth`: two-factor, "verification code", "reset your password".
  * `receipt_invoice`: presence of amounts + typical invoice keywords + from `@stripe.com`, `@paypal.com`, etc.
  * `job_alert_digest` / `newsletter_marketing`: known senders (Indeed, LinkedIn, daily/weekly digest patterns).

For each thread:

* Build a **candidate** label with a confidence:
  * If a high-precision rule matches: accept as training example with high weight.
  * If only the old heuristic says "opportunity", mark with lower confidence.

Store in `email_training_labels`:

* `thread_id`
* `label_category`
* `label_is_real_opportunity`
* `label_source` (`"rule" | "heuristic" | "gmail_label" | …`)
* `confidence` (0–1)

Later you can filter to confidence ≥ 0.8 when training.

---

## Phase 3 – Feature engineering & dataset assembly

Now we turn your DB into an actual **model dataset**.

### 3.1 Features per thread

For each thread, extract:

**Textual features:**

* `subject` (lowercased, canonicalized)
* Last 1–3 message bodies (plain text, truncated)
* `from` display name + domain of most recent sender
* `to` domains (you or your alias)

**Metadata features:**

* Gmail label family (Primary/Promotions/Social/etc.)
* Whether thread has attachments
* Whether thread includes links
* Sender domain type: free mail (`gmail`, `outlook`) vs company domain
* ATS sender signals: presence of `greenhouse`, `lever`, `workday`, `ashby`, etc. in `from` or headers.
* Time features:
  * hour of day, day of week
* Thread length (messages count)

**Existing internal signals:**

* Current heuristics output (category + flags)
* Risk score (from your security/risk analyzer) as a feature (some high-risk patterns correlate with specific categories).

### 3.2 Text representation

For v1, keep it classic:

* Subject + last body text → **TF-IDF** (unigram/bigrams) or simple hashed features.
* Optionally add an embedding from your existing **bge-m3** model:
  * Precompute a sentence embedding of `subject + first 512 chars of body`.
  * Use 256–1024 dims.

Then:

* Build a training table / parquet: one row per thread with:
  * Features
  * Label (from `email_training_labels`)
  * Weight based on `confidence`.

Create a script like:

`services/api/scripts/build_email_dataset.py`

that dumps `train.csv` + `valid.csv` (or better: `.parquet`) for experimentation.

---

## Phase 4 – Baseline model(s)

Because latency and complexity matter, start simple and iterate.

### 4.1 Binary "real opportunity" model

First, a strong **binary classifier**: `is_real_opportunity`.

* Model: `LogisticRegression` or `LinearSVC` on TF-IDF subject+body.
* Features:
  * Subject/body TF-IDF
  * Sender domain type
  * Gmail label family
  * Heuristic outputs as features (not labels)

Evaluate on:

* **Training/validation split** of high-confidence training examples.
* **Golden set** for real quality.

Goal: high recall on *actual* opportunities, decent precision.

### 4.2 Multi-class category model

Once binary is decent, train a **multi-class** model:

* Model: LightGBM or XGBoost, or still LogisticRegression with one-vs-rest, using:
  * TF-IDF
  * Metadata & heuristic features
* Predict:
  * `category`
  * `probabilities per class`

You can treat this as *secondary*: only applied where `is_real_opportunity` is ≥ some confidence threshold.

### 4.3 Hybrid model architecture

Define a `Classifier` service in code:

```python
class EmailClassifier:
    def predict(self, thread) -> ClassificationResult:
        # 1. High-precision hard rules
        if rule_says_security_auth(thread):
            return Result(category="security_auth", is_real_opportunity=False, confidence=0.99, source="rule_v1")

        # 2. Binary ML model
        opp_prob = self.opp_model.predict_proba(features)[1]
        is_opp = opp_prob >= 0.5

        # 3. Multi-class model for opportunities
        if is_opp:
            cat_probs = self.category_model.predict_proba(features)
            category, cat_conf = argmax(cat_probs)
        else:
            category, cat_conf = "newsletter_marketing", 1 - opp_prob  # fallback

        # 4. Confidence and fallback
        confidence = combine(opp_prob, cat_conf)
        if confidence < 0.6:
            category = heuristic_fallback(thread)

        return Result(
            category=category,
            is_real_opportunity=is_opp,
            confidence=confidence,
            source="hybrid_ml_v1"
        )
```

This keeps **rules** for obvious things and uses ML for the messy middle.

---

## Phase 5 – Integration into ApplyLens pipeline

Now we wire this into actual ingestion and ES index.

### 5.1 Ingestion path

In the Gmail ingest job (and any incremental backfill):

1. Fetch/normalize thread.
2. Compute features (subject, snippet, etc.).
3. Call `EmailClassifier`.
4. Store:
   * `emails.category`
   * `emails.is_real_opportunity`
   * `emails.category_confidence`
   * `emails.classifier_version`
5. Log `email_classification_events` row.

### 5.2 Elasticsearch fields

Update ES mapping to include:

* `category` (keyword)
* `is_real_opportunity` (boolean)
* `category_confidence` (float)

Use them in:

* Search boosts (e.g., filter or boost by opportunities in Search page).
* Opportunities index queries (instead of pure heuristic filtering).

### 5.3 Follow-ups & Opportunities integration

Update your existing scoring functions to use **new classifier outputs**:

* `is_real_opportunity` becomes the gate for inclusion in `/api/opportunities`.
* `email_category` from the model feeds into:
  * `compute_opportunity_priority`
  * `compute_followup_priority`

so your scoring is aligned with the improved categories.

---

## Phase 6 – Rollout, A/B, and continuous learning

Don't flip the switch blindly; use a **shadow + canary** path, similar to your LedgerMind ML roadmap.

### 6.1 Shadow mode

For a while:

* Keep the old heuristic pipeline as the **live** source of category.
* Run the new classifier in **shadow mode** on the same threads:
  * Store its predictions in `email_classification_events` with `source="ml_shadow_v1"`.
  * Compare to:
    * Heuristic labels
    * Golden set
    * User corrections

This gives you:

* Offline "confusion matrix" between `heuristic` vs `ml_shadow_v1`.
* Actual measured improvement for key classes.

### 6.2 Canary rollout

Once you're happy with the numbers:

* Enable `ml_v1` for a small fraction of users (or just a fraction of *new threads* if user segmentation is hard).
* Add a feature flag: `EMAIL_CLASSIFIER_MODE = "heuristic" | "ml_shadow" | "ml_live"`.

Monitor:

* Correction rate vs baseline.
* # of Hot/Warm opportunities the user interacts with.

If regression: roll back to `heuristic`.

### 6.3 Continuous learning loop

With logs in place, you can:

* Periodically build a **new training dataset**:
  * Old training labels
  * Plus:
    * High-confidence model predictions that were not corrected (self-training).
    * User corrections as hard labels.

* Re-train and version models:
  * `ml_v2`, `ml_v3`, etc.

* Airflow/cron job or GitHub Actions job for:
  * `/scripts/train_email_classifier.py`
  * Upload/save `model.pkl` or ONNX to a models dir.
  * Kick a deploy with the new `MODEL_VERSION`.

Set up Datadog/Grafana alerts when:

* Correction rate spikes over threshold.
* Category distribution shifts drastically (drift detection).

---

## Phase 7 – UI & UX feedback tools

The more feedback you collect, the better the model gets.

* Add a small **"Not an opportunity"** / **"Wrong category"** control on:
  * Thread details
  * Opportunities cards
  * Follow-ups cards

* UX: one click to:
  * De-opportunity a thread
  * Or pick the correct category from a small list

* Backend:
  * Writes to `email_category_corrections`
  * Triggers an optional re-classification / re-index.

Also consider a **"Why is this here?"** tooltip:

* Show:
  * Category
  * Confidence
  * A couple of keyword cues (from rules) or "recent recruiter email with subject containing 'interview'".

That's both user-friendly *and* gives you a hook to log which explanations are used.

---

## Implementation Tasks

### Phase 1: Instrumentation
- [ ] Add `email_classification_events` table (Alembic migration)
- [ ] Add `email_category_corrections` table (Alembic migration)
- [ ] Implement logging of classification events in Gmail ingest pipeline
- [ ] Implement logging in reclassify API endpoints
- [ ] Add dbt models: `fct_classification_events`, `fct_category_corrections`, `mart_classification_quality_daily`
- [ ] Create Grafana/Datadog dashboard panels for classification quality

### Phase 2: Dataset Building
- [ ] Add `email_golden_labels` table (Alembic migration)
- [ ] Add `email_training_labels` table (Alembic migration)
- [ ] Create UI for manual labeling of golden set
- [ ] Implement high-precision rule detection for training labels
- [ ] Create `scripts/build_email_dataset.py`

### Phase 3: Feature Engineering
- [ ] Implement feature extraction module (`app/ml/features.py`)
- [ ] Add text preprocessing utilities
- [ ] Implement TF-IDF feature extraction
- [ ] Add BGE-M3 embedding generation
- [ ] Create dataset assembly pipeline

### Phase 4: Model Training
- [ ] Implement `EmailClassifier` base class (`app/ml/classifier.py`)
- [ ] Create `scripts/train_email_classifier.py`
- [ ] Train binary "real opportunity" model
- [ ] Train multi-class category model
- [ ] Implement hybrid rule + ML architecture
- [ ] Add model versioning and storage

### Phase 5: Integration
- [ ] Add ES mapping for `category`, `is_real_opportunity`, `category_confidence`
- [ ] Wire classifier into Gmail ingest pipeline
- [ ] Update `/api/opportunities` to use `is_real_opportunity`
- [ ] Update `/api/v2/agent/followup-queue` to use new categories
- [ ] Add `emails.category`, `emails.category_confidence`, `emails.classifier_version` DB fields

### Phase 6: Rollout
- [ ] Add `EMAIL_CLASSIFIER_MODE` feature flag
- [ ] Implement shadow mode logging
- [ ] Create comparison dashboard (heuristic vs ML)
- [ ] Set up canary deployment infrastructure
- [ ] Add Datadog/Grafana alerts for drift detection
- [ ] Create continuous learning pipeline (Airflow/GitHub Actions)

### Phase 7: User Feedback
- [ ] Add "Not an opportunity" button to Opportunities cards
- [ ] Add "Wrong category" dropdown to thread details
- [ ] Implement category correction API endpoint
- [ ] Add "Why is this here?" tooltip with explanation
- [ ] Wire corrections into `email_category_corrections` table
- [ ] Trigger re-classification on user correction

---

## Repo Audit Checklist

When starting implementation, audit the codebase for:

1. **Current category/classification logic**:
   - [ ] Where `email.category` / `is_real_opportunity` fields are defined in models
   - [ ] Current heuristics in `app/email_parsing.py` or similar
   - [ ] How opportunities are filtered in `/api/opportunities` endpoint

2. **Gmail ingest pipeline**:
   - [ ] Location of Gmail message → DB code
   - [ ] Backfill worker implementation
   - [ ] Thread normalization logic

3. **Existing analytics**:
   - [ ] Current dbt models structure
   - [ ] Existing Grafana/Datadog dashboards
   - [ ] BigQuery export patterns

4. **Current scoring logic**:
   - [ ] `compute_opportunity_priority` implementation
   - [ ] `compute_followup_priority` implementation
   - [ ] How categories influence priority today

---

## Success Criteria

### Phase 1 (Instrumentation):
- ✅ Classification events logged for 100% of ingested emails
- ✅ Dashboard showing correction rate by category
- ✅ Baseline metrics established

### Phase 2 (Dataset):
- ✅ 500+ threads in golden set
- ✅ 5,000+ high-confidence training examples
- ✅ Dataset export pipeline working

### Phase 3-4 (Model):
- ✅ Binary opportunity model: >90% recall, >70% precision on golden set
- ✅ Multi-class model: >80% accuracy on high-confidence classes
- ✅ End-to-end inference latency <100ms

### Phase 5-6 (Integration):
- ✅ Shadow mode shows 20%+ reduction in correction rate
- ✅ No increase in user friction (time-to-act stays same or improves)
- ✅ Canary rollout completes without rollback

### Phase 7 (Feedback):
- ✅ User correction flow takes <3 clicks
- ✅ 5%+ of opportunities get user feedback in first month
- ✅ Corrections feed back into training pipeline

---

## Timeline Estimate

- **Phase 1**: 1-2 weeks (instrumentation + analytics)
- **Phase 2**: 1-2 weeks (dataset building)
- **Phase 3-4**: 2-3 weeks (features + baseline models)
- **Phase 5**: 1-2 weeks (integration)
- **Phase 6**: 2-4 weeks (shadow mode + rollout)
- **Phase 7**: 1 week (UI feedback tools)

**Total**: ~2-3 months for full deployment with continuous learning

---

## Next Steps

1. **Immediate**: Create DB migrations for Phase 1 tables
2. **Week 1**: Implement classification event logging in ingest pipeline
3. **Week 2**: Set up analytics dashboards
4. **Week 3**: Begin golden set labeling
5. **Month 2**: Train and validate baseline models
6. **Month 3**: Shadow mode deployment and monitoring
