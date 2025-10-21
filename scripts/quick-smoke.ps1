# Quick 30-second Smoke Test (PowerShell)
# Copy-paste friendly version for rapid verification

param(
    [string]$BaseUrl = "http://localhost:5175"
)

$ErrorActionPreference = "Stop"

Write-Host "Testing $BaseUrl..." -ForegroundColor Cyan
Write-Host ""

# 1. CSRF block test
Write-Host -NoNewline "1. CSRF block (expect 403)... "
try {
    Invoke-WebRequest -Uri "$BaseUrl/api/auth/logout" -Method POST -ErrorAction SilentlyContinue | Out-Null
    Write-Host "❌ Should have been blocked" -ForegroundColor Red
    exit 1
} catch {
    if ($_.Exception.Response.StatusCode -eq 403) {
        Write-Host "✅" -ForegroundColor Green
    } else {
        Write-Host "❌ Wrong status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        exit 1
    }
}

# 2. Get CSRF cookie
Write-Host -NoNewline "2. CSRF allow (get cookie)... "
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-WebRequest -Uri "$BaseUrl/api/auth/status" -WebSession $session -UseBasicParsing | Out-Null
$token = ($session.Cookies.GetCookies($BaseUrl) | Where-Object {$_.Name -eq "csrf_token"}).Value

if ($token) {
    Write-Host "✅" -ForegroundColor Green
} else {
    Write-Host "❌ No token" -ForegroundColor Red
    exit 1
}

# 3. CSRF allow with token
Write-Host -NoNewline "3. CSRF allow (with token)... "
try {
    $response = Invoke-WebRequest `
        -Uri "$BaseUrl/api/auth/demo/start" `
        -Method POST `
        -Headers @{"X-CSRF-Token"=$token} `
        -WebSession $session `
        -UseBasicParsing `
        -ErrorAction SilentlyContinue
    
    if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 400) {
        Write-Host "✅ ($($response.StatusCode))" -ForegroundColor Green
    } else {
        Write-Host "❌ Got $($response.StatusCode)" -ForegroundColor Red
        exit 1
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 200 -or $_.Exception.Response.StatusCode -eq 400) {
        Write-Host "✅ ($($_.Exception.Response.StatusCode))" -ForegroundColor Green
    } else {
        Write-Host "❌ Got $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        exit 1
    }
}

# 4. Check metrics
Write-Host -NoNewline "4. Metrics present... "
$metrics = Invoke-WebRequest -Uri "$BaseUrl/api/metrics" -UseBasicParsing
if ($metrics.Content -match "applylens_(csrf|crypto|rate_limit|recaptcha)") {
    Write-Host "✅" -ForegroundColor Green
} else {
    Write-Host "❌ No metrics" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎉 Quick smoke test passed!" -ForegroundColor Green
Write-Host ""

# Show sample metrics
Write-Host "Sample metrics:" -ForegroundColor Cyan
$metrics.Content -split "`n" | Select-String "applylens_(csrf|crypto|rate_limit)" | Select-Object -First 5
