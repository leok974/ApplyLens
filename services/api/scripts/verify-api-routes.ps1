# API Server Verification Script
# Tests that the running server has the correct routes and environment
# Usage: .\scripts\verify-api-routes.ps1

$baseUrl = "http://localhost:8003"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "API SERVER VERIFICATION" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1) Check server is running
Write-Host "1️⃣  Checking if server is running on $baseUrl..." -ForegroundColor Yellow
try {
    $null = Invoke-RestMethod -Uri "$baseUrl/ready" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✓ Server is running" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Server not responding on $baseUrl" -ForegroundColor Red
    Write-Host "   Run: Ctrl+Shift+B to start the dev server" -ForegroundColor Yellow
    exit 1
}

# 2) Check OpenAPI includes DevDiag and Extension routes
Write-Host "`n2️⃣  Verifying routes in OpenAPI spec..." -ForegroundColor Yellow
try {
    $openapi = Invoke-RestMethod -Uri "$baseUrl/openapi.json" -ErrorAction Stop
    $paths = $openapi.paths.PSObject.Properties.Name

    # Check for DevDiag routes
    $devdiagHealth = $paths -contains "/api/ops/diag/health"
    $devdiagRun = $paths -contains "/api/ops/diag"

    # Check for Extension routes
    $extensionApp = $paths -contains "/api/extension/applications"
    $extensionOutreach = $paths -contains "/api/extension/outreach"
    $extensionForm = $paths -contains "/api/extension/generate-form-answers"
    $extensionDM = $paths -contains "/api/extension/generate-recruiter-dm"
    $profileMe = $paths -contains "/api/profile/me"

    if ($devdiagHealth -and $devdiagRun) {
        Write-Host "   ✓ DevDiag routes found" -ForegroundColor Green
        Write-Host "     - /api/ops/diag/health" -ForegroundColor Gray
        Write-Host "     - /api/ops/diag" -ForegroundColor Gray
    } else {
        Write-Host "   ✗ DevDiag routes missing!" -ForegroundColor Red
        Write-Host "     Expected: /api/ops/diag/health, /api/ops/diag" -ForegroundColor Yellow
    }

    if ($extensionApp -and $extensionOutreach -and $extensionForm -and $extensionDM -and $profileMe) {
        Write-Host "   ✓ Extension routes found" -ForegroundColor Green
        Write-Host "     - /api/profile/me" -ForegroundColor Gray
        Write-Host "     - /api/extension/applications" -ForegroundColor Gray
        Write-Host "     - /api/extension/outreach" -ForegroundColor Gray
        Write-Host "     - /api/extension/generate-form-answers" -ForegroundColor Gray
        Write-Host "     - /api/extension/generate-recruiter-dm" -ForegroundColor Gray
    } else {
        Write-Host "   ✗ Some extension routes missing!" -ForegroundColor Red
    }

} catch {
    Write-Host "   ✗ Failed to fetch OpenAPI spec: $($_.Exception.Message)" -ForegroundColor Red
}

# 3) Test DevDiag health endpoint
Write-Host "`n3️⃣  Testing DevDiag health endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/ops/diag/health" -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 503) {
        Write-Host "   ⚠️  DevDiag health check returned 503 (service not configured)" -ForegroundColor Yellow
        Write-Host "      This is expected if DEVDIAG_BASE is not set or DevDiag service is not running" -ForegroundColor Gray
    } elseif ($response.StatusCode -eq 200) {
        Write-Host "   ✓ DevDiag health check passed" -ForegroundColor Green
    } else {
        Write-Host "   ? DevDiag health returned status $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 503) {
        Write-Host "   ⚠️  DevDiag service unavailable (503 - expected if not configured)" -ForegroundColor Yellow
    } elseif ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "   ✗ DevDiag route not found (404) - route not registered!" -ForegroundColor Red
    } else {
        Write-Host "   ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 4) Test profile endpoint
Write-Host "`n4️⃣  Testing profile endpoint..." -ForegroundColor Yellow
try {
    $profileData = Invoke-RestMethod -Uri "$baseUrl/api/profile/me" -ErrorAction Stop
    Write-Host "   ✓ Profile endpoint working" -ForegroundColor Green
    Write-Host "     Name: $($profileData.name)" -ForegroundColor Gray
} catch {
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "   ✗ Profile endpoint not found (404) - route not registered!" -ForegroundColor Red
    } else {
        Write-Host "   ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 5) Check CSRF metrics
Write-Host "`n5️⃣  Checking CSRF metrics..." -ForegroundColor Yellow
try {
    $metrics = Invoke-WebRequest -Uri "$baseUrl/metrics" -UseBasicParsing
    $csrfFailures = ($metrics.Content -split "`n") | Select-String 'csrf_fail_total.*path="/api/(extension|ops/diag)"'

    if ($csrfFailures.Count -eq 0) {
        Write-Host "   ✓ No CSRF failures for extension/DevDiag endpoints" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Found CSRF failures:" -ForegroundColor Yellow
        $csrfFailures | ForEach-Object { Write-Host "     $_" -ForegroundColor Gray }
    }
} catch {
    Write-Host "   ✗ Failed to fetch metrics: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Verification complete!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
