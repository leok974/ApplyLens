#!/usr/bin/env bash
# BigQuery Warehouse Health Check Script (Bash)
# Usage: ./analytics/bq/health.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - GCP_PROJECT environment variable set (or use default)
#   - Service account has BigQuery Data Viewer role

set -e

PROJECT="${GCP_PROJECT:-applylens-app}"

echo "========================================"
echo "BigQuery Warehouse Health Check"
echo "Project: $PROJECT"
echo "========================================"
echo ""

# Function to run a query and display results
run_health_query() {
    local name="$1"
    local query="$2"
    
    echo "[$name]"
    
    # Replace template variable with actual project
    query="${query//\{\{ project \}\}/$PROJECT}"
    
    # Run query using bq CLI
    if bq query --use_legacy_sql=false --format=pretty --max_rows=20 "$query"; then
        echo ""
    else
        echo "ERROR: Query failed" >&2
        echo ""
    fi
}

# Query 1: Messages in last 24 hours
q1="SELECT
  COUNT(*) AS messages_last_24h,
  MAX(_fivetran_synced) AS last_sync_timestamp
FROM \`$PROJECT.gmail_raw.message\`
WHERE _fivetran_synced >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND _fivetran_deleted = FALSE"

run_health_query "Messages synced in last 24h" "$q1"

# Query 2: Top senders 30d
q2="SELECT
  h.value AS from_email,
  COUNT(DISTINCT m.id) AS email_count
FROM \`$PROJECT.gmail_raw.message\` AS m
INNER JOIN \`$PROJECT.gmail_raw.payload_header\` AS h
  ON m.id = h.message_id
WHERE m.internal_date >= UNIX_MILLIS(TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY))
  AND h.name = 'From'
  AND m._fivetran_deleted = FALSE
GROUP BY h.value
ORDER BY email_count DESC
LIMIT 10"

run_health_query "Top senders (30 days)" "$q2"

# Query 3: Data freshness
q3="SELECT
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_fivetran_synced), HOUR) AS hours_since_last_sync,
  MAX(_fivetran_synced) AS last_sync_timestamp,
  COUNT(*) AS total_messages
FROM \`$PROJECT.gmail_raw.message\`
WHERE _fivetran_deleted = FALSE"

run_health_query "Data freshness check" "$q3"

echo "========================================"
echo "Health check complete!"
echo "========================================"
echo ""
echo "Expected results:"
echo "  • messages_last_24h > 0 (if receiving emails)"
echo "  • hours_since_last_sync < 6 (Fivetran sync every 6h)"
echo "  • Top senders should include recruiting/job sites"
