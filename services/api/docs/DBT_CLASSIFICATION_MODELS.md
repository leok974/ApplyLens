# dbt Models for Email Classification Analytics

Minimal analytics stack for monitoring email classification quality and drift.

## Setup

Add these models to your dbt project (adjust schema names to match your warehouse).

## 1. Source Configuration

**`models/staging/sources.yml`** (add to existing file):

```yaml
sources:
  - name: applylens
    database: your_db_name  # Adjust for your warehouse
    schema: public
    tables:
      - name: email_classification_events
        description: "Log of all email classification predictions"
        columns:
          - name: id
            description: "Primary key"
          - name: email_id
            description: "Foreign key to emails table"
          - name: model_version
            description: "Classifier version (heuristic_v1, ml_v1, etc.)"
          - name: source
            description: "Prediction source (heuristic, ml_shadow, ml_live)"
          - name: predicted_category
            description: "Predicted email category"
          - name: predicted_is_real_opportunity
            description: "Whether email is a real job opportunity"
          - name: confidence
            description: "Prediction confidence score (0.0-1.0)"

      - name: email_category_corrections
        description: "User corrections to classification predictions"
        columns:
          - name: id
            description: "Primary key"
          - name: email_id
            description: "Foreign key to emails table"
          - name: old_category
            description: "Original predicted category"
          - name: new_category
            description: "User-corrected category"
          - name: old_is_real_opportunity
            description: "Original prediction"
          - name: new_is_real_opportunity
            description: "User-corrected value"

      - name: email_training_labels
        description: "Training labels from bootstrap rules"

      - name: email_golden_labels
        description: "Hand-labeled ground truth for evaluation"
```

## 2. Staging Models

### 2.1. Classification Events

**`models/staging/stg_email_classification_events.sql`**

```sql
{{ config(materialized = "view") }}

SELECT
  id,
  email_id,
  thread_id,
  model_version,
  predicted_category,
  predicted_is_real_opportunity,
  confidence,
  source,
  created_at AT TIME ZONE 'UTC' AS created_at_utc
FROM {{ source("applylens", "email_classification_events") }}
```

### 2.2. Category Corrections

**`models/staging/stg_email_category_corrections.sql`**

```sql
{{ config(materialized = "view") }}

SELECT
  id,
  email_id,
  thread_id,
  old_category,
  new_category,
  old_is_real_opportunity,
  new_is_real_opportunity,
  user_id,
  created_at AT TIME ZONE 'UTC' AS created_at_utc
FROM {{ source("applylens", "email_category_corrections") }}
```

### 2.3. Training Labels

**`models/staging/stg_email_training_labels.sql`**

```sql
{{ config(materialized = "view") }}

SELECT
  id,
  email_id,
  thread_id,
  label_category,
  label_is_real_opportunity,
  label_source,
  confidence,
  created_at AT TIME ZONE 'UTC' AS created_at_utc
FROM {{ source("applylens", "email_training_labels") }}
```

## 3. Mart Models

### 3.1. Daily Classification Quality

**`models/marts/mart_classification_quality_daily.sql`**

```sql
{{ config(materialized = "table") }}

WITH events AS (
    SELECT
        date_trunc('day', created_at_utc) AS event_date,
        model_version,
        source,
        predicted_category,
        predicted_is_real_opportunity,
        COUNT(*) AS event_count,
        AVG(confidence) AS avg_confidence,
        MIN(confidence) AS min_confidence,
        MAX(confidence) AS max_confidence
    FROM {{ ref("stg_email_classification_events") }}
    GROUP BY 1, 2, 3, 4, 5
),
corrections AS (
    SELECT
        date_trunc('day', created_at_utc) AS correction_date,
        COUNT(*) AS correction_count,
        COUNT(CASE WHEN old_is_real_opportunity != new_is_real_opportunity THEN 1 END) AS opportunity_corrections,
        COUNT(CASE WHEN old_category != new_category THEN 1 END) AS category_corrections
    FROM {{ ref("stg_email_category_corrections") }}
    GROUP BY 1
)
SELECT
    e.event_date,
    e.model_version,
    e.source,
    e.predicted_category,
    e.predicted_is_real_opportunity,
    e.event_count,
    e.avg_confidence,
    e.min_confidence,
    e.max_confidence,
    COALESCE(c.correction_count, 0) AS correction_count,
    COALESCE(c.opportunity_corrections, 0) AS opportunity_corrections,
    COALESCE(c.category_corrections, 0) AS category_corrections,
    CASE
        WHEN e.event_count > 0 THEN COALESCE(c.correction_count, 0)::float / e.event_count
        ELSE NULL
    END AS correction_rate
FROM events e
LEFT JOIN corrections c
  ON c.correction_date = e.event_date
ORDER BY e.event_date DESC, e.model_version, e.source, e.predicted_category;
```

### 3.2. Model Comparison (Shadow Mode Analysis)

**`models/marts/mart_model_comparison.sql`**

```sql
{{ config(materialized = "table") }}

-- Compare heuristic vs ML predictions on the same emails
WITH heuristic_preds AS (
    SELECT
        email_id,
        predicted_category AS heuristic_category,
        predicted_is_real_opportunity AS heuristic_is_opp,
        confidence AS heuristic_confidence
    FROM {{ ref("stg_email_classification_events") }}
    WHERE source = 'heuristic'
    AND created_at_utc >= CURRENT_DATE - INTERVAL '7 days'
),
ml_preds AS (
    SELECT
        email_id,
        predicted_category AS ml_category,
        predicted_is_real_opportunity AS ml_is_opp,
        confidence AS ml_confidence
    FROM {{ ref("stg_email_classification_events") }}
    WHERE source = 'ml_shadow'
    AND created_at_utc >= CURRENT_DATE - INTERVAL '7 days'
)
SELECT
    h.email_id,
    h.heuristic_category,
    m.ml_category,
    h.heuristic_is_opp,
    m.ml_is_opp,
    h.heuristic_confidence,
    m.ml_confidence,
    CASE
        WHEN h.heuristic_category = m.ml_category THEN 'match'
        ELSE 'mismatch'
    END AS category_agreement,
    CASE
        WHEN h.heuristic_is_opp = m.ml_is_opp THEN 'match'
        ELSE 'mismatch'
    END AS opportunity_agreement
FROM heuristic_preds h
INNER JOIN ml_preds m ON h.email_id = m.email_id
ORDER BY h.email_id DESC;
```

### 3.3. Category Distribution Over Time

**`models/marts/mart_category_distribution_weekly.sql`**

```sql
{{ config(materialized = "table") }}

SELECT
    date_trunc('week', created_at_utc) AS week_start,
    model_version,
    source,
    predicted_category,
    COUNT(*) AS email_count,
    COUNT(CASE WHEN predicted_is_real_opportunity THEN 1 END) AS opportunity_count,
    AVG(confidence) AS avg_confidence
FROM {{ ref("stg_email_classification_events") }}
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 2, 3, 4;
```

## 4. Grafana Dashboards

### 4.1. Classification Quality Dashboard

**Key Panels:**

1. **Correction Rate Over Time** (Time Series)
   ```sql
   SELECT
     event_date AS time,
     correction_rate,
     model_version
   FROM mart_classification_quality_daily
   WHERE event_date >= NOW() - INTERVAL '30 days'
   ORDER BY event_date;
   ```

2. **Daily Classification Volume** (Time Series)
   ```sql
   SELECT
     event_date AS time,
     SUM(event_count) AS total_classifications,
     source
   FROM mart_classification_quality_daily
   WHERE event_date >= NOW() - INTERVAL '30 days'
   GROUP BY event_date, source
   ORDER BY event_date;
   ```

3. **Category Distribution** (Pie Chart)
   ```sql
   SELECT
     predicted_category,
     SUM(event_count) AS count
   FROM mart_classification_quality_daily
   WHERE event_date >= NOW() - INTERVAL '7 days'
   GROUP BY predicted_category
   ORDER BY count DESC;
   ```

4. **Model Confidence Distribution** (Histogram)
   ```sql
   SELECT
     FLOOR(confidence * 10) / 10 AS confidence_bucket,
     COUNT(*) AS count
   FROM stg_email_classification_events
   WHERE created_at_utc >= NOW() - INTERVAL '7 days'
   GROUP BY confidence_bucket
   ORDER BY confidence_bucket;
   ```

### 4.2. Shadow Mode Comparison Dashboard

**Purpose:** Monitor ML classifier performance in shadow mode (ml_shadow) where heuristic drives production but ML predictions are logged for comparison.

**Key Panels:**

1. **Agreement Rate** (Stat)
   ```sql
   SELECT
     COUNT(CASE WHEN opportunity_agreement = 'match' THEN 1 END)::float / COUNT(*) AS agreement_rate
   FROM mart_model_comparison;
   ```
   - **Target:** >85% agreement before promoting to ml_live
   - **Warning:** <75% suggests ML needs more training data

2. **Disagreement Examples** (Table)
   ```sql
   SELECT
     email_id,
     heuristic_category,
     ml_category,
     heuristic_is_opp,
     ml_is_opp,
     heuristic_confidence,
     ml_confidence
   FROM mart_model_comparison
   WHERE opportunity_agreement = 'mismatch'
   ORDER BY ABS(heuristic_confidence - ml_confidence) DESC
   LIMIT 20;
   ```
   - **Action:** Review high-confidence disagreements manually
   - **Purpose:** Identify where ML outperforms or underperforms heuristics

3. **Shadow Mode Coverage** (Time Series)
   ```sql
   SELECT
     DATE(created_at_utc) AS date,
     source,
     COUNT(*) AS prediction_count
   FROM stg_email_classification_events
   WHERE created_at_utc >= NOW() - INTERVAL '7 days'
   GROUP BY date, source
   ORDER BY date;
   ```
   - **Validation:** Ensure both 'heuristic' and 'ml_shadow' sources exist
   - **Expected:** Equal counts (1 heuristic + 1 ml_shadow per email)

## 5. Alerts

Set up alerts in Grafana for:

1. **High Correction Rate**
   - Trigger: `correction_rate > 0.15` for 2 consecutive days
   - Action: Page on-call, review model quality

2. **Category Distribution Drift**
   - Trigger: Major shift in category proportions (>20% change week-over-week)
   - Action: Investigate data quality issues

3. **Low Confidence Predictions**
   - Trigger: `avg_confidence < 0.6` for any category
   - Action: Review classification logic

## 6. Usage

### Build models:
```bash
dbt run --select +mart_classification_quality_daily
dbt run --select +mart_model_comparison
dbt run --select +mart_category_distribution_weekly
```

### Test:
```bash
dbt test --select stg_email_classification_events
```

### Query example:
```sql
-- Check correction rate trend
SELECT
  event_date,
  model_version,
  source,
  SUM(correction_count)::float / SUM(event_count) AS overall_correction_rate
FROM mart_classification_quality_daily
WHERE event_date >= CURRENT_DATE - 30
GROUP BY event_date, model_version, source
ORDER BY event_date DESC;
```

## 7. Next Steps

After deploying these models:

1. ✅ Run bootstrap: `python -m scripts.bootstrap_email_training_labels`
2. ✅ Train ml_v1: `python -m scripts.train_email_classifier`
3. ✅ Evaluate: `python -m scripts.eval_email_classifier_on_golden`
4. ✅ Deploy ml_shadow mode
5. ✅ Monitor `mart_model_comparison` for 1-2 weeks
6. ✅ If agreement rate >85% and correction rate <10%, switch to ml_live
7. ✅ Continue monitoring correction rate and retrain monthly
