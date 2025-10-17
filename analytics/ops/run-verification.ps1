# Comprehensive Warehouse Verification Script
# Usage: .\run-verification.ps1

param(
    [string]$RawDataset = "gmail"
)

$ErrorActionPreference = "Continue"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  WAREHOUSE VERIFICATION" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  RAW_DATASET: $RawDataset"
Write-Host "  GCP_PROJECT: applylens-gmail-1759983601`n"

$passed = 0
$failed = 0
$warnings = 0

# 1. API Health Checks
Write-Host "1. API HEALTH CHECKS" -ForegroundColor Cyan
Write-Host "-------------------" -ForegroundColor Cyan

try {
    $freshness = Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/freshness' -ErrorAction Stop
    if ($freshness.is_fresh) {
        Write-Host "  ✅ Freshness: $($freshness.minutes_since_sync) min (Fresh)" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "  ⚠️ Freshness: $($freshness.minutes_since_sync) min (Stale)" -ForegroundColor Yellow
        $warnings++
    }
} catch {
    Write-Host "  ❌ Freshness endpoint failed: $_" -ForegroundColor Red
    $failed++
}

try {
    $activity = Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/activity_daily?days=7' -ErrorAction Stop
    Write-Host "  ✅ Activity: $($activity.count) days returned" -ForegroundColor Green
    $passed++
} catch {
    Write-Host "  ❌ Activity endpoint failed: $_" -ForegroundColor Red
    $failed++
}

try {
    $senders = Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/top_senders_30d?limit=5' -ErrorAction Stop
    Write-Host "  ✅ Top Senders: $($senders.count) senders returned" -ForegroundColor Green
    $passed++
} catch {
    Write-Host "  ❌ Top Senders endpoint failed: $_" -ForegroundColor Red
    $failed++
}

try {
    $categories = Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/categories_30d' -ErrorAction Stop
    Write-Host "  ✅ Categories: $($categories.count) categories returned" -ForegroundColor Green
    $passed++
} catch {
    Write-Host "  ❌ Categories endpoint failed: $_" -ForegroundColor Red
    $failed++
}

# 2. BigQuery Data Quality
Write-Host "`n2. BIGQUERY DATA QUALITY" -ForegroundColor Cyan
Write-Host "------------------------" -ForegroundColor Cyan

# Check if bq CLI is available
if (Get-Command bq -ErrorAction SilentlyContinue) {
    Write-Host "  Running BigQuery checks..." -ForegroundColor Gray
    
    # Raw message count
    $rawQuery = "SELECT COUNT(*) as count FROM \`applylens-gmail-1759983601.$RawDataset.message\` WHERE _fivetran_deleted = false"
    try {
        $result = bq query --nouse_legacy_sql --format=json $rawQuery 2>$null | ConvertFrom-Json
        if ($result.count -gt 0) {
            Write-Host "  ✅ Raw messages: $($result.count)" -ForegroundColor Green
            $passed++
        } else {
            Write-Host "  ⚠️ Raw messages: 0 (check Fivetran sync)" -ForegroundColor Yellow
            $warnings++
        }
    } catch {
        Write-Host "  ⚠️ BigQuery check skipped (authentication or timeout)" -ForegroundColor Yellow
        $warnings++
    }
} else {
    Write-Host "  ⚠️ bq CLI not found, skipping BigQuery checks" -ForegroundColor Yellow
    $warnings++
}

# 3. GitHub Actions Status
Write-Host "`n3. GITHUB ACTIONS STATUS" -ForegroundColor Cyan
Write-Host "------------------------" -ForegroundColor Cyan

try {
    $runs = gh run list --workflow "Warehouse Nightly" --limit 1 --json status,conclusion,createdAt | ConvertFrom-Json
    if ($runs.Count -gt 0) {
        $latestRun = $runs[0]
        if ($latestRun.conclusion -eq "success") {
            Write-Host "  ✅ Latest run: Success" -ForegroundColor Green
            $passed++
        } elseif ($latestRun.conclusion -eq "failure") {
            Write-Host "  ❌ Latest run: Failed" -ForegroundColor Red
            $failed++
        } else {
            Write-Host "  ⏳ Latest run: $($latestRun.status)" -ForegroundColor Yellow
        }
        Write-Host "     Created: $($latestRun.createdAt)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ⚠️ GitHub CLI not available or not authenticated" -ForegroundColor Yellow
    $warnings++
}

# 4. Docker Services
Write-Host "`n4. DOCKER SERVICES" -ForegroundColor Cyan
Write-Host "------------------" -ForegroundColor Cyan

$services = @("applylens-api-prod", "applylens-elasticsearch-prod", "applylens-redis-prod")
foreach ($service in $services) {
    try {
        $status = docker ps --filter "name=$service" --format "{{.Status}}" 2>$null
        if ($status -match "Up") {
            Write-Host "  ✅ $service`: Running" -ForegroundColor Green
            $passed++
        } else {
            Write-Host "  ❌ $service`: Not running" -ForegroundColor Red
            $failed++
        }
    } catch {
        Write-Host "  ⚠️ Docker check failed for $service" -ForegroundColor Yellow
        $warnings++
    }
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "  ✅ Passed:   $passed" -ForegroundColor Green
Write-Host "  ❌ Failed:   $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Gray" })
Write-Host "  ⚠️  Warnings: $warnings" -ForegroundColor $(if ($warnings -gt 0) { "Yellow" } else { "Gray" })

$total = $passed + $failed + $warnings
$successRate = if ($total -gt 0) { [math]::Round(($passed / $total) * 100, 1) } else { 0 }

Write-Host "`n  Success Rate: $successRate%" -ForegroundColor $(if ($successRate -ge 80) { "Green" } elseif ($successRate -ge 50) { "Yellow" } else { "Red" })

if ($failed -eq 0) {
    Write-Host "`n  🎉 All critical checks passed!" -ForegroundColor Green
} elseif ($failed -le 2) {
    Write-Host "`n  ⚠️ Some checks failed - review above" -ForegroundColor Yellow
} else {
    Write-Host "`n  ❌ Multiple failures detected - action required" -ForegroundColor Red
}

Write-Host "========================================`n" -ForegroundColor Cyan

# Exit with appropriate code
if ($failed -gt 0) {
    exit 1
} else {
    exit 0
}
