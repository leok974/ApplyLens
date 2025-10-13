# Phase 2: Complete Workflow Guide

## 🎯 Quick Reference

### Prerequisites

✅ Gmail backfill completed (`analytics/ingest/gmail_backfill_to_es_bq.py`)  
✅ Elasticsearch index `emails_v1-000001` exists and has data  
✅ API running on port 8003  

---

## 📋 Workflow Options

### Option A: Rules Only (Fast, No Training)

Best for: Quick start, testing, or when you have good rule coverage

```bash
# 1. Apply labels using rules only
curl -X POST "http://localhost:8003/labels/apply" \
  -H "Content-Type: application/json" \
  -d '{}'

# 2. Check results
curl "http://localhost:8003/labels/stats" | jq

# 3. View profile
curl "http://localhost:8003/profile/summary?days=60" | jq
```

**Expected Results**:

- High confidence (0.95) for rule matches
- Low confidence (0.01) for "other" category
- Fast processing (~100-200 emails/sec)

---

### Option B: Rules + ML (Recommended)

Best for: Production use, better coverage, probabilistic confidence

```bash
# 1. Export training data from Elasticsearch
cd services/api/app/labeling
python export_weak_labels.py \
    --days 60 \
    --limit 40000 \
    --limit-per-cat 8000 \
    --out /tmp/weak_labels.jsonl

# Expected output:
# 🚀 Starting export from emails_v1-000001
#    Time window: 60 days
#    Output: /tmp/weak_labels.jsonl
#
#    Processed 500 documents...
#    Processed 1000 documents...
#    ...
# ✅ Export complete!
#    Written: 8,234 documents

# 2. Train ML model
python train_ml.py \
    /tmp/weak_labels.jsonl \
    label_model.joblib

# Expected output:
# ✅ Loaded 8234 training examples
# 📊 Train set: 6587 examples
# 📊 Test set: 1647 examples
# 🏋️  Training model...
# 📈 Test Set Performance:
#               precision    recall  f1-score
#    newsletter       0.92      0.88      0.90
#         promo       0.89      0.91      0.90
#    recruiting       0.95      0.89      0.92
#          bill       0.87      0.85      0.86
#         other       0.78      0.82      0.80
# ✅ Model training complete!

# 3. Configure API to use model
export LABEL_MODEL_PATH=/app/app/labeling/label_model.joblib
docker compose -f infra/docker-compose.yml restart api

# Wait for API to restart
sleep 5

# 4. Apply labels (rules + ML fallback)
curl -X POST "http://localhost:8003/labels/apply" \
  -H "Content-Type: application/json" \
  -d '{}'

# 5. Check results
curl "http://localhost:8003/labels/stats" | jq

# 6. View profile
curl "http://localhost:8003/profile/summary?days=60" | jq
```

**Expected Results**:

- High confidence (0.95) for rule matches
- Probabilistic confidence (0.5-0.95) for ML predictions
- Better coverage (fewer "other" labels)
- Slower processing (~50-100 emails/sec)

---

## 🔧 Export Options

### Balanced Export (Recommended)

```bash
python export_weak_labels.py \
    --days 60 \
    --limit 40000 \
    --limit-per-cat 8000 \
    --out /tmp/weak_labels.jsonl
```

### All Data (No Time Filter)

```bash
python export_weak_labels.py \
    --days 0 \
    --out /tmp/all_labels.jsonl
```

### Include Unlabeled (for "other" category)

```bash
python export_weak_labels.py \
    --days 60 \
    --include-unlabeled \
    --out /tmp/with_other.jsonl
```

### Small Test Export

```bash
python export_weak_labels.py \
    --days 7 \
    --limit 5000 \
    --limit-per-cat 1000 \
    --out /tmp/test_labels.jsonl
```

### Custom Elasticsearch Connection

```bash
ES_URL=http://elasticsearch:9200 \
ES_EMAIL_INDEX=emails_v1-000001 \
python export_weak_labels.py \
    --days 60 \
    --out /tmp/weak_labels.jsonl
```

---

## 📊 Profile Analytics Endpoints

### Summary (Category Breakdown)

```bash
curl "http://localhost:8003/profile/summary?days=60" | jq
```

**Response**:

```json
{
  "total": 1234,
  "days": 60,
  "avg_per_day": 20.5,
  "by_category": [
    {"category": "newsletter", "count": 456, "percent": 37.0},
    {"category": "promo", "count": 321, "percent": 26.0},
    {"category": "recruiting", "count": 89, "percent": 7.2},
    {"category": "bill", "count": 124, "percent": 10.0},
    {"category": "other", "count": 244, "percent": 19.8}
  ],
  "top_senders": [
    {"sender_domain": "example.com", "count": 42}
  ]
}
```

### Senders by Category

```bash
# All senders
curl "http://localhost:8003/profile/senders?days=60&size=20" | jq

# Newsletter senders only
curl "http://localhost:8003/profile/senders?category=newsletter&days=60" | jq

# Promo senders only
curl "http://localhost:8003/profile/senders?category=promo&days=60" | jq
```

### Category Details

```bash
curl "http://localhost:8003/profile/categories/newsletter?days=30" | jq
```

**Response**:

```json
{
  "category": "newsletter",
  "total": 456,
  "days": 30,
  "avg_per_day": 15.2,
  "top_senders": [
    {"sender_domain": "newsletter.example.com", "count": 42}
  ],
  "recent_subjects": [
    {
      "subject": "Weekly Digest",
      "sender": "example.com",
      "received_at": "2024-12-15T10:00:00Z"
    }
  ]
}
```

### Time Series

```bash
# Daily for last 30 days
curl "http://localhost:8003/profile/time-series?days=30&interval=1d" | jq

# Hourly for last 7 days
curl "http://localhost:8003/profile/time-series?days=7&interval=1h" | jq

# Weekly for last 90 days
curl "http://localhost:8003/profile/time-series?days=90&interval=1w" | jq
```

---

## 🐛 Troubleshooting

### Export: "No documents found"

```bash
# Check if index exists
curl "http://localhost:9200/emails_v1-000001/_count"

# If 404, run Gmail backfill first
cd analytics/ingest
python gmail_backfill_to_es_bq.py
```

### Training: "No valid training examples"

```bash
# Check JSONL file
head -n 5 /tmp/weak_labels.jsonl | jq

# Verify weak_label field exists
jq -r '.weak_label' /tmp/weak_labels.jsonl | sort | uniq -c
```

### Labels: "Model not found"

```bash
# Check if model file exists
ls -lh services/api/app/labeling/label_model.joblib

# Set environment variable
export LABEL_MODEL_PATH=/app/app/labeling/label_model.joblib
docker compose restart api
```

### API: "404 Not Found on ES"

```bash
# Check Elasticsearch is running
curl "http://localhost:9200/_cluster/health"

# Check index exists
curl "http://localhost:9200/_cat/indices/emails*"

# Apply template
curl -X PUT "http://localhost:9200/_index_template/emails_v1" \
  -H 'Content-Type: application/json' \
  --data-binary @infra/elasticsearch/emails_v1.template.json
```

---

## 📈 Performance Tips

### Faster Exports

- Use `--limit` to cap total rows
- Use `--limit-per-cat` for balanced classes
- Use `--days` to filter recent emails only

### Better ML Model

- Export 10k+ examples (aim for 2k+ per category)
- Balance classes with `--limit-per-cat`
- Retrain periodically as data grows
- Tune hyperparameters in `train_ml.py`

### Faster Labeling

- Use `batch_size=200` (default) for balanced speed
- Rules-only mode is 2x faster than ML
- Process in batches (filter by date range)

---

## 🎯 Success Criteria

- [ ] Export completes with balanced category distribution
- [ ] Training achieves >0.85 F1-score on test set
- [ ] `/labels/stats` shows category distribution
- [ ] `/profile/summary` returns data
- [ ] High confidence (>0.8) for most emails
- [ ] Low "other" category percentage (<30%)

---

## 🔗 Related Documentation

- **Full Guide**: `PHASE_2_IMPLEMENTATION.md`
- **Completion Summary**: `PHASE_2_COMPLETE.md`
- **Test Script**: `scripts/test-phase2-endpoints.ps1`
- **API Docs**: <http://localhost:8003/docs>
