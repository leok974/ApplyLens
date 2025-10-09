# Smart Search Deployment Guide

## Quick Deploy: ATS Synonyms + Label Boosts + 7-Day Recency

This guide shows how to deploy the smart search features with one-shot reindexing.

---

## 1. Reindex with ATS Synonyms

Run the reindex script to create a new index with ATS search-time synonyms:

```bash
# From repo root
python -m services.api.scripts.es_reindex_with_ats
```

**What it does:**
- Creates new index `gmail_emails_v2` with ATS synonym analyzer
- Copies all data from current index
- Swaps alias `gmail_emails` to point to new index
- Zero downtime (alias swap is atomic)

**Output:**
```
Alias gmail_emails -> gmail_emails_v2 (from gmail_emails)
```

---

## 2. Restart API

Restart the API to pick up the search router changes:

```bash
# Docker Compose
docker compose restart api

# OR local development
cd services/api
uvicorn app.main:app --reload --port 8001
```

---

## 3. Test the Search

### Basic Search
```bash
curl -s "http://127.0.0.1:8001/search?q=interview" | jq '.hits[0] | {subject, labels, score}'
```

### ATS Synonym Expansion

Test that "workday" matches emails with "myworkdayjobs":

```bash
curl -s "http://127.0.0.1:8001/search?q=workday%20invite" | jq '.hits[] | {subject, sender, score}'
```

Expected: Results include emails from `myworkdayjobs.com`, `wd5.myworkday.com`, etc.

### Label Boost Verification

Search for a common term and check that offers score highest:

```bash
curl -s "http://127.0.0.1:8001/search?q=application" | jq '.hits[] | {subject, labels, score}' | head -20
```

Expected order:
1. Emails with `offer` label (score ~4x higher)
2. Emails with `interview` label (score ~3x higher)
3. Emails with no label
4. Emails with `rejection` label (score ~0.5x, demoted)

### Recency Decay

Search and compare scores by date:

```bash
curl -s "http://127.0.0.1:8001/search?q=status&size=20" | jq '.hits[] | {subject, received_at, score}' | grep -A 2 -B 2 "2025-10"
```

Expected: Recent emails (< 7 days) score higher than old emails (> 14 days)

---

## 4. Run Tests

```bash
cd services/api

# Run the scoring test
pytest -q tests/test_search_scoring.py
```

**Test verifies:**
- Label boost ordering (rejection ≤ neutral)
- Recency decay (recent > old)
- Response structure

---

## Features Enabled

### ✅ ATS Synonym Expansion

Search queries automatically expand:

| Search | Matches |
|--------|---------|
| `lever` | lever, lever.co, hire.lever.co |
| `workday` | workday, myworkdayjobs, wd1-5.myworkday |
| `smartrecruiters` | smartrecruiters, smartrecruiters.com, sr.job |

### ✅ Label Boost Scoring

Emails prioritized by importance:

| Label | Weight | Use Case |
|-------|--------|----------|
| `offer` | 4.0× | Offer letters, acceptance emails |
| `interview` | 3.0× | Interview invites, schedules |
| `rejection` | 0.5× | Rejections (demoted but searchable) |

### ✅ 7-Day Recency Decay

Gaussian decay function:
- **Today**: 100% weight
- **7 days ago**: 50% weight (half-life)
- **14 days ago**: 25% weight
- **30 days ago**: ~6% weight

### ✅ Field Boosting

Important fields weighted higher:

| Field | Boost | Rationale |
|-------|-------|-----------|
| `subject` | 3× | Subject most important |
| `sender` | 1.5× | Sender identity matters |
| `body_text` | 1× | Baseline |
| `to` | 1× | Baseline |

### ✅ Phrase + Prefix Matching

Query pattern: `"{query}" | {query}*`

Examples:
- `"job offer"` → Exact phrase "job offer"
- `interv*` → Matches interview, interviewing, etc.

---

## Tunables (in `search.py`)

You can adjust scoring weights at the top of the file:

```python
# services/api/app/routers/search.py

LABEL_WEIGHTS = {
    "offer": 4.0,        # Adjust boost for offers
    "interview": 3.0,    # Adjust boost for interviews
    "rejection": 0.5,    # Adjust penalty for rejections
}

RECENCY = {
    "origin": "now",
    "scale": "7d",       # Change to "14d" for slower decay
    "offset": "0d",
    "decay": 0.5,
}

SEARCH_FIELDS = [
    "subject^3",         # Adjust subject boost
    "body_text",
    "sender^1.5",        # Adjust sender boost
    "to"
]
```

After changing tunables:
- **No reindex required** (scoring only)
- Just restart the API

---

## Troubleshooting

### Synonyms Not Working

**Check analyzer exists:**
```bash
curl -s "http://localhost:9200/gmail_emails/_settings" | jq '.*.settings.index.analysis.analyzer.ats_search_analyzer'
```

**Test analyzer:**
```bash
curl -X POST "http://localhost:9200/gmail_emails/_analyze" -H 'Content-Type: application/json' -d'
{
  "analyzer": "ats_search_analyzer",
  "text": "workday lever"
}'
```

Should return tokens: `[workday, myworkdayjobs, wd1.myworkday, ..., lever, lever.co, hire.lever.co]`

**If missing:**
- Run reindex script again
- Check ES logs for errors

### Label Boosts Not Applied

**Verify labels field populated:**
```bash
curl -s "http://localhost:9200/gmail_emails/_search?size=1" | jq '.hits.hits[0]._source.labels'
```

**Check function_score in API logs:**
- Should see `"function_score"` with `"filter": {"terms": {"labels": ["offer"]}}`

### Recency Decay Not Working

**Check received_at field type:**
```bash
curl -s "http://localhost:9200/gmail_emails/_mapping" | jq '.*.mappings.properties.received_at'
```

Should be: `{"type": "date"}`

**Verify dates are ISO format:**
```bash
curl -s "http://localhost:9200/gmail_emails/_search?size=1" | jq '.hits.hits[0]._source.received_at'
```

Should be: `"2025-10-09T12:00:00Z"` (ISO 8601)

---

## Performance Notes

### Index Settings

Current settings (from reindex script):
```python
"number_of_shards": 1,
"number_of_replicas": 0,
```

**For production:**
- Use 3+ shards for >10M docs
- Use 1 replica for high availability
- Adjust in `es_reindex_with_ats.py` before running

### Query Performance

Expected latency:
- **< 50ms**: Simple queries (1-2 words)
- **< 100ms**: Complex queries with filters
- **< 200ms**: Queries with highlights

**If slow:**
- Check shard count (more shards = more parallelism)
- Enable query cache: `"index.queries.cache.enabled": true`
- Monitor with: `curl "http://localhost:9200/_cat/nodes?v&h=name,search.query_total,search.query_time"`

---

## Next Steps

1. ✅ Reindex with ATS synonyms
2. ✅ Restart API
3. ✅ Test search queries
4. ✅ Run pytest
5. 🔄 Monitor query performance
6. 🔄 Fine-tune weights based on user feedback
7. 🔄 Add frontend label badges (see SMART_SEARCH.md)

---

**Files Modified:**
- `services/api/scripts/es_reindex_with_ats.py` ✅ NEW
- `services/api/app/routers/search.py` ✅ Updated
- `services/api/tests/test_search_scoring.py` ✅ Simplified

**Status:** 🚀 Ready to Deploy
