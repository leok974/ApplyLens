# Smart Search - Label Boosts, Recency Decay & ATS Synonyms 🔍

**Status**: ✅ Demo-Ready  
**Date**: October 9, 2025

## Overview

Enhanced Elasticsearch/OpenSearch search with intelligent scoring:

- **Label boosts**: Offer (4x), Interview (3x), Rejection (0.5x)
- **7-day recency decay**: Recent emails score higher (Gaussian half-life)
- **ATS synonyms**: Lever, Workday, SmartRecruiters, Greenhouse
- **Field boosting**: Subject (3x), Sender (1.5x), Body (1x)
- **Phrase + prefix matching**: "exact phrase" | prefix*

---

## Quick Start

### 1. Update Index Settings

If index already exists, you'll need to reindex to add the new analyzer.

```bash
# Check if index exists
curl http://localhost:9200/gmail_emails

# If exists, back it up
curl -X POST "http://localhost:9200/_reindex" -H 'Content-Type: application/json' -d'
{
  "source": {"index": "gmail_emails"},
  "dest": {"index": "gmail_emails_backup"}
}'

# Delete old index
curl -X DELETE "http://localhost:9200/gmail_emails"

# Restart API (will recreate with new settings)
# Or set ES_RECREATE_ON_START=true
```

### 2. Restart API

```bash
cd services/api
uvicorn app.main:app --reload --port 8003
```

The new index settings with ATS synonyms will be created automatically.

### 3. Test Search

```bash
# Basic search
curl "http://localhost:8003/search/?q=interview"

# ATS synonym expansion
curl "http://localhost:8003/search/?q=lever"
# Matches: lever, lever.co, hire.lever.co

curl "http://localhost:8003/search/?q=workday"
# Matches: workday, myworkdayjobs, wd5.myworkday

# With filters
curl "http://localhost:8003/search/?q=offer&label_filter=offer&size=10"
```

---

## Features Explained

### 1. ATS Synonym Expansion

Automatically expands platform names to common variations:

```python
# In es.py SYNONYMS
"lever, lever.co, hire.lever.co",
"workday, myworkdayjobs, wd5.myworkday, myworkday.com",
"smartrecruiters, smartrecruiters.com, sr.job",
"greenhouse, greenhouse.io, mailer.greenhouse.io",
```

**Example**:

```bash
# Search: "lever status"
# Matches emails from:
# - lever.co
# - hire.lever.co
# - Any "lever" mention
```

### 2. Label Boost Scoring

Important emails surface first:

| Label | Weight | Use Case |
|-------|--------|----------|
| Offer | 4.0x | Offer letters, acceptance |
| Interview | 3.0x | Interview invites, schedules |
| Rejection | 0.5x | Deprioritize (still searchable) |

**Implementation**:

```python
# In search.py query
"functions": [
    {"filter": {"terms": {"labels": ["offer"]}}, "weight": 4.0},
    {"filter": {"terms": {"labels": ["interview"]}}, "weight": 3.0},
    {"filter": {"terms": {"labels": ["rejection"]}}, "weight": 0.5},
    # Also check label_heuristics
    {"filter": {"term": {"label_heuristics": "offer"}}, "weight": 4.0},
    # ...
]
```

### 3. 7-Day Recency Decay

Recent emails score higher with Gaussian decay:

```python
{
    "gauss": {
        "received_at": {
            "origin": "now",
            "scale": "7d",    # Half-life = 7 days
            "offset": "0d",   # Start decay immediately
            "decay": 0.5      # 50% score at 7 days
        }
    }
}
```

**Scoring Examples**:

- Today: 100% weight
- 7 days ago: 50% weight
- 14 days ago: 25% weight
- 30 days ago: ~6% weight

### 4. Field Boosting

Important fields get higher weight:

```python
"fields": [
    "subject^3",      # 3x weight
    "body_text",      # 1x weight (baseline)
    "sender^1.5",     # 1.5x weight
    "to"              # 1x weight
]
```

**Example**:

- Query "offer" in subject → Score × 3
- Query "offer" in body → Score × 1
- Query "offer" in sender → Score × 1.5

### 5. Phrase + Prefix Matching

Smart query parsing:

```python
f'"{q}" | {q}*'
# "interview" → Exact phrase "interview"
# interview*  → Prefix match (interviewing, interviews)
```

**Examples**:

- `"job offer"` → Exact phrase "job offer"
- `interv*` → Matches interview, interviewing, intervening

---

## API Endpoint

### GET /search/

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | required | Search query |
| `size` | int | 25 | Results per page (1-100) |
| `label_filter` | string | null | Filter by label (offer, interview, rejection) |
| `company` | string | null | Filter by company name |
| `source` | string | null | Filter by ATS source |

**Response**:

```json
{
  "total": 42,
  "hits": [
    {
      "id": 123,
      "gmail_id": "18f2a3b4c5d6e7f8",
      "thread_id": "thread_123",
      "subject": "Offer from Acme - Senior Engineer",
      "sender": "recruiting@acme.ai",
      "recipient": "you@example.com",
      "labels": ["offer"],
      "label_heuristics": ["offer"],
      "received_at": "2025-10-09T12:00:00Z",
      "company": "acme",
      "role": "Senior Engineer",
      "source": "Greenhouse",
      "score": 24.567,
      "snippet": "We're excited to extend an <mark>offer</mark> for the position...",
      "highlight": {
        "subject": ["<mark>Offer</mark> from Acme"],
        "body_text": ["extend an <mark>offer</mark> for the position"]
      }
    }
  ]
}
```

---

## Examples

### 1. Find All Offers

```bash
curl "http://localhost:8003/search/?q=offer&label_filter=offer"
```

Results sorted by:

1. Offer label boost (4x)
2. Recency (7-day decay)
3. Text relevance

### 2. Search Lever Applications

```bash
curl "http://localhost:8003/search/?q=lever application"
```

Matches:

- "lever" (synonym expansion)
- "lever.co" emails
- "hire.lever.co" emails
- "application" keyword

### 3. Recent Interview Invites

```bash
curl "http://localhost:8003/search/?q=interview&label_filter=interview&size=10"
```

Sorted by:

1. Interview label boost (3x)
2. Recency (recent first)
3. Text relevance

### 4. Company-Specific Search

```bash
curl "http://localhost:8003/search/?q=status&company=acme&size=20"
```

Filters to "acme" company, then ranks by relevance + recency.

---

## Testing

### Unit Tests

```bash
cd services/api
pytest tests/test_search_scoring.py -v
```

**Tests**:

- ✅ Response structure validation
- ✅ Filter application
- ✅ Pydantic model conformance
- ✅ Snippet extraction

### Integration Tests (Requires ES)

```bash
# Start Elasticsearch
docker run -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.11.0

# Run integration tests
export ES_ENABLED=true
export ES_URL=http://localhost:9200
pytest tests/test_search_scoring.py -v -m integration
```

**Integration Tests**:

- Label boost ordering (offer > interview > none > rejection)
- ATS synonym expansion (lever, workday)
- Recency decay (recent > old)
- Field boosting (subject > body)

### Manual Testing

```bash
# 1. Check index settings
curl http://localhost:9200/gmail_emails/_settings | jq

# Verify: ats_search_analyzer present
# Verify: synonyms include lever, workday

# 2. Test synonym expansion
curl -X POST "http://localhost:9200/gmail_emails/_analyze" -H 'Content-Type: application/json' -d'
{
  "analyzer": "ats_search_analyzer",
  "text": "lever workday"
}'

# Should return tokens: [lever, lever.co, hire.lever.co, workday, myworkdayjobs, ...]

# 3. Test search scoring
curl "http://localhost:8003/search/?q=offer" | jq '.hits[0].score'

# Compare scores:
# - Email with "offer" label should score ~4x higher
# - Recent email should score higher than old email
```

---

## Frontend Integration

### Display Label Badges

Render labels with visual priority:

```typescript
// In your React component
function LabelBadge({ label }: { label: string }) {
  const styles = {
    offer: "bg-yellow-100 text-yellow-800 border-yellow-300", // Gold
    interview: "bg-green-100 text-green-800 border-green-300", // Green
    rejection: "bg-gray-100 text-gray-500 border-gray-300", // Gray
    default: "bg-blue-100 text-blue-800 border-blue-300"
  };
  
  const icons = {
    offer: "🎉",
    interview: "📅",
    rejection: "↓"
  };
  
  return (
    <span className={`px-2 py-1 rounded border text-xs ${styles[label] || styles.default}`}>
      {icons[label]} {label}
    </span>
  );
}
```

### Show Recency Indicator

```typescript
function RecencyBadge({ receivedAt }: { receivedAt: string }) {
  const daysAgo = Math.floor(
    (Date.now() - new Date(receivedAt).getTime()) / (1000 * 60 * 60 * 24)
  );
  
  if (daysAgo === 0) return <span className="text-green-600">🕐 Today</span>;
  if (daysAgo < 7) return <span className="text-green-600">🕐 {daysAgo}d ago</span>;
  if (daysAgo < 30) return <span className="text-gray-600">{daysAgo}d ago</span>;
  return <span className="text-gray-400">{daysAgo}d ago</span>;
}
```

### Highlight Search Terms

```typescript
function HighlightedText({ text, highlight }: { text: string; highlight?: string }) {
  if (!highlight) return <>{text}</>;
  
  // Backend already adds <mark> tags
  return <span dangerouslySetInnerHTML={{ __html: highlight }} />;
}

// Usage
<HighlightedText 
  text={hit.subject}
  highlight={hit.highlight?.subject?.[0]}
/>
```

---

## Index Migration

If you have existing data, follow this migration process:

### Step 1: Create New Index

```bash
# Handled automatically by API startup with new settings
# Or manually:
curl -X PUT "http://localhost:9200/gmail_emails_v2" -H 'Content-Type: application/json' -d'
{
  "settings": { ... },  # New settings with ats_search_analyzer
  "mappings": { ... }   # Updated mappings
}'
```

### Step 2: Reindex

```bash
curl -X POST "http://localhost:9200/_reindex" -H 'Content-Type: application/json' -d'
{
  "source": {"index": "gmail_emails"},
  "dest": {"index": "gmail_emails_v2"}
}'

# Monitor progress
curl "http://localhost:9200/_tasks?detailed=true&actions=*reindex"
```

### Step 3: Swap Alias

```bash
curl -X POST "http://localhost:9200/_aliases" -H 'Content-Type: application/json' -d'
{
  "actions": [
    {"remove": {"index": "gmail_emails", "alias": "gmail_emails"}},
    {"add": {"index": "gmail_emails_v2", "alias": "gmail_emails"}}
  ]
}'
```

### Step 4: Verify

```bash
# Check alias
curl "http://localhost:9200/_cat/aliases?v"

# Test search
curl "http://localhost:8003/search/?q=lever"
```

### Step 5: Delete Old Index (Optional)

```bash
# After verifying everything works
curl -X DELETE "http://localhost:9200/gmail_emails_old"
```

---

## Performance Optimization

### 1. Index Warming

Warm up frequently used queries:

```bash
# Top queries to warm
curl "http://localhost:8003/search/?q=offer"
curl "http://localhost:8003/search/?q=interview"
curl "http://localhost:8003/search/?q=status"
```

### 2. Shard Configuration

For large datasets (>10M docs):

```json
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "refresh_interval": "30s"  # Reduce indexing load
  }
}
```

### 3. Query Caching

Enable query cache:

```json
{
  "settings": {
    "index.queries.cache.enabled": true
  }
}
```

### 4. Monitor Performance

```bash
# Check slow queries
curl "http://localhost:9200/gmail_emails/_settings" -H 'Content-Type: application/json' -d'
{
  "index.search.slowlog.threshold.query.warn": "10s",
  "index.search.slowlog.threshold.query.info": "5s"
}'

# Check query stats
curl "http://localhost:9200/_cat/nodes?v&h=name,search.query_total,search.query_time"
```

---

## Troubleshooting

### Synonyms Not Working

**Problem**: Searching "lever" doesn't match "lever.co"

**Solution**:

1. Check analyzer exists:

   ```bash
   curl "http://localhost:9200/gmail_emails/_settings" | jq '.*.settings.index.analysis'
   ```

2. Test analyzer:

   ```bash
   curl -X POST "http://localhost:9200/gmail_emails/_analyze" -H 'Content-Type: application/json' -d'
   {
     "analyzer": "ats_search_analyzer",
     "text": "lever"
   }'
   # Should return: [lever, lever.co, hire.lever.co]
   ```

3. Reindex if needed (see migration section)

### Label Boosts Not Applied

**Problem**: Offer emails don't score higher

**Solution**:

1. Check labels field populated:

   ```bash
   curl "http://localhost:9200/gmail_emails/_search?size=1" | jq '.hits.hits[0]._source.labels'
   ```

2. Verify function_score in query:

   ```bash
   # Check API logs for ES query
   # Should see "function_score" with "filter": {"terms": {"labels": ["offer"]}}
   ```

3. Test with known offer email:

   ```bash
   curl "http://localhost:8003/search/?q=offer&label_filter=offer"
   ```

### Recency Decay Not Working

**Problem**: Old emails score same as new

**Solution**:

1. Check received_at field type:

   ```bash
   curl "http://localhost:9200/gmail_emails/_mapping" | jq '.*.mappings.properties.received_at'
   # Should be: {"type": "date"}
   ```

2. Verify dates are ISO format:

   ```bash
   curl "http://localhost:9200/gmail_emails/_search?size=1" | jq '.hits.hits[0]._source.received_at'
   # Should be: "2025-10-09T12:00:00Z"
   ```

3. Test gauss decay:

   ```bash
   # Search for old and new emails, compare scores
   curl "http://localhost:8003/search/?q=application&size=50" | jq '.hits[] | {subject, received_at, score}'
   ```

---

## Production Considerations

### 1. Index Alias Pattern

Always use aliases for zero-downtime migrations:

```
gmail_emails (alias) → gmail_emails_v1 (index)
                    → gmail_emails_v2 (index) [after migration]
```

### 2. Monitoring

Track these metrics:

- Query latency (p50, p95, p99)
- Cache hit rate
- Index size growth
- Slow query count

### 3. Backup Strategy

```bash
# Daily snapshots
curl -X PUT "http://localhost:9200/_snapshot/my_backup/snapshot_$(date +%Y%m%d)" -H 'Content-Type: application/json' -d'
{
  "indices": "gmail_emails",
  "ignore_unavailable": true,
  "include_global_state": false
}'
```

### 4. Scaling

For >50M documents:

- Use 5+ shards
- Enable force merge for old indices
- Consider index-per-month pattern
- Use coordinating-only nodes

---

## Summary

✅ **ATS synonyms** - Lever, Workday, Greenhouse expansion  
✅ **Label boosts** - Offer (4x), Interview (3x), Rejection (0.5x)  
✅ **7-day recency** - Gaussian decay for recent emails  
✅ **Field boosting** - Subject (3x), Sender (1.5x)  
✅ **Phrase matching** - Exact phrase + prefix support  
✅ **Demo-ready** - Visual badges, highlights, snippets  
✅ **Tested** - Unit + integration test suite  
✅ **Production-ready** - Migration guide, monitoring, scaling  

**Next Steps**:

1. Reindex if needed (see migration section)
2. Test with real queries
3. Add frontend label badges
4. Monitor performance
5. Fine-tune weights based on user feedback

---

**Last Updated**: October 9, 2025  
**Status**: ✅ Production Ready  
**Files Changed**: 3 (es.py, search.py, test_search_scoring.py)
