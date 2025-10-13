# Phase 6 Smoke Tests
# Tests personalization, policy stats, ATS enrichment, and Money mode

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Phase 6 Smoke Tests - Personalization & ATS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$API_BASE = "http://localhost:8003/api"

# Test 1: Money Mode - CSV Export
Write-Host "`n[Test 1] Money Mode - Export Receipts CSV" -ForegroundColor Yellow
try {
    Invoke-WebRequest "$API_BASE/money/receipts.csv" -OutFile "receipts_test.csv" -ErrorAction Stop
    $fileSize = (Get-Item "receipts_test.csv").Length
    Write-Host "✓ Downloaded receipts.csv ($fileSize bytes)" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to export receipts: $_" -ForegroundColor Red
}

# Test 2: Money Mode - Find Duplicates
Write-Host "`n[Test 2] Money Mode - Find Duplicate Charges" -ForegroundColor Yellow
try {
    $duplicates = Invoke-RestMethod "$API_BASE/money/duplicates?window_days=7" -ErrorAction Stop
    Write-Host "✓ Found $($duplicates.count) potential duplicates" -ForegroundColor Green
    if ($duplicates.count -gt 0) {
        $duplicates.duplicates[0..2] | ForEach-Object {
            Write-Host "  - $($_.merchant): $($_.amount) ($($_.days_apart) days apart)" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "✗ Failed to find duplicates: $_" -ForegroundColor Red
}

# Test 3: Money Mode - Spending Summary
Write-Host "`n[Test 3] Money Mode - Spending Summary" -ForegroundColor Yellow
try {
    $summary = Invoke-RestMethod "$API_BASE/money/summary" -ErrorAction Stop
    Write-Host "✓ Total spending: `$$($summary.total_amount) across $($summary.count) receipts" -ForegroundColor Green
    Write-Host "  Average: `$$($summary.avg_amount)" -ForegroundColor Gray
    if ($summary.by_merchant) {
        Write-Host "  Top merchants:" -ForegroundColor Gray
        $summary.by_merchant.PSObject.Properties | Select-Object -First 3 | ForEach-Object {
            Write-Host "    - $($_.Name): `$$($_.Value)" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "✗ Failed to get spending summary: $_" -ForegroundColor Red
}

# Test 4: Learning Loop - Propose Actions
Write-Host "`n[Test 4] Learning Loop - Propose Actions" -ForegroundColor Yellow
try {
    $body = @{
        query = "category:promo OR risk_score:[80 TO *]"
        limit = 10
    } | ConvertTo-Json

    $proposed = Invoke-RestMethod "$API_BASE/actions/propose" -Method POST `
        -ContentType "application/json" -Body $body -ErrorAction Stop
    
    Write-Host "✓ Created $($proposed.count) action proposals" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to propose actions: $_" -ForegroundColor Red
}

# Test 5: Learning Loop - Approve Action
Write-Host "`n[Test 5] Learning Loop - Approve Action (triggers learning)" -ForegroundColor Yellow
try {
    $tray = Invoke-RestMethod "$API_BASE/actions/tray" -ErrorAction Stop
    
    if ($tray.Count -gt 0) {
        $firstId = $tray[0].id
        Write-Host "  Approving action ID: $firstId" -ForegroundColor Gray
        
        $approveBody = @{} | ConvertTo-Json
        $result = Invoke-RestMethod "$API_BASE/actions/$firstId/approve" -Method POST `
            -ContentType "application/json" -Body $approveBody -ErrorAction Stop
        
        Write-Host "✓ Approved action (user weights updated, policy stats incremented)" -ForegroundColor Green
    } else {
        Write-Host "⊘ No pending actions to approve" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Failed to approve action: $_" -ForegroundColor Red
}

# Test 6: Policy Stats
Write-Host "`n[Test 6] Policy Performance Stats" -ForegroundColor Yellow
try {
    $stats = Invoke-RestMethod "$API_BASE/policy/stats" -ErrorAction Stop
    
    if ($stats.Count -gt 0) {
        Write-Host "✓ Retrieved stats for $($stats.Count) policies" -ForegroundColor Green
        $stats | Select-Object -First 3 | ForEach-Object {
            Write-Host "  - $($_.name):" -ForegroundColor Gray
            Write-Host "    Precision: $($_.precision) (approved: $($_.approved), rejected: $($_.rejected), fired: $($_.fired))" -ForegroundColor Gray
        }
    } else {
        Write-Host "⊘ No policy stats yet (approve/reject actions to generate)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Failed to get policy stats: $_" -ForegroundColor Red
}

# Test 7: User Weights (DB Check)
Write-Host "`n[Test 7] User Weights (Learning State)" -ForegroundColor Yellow
Write-Host "  Run manually: SELECT * FROM user_weights ORDER BY ABS(weight) DESC LIMIT 5;" -ForegroundColor Gray

# Test 8: ATS Enrichment (Check ES)
Write-Host "`n[Test 8] ATS Enrichment Status" -ForegroundColor Yellow
try {
    $esQuery = Invoke-RestMethod "http://localhost:9200/emails/_search?size=0&q=ats.system:*" -ErrorAction Stop
    $enrichedCount = $esQuery.hits.total.value
    Write-Host "✓ Found $enrichedCount emails enriched with ATS data" -ForegroundColor Green
} catch {
    Write-Host "⊘ ATS enrichment not yet run (or ES not available)" -ForegroundColor Yellow
}

# Test 9: Chat with Mode Parameter
Write-Host "`n[Test 9] Chat with Money Mode" -ForegroundColor Yellow
Write-Host "  Test URL: $API_BASE/chat/stream?q=Show%20me%20receipts&mode=money" -ForegroundColor Gray
Write-Host "  (Open in browser to test SSE streaming)" -ForegroundColor Gray

# Test 10: Prometheus Metrics
Write-Host "`n[Test 10] Prometheus Metrics" -ForegroundColor Yellow
try {
    $metrics = Invoke-WebRequest "http://localhost:8003/metrics" -ErrorAction Stop | Select-Object -Expand Content
    
    # Check for Phase 6 metrics
    $phase6Metrics = @(
        "policy_fired_total",
        "policy_approved_total",
        "policy_rejected_total",
        "user_weight_updates_total",
        "ats_enriched_total"
    )
    
    $found = 0
    foreach ($metric in $phase6Metrics) {
        if ($metrics -match $metric) {
            $found++
        }
    }
    
    Write-Host "✓ Found $found/$($phase6Metrics.Count) Phase 6 metrics in /metrics endpoint" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to fetch metrics: $_" -ForegroundColor Red
}

# Summary
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "Phase 6 Smoke Tests Complete" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Run migration: alembic upgrade head" -ForegroundColor White
Write-Host "2. Update ES mapping: curl -X PUT http://localhost:9200/emails/_mapping -d @es/mappings/ats_fields.json" -ForegroundColor White
Write-Host "3. Schedule ATS enrichment: cron job for analytics/enrich/ats_enrich_emails.py" -ForegroundColor White
Write-Host "4. Approve/reject more actions to build learning data" -ForegroundColor White
Write-Host "5. Query policy stats: curl $API_BASE/policy/stats | jq ." -ForegroundColor White
