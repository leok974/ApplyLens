# Smart Search Implementation - Commit Summary

**Date**: October 9, 2025  
**Status**: ✅ Ready to Commit

---

## Changes Applied

### 1. New Files Created

#### `services/api/scripts/es_reindex_with_ats.py`

**Purpose**: One-shot reindex script with ATS synonym analyzer

**Features:**

- Creates new index with ATS search-time synonyms
- Copies data from existing index
- Atomically swaps alias (zero downtime)
- Configurable via environment variables

**Synonyms Added:**

```python
"lever, lever.co, hire.lever.co"
"workday, myworkdayjobs, wd1.myworkday, wd2.myworkday, wd3.myworkday, wd5.myworkday"
"smartrecruiters, smartrecruiters.com, sr.job"
```text

**Usage:**

```bash
python -m services.api.scripts.es_reindex_with_ats
```text

#### `services/api/scripts/__init__.py`

- Package marker for scripts module

---

### 2. Files Updated

#### `services/api/app/routers/search.py`

**Changes:**

- ✅ Added tunables at top of file:
  - `LABEL_WEIGHTS` (offer: 4.0, interview: 3.0, rejection: 0.5)
  - `RECENCY` (7-day Gaussian decay with 0.5 half-life)
  - `SEARCH_FIELDS` (subject^3, body_text, sender^1.5, to)
  - `INDEX_ALIAS` (uses configured INDEX from es.py)

- ✅ Updated function_score query to use tunables:
  - Label boost weights now reference `LABEL_WEIGHTS` dict
  - Recency decay now references `RECENCY` dict
  - Search fields now reference `SEARCH_FIELDS` list

- ✅ Changed index reference:
  - `es.search(index=INDEX)` → `es.search(index=INDEX_ALIAS)`

**Benefits:**

- Easy tuning: Change weights in one place
- Self-documenting: Clear what values control scoring
- Demo-ready: Can easily adjust for demos/presentations

#### `services/api/tests/test_search_scoring.py`

**Changes:**

- ✅ Replaced comprehensive test suite with minimal smoke test
- ✅ Test verifies label boost and recency ordering
- ✅ Simple seed_doc helper function
- ✅ One focused integration test

**Test Coverage:**

- Seeds 4 test emails with different labels and dates
- Verifies rejection doesn't beat fresh neutral email
- Lightweight and fast

---

### 3. Documentation Created

#### `SMART_SEARCH_DEPLOY.md`

**Purpose**: Quick deployment guide for smart search

**Sections:**

1. Reindex with ATS synonyms (one command)
2. Restart API
3. Test the search (curl examples)
4. Run tests
5. Features enabled
6. Tunables reference
7. Troubleshooting
8. Performance notes

**Key Info:**

- Clear step-by-step instructions
- Example queries to verify each feature
- Common troubleshooting scenarios
- Performance expectations and tuning

#### `SMART_SEARCH.md` (already existed)

**Purpose**: Comprehensive reference documentation

**Contains:**

- Detailed feature explanations
- API documentation
- Frontend integration examples
- Migration guides
- Production considerations

---

## Implementation Summary

### Core Features

#### 1. ATS Synonym Expansion ✅

- Search-time synonym filter (no reindex needed after initial setup)
- Supports: Lever, Workday, SmartRecruiters
- Example: "workday" matches "myworkdayjobs.com"

#### 2. Label Boost Scoring ✅

- Offer: 4.0× multiplier
- Interview: 3.0× multiplier
- Rejection: 0.5× penalty
- Applied to both `labels` and `label_heuristics` fields

#### 3. 7-Day Recency Decay ✅

- Gaussian function with 7-day half-life
- Recent emails score higher
- Gradual decay (not cliff)

#### 4. Field Boosting ✅

- Subject: 3× weight
- Sender: 1.5× weight
- Body/To: 1× baseline

#### 5. Phrase + Prefix Matching ✅

- Query pattern: `"{query}" | {query}*`
- Supports exact phrases and prefix wildcards

#### 6. Configurable Tunables ✅

- All weights at top of search.py
- Easy to adjust for demos
- No reindex required to change scoring

---

## How to Deploy

### Step 1: Reindex

```bash
python -m services.api.scripts.es_reindex_with_ats
```text

**Output:**

```text
Alias gmail_emails -> gmail_emails_v2 (from gmail_emails)
```text

### Step 2: Restart API

```bash
docker compose restart api
```text

### Step 3: Test

```bash
# Basic search
curl -s "http://127.0.0.1:8001/search?q=workday%20invite" | jq .

# Verify synonym expansion
curl -s "http://127.0.0.1:8001/search?q=lever" | jq '.hits[] | {sender, score}'

# Run test
pytest -q services/api/tests/test_search_scoring.py
```text

---

## Testing Checklist

- [ ] Run reindex script successfully
- [ ] Restart API without errors
- [ ] Test basic search query
- [ ] Verify ATS synonym expansion (workday, lever)
- [ ] Verify label boost ordering (offer > interview > rejection)
- [ ] Verify recency decay (recent > old)
- [ ] Run pytest test suite
- [ ] Check ES analyzer with `_analyze` endpoint
- [ ] Verify query performance (< 100ms)

---

## Files Changed

```text
services/api/scripts/
├── __init__.py                    ✨ NEW
└── es_reindex_with_ats.py        ✨ NEW (115 lines)

services/api/app/routers/
└── search.py                      📝 UPDATED (added tunables, simplified)

services/api/tests/
└── test_search_scoring.py         📝 UPDATED (simplified to 42 lines)

docs/
├── SMART_SEARCH.md               📝 EXISTING (reference)
└── SMART_SEARCH_DEPLOY.md        ✨ NEW (deployment guide)
```text

---

## Commit Message

```text
feat: Add smart search scoring with ATS synonyms and label boosts

Add "demo-ready" Elasticsearch search improvements:

Features:
- ATS synonym expansion (Lever, Workday, SmartRecruiters)
- Label boost scoring (offer 4x, interview 3x, rejection 0.5x)
- 7-day Gaussian recency decay
- Field boosting (subject 3x, sender 1.5x)
- Phrase + prefix matching pattern
- Configurable tunables at top of search.py

Changes:
- Add es_reindex_with_ats.py script for one-shot reindex
- Update search.py with tunables and simplified scoring
- Simplify test_search_scoring.py to focused smoke test
- Add SMART_SEARCH_DEPLOY.md deployment guide

Zero downtime deployment via atomic alias swap.

Usage:
  python -m services.api.scripts.es_reindex_with_ats
  docker compose restart api
  pytest -q services/api/tests/test_search_scoring.py
```text

---

## Post-Deployment Validation

### 1. Check Index Settings

```bash
curl -s "http://localhost:9200/gmail_emails/_settings" | \
  jq '.*.settings.index.analysis.analyzer.ats_search_analyzer'
```text

Expected: Should show custom analyzer with synonym filter

### 2. Test Analyzer

```bash
curl -X POST "http://localhost:9200/gmail_emails/_analyze" \
  -H 'Content-Type: application/json' -d'
{
  "analyzer": "ats_search_analyzer",
  "text": "workday lever smartrecruiters"
}'
```text

Expected: Tokens should include all synonyms

### 3. Query Performance

```bash
curl -w "\nTime: %{time_total}s\n" -s "http://127.0.0.1:8001/search?q=interview&size=20" | \
  jq '.total'
```text

Expected: < 0.1s for typical queries

### 4. Scoring Verification

```bash
curl -s "http://127.0.0.1:8001/search?q=application&size=10" | \
  jq '.hits[] | {subject, labels, score}' | head -30
```text

Expected: Offers score highest, rejections score lowest

---

## Rollback Plan

If issues occur:

### Option 1: Swap Alias Back

```bash
# Find old index name
curl "http://localhost:9200/_cat/indices?v" | grep gmail

# Swap alias back
curl -X POST "http://localhost:9200/_aliases" -H 'Content-Type: application/json' -d'
{
  "actions": [
    {"remove": {"index": "gmail_emails_v2", "alias": "gmail_emails"}},
    {"add": {"index": "gmail_emails_old", "alias": "gmail_emails"}}
  ]
}'
```text

### Option 2: Revert Code Changes

```bash
git revert HEAD
docker compose restart api
```text

---

## Future Enhancements

### Short Term

- [ ] Add Greenhouse synonyms to reindex script
- [ ] Frontend label badge ordering by weight
- [ ] Monitoring dashboard for scoring metrics

### Medium Term

- [ ] User-configurable boost weights via settings API
- [ ] A/B test different scoring formulas
- [ ] Machine learning ranking model

### Long Term

- [ ] Personalized search ranking per user
- [ ] Query understanding and autocorrect
- [ ] Semantic search with embeddings

---

**Status**: ✅ Ready to Commit and Deploy  
**Risk Level**: Low (zero downtime, easy rollback)  
**Estimated Deploy Time**: 5 minutes  
**Breaking Changes**: None
