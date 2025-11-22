# Test Backfill Dual-Path Support and Metrics
# Usage: .\scripts\test-backfill.ps1

$base = "http://localhost:8003"

Write-Host "`n=== Backfill Endpoint Tests ===" -ForegroundColor Green

# 1. Check routes in OpenAPI
Write-Host "`n1. Available Backfill Routes:" -ForegroundColor Cyan
$openapi = curl -s "$base/openapi.json" | ConvertFrom-Json
$paths = $openapi.paths.PSObject.Properties.Name | Where-Object { $_ -like "*backfill*" }
$paths | Sort-Object | ForEach-Object {
    Write-Host "   $_" -ForegroundColor White
}

# 2. Test production path (/gmail/backfill/start)
Write-Host "`n2. Production Path Test:" -ForegroundColor Cyan
Write-Host "   POST /gmail/backfill/start?days=3" -ForegroundColor Yellow
try {
    $response1 = curl -s -i -X POST "$base/gmail/backfill/start?days=3" `
        -H "Content-Type: application/json" 2>&1

    $statusLine = ($response1 | Select-String "HTTP/").ToString()
    Write-Host "   $statusLine" -ForegroundColor $(if ($statusLine -match "202|200") { "Green" } else { "Red" })

    # Check for rate limit headers
    $rateLimitHeader = $response1 | Select-String "X-RateLimit-Limit:"
    if ($rateLimitHeader) {
        Write-Host "   $($rateLimitHeader.ToString().Trim())" -ForegroundColor Gray
    }
} catch {
    Write-Host "   Error: $_" -ForegroundColor Red
}

# 3. Test API path (/api/gmail/backfill/start)
Write-Host "`n3. API Path Test:" -ForegroundColor Cyan
Write-Host "   POST /api/gmail/backfill/start?days=3" -ForegroundColor Yellow
try {
    $response2 = curl -s -i -X POST "$base/api/gmail/backfill/start?days=3" `
        -H "Content-Type: application/json" 2>&1

    $statusLine = ($response2 | Select-String "HTTP/").ToString()
    Write-Host "   $statusLine" -ForegroundColor $(if ($statusLine -match "202|200") { "Green" } else { "Red" })

    # Check for rate limit headers
    $rateLimitHeader = $response2 | Select-String "X-RateLimit-Limit:"
    if ($rateLimitHeader) {
        Write-Host "   $($rateLimitHeader.ToString().Trim())" -ForegroundColor Gray
    }
} catch {
    Write-Host "   Error: $_" -ForegroundColor Red
}

# 4. Check metrics
Write-Host "`n4. Backfill Metrics:" -ForegroundColor Cyan
$metrics = curl -s "$base/metrics" | Select-String "backfill"
if ($metrics) {
    Write-Host "   Found $(($metrics | Measure-Object).Count) backfill metrics:" -ForegroundColor Green
    $metrics | Select-Object -First 10 | ForEach-Object {
        $line = $_.Line.Trim()
        if ($line -match "^# ") {
            Write-Host "   $line" -ForegroundColor Gray
        } else {
            Write-Host "   $line" -ForegroundColor White
        }
    }
} else {
    Write-Host "   No backfill metrics found (server may need restart)" -ForegroundColor Yellow
}

# 5. Test status endpoint
Write-Host "`n5. Status Endpoint Test:" -ForegroundColor Cyan
Write-Host "   GET /gmail/backfill/status?job_id=test-123" -ForegroundColor Yellow
try {
    $status = curl -s "$base/gmail/backfill/status?job_id=test-123" | ConvertFrom-Json
    Write-Host "   Status: $($status.status)" -ForegroundColor Green
    Write-Host "   State: $($status.state)" -ForegroundColor Green
} catch {
    Write-Host "   Error: $_" -ForegroundColor Red
}

Write-Host "`n✅ Backfill tests complete!`n" -ForegroundColor Green

# Summary
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "• Both /gmail/backfill/* and /api/gmail/backfill/* paths should work" -ForegroundColor White
Write-Host "• Rate-limit headers (X-RateLimit-Limit) should be present" -ForegroundColor White
Write-Host "• Metrics should track runs and emails synced" -ForegroundColor White
Write-Host "• Requires ALLOW_DEV_ROUTES=1 environment variable`n" -ForegroundColor Yellow
