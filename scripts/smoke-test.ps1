#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Comprehensive E2E smoke test for ApplyLens full stack

.DESCRIPTION
    Tests the complete system:
    1. Frontend accessibility
    2. API health (docs, metrics)
    3. Actions API flow (propose → tray → approve)
    4. Phase 4 endpoints (policies, always)
    5. Prometheus metrics validation

.EXAMPLE
    .\smoke-test.ps1
#>

$ErrorActionPreference = "Stop"
$ProgressPreference = 'SilentlyContinue'  # Speed up Invoke-WebRequest

Write-Host "`n╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                      ║" -ForegroundColor Cyan
Write-Host "║      🧪 ApplyLens E2E Smoke Test                    ║" -ForegroundColor Cyan
Write-Host "║                                                      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$TestsPassed = 0
$TestsFailed = 0
$TestsWarning = 0

# Test 1: Frontend ping
Write-Host "[1/6] Frontend accessibility..." -ForegroundColor Yellow
try {
    $fe = Invoke-WebRequest http://localhost:5175 -UseBasicParsing -TimeoutSec 5
    if ($fe.StatusCode -eq 200) {
        Write-Host "  ✅ Frontend: HTTP $($fe.StatusCode) ($($fe.Content.Length) bytes)" -ForegroundColor Green
        $TestsPassed++
    } else {
        Write-Host "  ⚠️ Frontend: HTTP $($fe.StatusCode)" -ForegroundColor Yellow
        $TestsWarning++
    }
} catch {
    Write-Host "  ❌ Frontend: Failed - $($_.Exception.Message)" -ForegroundColor Red
    $TestsFailed++
}

# Test 2: API docs
Write-Host ""
Write-Host "[2/6] API documentation..." -ForegroundColor Yellow
try {
    $docs = Invoke-WebRequest http://localhost:8003/docs -UseBasicParsing -TimeoutSec 5
    if ($docs.StatusCode -eq 200) {
        Write-Host "  ✅ API Docs: HTTP $($docs.StatusCode)" -ForegroundColor Green
        $TestsPassed++
    } else {
        Write-Host "  ⚠️ API Docs: HTTP $($docs.StatusCode)" -ForegroundColor Yellow
        $TestsWarning++
    }
} catch {
    Write-Host "  ❌ API Docs: Failed - $($_.Exception.Message)" -ForegroundColor Red
    $TestsFailed++
}

# Test 3: Prometheus metrics
Write-Host ""
Write-Host "[3/6] Prometheus metrics..." -ForegroundColor Yellow
try {
    $metrics = Invoke-WebRequest http://localhost:8003/metrics -UseBasicParsing -TimeoutSec 5
    if ($metrics.StatusCode -eq 200) {
        # Check for Phase 4 metrics
        $content = $metrics.Content
        $hasProposed = $content -match "actions_proposed_total"
        $hasExecuted = $content -match "actions_executed_total"
        $hasFailed = $content -match "actions_failed_total"
        
        if ($hasProposed -and $hasExecuted -and $hasFailed) {
            Write-Host "  ✅ Metrics: HTTP $($metrics.StatusCode) (Phase 4 metrics present)" -ForegroundColor Green
            $TestsPassed++
        } else {
            Write-Host "  ⚠️ Metrics: HTTP $($metrics.StatusCode) (some metrics missing)" -ForegroundColor Yellow
            $TestsWarning++
        }
    }
} catch {
    Write-Host "  ❌ Metrics: Failed - $($_.Exception.Message)" -ForegroundColor Red
    $TestsFailed++
}

# Test 4: Actions API flow
Write-Host ""
Write-Host "[4/6] Actions API flow (propose → tray)..." -ForegroundColor Yellow
try {
    # Propose actions
    $proposeBody = @{ email_ids = @(1,2,3,4,5) } | ConvertTo-Json
    $propose = Invoke-RestMethod -Uri http://localhost:8003/api/actions/propose -Method POST -Body $proposeBody -ContentType application/json -TimeoutSec 10
    
    # Fetch tray
    $tray = Invoke-RestMethod http://localhost:8003/api/actions/tray -TimeoutSec 10
    
    Write-Host "  ✅ Propose: Created $($propose.Count) action(s)" -ForegroundColor Green
    Write-Host "  ✅ Tray: $($tray.Count) pending action(s)" -ForegroundColor Green
    $TestsPassed += 2
    
    # Try to approve if we have actions
    if ($tray.Count -gt 0) {
        $id = $tray[0].id
        $approve = Invoke-RestMethod -Uri "http://localhost:8003/api/actions/$id/approve" -Method POST -Body '{}' -ContentType application/json -TimeoutSec 10
        if ($approve.ok) {
            Write-Host "  ✅ Approve: Action $id approved successfully" -ForegroundColor Green
            $TestsPassed++
        } else {
            Write-Host "  ⚠️ Approve: Action $id failed - $($approve.error)" -ForegroundColor Yellow
            $TestsWarning++
        }
    } else {
        Write-Host "  ℹ️ No pending actions (expected for empty dev data)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ❌ Actions flow: Failed - $($_.Exception.Message)" -ForegroundColor Red
    $TestsFailed++
}

# Test 5: Policies endpoint
Write-Host ""
Write-Host "[5/6] Phase 4 policies..." -ForegroundColor Yellow
try {
    $policies = Invoke-RestMethod http://localhost:8003/api/actions/policies -TimeoutSec 10
    if ($policies.Count -gt 0) {
        Write-Host "  ✅ Policies: $($policies.Count) configured" -ForegroundColor Green
        
        # Show policy names
        $policyNames = $policies | Select-Object -First 3 | ForEach-Object { "    - $($_.name)" }
        $policyNames | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
        if ($policies.Count -gt 3) {
            Write-Host "    ... and $($policies.Count - 3) more" -ForegroundColor Gray
        }
        
        $TestsPassed++
    } else {
        Write-Host "  ⚠️ Policies: No policies found" -ForegroundColor Yellow
        $TestsWarning++
    }
} catch {
    Write-Host "  ❌ Policies: Failed - $($_.Exception.Message)" -ForegroundColor Red
    $TestsFailed++
}

# Test 6: Phase 4 "Always" endpoint verification
Write-Host ""
Write-Host "[6/6] Phase 4 'Always' endpoint..." -ForegroundColor Yellow
try {
    $openapi = Invoke-RestMethod http://localhost:8003/openapi.json -TimeoutSec 10
    $hasAlwaysEndpoint = $openapi.paths.PSObject.Properties.Name -contains "/api/actions/{action_id}/always"
    
    if ($hasAlwaysEndpoint) {
        Write-Host "  ✅ 'Always' endpoint registered in OpenAPI" -ForegroundColor Green
        $TestsPassed++
    } else {
        Write-Host "  ❌ 'Always' endpoint NOT found in OpenAPI" -ForegroundColor Red
        $TestsFailed++
    }
} catch {
    Write-Host "  ❌ OpenAPI check: Failed - $($_.Exception.Message)" -ForegroundColor Red
    $TestsFailed++
}

# Summary
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                 Test Summary                         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ✅ Passed:  $TestsPassed" -ForegroundColor Green
if ($TestsWarning -gt 0) {
    Write-Host "  ⚠️ Warnings: $TestsWarning" -ForegroundColor Yellow
}
if ($TestsFailed -gt 0) {
    Write-Host "  ❌ Failed:  $TestsFailed" -ForegroundColor Red
}
Write-Host ""

if ($TestsFailed -eq 0) {
    Write-Host "🎉 All critical tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  • Open UI: http://localhost:5175" -ForegroundColor Gray
    Write-Host "  • View metrics: http://localhost:8003/metrics" -ForegroundColor Gray
    Write-Host "  • API docs: http://localhost:8003/docs" -ForegroundColor Gray
    Write-Host ""
    exit 0
} else {
    Write-Host "❌ Some tests failed. Check the output above." -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  • Check Docker: cd d:/ApplyLens/infra && docker compose ps" -ForegroundColor Gray
    Write-Host "  • Check logs: docker compose logs api" -ForegroundColor Gray
    Write-Host "  • Restart services: docker compose restart" -ForegroundColor Gray
    Write-Host ""
    exit 1
}
