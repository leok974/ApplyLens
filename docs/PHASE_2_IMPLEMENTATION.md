# Phase 2: Email Categorization & Profile Analytics

## Overview

**Core Labeling Logic**

**`services/api/app/labeling/rules.py`**

- High-precision rule engine
- Pattern matching for categories
- Domain-based detection
- Header analysis

**`services/api/app/labeling/export_weak_labels.py`** ⭐ NEW

- Streams emails from Elasticsearch
- Applies rules to generate weak labels
- Extracts features for ML
- Exports balanced training data (JSONL)
- CLI with filtering options

**`services/api/app/labeling/train_ml.py`**

- ML model training script
- TF-IDF vectorization
- Logistic regression classifier
- Train/test split and evaluationends ApplyLens with intelligent email categorization and user profile analytics:

- **Automated Labeling**: High-precision rules + ML fallback for categorizing emails
- **Time-Relevance Extraction**: Parse expiration dates and event times from content
- **Profile Analytics**: Understand your email composition and sender patterns
- **Expiry Management**: Auto-hide expired promos, prioritize time-sensitive emails

## 🎯 Features

### 1. Email Categories

Emails are automatically classified into:

- **newsletter**: Mailing lists with unsubscribe headers
- **promo**: Promotional content, deals, offers
- **recruiting**: ATS systems (Lever, Greenhouse, etc.)
- **bill**: Invoices, receipts, financial documents
- **other**: Everything else

### 2. Labeling Approach

**Two-stage labeling**:

1. **High-precision rules** (95% confidence)
   - Header-based detection (List-Unsubscribe, Precedence: bulk)
   - Domain patterns (known ATS domains)
   - Content keywords (invoice, deal, promo)

2. **ML fallback** (probabilistic confidence)
   - TF-IDF + Logistic Regression
   - Trained on weak labels from rules
   - Handles ambiguous cases

### 3. Time-Relevance Features

**Expiration Detection**:

- Parses "Valid through", "Expires", "Offer ends" patterns
- Extracts dates in MM/DD/YYYY or "Month DD, YYYY" formats
- Falls back to received_at + 7 days heuristic
- Enables auto-hide of expired promos

**Event Time Parsing**:

- Detects "Meeting on", "Scheduled for" patterns
- Extracts date and time from invitations
- Powers "upcoming events" digests (future)

### 4. Profile Analytics

**Summary Statistics**:

- Total email volume
- Category breakdown with percentages
- Top senders by volume
- Average emails per day

**Sender Analysis**:

- Filter senders by category
- Track latest email from each sender
- Identify subscription opportunities

**Time Series**:

- Email volume over time
- Category trends
- Configurable intervals (hourly, daily, weekly)

## 📁 Files Created

### Core Labeling Logic

**`services/api/app/labeling/rules.py`**

- High-precision rule engine
- Pattern matching for categories
- Domain-based detection
- Header analysis

**`services/api/app/labeling/train_ml.py`**

- ML model training script
- TF-IDF vectorization
- Logistic regression classifier
- Train/test split and evaluation

**`services/api/app/labeling/relevance.py`**

- Expiration date parsing
- Event time extraction
- Time-to-expiry calculations
- Auto-hide logic

### API Routers

**`services/api/app/routers/labels.py`**

- `POST /labels/apply` - Apply labels to all emails
- `POST /labels/apply-batch` - Label specific documents
- `GET /labels/stats` - Category statistics

**`services/api/app/routers/profile.py`**

- `GET /profile/summary` - Email profile overview
- `GET /profile/senders` - Sender breakdown
- `GET /profile/categories/{category}` - Category details
- `GET /profile/time-series` - Email volume trends

### Infrastructure

**`infra/elasticsearch/emails_v1.template.json`** (Updated)

- Added Phase-2 fields:
  - `category` (keyword)
  - `confidence` (float)
  - `expires_at` (date)
  - `event_time` (date)
  - `features` (object)
  - `profile_signals` (object)
  - `auto_hide_candidate` (boolean)
  - `digest_candidates` (keyword array)

## 🚀 Quick Start

### 1. Install ML Dependencies

```bash
cd services/api
pip install scikit-learn joblib tldextract
```text

### 2. Apply Template (Already Done)

Template has been applied to Elasticsearch cluster.

### 3. Apply Labels to Existing Emails

```bash
# Label all emails (uses rules only, no ML model yet)
curl -X POST "http://localhost:8003/labels/apply" \
  -H "Content-Type: application/json" \
  -d '{}'

# Response:
# {
#   "updated": 1234,
#   "by_category": {"newsletter": 456, "promo": 321, ...},
#   "by_method": {"rule": 890, "default": 344}
# }
```text

### 4. View Profile Analytics

```bash
# Get summary
curl "http://localhost:8003/profile/summary?days=60"

# Get newsletter senders
curl "http://localhost:8003/profile/senders?category=newsletter&days=60"

# Get category details
curl "http://localhost:8003/profile/categories/promo?days=30"

# Get time series
curl "http://localhost:8003/profile/time-series?days=30&interval=1d"
```text

## 🎓 Training ML Model (Optional)

### Step 1: Export Training Data

Use the built-in weak label exporter to generate training data from Elasticsearch:

```bash
cd services/api/app/labeling

# Export 60 days of data with balanced classes (recommended)
python export_weak_labels.py \
    --days 60 \
    --limit 40000 \
    --limit-per-cat 8000 \
    --out /tmp/weak_labels.jsonl

# Output:
# 🚀 Starting export from emails_v1-000001
#    Time window: 60 days
#    Output: /tmp/weak_labels.jsonl
#
#    Processed 500 documents...
#    Processed 1000 documents...
#    ...
#
# ✅ Export complete!
#    Seen: 12,345 documents
#    Written: 8,234 documents
#
# 📊 Export Statistics:
# {
#   "seen": 12345,
#   "written": 8234,
#   "by_category": {
#     "newsletter": 2000,
#     "promo": 2000,
#     "recruiting": 1500,
#     "bill": 1234,
#     "other": 1500
#   }
# }
```text

**Export Options**:

```bash
# Export all data (no time filter)
python export_weak_labels.py --days 0 --out all_labels.jsonl

# Include unlabeled emails (for "other" category)
python export_weak_labels.py --days 60 --include-unlabeled

# Custom Elasticsearch connection
ES_URL=http://elasticsearch:9200 \
ES_EMAIL_INDEX=emails_v1-000001 \
python export_weak_labels.py --days 60

# Small balanced export for testing
python export_weak_labels.py \
    --days 30 \
    --limit 5000 \
    --limit-per-cat 1000
```text

**How it works**:

1. Streams emails from Elasticsearch using scroll API
2. Applies high-precision rules (`rules.py`) to each email
3. Extracts features (URL count, money mentions, due dates)
4. Writes JSONL with `weak_label` from rules
5. Balances classes with `--limit-per-cat`

### Step 2: Train Model

```bash
cd services/api/app/labeling

python train_ml.py /tmp/weak_labels.jsonl label_model.joblib

# Output:
# ✅ Loaded 1234 training examples
# 📊 Train set: 987 examples
# 📊 Test set: 247 examples
# 🔨 Building pipeline...
# 🏋️  Training model...
# 📈 Test Set Performance:
#               precision    recall  f1-score   support
#    newsletter       0.92      0.88      0.90        42
#         promo       0.89      0.91      0.90        35
#    recruiting       0.95      0.89      0.92        28
#          bill       0.87      0.85      0.86        20
#         other       0.78      0.82      0.80       122
# ✅ Model training complete!
```text

### Step 3: Use Model

Set environment variable to enable ML fallback:

```bash
export LABEL_MODEL_PATH=services/api/app/labeling/label_model.joblib
```text

Restart API:

```bash
cd infra
docker compose restart api
```text

Now `/labels/apply` will use ML for emails without rule matches.

## 📊 Kibana Queries

### Time to Expire (Promos)

```sql
FROM emails_v1-*
| WHERE category == "promo" AND expires_at IS NOT NULL
| EVAL tte_days = TO_LONG(expires_at - NOW()) / 86400000
| STATS avg_tte = AVG(tte_days), 
        soon = COUNT(IF(tte_days <= 3, 1, NULL)),
        expired = COUNT(IF(tte_days < 0, 1, NULL))
```text

### Inactive Subscriptions

```sql
FROM emails_v1-*
| WHERE category IN ("newsletter", "promo") 
  AND received_at >= NOW() - 60 DAY
| STATS cnt = COUNT(*) BY sender_domain
| SORT cnt DESC
| LIMIT 50
```text

### Low-Confidence Labels

```sql
FROM emails_v1-*
| WHERE confidence IS NOT NULL AND confidence < 0.5
| STATS cnt = COUNT(*) BY category
| SORT cnt DESC
```text

### Category Distribution Over Time

```sql
FROM emails_v1-*
| WHERE received_at >= NOW() - 30 DAY
| STATS emails_per_day = COUNT(*) BY DATE_TRUNC(1 DAY, received_at), category
| SORT DATE_TRUNC(1 DAY, received_at) ASC
```text

## 🔧 API Reference

### Labels Router

#### `POST /labels/apply`

Apply labels to all emails matching query.

**Request**:

```json
{
  "query": {"match_all": {}},  // ES query (optional)
  "batch_size": 200
}
```text

**Response**:

```json
{
  "updated": 1234,
  "by_category": {
    "newsletter": 456,
    "promo": 321,
    "recruiting": 89,
    "bill": 124,
    "other": 244
  },
  "by_method": {
    "rule": 890,
    "ml": 100,
    "default": 244
  }
}
```text

#### `POST /labels/apply-batch`

Label specific documents by ID.

**Request**:

```json
{
  "doc_ids": ["abc123", "def456"]
}
```text

#### `GET /labels/stats`

Get labeling statistics.

**Response**:

```json
{
  "total": 5000,
  "by_category": [
    {"category": "newsletter", "count": 1200},
    {"category": "promo", "count": 800}
  ],
  "avg_confidence": 0.87,
  "low_confidence_count": 42
}
```text

### Profile Router

#### `GET /profile/summary?days=60`

Get email profile summary.

**Response**:

```json
{
  "total": 1234,
  "days": 60,
  "avg_per_day": 20.5,
  "by_category": [
    {"category": "newsletter", "count": 456, "percent": 37.0},
    {"category": "promo", "count": 321, "percent": 26.0}
  ],
  "top_senders": [
    {"sender_domain": "example.com", "count": 42}
  ]
}
```text

#### `GET /profile/senders?category=newsletter&days=60`

Get senders filtered by category.

**Response**:

```json
{
  "category": "newsletter",
  "days": 60,
  "senders": [
    {
      "sender_domain": "newsletter.example.com",
      "count": 42,
      "latest": "2024-12-15T10:00:00Z"
    }
  ]
}
```text

#### `GET /profile/categories/newsletter?days=60`

Get detailed breakdown for a category.

**Response**:

```json
{
  "category": "newsletter",
  "total": 456,
  "days": 60,
  "avg_per_day": 7.6,
  "top_senders": [...],
  "recent_subjects": [
    {
      "subject": "Weekly Digest",
      "sender": "example.com",
      "received_at": "2024-12-15T10:00:00Z"
    }
  ]
}
```text

#### `GET /profile/time-series?days=30&interval=1d`

Get email volume time series.

**Response**:

```json
{
  "interval": "1d",
  "buckets": [
    {
      "timestamp": "2024-12-01T00:00:00Z",
      "count": 42,
      "by_category": {"newsletter": 20, "promo": 15}
    }
  ]
}
```text

## 🎨 UI Integration Points

### Inbox Enhancements

**Add Category Chips**:

```tsx
// In InboxWithActions.tsx or similar
<div className="flex gap-2 mb-4">
  {['newsletter', 'promo', 'recruiting', 'bill'].map(cat => (
    <button
      key={cat}
      onClick={() => setCategory(cat)}
      className="px-3 py-1 rounded-full text-sm bg-gray-200"
    >
      {cat}
    </button>
  ))}
</div>
```text

**Show Expiry Info**:

```tsx
// In email row component
{email.expires_at && (
  <span className="text-xs text-orange-600">
    Expires {new Date(email.expires_at).toLocaleDateString()}
  </span>
)}
```text

### Profile Page

Create new route `/profile` that displays:

1. **Summary Cards**:
   - Total emails
   - Category breakdown (pie chart)
   - Avg per day

2. **Top Senders Table**:
   - Sender domain
   - Email count
   - Category filter

3. **Time Series Chart**:
   - Line chart of email volume
   - Stacked by category

**Example**:

```tsx
// apps/web/src/pages/Profile.tsx
import { useState, useEffect } from 'react';
import { getProfile } from '../lib/api';

export default function Profile() {
  const [summary, setSummary] = useState(null);
  
  useEffect(() => {
    getProfile(60).then(setSummary);
  }, []);
  
  if (!summary) return <div>Loading...</div>;
  
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Email Profile</h1>
      
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-4 rounded shadow">
          <div className="text-3xl font-bold">{summary.total}</div>
          <div className="text-gray-600">Total Emails</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-3xl font-bold">{summary.avg_per_day}</div>
          <div className="text-gray-600">Per Day</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-3xl font-bold">{summary.by_category.length}</div>
          <div className="text-gray-600">Categories</div>
        </div>
      </div>
      
      <div className="bg-white p-6 rounded shadow">
        <h2 className="text-xl font-bold mb-4">Category Breakdown</h2>
        <div className="space-y-2">
          {summary.by_category.map(cat => (
            <div key={cat.category} className="flex items-center gap-4">
              <div className="w-32">{cat.category}</div>
              <div className="flex-1 bg-gray-200 rounded h-6 relative">
                <div 
                  className="bg-blue-500 h-full rounded"
                  style={{width: `${cat.percent}%`}}
                />
              </div>
              <div className="w-20 text-right">{cat.count}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```text

## 🔄 Workflows

### Initial Setup

1. **Apply template** (✅ done)
2. **Install dependencies**: `pip install scikit-learn joblib tldextract`
3. **Apply labels**: `curl -X POST "http://localhost:8000/labels/apply"`
4. **Check stats**: `curl "http://localhost:8000/labels/stats"`

### With Gmail Backfill

After running `gmail_backfill_to_es_bq.py`:

```bash
# 1. Backfill completes
python analytics/ingest/gmail_backfill_to_es_bq.py

# 2. Apply labels to all new emails
curl -X POST "http://localhost:8000/labels/apply"

# 3. Check category distribution
curl "http://localhost:8000/profile/summary?days=60"

# 4. Find newsletter senders to unsubscribe from
curl "http://localhost:8000/profile/senders?category=newsletter&days=60"
```text

### Training Model

```bash
# 1. Export weak labels (emails with rule matches)
cd services/api/app/labeling
python export_weak_labels.py \
  --days 60 \
  --limit 40000 \
  --limit-per-cat 8000 \
  --out /tmp/weak_labels.jsonl

# 2. Train model
python train_ml.py \
  /tmp/weak_labels.jsonl \
  label_model.joblib

# 3. Restart API with model
export LABEL_MODEL_PATH=services/api/app/labeling/label_model.joblib
docker compose -f infra/docker-compose.yml restart api

# 4. Re-label everything (now with ML fallback)
curl -X POST "http://localhost:8000/labels/apply"
```text

### Scheduled Updates

Add cron job to re-label daily:

```bash
# crontab -e
0 3 * * * curl -X POST "http://localhost:8000/labels/apply" \
  -H "Content-Type: application/json" \
  -d '{"query": {"range": {"received_at": {"gte": "now-2d"}}}}'
```text

## 🧪 Testing

### Test Rules

```bash
# Test newsletter detection
curl -X POST "http://localhost:8000/labels/apply-batch" \
  -H "Content-Type: application/json" \
  -d '{"doc_ids": ["<doc_with_list_unsubscribe>"]}'

# Verify category
curl "http://localhost:9200/emails_v1-000001/_doc/<doc_id>"
# Should see: "category": "newsletter", "reason": "Unsubscribe header present"
```text

### Test Profile Endpoints

```bash
# Summary
curl "http://localhost:8000/profile/summary?days=30" | jq

# Senders (all)
curl "http://localhost:8000/profile/senders?days=30" | jq

# Senders (newsletter only)
curl "http://localhost:8000/profile/senders?category=newsletter" | jq

# Category details
curl "http://localhost:8000/profile/categories/promo?days=7" | jq

# Time series
curl "http://localhost:8000/profile/time-series?days=30&interval=1d" | jq
```text

### Test Relevance Parsing

```python
from services.api.app.labeling.relevance import parse_promo_expiry

text = "Sale ends 12/31/2024!"
received = "2024-12-15T10:00:00Z"
expires = parse_promo_expiry(text, received)
print(expires)  # 2024-12-31 23:59:59+00:00
```text

## 📈 Metrics & Monitoring

### Prometheus Metrics

Add to API metrics:

```python
from prometheus_client import Counter, Histogram

LABELS_APPLIED = Counter(
    'applylens_labels_applied_total',
    'Total labels applied',
    ['method', 'category']
)

LABEL_CONFIDENCE = Histogram(
    'applylens_label_confidence',
    'Label confidence scores',
    ['category']
)
```text

### Grafana Dashboard

**Panel 1: Category Distribution**

```text
sum by (category) (applylens_labels_applied_total)
```text

**Panel 2: Labeling Methods**

```text
sum by (method) (applylens_labels_applied_total)
```text

**Panel 3: Average Confidence**

```text
avg(applylens_label_confidence)
```text

## 🎯 Success Criteria

- [ ] Template applied with Phase-2 fields
- [ ] `/labels/apply` endpoint working
- [ ] `/profile/summary` returns category breakdown
- [ ] Rules detect newsletters, promos, recruiting, bills
- [ ] Expiration dates parsed for promos
- [ ] Kibana queries saved and working
- [ ] ML model trained (optional but recommended)
- [ ] Profile page in web UI (next step)

## 🚀 Next Steps (Phase 3)

1. **Enhanced Relevance**:
   - Parse event times for calendar invitations
   - Extract bill due dates
   - Build "expiring soon" digest

2. **Smart Digest Candidates**:
   - Identify bills due this week
   - Find networking opportunities
   - Group similar newsletters

3. **Auto-Actions**:
   - Auto-hide expired promos
   - Batch unsubscribe suggestions
   - Priority scoring

4. **ELSER Integration**:
   - Semantic search using ELSER embeddings
   - Better categorization for edge cases
   - Content similarity detection

## 📝 Notes

- Labels can be re-applied anytime without data loss
- No reindex needed - new fields appear as written
- ML model is optional but improves coverage
- Confidence scores help identify uncertain classifications
- Profile analytics work best with 30+ days of data

## 🐛 Troubleshooting

### No Categories Showing

**Problem**: All emails have `category: null`

**Solution**: Apply labels:

```bash
curl -X POST "http://localhost:8000/labels/apply"
```text

### Low Confidence Scores

**Problem**: Most emails have confidence < 0.5

**Solution**: Train ML model with more examples

### Rules Not Matching

**Problem**: Expected newsletters not detected

**Solution**: Check for missing fields:

```bash
# Verify list_unsubscribe header present
curl "http://localhost:9200/emails_v1-000001/_search" \
  -d '{"query": {"exists": {"field": "list_unsubscribe"}}}'
```text

### Profile Shows Zero Emails

**Problem**: `/profile/summary` returns `total: 0`

**Solution**: Check date filter:

```bash
# Try larger time window
curl "http://localhost:8000/profile/summary?days=365"
```text
