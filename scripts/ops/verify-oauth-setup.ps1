# Quick verification that regression prevention is working

Write-Host "`n=== OAuth Router Verification ===" -ForegroundColor Cyan

Write-Host "`n1. Checking environment variables..." -ForegroundColor Yellow
$envVars = docker exec applylens-api-prod printenv | Select-String "APPLYLENS_GOOGLE"
if ($envVars) {
    Write-Host "   ✅ APPLYLENS_GOOGLE_* variables are set" -ForegroundColor Green
    $envVars | ForEach-Object {
        $line = $_.Line
        if ($line -match "SECRET") {
            Write-Host "   $($line.Substring(0, [Math]::Min(40, $line.Length)))..." -ForegroundColor Gray
        } else {
            Write-Host "   $line" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "   ❌ APPLYLENS_GOOGLE_* variables NOT set!" -ForegroundColor Red
}

Write-Host "`n2. Checking API health..." -ForegroundColor Yellow
$health = docker exec applylens-nginx-prod wget -qO- http://api:8003/ready 2>&1
if ($health -match "ready") {
    Write-Host "   ✅ API is healthy: $health" -ForegroundColor Green
} else {
    Write-Host "   ❌ API health check failed: $health" -ForegroundColor Red
}

Write-Host "`n3. Checking router prefixes..." -ForegroundColor Yellow
Write-Host "   Searching for router definitions in code..." -ForegroundColor Gray

$authRouterPrefix = Get-Content "services\api\app\routers\auth.py" | Select-String 'prefix="/auth"'
$legacyRouterPrefix = Get-Content "services\api\app\auth_google.py" | Select-String 'prefix="/auth2/google"'

if ($authRouterPrefix) {
    Write-Host "   ✅ Modern router: /auth (ACTIVE)" -ForegroundColor Green
} else {
    Write-Host "   ❌ Modern router prefix not found" -ForegroundColor Red
}

if ($legacyRouterPrefix) {
    Write-Host "   ✅ Legacy router: /auth2/google (DISABLED)" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Legacy router still on /auth/google (CONFLICT!)" -ForegroundColor Yellow
}

Write-Host "`n4. Checking for logging statement..." -ForegroundColor Yellow
$logLine = Get-Content "services\api\app\routers\auth.py" | Select-String "Auth router: core auth.py"
if ($logLine) {
    Write-Host "   ✅ Logging added for monitoring" -ForegroundColor Green
    Write-Host "   Found: $($logLine.Line.Trim())" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Logging statement not found" -ForegroundColor Red
}

Write-Host "`n5. Testing OAuth endpoint..." -ForegroundColor Yellow
Write-Host "   Making request to /auth/google/login..." -ForegroundColor Gray

try {
    $response = Invoke-WebRequest -Uri "https://applylens.app/api/auth/google/login" `
        -Method GET `
        -MaximumRedirection 0 `
        -ErrorAction SilentlyContinue `
        -TimeoutSec 5

    if ($response.StatusCode -eq 302) {
        Write-Host "   ✅ Redirects to Google (302 Found)" -ForegroundColor Green
        $location = $response.Headers.Location
        if ($location -match "accounts.google.com") {
            Write-Host "   ✅ Redirects to: $($location.Substring(0, 60))..." -ForegroundColor Green
        }
    } else {
        Write-Host "   ⚠️  Unexpected status: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 302 -or $statusCode -eq 307) {
        Write-Host "   ✅ Redirects to Google ($statusCode redirect)" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Error: $statusCode - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n6. Recent logs check..." -ForegroundColor Yellow
Write-Host "   Checking last 20 lines for OAuth activity..." -ForegroundColor Gray
$logs = docker logs applylens-api-prod --tail 20 2>&1 | Select-String "auth.py|/auth/google|OAuth"
if ($logs) {
    Write-Host "   Recent OAuth logs:" -ForegroundColor Gray
    $logs | Select-Object -First 5 | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
} else {
    Write-Host "   No recent OAuth logs (try accessing /auth/google/login first)" -ForegroundColor Gray
}

Write-Host "`n=== Verification Complete ===" -ForegroundColor Cyan
Write-Host "`nTo test OAuth login, visit:" -ForegroundColor White
Write-Host "https://applylens.app/api/auth/google/login" -ForegroundColor Cyan
Write-Host "`nThen monitor logs with:" -ForegroundColor White
Write-Host 'docker logs -f applylens-api-prod | Select-String "Auth router|/auth/google"' -ForegroundColor Cyan
Write-Host ""
