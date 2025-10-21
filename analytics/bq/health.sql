-- BigQuery Warehouse Health Check Queries
-- Run these to verify Fivetran → BigQuery sync is working
-- Usage: bq query --use_legacy_sql=false < health.sql

-- Query 1: Messages synced in last 24 hours
-- Expected: > 0 if daily emails are being received
SELECT
  COUNT(*) AS messages_last_24h,
  MAX(_fivetran_synced) AS last_sync_timestamp
FROM `{{ project }}.gmail_raw.message`
WHERE _fivetran_synced >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND _fivetran_deleted = FALSE;

-- Query 2: Top senders in last 30 days
-- Expected: List of frequent senders (recruiting, newsletters, etc.)
SELECT
  h.value AS from_email,
  COUNT(DISTINCT m.id) AS email_count
FROM `{{ project }}.gmail_raw.message` AS m
INNER JOIN `{{ project }}.gmail_raw.payload_header` AS h
  ON m.id = h.message_id
WHERE m.internal_date >= UNIX_MILLIS(TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY))
  AND h.name = 'From'
  AND m._fivetran_deleted = FALSE
GROUP BY h.value
ORDER BY email_count DESC
LIMIT 10;

-- Query 3: Email categories/labels in last 30 days
-- Expected: Distribution of Gmail labels (if labels are being synced)
SELECT
  l.name AS category,
  COUNT(DISTINCT ml.message_id) AS email_count
FROM `{{ project }}.gmail_raw.message_label` AS ml
INNER JOIN `{{ project }}.gmail_raw.label` AS l
  ON ml.label_id = l.id
INNER JOIN `{{ project }}.gmail_raw.message` AS m
  ON ml.message_id = m.id
WHERE m.internal_date >= UNIX_MILLIS(TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY))
  AND m._fivetran_deleted = FALSE
GROUP BY l.name
ORDER BY email_count DESC
LIMIT 10;

-- Query 4: Data freshness check
-- Expected: _fivetran_synced should be within last few hours
SELECT
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_fivetran_synced), HOUR) AS hours_since_last_sync,
  MAX(_fivetran_synced) AS last_sync_timestamp,
  COUNT(*) AS total_messages
FROM `{{ project }}.gmail_raw.message`
WHERE _fivetran_deleted = FALSE;
