#!/usr/bin/env pwsh
# BigQuery Warehouse Health Check Script (PowerShell)
# Usage: .\analytics\bq\health.ps1
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - GCP_PROJECT environment variable set (or use default)
#   - Service account has BigQuery Data Viewer role

param(
    [string]$Project = $env:GCP_PROJECT ?? "applylens-app"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BigQuery Warehouse Health Check" -ForegroundColor Cyan
Write-Host "Project: $Project" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Function to run a query and display results
function Invoke-BQHealthQuery {
    param(
        [string]$Name,
        [string]$Query
    )
    
    Write-Host "[$Name]" -ForegroundColor Yellow
    
    # Replace template variable with actual project
    $Query = $Query -replace '\{\{ project \}\}', $Project
    
    # Run query using bq CLI
    $result = bq query --use_legacy_sql=false --format=pretty --max_rows=20 $Query 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host $result
        Write-Host ""
    } else {
        Write-Host "ERROR: Query failed" -ForegroundColor Red
        Write-Host $result -ForegroundColor Red
        Write-Host ""
    }
}

# Query 1: Messages in last 24 hours
$q1 = @"
SELECT
  COUNT(*) AS messages_last_24h,
  MAX(_fivetran_synced) AS last_sync_timestamp
FROM ``$Project.gmail_raw.message``
WHERE _fivetran_synced >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND _fivetran_deleted = FALSE
"@

Invoke-BQHealthQuery -Name "Messages synced in last 24h" -Query $q1

# Query 2: Top senders 30d
$q2 = @"
SELECT
  h.value AS from_email,
  COUNT(DISTINCT m.id) AS email_count
FROM ``$Project.gmail_raw.message`` AS m
INNER JOIN ``$Project.gmail_raw.payload_header`` AS h
  ON m.id = h.message_id
WHERE m.internal_date >= UNIX_MILLIS(TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY))
  AND h.name = 'From'
  AND m._fivetran_deleted = FALSE
GROUP BY h.value
ORDER BY email_count DESC
LIMIT 10
"@

Invoke-BQHealthQuery -Name "Top senders (30 days)" -Query $q2

# Query 3: Data freshness
$q3 = @"
SELECT
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_fivetran_synced), HOUR) AS hours_since_last_sync,
  MAX(_fivetran_synced) AS last_sync_timestamp,
  COUNT(*) AS total_messages
FROM ``$Project.gmail_raw.message``
WHERE _fivetran_deleted = FALSE
"@

Invoke-BQHealthQuery -Name "Data freshness check" -Query $q3

Write-Host "========================================" -ForegroundColor Green
Write-Host "Health check complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Expected results:" -ForegroundColor White
Write-Host "  • messages_last_24h > 0 (if receiving emails)" -ForegroundColor White
Write-Host "  • hours_since_last_sync < 6 (Fivetran sync every 6h)" -ForegroundColor White
Write-Host "  • Top senders should include recruiting/job sites" -ForegroundColor White
