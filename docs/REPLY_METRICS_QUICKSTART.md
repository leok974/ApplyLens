# Reply Metrics - Quick Deployment Guide

## 🚀 Deployment Steps (5 minutes)

### 1. Run Database Migration

```bash
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
```

✅ Adds `first_user_reply_at`, `last_user_reply_at`, `user_reply_count` columns to emails table

### 2. Update Elasticsearch Mapping  

```bash
docker compose -f infra/docker-compose.yml exec api python -m services.api.scripts.es_reindex_with_ats
```

✅ Creates new index with reply metric fields (`replied`, `first_user_reply_at`, `last_user_reply_at`, `user_reply_count`)

### 3. Backfill Existing Data

```bash
docker compose -f infra/docker-compose.yml exec api python -m services.api.scripts.backfill_reply_metrics
```

✅ Computes reply metrics for all existing emails (~1807 emails, ~156 threads)

### 4. Restart API (optional)

```bash
docker compose -f infra/docker-compose.yml restart api
```

---

## 🧪 Quick Tests

### Test 1: Check Database

```bash
docker compose -f infra/docker-compose.yml exec api psql "$DATABASE_URL" -c "
SELECT COUNT(*) as total, COUNT(first_user_reply_at) as replied FROM emails;
"
```

### Test 2: Check Elasticsearch

```bash
curl -s "http://localhost:9200/gmail_emails/_search?size=1&q=replied:true" | jq '.hits.hits[0]._source | {subject, replied, user_reply_count, first_user_reply_at}'
```

### Test 3: Test Search API

```bash
# Find unanswered threads
curl "http://localhost:8003/search?q=interview&replied=false&size=5"

# Find threads you replied to
curl "http://localhost:8003/search?q=offer&replied=true&size=5"
```

---

## 📊 Kibana Lens Setup (2 minutes)

### Create Runtime Field

1. Open Kibana → Stack Management → Index Patterns → `gmail_emails`
2. Click "Add field" → "Runtime field"
3. Name: `time_to_response_hours`
4. Type: **Number**
5. Script:

```painless
if (!doc['first_user_reply_at'].empty && !doc['received_at'].empty) {
  def start = doc['received_at'].value.toInstant().toEpochMilli();
  def end   = doc['first_user_reply_at'].value.toInstant().toEpochMilli();
  if (end >= start) emit((end - start) / 3600000.0);
}
```

### Create Visualization

1. Open Lens
2. **Metric**: Average of `time_to_response_hours`
3. **X-axis**: `received_at` (Date histogram, daily)
4. **Filter**: `time_to_response_hours >= 0` AND `time_to_response_hours <= 168`
5. **Optional break down**: `labels` (top 3)

---

## ✅ Success Checklist

- [ ] Migration shows: `Running upgrade 0005_add_gmail_tokens -> 0006_reply_metrics`
- [ ] Reindex creates new index: `gmail_emails_v2`
- [ ] Backfill processes all threads: `✅ Backfill complete!`
- [ ] Database shows replied count > 0
- [ ] Elasticsearch returns docs with `replied: true`
- [ ] Search API `?replied=false` returns unanswered threads
- [ ] Kibana runtime field calculates response times

---

## 🔧 Troubleshooting

**Migration fails**: Already applied? Check `alembic current`

**Backfill error "GMAIL_PRIMARY_ADDRESS not set"**: Set in `.env`:

```bash
GMAIL_PRIMARY_ADDRESS=leoklemet.pa@gmail.com
```

**No replied=true results**: Backfill script didn't run or user has no replies

**Negative response times**: Add Kibana filter `>= 0`

---

## 📖 Full Documentation

See `REPLY_METRICS_IMPLEMENTATION.md` for complete details.
