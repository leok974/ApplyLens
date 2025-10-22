#!/usr/bin/env pwsh
# ApplyLens Production Smoke Test
# Tests all critical fixes after OAuth/DB password resolution

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "ApplyLens Production Smoke Test" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "https://applylens.app"
$passed = 0
$failed = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedStatus,
        [string]$Method = "GET"
    )

    Write-Host "Testing: $Name..." -NoNewline
    try {
        $response = Invoke-WebRequest -Uri $Url -Method $Method -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq $ExpectedStatus) {
            Write-Host " ✅ PASS ($($response.StatusCode))" -ForegroundColor Green
            $script:passed++
        } else {
            Write-Host " ❌ FAIL (Expected $ExpectedStatus, got $($response.StatusCode))" -ForegroundColor Red
            $script:failed++
        }
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq $ExpectedStatus) {
            Write-Host " ✅ PASS ($statusCode)" -ForegroundColor Green
            $script:passed++
        } else {
            Write-Host " ❌ FAIL (Expected $ExpectedStatus, got $statusCode)" -ForegroundColor Red
            $script:failed++
        }
    }
}

# Health Checks
Write-Host "`n[Health Checks]" -ForegroundColor Yellow
Test-Endpoint "Liveness" "$baseUrl/live" 200
Test-Endpoint "Readiness" "$baseUrl/ready" 200

# Auth Endpoints
Write-Host "`n[Auth Endpoints]" -ForegroundColor Yellow
Test-Endpoint "Auth Me (Unauthenticated)" "$baseUrl/api/auth/me" 401
Test-Endpoint "OAuth Login Redirect" "$baseUrl/api/auth/google/login" 307

# Internal Container Checks
Write-Host "`n[Internal Container Checks]" -ForegroundColor Yellow
Write-Host "Upstream API Health..." -NoNewline
$apiHealth = docker exec applylens-nginx-prod curl -s -o /dev/null -w "%{http_code}" http://api:8003/live 2>$null
if ($apiHealth -eq "200") {
    Write-Host " ✅ PASS (200)" -ForegroundColor Green
    $passed++
} else {
    Write-Host " ❌ FAIL (Expected 200, got $apiHealth)" -ForegroundColor Red
    $failed++
}

Write-Host "Database Connection..." -NoNewline
$dbTest = docker exec applylens-api-prod python -c "import os; from sqlalchemy import create_engine; engine = create_engine(os.environ['DATABASE_URL']); engine.connect().close(); print('OK')" 2>&1
if ($dbTest -match "OK") {
    Write-Host " ✅ PASS" -ForegroundColor Green
    $passed++
} else {
    Write-Host " ❌ FAIL" -ForegroundColor Red
    Write-Host "Error: $dbTest" -ForegroundColor Red
    $failed++
}

Write-Host "API Port Configuration..." -NoNewline
$apiPort = docker logs applylens-api-prod --tail 50 2>&1 | Select-String "Uvicorn running on" | Select-Object -Last 1
if ($apiPort -match "8003") {
    Write-Host " ✅ PASS (Port 8003)" -ForegroundColor Green
    $passed++
} else {
    Write-Host " ❌ FAIL (Expected port 8003)" -ForegroundColor Red
    Write-Host "Port info: $apiPort" -ForegroundColor Red
    $failed++
}

# Configuration Checks
Write-Host "`n[Configuration Checks]" -ForegroundColor Yellow
Write-Host "DATABASE_URL encoding..." -NoNewline
$dbUrl = docker exec applylens-api-prod printenv DATABASE_URL 2>&1
if ($dbUrl -match "%21") {
    Write-Host " ✅ PASS (Password URL-encoded)" -ForegroundColor Green
    $passed++
} else {
    Write-Host " ❌ FAIL (Password not URL-encoded)" -ForegroundColor Red
    $failed++
}

Write-Host "OAuth Redirect URI..." -NoNewline
$redirectUri = docker exec applylens-api-prod printenv APPLYLENS_OAUTH_REDIRECT_URI 2>&1
if ($redirectUri -match "https://applylens.app/api/auth/google/callback") {
    Write-Host " ✅ PASS" -ForegroundColor Green
    $passed++
} else {
    Write-Host " ❌ FAIL (Unexpected redirect URI: $redirectUri)" -ForegroundColor Red
    $failed++
}

# Summary
Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Total Tests: $($passed + $failed)" -ForegroundColor White
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor Red

if ($failed -eq 0) {
    Write-Host "`n✅ All tests passed!" -ForegroundColor Green
    Write-Host "`nNext step: Test OAuth flow at $baseUrl/web/welcome" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "`n❌ Some tests failed. Check errors above." -ForegroundColor Red
    exit 1
}
