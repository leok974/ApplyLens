# ci-smoke-test.ps1
# ApplyLens Security Features Smoke Test (PowerShell)
# Tests: CSRF, Metrics, Health

param(
    [string]$Base = "http://localhost:5175"
)

$ErrorActionPreference = "Stop"
Write-Host "Testing $Base..." -ForegroundColor Cyan
Write-Host ""

# 1. CSRF cookie
Write-Host -NoNewline "Getting CSRF cookie... "
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
try {
    Invoke-WebRequest -Uri "$Base/api/auth/status" -WebSession $session -UseBasicParsing | Out-Null
} catch {
    Write-Host "❌ Failed to get status" -ForegroundColor Red
    exit 1
}

$csrfCookie = $session.Cookies.GetCookies($Base) | Where-Object { $_.Name -eq "csrf_token" }
if (-not $csrfCookie) {
    Write-Host "❌ No token" -ForegroundColor Red
    exit 1
}
$token = $csrfCookie.Value
Write-Host "✅" -ForegroundColor Green

# 2. CSRF blocked
Write-Host -NoNewline "Testing CSRF block... "
try {
    Invoke-WebRequest -Uri "$Base/api/auth/logout" -Method POST -UseBasicParsing -ErrorAction Stop | Out-Null
    Write-Host "❌ Should have blocked" -ForegroundColor Red
    exit 1
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 403) {
        Write-Host "✅" -ForegroundColor Green
    } else {
        Write-Host "❌ Expected 403, got $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
        exit 1
    }
}

# 3. CSRF allowed
Write-Host -NoNewline "Testing CSRF allow... "
$headers = @{
    "X-CSRF-Token" = $token
    "Content-Type" = "application/json"
}
$body = "{}"

try {
    $response = Invoke-WebRequest -Uri "$Base/api/auth/demo/start" -Method POST -Headers $headers -Body $body -WebSession $session -UseBasicParsing
    $statusCode = $response.StatusCode
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
}

if ($statusCode -in @(200, 400)) {
    Write-Host "✅ (got $statusCode)" -ForegroundColor Green
} else {
    Write-Host "❌ Expected 200/400, got $statusCode" -ForegroundColor Red
    exit 1
}

# 4. Metrics endpoint
Write-Host -NoNewline "Testing metrics... "
try {
    $metrics = Invoke-WebRequest -Uri "$Base/api/metrics" -UseBasicParsing
    if ($metrics.Content -match "applylens_csrf_fail_total") {
        Write-Host "✅" -ForegroundColor Green
    } else {
        Write-Host "❌ No CSRF metrics" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Metrics endpoint failed" -ForegroundColor Red
    exit 1
}

# 5. Health check
Write-Host -NoNewline "Testing health... "
try {
    Invoke-WebRequest -Uri "$Base/api/healthz" -UseBasicParsing | Out-Null
    Write-Host "✅" -ForegroundColor Green
} catch {
    Write-Host "❌ Health check failed" -ForegroundColor Red
    exit 1
}

# 6. Crypto metrics
Write-Host -NoNewline "Testing crypto metrics... "
if ($metrics.Content -match "applylens_crypto_encrypt_total") {
    Write-Host "✅" -ForegroundColor Green
} else {
    Write-Host "❌ No crypto metrics" -ForegroundColor Red
    exit 1
}

# 7. Rate limit metrics
Write-Host -NoNewline "Testing rate limit metrics... "
if ($metrics.Content -match "applylens_rate_limit_allowed_total") {
    Write-Host "✅" -ForegroundColor Green
} else {
    Write-Host "❌ No rate limit metrics" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎉 All smoke tests passed!" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  ✅ CSRF protection working" -ForegroundColor Green
Write-Host "  ✅ Metrics exposed" -ForegroundColor Green
Write-Host "  ✅ Health check passing" -ForegroundColor Green
Write-Host "  ✅ All security features initialized" -ForegroundColor Green
