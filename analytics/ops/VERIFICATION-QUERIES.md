# Warehouse Verification Queries
# Quick health checks for Fivetran → BigQuery → dbt pipeline

## 1. Counts Present

### Raw data from Fivetran
```sql
-- Messages in Fivetran raw dataset
SELECT COUNT(*) as message_count
FROM `applylens-gmail-1759983601.gmail.message`
WHERE _fivetran_deleted = false;

-- Threads
SELECT COUNT(*) as thread_count
FROM `applylens-gmail-1759983601.gmail.thread`
WHERE _fivetran_deleted = false;

-- Labels
SELECT COUNT(*) as label_count
FROM `applylens-gmail-1759983601.gmail.label`
WHERE _fivetran_deleted = false;
```

### Mart tables (dbt output)
```sql
-- Daily activity mart
SELECT COUNT(*) as days_count, MIN(day) as earliest_day, MAX(day) as latest_day
FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_marts.mart_email_activity_daily`;

-- Top senders
SELECT COUNT(*) as senders_count
FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_marts.mart_top_senders_30d`;

-- Categories
SELECT category, messages_30d, pct_of_total
FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_marts.mart_categories_30d`
ORDER BY messages_30d DESC;
```

## 2. Freshness Checks

### Last loaded message (from staging view)
```sql
SELECT 
  MAX(synced_at) as last_fivetran_sync,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(synced_at), MINUTE) AS minutes_lag,
  CASE 
    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(synced_at), MINUTE) <= 30 THEN '✅ FRESH'
    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(synced_at), MINUTE) <= 60 THEN '⚠️ WARNING'
    ELSE '❌ STALE'
  END as freshness_status
FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_raw_stg.stg_gmail__messages`;
```

### Fivetran connector status (if fivetran_metadata exists)
```sql
-- Check if metadata dataset exists first
SELECT table_name
FROM `applylens-gmail-1759983601.gmail.INFORMATION_SCHEMA.TABLES`
WHERE table_name LIKE '%fivetran%'
LIMIT 10;

-- If metadata exists, check last sync
SELECT 
  connector_name,
  MAX(_fivetran_synced) AS last_sync,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_fivetran_synced), MINUTE) AS minutes_ago
FROM `applylens-gmail-1759983601.fivetran_metadata.connectors`
GROUP BY connector_name
ORDER BY last_sync DESC;
```

## 3. Data Quality Checks

### Email header parsing validation
```sql
-- Check that headers are being parsed (not null)
SELECT 
  COUNT(*) as total_messages,
  COUNT(from_email) as messages_with_from,
  COUNT(subject) as messages_with_subject,
  ROUND(COUNT(from_email) * 100.0 / COUNT(*), 2) as pct_with_from,
  ROUND(COUNT(subject) * 100.0 / COUNT(*), 2) as pct_with_subject
FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_raw_stg.stg_gmail__messages`
WHERE received_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);
-- Expected: >95% have from_email and subject
```

### Category distribution
```sql
-- Check label parsing and categorization
SELECT 
  CASE 
    WHEN label_ids LIKE '%CATEGORY_UPDATES%' THEN 'updates'
    WHEN label_ids LIKE '%CATEGORY_PROMOTIONS%' THEN 'promotions'
    WHEN label_ids LIKE '%CATEGORY_SOCIAL%' THEN 'social'
    WHEN label_ids LIKE '%CATEGORY_FORUMS%' THEN 'forums'
    WHEN label_ids IS NULL THEN 'no_labels'
    ELSE 'other'
  END as category,
  COUNT(*) as count
FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_raw_stg.stg_gmail__messages`
WHERE received_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY 1
ORDER BY count DESC;
```

## 4. Performance & Cost Checks

### Storage usage
```sql
-- Dataset sizes
SELECT 
  table_schema as dataset,
  SUM(size_bytes) / POW(10, 9) as size_gb,
  SUM(row_count) as total_rows
FROM `applylens-gmail-1759983601.gmail.INFORMATION_SCHEMA.TABLE_STORAGE`
WHERE table_schema IN ('gmail', 'gmail_raw_stg_gmail_raw_stg', 'gmail_raw_stg_gmail_marts')
GROUP BY 1
ORDER BY size_gb DESC;
```

### Most expensive queries (last 24h)
```sql
SELECT 
  user_email,
  query,
  total_bytes_processed / POW(10, 9) as gb_processed,
  total_slot_ms / 1000 as slot_seconds,
  TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) as duration_ms
FROM `applylens-gmail-1759983601.region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND job_type = 'QUERY'
  AND statement_type = 'SELECT'
ORDER BY total_bytes_processed DESC
LIMIT 10;
```

## 5. Drift Detection (ES vs BQ)

### Compare last 7 days
```sql
-- BigQuery count (from mart)
SELECT 
  'BigQuery' as source,
  SUM(messages_count) as total_messages,
  MIN(day) as start_date,
  MAX(day) as end_date
FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_marts.mart_email_activity_daily`
WHERE day >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY);

-- Compare with Elasticsearch (run separately)
-- GET /gmail_emails/_count
-- {
--   "query": {
--     "range": {
--       "received_at": {
--         "gte": "now-7d/d"
--       }
--     }
--   }
-- }
```

## 6. Quick Smoke Tests

### Sample recent emails
```sql
-- Recent emails with all fields populated
SELECT 
  message_id,
  received_ts,
  from_email,
  subject,
  SUBSTR(snippet, 1, 50) as snippet_preview,
  size_bytes,
  synced_at
FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_raw_stg.stg_gmail__messages`
WHERE received_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
ORDER BY received_ts DESC
LIMIT 5;
```

### Top senders this week
```sql
SELECT 
  from_email,
  COUNT(*) as messages,
  ROUND(SUM(size_bytes) / 1024 / 1024, 2) as total_mb
FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_raw_stg.stg_gmail__messages`
WHERE received_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND from_email IS NOT NULL
GROUP BY 1
ORDER BY messages DESC
LIMIT 10;
```

---

## Quick Copy-Paste Commands

### PowerShell (Windows)
```powershell
# Test all queries
cd D:\ApplyLens\analytics\ops

# Count check
bq query --nouse_legacy_sql "SELECT COUNT(*) FROM \`applylens-gmail-1759983601.gmail.message\` WHERE _fivetran_deleted = false"

# Freshness check
bq query --nouse_legacy_sql "SELECT MAX(synced_at) as last_sync, TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(synced_at), MINUTE) AS lag_min FROM \`applylens-gmail-1759983601.gmail_raw_stg_gmail_raw_stg.stg_gmail__messages\`"

# Category distribution
bq query --nouse_legacy_sql "SELECT * FROM \`applylens-gmail-1759983601.gmail_raw_stg_gmail_marts.mart_categories_30d\` ORDER BY messages_30d DESC"
```

### API Health Checks
```powershell
# Activity daily
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/activity_daily?days=7' | ConvertTo-Json -Depth 3

# Freshness
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/freshness' | ConvertTo-Json

# All endpoints smoke test
@('activity_daily?days=7', 'top_senders_30d?limit=5', 'categories_30d', 'freshness') | ForEach-Object {
    Write-Host "`nTesting: $_" -ForegroundColor Cyan
    try {
        $result = Invoke-RestMethod "http://localhost:8003/api/metrics/profile/$_"
        Write-Host "✓ Success: $(($result | ConvertTo-Json -Compress).Length) bytes" -ForegroundColor Green
    } catch {
        Write-Host "✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}
```
