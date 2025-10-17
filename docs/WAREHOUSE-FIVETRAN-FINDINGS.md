# Fivetran & BigQuery Warehouse Integration - Findings & Next Steps

**Date:** October 16, 2025  
**Status:** ✅ dbt models working, API integration pending

## 🔍 Key Findings

### 1. Fivetran Dataset Location
**Expected:** `gmail_raw`  
**Actual:** `gmail` 

Fivetran created the dataset using the connector/group name, not our assumed `gmail_raw`.

**Tables in `gmail` dataset:**
- `message` (not `messages` - singular!)
- `thread` (not `threads`)
- `label` (not `labels`)
- `message_label`
- `message_payload_part`
- `message_payload_part_header`
- `message_sub_part_header`
- `payload_header`
- `profile`

### 2. Schema Differences

The Fivetran Gmail schema is more normalized than expected:

**Expected (simple):**
```sql
messages {
  id, thread_id, from, to, subject, label_ids
}
```

**Actual (normalized):**
```sql
message {
  id, thread_id, internal_date, snippet, size_estimate
  -- No from/to/subject in main table!
}

payload_header {
  message_id, name, value
  -- Extract from/to/subject via JOINs
}

message_payload_part_header {
  -- Additional email headers
}
```

### 3. dbt Configuration Solution

Created `sources.yml` with dynamic dataset name:

```yaml
sources:
  - name: gmail_raw
    database: "{{ env_var('GCP_PROJECT') }}"
    schema: "{{ var('raw_dataset', env_var('RAW_DATASET', 'gmail_raw')) }}"
    tables:
      - name: message
      - name: thread
      - name: label
```

**Run with:**
```bash
dbt run --target prod --vars 'raw_dataset: gmail'
```

Or set `RAW_DATASET=gmail` in environment.

## ✅ What's Working

### dbt Models (Successfully Built)

**Staging Views** (in `gmail_raw_stg_gmail_raw_stg`):
- ✅ `stg_gmail__messages` - 3,000+ messages (90 days)
- ✅ `stg_gmail__threads` - Thread metadata
- ✅ `stg_gmail__labels` - Label metadata

**Mart Tables** (in `gmail_raw_stg_gmail_marts`):
- ✅ `mart_email_activity_daily` - 90 rows (90 days of data)
  - Partitioned by `day`, clustered by `day`
  - Metrics: messages_count, avg_size_kb, total_size_mb
  - Note: `unique_senders` = 0 (need to parse headers)
  
- ✅ `mart_top_senders_30d` - 0 rows (no sender data yet)
  
- ✅ `mart_categories_30d` - 1 row (simplified)
  - Currently shows all as 'uncategorized'
  - Need to parse `message_label` join table

**Sample Data:**
```
+------------+----------------+----------------+-------------+---------------+
|    day     | messages_count | unique_senders | avg_size_kb | total_size_mb |
+------------+----------------+----------------+-------------+---------------+
| 2025-10-08 |             23 |              0 |       31.22 |          0.70 |
| 2025-09-23 |             32 |              0 |       46.39 |          1.45 |
| 2025-08-12 |             10 |              0 |       69.63 |          0.68 |
+------------+----------------+----------------+-------------+---------------+
```

### Environment Configuration

**Updated `.env.prod`:**
```bash
USE_WAREHOUSE_METRICS=0  # Temporarily disabled
GCP_PROJECT=applylens-gmail-1759983601
RAW_DATASET=gmail  # NEW: Actual Fivetran dataset
BQ_MARTS_DATASET=gmail_raw_stg_gmail_marts  # Actual mart dataset created by dbt
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/applylens-warehouse-key.json
```

## 🚧 What Needs Work

### 1. Parse Email Headers (High Priority)

**Problem:** `from_email`, `to_emails`, `subject` are NULL in staging models.

**Solution:** Join with `payload_header` table:

```sql
-- Enhanced stg_gmail__messages.sql
with msg_base as (
  select * from {{ source('gmail_raw', 'message') }}
),

headers as (
  select
    message_id,
    max(case when name = 'From' then value end) as from_email,
    max(case when name = 'To' then value end) as to_emails,
    max(case when name = 'Subject' then value end) as subject
  from {{ source('gmail_raw', 'payload_header') }}
  where name in ('From', 'To', 'Subject')
  group by 1
)

select
  msg.id as message_id,
  msg.thread_id,
  timestamp_millis(cast(msg.internal_date as int64)) as received_ts,
  msg.snippet,
  h.from_email,
  h.to_emails,
  h.subject,
  msg.size_estimate as size_bytes,
  msg._fivetran_synced as synced_at
from msg_base msg
left join headers h on msg.id = h.message_id
where msg._fivetran_deleted is false
```

**Impact:**
- ✅ `unique_senders` will have real data
- ✅ `mart_top_senders_30d` will populate
- ✅ API endpoints will return meaningful data

### 2. Parse Category Labels (Medium Priority)

**Problem:** `mart_categories_30d` shows only 'uncategorized'.

**Solution:** Join with `message_label` table:

```sql
with msg_labels as (
  select 
    ml.message_id,
    array_agg(l.name) as label_names
  from {{ source('gmail_raw', 'message_label') }} ml
  join {{ source('gmail_raw', 'label') }} l on ml.label_id = l.id
  group by 1
)

select
  msg.message_id,
  case
    when 'CATEGORY_PROMOTIONS' in unnest(ml.label_names) then 'promotions'
    when 'CATEGORY_UPDATES' in unnest(ml.label_names) then 'updates'
    ...
  end as category
from {{ ref('stg_gmail__messages') }} msg
left join msg_labels ml on msg.message_id = ml.message_id
```

### 3. Enable API Endpoints (Blocked by #1)

**Current Status:** API imports are working, but warehouse metrics disabled.

**Dependencies:**
- ✅ `google-cloud-bigquery>=3.25.0` already in `pyproject.toml`
- ✅ Service account has `bigquery.dataEditor` role
- ✅ API code in `metrics_profile.py` is ready
- ❌ Need meaningful data (parse headers first)

**Steps to Enable:**
1. Fix staging models (parse headers)
2. Rebuild marts: `dbt run --target prod --vars 'raw_dataset: gmail'`
3. Verify data: Check `unique_senders > 0`
4. Set `USE_WAREHOUSE_METRICS=1` in `.env.prod`
5. Restart API: `docker compose -f docker-compose.prod.yml --env-file infra/.env.prod restart api`
6. Test endpoints:
   ```bash
   curl http://localhost/api/metrics/profile/activity_daily?days=7
   curl http://localhost/api/metrics/profile/top_senders_30d?limit=10
   curl http://localhost/api/metrics/profile/categories_30d
   curl http://localhost/api/metrics/profile/freshness
   ```

## 📋 Action Plan (Priority Order)

### Phase 1: Fix Data Quality (Next Steps)

1. **Update `stg_gmail__messages.sql`** to parse `payload_header`
   - Join with `payload_header` table
   - Extract `From`, `To`, `Subject` headers
   - Update tests in `schema.yml`

2. **Update `mart_categories_30d.sql`** to parse labels
   - Join with `message_label` and `label` tables
   - Map Gmail category labels to our categories

3. **Rebuild marts:**
   ```bash
   cd analytics/dbt
   dbt run --target prod --vars 'raw_dataset: gmail'
   dbt test --target prod --vars 'raw_dataset: gmail'
   ```

4. **Verify data quality:**
   ```sql
   -- Should see non-zero unique_senders
   SELECT day, messages_count, unique_senders
   FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_marts.mart_email_activity_daily`
   ORDER BY day DESC
   LIMIT 7;
   
   -- Should see top senders
   SELECT * 
   FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_marts.mart_top_senders_30d`
   LIMIT 10;
   ```

### Phase 2: Enable API Integration

5. **Enable warehouse metrics:**
   ```bash
   # In infra/.env.prod
   USE_WAREHOUSE_METRICS=1
   ```

6. **Restart API:**
   ```bash
   docker compose -f docker-compose.prod.yml --env-file infra/.env.prod restart api
   ```

7. **Smoke test endpoints:**
   ```bash
   curl -sS http://localhost/api/metrics/profile/activity_daily | jq '.rows | length'
   # Expected: 90 (90 days of data)
   
   curl -sS http://localhost/api/metrics/profile/top_senders_30d?limit=5 | jq '.rows[].sender_email'
   # Expected: List of email addresses
   ```

### Phase 3: Automation & Monitoring

8. **Update GitHub Actions secrets:**
   ```bash
   gh secret set GCP_PROJECT --body "applylens-gmail-1759983601"
   gh secret set GCP_SA_JSON --body "$(cat secrets/applylens-warehouse-key.json)"
   gh secret set RAW_DATASET --body "gmail"
   ```

9. **Update `.github/workflows/dbt.yml`:**
   ```yaml
   - name: Run dbt models
     run: |
       dbt run --target prod --vars 'raw_dataset: gmail'
       dbt test --target prod --vars 'raw_dataset: gmail'
   ```

10. **Run validation script:**
    ```bash
    cd analytics/ops
    python validate_es_vs_bq.py
    # Should pass (delta < 2%)
    ```

11. **Set up Grafana dashboard:**
    - Import warehouse monitoring panels
    - Add freshness alerts (SLO: <30 min)
    - Add data drift alerts (threshold: 2%)

## 📊 Current Metrics

**BigQuery Storage:**
- `gmail` dataset: ~38 KB processed (3,000+ messages)
- `gmail_raw_stg_gmail_marts`: 3 tables
  - `mart_email_activity_daily`: 90 rows
  - `mart_top_senders_30d`: 0 rows (no sender data)
  - `mart_categories_30d`: 1 row

**Estimated Costs:**
- Query processing: ~$5/month (nightly dbt + API queries)
- Storage: <$1/month (minimal data)
- **Total: ~$6/month** (well under $30 budget)

## 🔗 References

- **GCP Console:** https://console.cloud.google.com/bigquery?project=applylens-gmail-1759983601
- **Fivetran Dashboard:** https://fivetran.com/dashboard/connectors
- **dbt Docs:** `analytics/dbt/README.md`
- **API Endpoints:** `services/api/app/routers/metrics_profile.py`
- **Quick Commands:** `docs/QUICK-COMMANDS-WAREHOUSE.md`

---

**Last Updated:** October 16, 2025  
**Status:** Ready for Phase 1 (Parse Headers)
