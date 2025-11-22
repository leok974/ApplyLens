# Cloudflare Cache Purge & Verification Script
# Run this after purging cache in Cloudflare dashboard

Write-Host "=== ApplyLens Production Health Check ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check containers
Write-Host "1. Checking Docker container status..." -ForegroundColor Yellow
$containers = docker ps --format "{{.Names}} {{.Status}}" | Select-String "applylens-(nginx|web|api|cloudflared)-prod"
$containers | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
Write-Host ""

# Test 2: Test public endpoints (10 times to catch intermittent issues)
Write-Host "2. Testing public endpoints (10 requests)..." -ForegroundColor Yellow
$successCount = 0
$failCount = 0
$results = @()

for ($i = 1; $i -le 10; $i++) {
    $response = curl.exe -s -o $null -w "%{http_code}" https://applylens.app/health 2>&1

    if ($response -match "200|ok") {
        $successCount++
        Write-Host "  Test $i : ✓ $response" -ForegroundColor Green
    } else {
        $failCount++
        Write-Host "  Test $i : ✗ $response" -ForegroundColor Red
    }

    Start-Sleep -Milliseconds 300
}

Write-Host ""
Write-Host "Results: $successCount/10 successful, $failCount/10 failed" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Yellow" })
Write-Host ""

# Test 3: Check nginx logs for errors
Write-Host "3. Checking nginx logs for errors..." -ForegroundColor Yellow
$nginxErrors = docker logs applylens-nginx-prod --tail 100 2>&1 | Select-String -Pattern "502|504|error" -CaseSensitive:$false
if ($nginxErrors) {
    Write-Host "  Found errors in nginx logs:" -ForegroundColor Red
    $nginxErrors | Select-Object -First 5 | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
} else {
    Write-Host "  ✓ No errors in nginx logs" -ForegroundColor Green
}
Write-Host ""

# Test 4: Check cloudflared tunnel connections
Write-Host "4. Checking cloudflared tunnel status..." -ForegroundColor Yellow
$tunnelStatus = docker logs applylens-cloudflared-prod --tail 50 2>&1 | Select-String "Registered tunnel connection|error"
$connections = ($tunnelStatus | Select-String "Registered tunnel connection").Count
$errors = ($tunnelStatus | Select-String "error" -CaseSensitive:$false).Count

Write-Host "  Tunnel connections: $connections/4" -ForegroundColor $(if ($connections -eq 4) { "Green" } else { "Yellow" })
if ($errors -gt 0) {
    Write-Host "  Recent errors: $errors" -ForegroundColor Yellow
    $tunnelStatus | Select-String "error" -CaseSensitive:$false | Select-Object -First 3 | ForEach-Object {
        Write-Host "    $_" -ForegroundColor Yellow
    }
}
Write-Host ""

# Summary
Write-Host "=== Summary ===" -ForegroundColor Cyan
if ($failCount -eq 0 -and $connections -eq 4 -and !$nginxErrors) {
    Write-Host "✓ All systems operational!" -ForegroundColor Green
    Write-Host "  - Docker containers: Healthy" -ForegroundColor Green
    Write-Host "  - Public endpoints: 100% success rate" -ForegroundColor Green
    Write-Host "  - Nginx: No errors" -ForegroundColor Green
    Write-Host "  - Cloudflare tunnel: 4/4 connections" -ForegroundColor Green
} elseif ($failCount -gt 0) {
    Write-Host "⚠ Intermittent failures detected!" -ForegroundColor Yellow
    Write-Host "  Action required: Purge Cloudflare cache" -ForegroundColor Yellow
    Write-Host "  Dashboard: https://dash.cloudflare.com/" -ForegroundColor Cyan
    Write-Host "  Navigate to: applylens.app → Caching → Purge Everything" -ForegroundColor Cyan
} else {
    Write-Host "⚠ Some issues detected - check logs above" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "For detailed troubleshooting, see: docs/CLOUDFLARE_502_FIX.md" -ForegroundColor Cyan
