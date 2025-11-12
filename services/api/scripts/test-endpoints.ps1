# Quick Dev Smoke Tests
# Usage: .\scripts\test-endpoints.ps1

$base = "http://localhost:8003"

Write-Host "`n=== ApplyLens API Smoke Tests ===" -ForegroundColor Green

# 1. Liveness / Readiness / Status
Write-Host "`n1. Health Checks:" -ForegroundColor Cyan
Write-Host "   Healthz: " -NoNewline -ForegroundColor Yellow
curl -s "$base/healthz" | ConvertFrom-Json | Select-Object -ExpandProperty status

Write-Host "   Ready:   " -NoNewline -ForegroundColor Yellow
$ready = curl -s "$base/ready" | ConvertFrom-Json
Write-Host "$($ready.status) (DB: $($ready.db), ES: $($ready.es))"

Write-Host "   Status:  " -NoNewline -ForegroundColor Yellow
$status = curl -s "$base/status" | ConvertFrom-Json
Write-Host "$($status.ok) (Gmail: $($status.gmail))"

# 2. Routes present?
Write-Host "`n2. Route Verification:" -ForegroundColor Cyan
$routes = curl -s "$base/openapi.json" | ConvertFrom-Json
$paths = $routes.paths.PSObject.Properties.Name

$checks = @(
    "/api/ops/diag",
    "/api/extension",
    "/api/gmail/backfill"
)

foreach ($check in $checks) {
    $found = $paths | Where-Object { $_ -like "*$check*" }
    if ($found) {
        Write-Host "   ✓ $check" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $check (NOT FOUND)" -ForegroundColor Red
    }
}

# 3. Metrics (ES disabled should be -1)
Write-Host "`n3. Metrics:" -ForegroundColor Cyan
$esMetric = curl -s "$base/metrics" | Select-String "applylens_es_up " | Select-Object -First 1
Write-Host "   $esMetric"

# 4. CSRF-exempt endpoints
Write-Host "`n4. CSRF-Exempt Endpoints:" -ForegroundColor Cyan

Write-Host "   Extension apps: " -NoNewline -ForegroundColor Yellow
try {
    $apps = curl -s "$base/api/extension/applications" | ConvertFrom-Json
    Write-Host "OK (count: $($apps.Count))" -ForegroundColor Green
} catch {
    Write-Host "FAILED" -ForegroundColor Red
}

Write-Host "   DevDiag health: " -NoNewline -ForegroundColor Yellow
try {
    $diag = curl -s "$base/api/ops/diag/health" 2>&1
    if ($diag -match "error|failed") {
        Write-Host "Expected (DevDiag not running)" -ForegroundColor Yellow
    } else {
        Write-Host "OK" -ForegroundColor Green
    }
} catch {
    Write-Host "Expected (DevDiag not running)" -ForegroundColor Yellow
}

Write-Host "`n✅ Smoke tests complete!`n" -ForegroundColor Green
