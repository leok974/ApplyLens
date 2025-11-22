param(
  [int]$SeedCount = 20,
  [switch]$Headed,
  [string]$TestPattern = ""
)

Write-Host "`n🔧 E2E Test Runner" -ForegroundColor Cyan
Write-Host "==================`n" -ForegroundColor Cyan

Write-Host "Stopping prod services that block ports (nginx, api, web, kibana, grafana, prometheus)..." -ForegroundColor Yellow
docker compose -f d:\ApplyLens\docker-compose.prod.yml stop nginx api web kibana grafana prometheus | Out-Null

Write-Host "Starting dev infra..." -ForegroundColor Cyan
Set-Location d:\ApplyLens\infra
docker compose up -d

Start-Sleep -Seconds 12
Write-Host "`nDev services status:" -ForegroundColor Cyan
$ports = docker ps --filter "name=infra" --format "{{.Names}} | {{.Ports}}" | Select-String -Pattern "(8888|8003|5175)"
$ports | ForEach-Object { Write-Host "  $_" }

Write-Host "`nVerifying API health..." -ForegroundColor Cyan
try {
  $health = Invoke-WebRequest -Uri "http://127.0.0.1:8888/api/healthz" -UseBasicParsing -TimeoutSec 5
  Write-Host "  ✓ API is healthy: $($health.Content)" -ForegroundColor Green
} catch {
  Write-Host "  ✗ API health check failed: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}

Write-Host "`nRunning Playwright tests..." -ForegroundColor Green
Set-Location d:\ApplyLens\apps\web

$env:E2E_BASE_URL = 'http://127.0.0.1:8888'
$env:E2E_API = 'http://127.0.0.1:8888/api'
$env:USE_SMOKE_SETUP = 'true'
$env:SEED_COUNT = "$SeedCount"

$playwrightArgs = @()
if ($TestPattern) {
  $playwrightArgs += $TestPattern
}
if ($Headed) {
  $playwrightArgs += "--headed"
}
$playwrightArgs += "--workers=4"

Write-Host "  Test pattern: $(if($TestPattern) { $TestPattern } else { 'all tests' })" -ForegroundColor Cyan
Write-Host "  Headed mode: $Headed" -ForegroundColor Cyan
Write-Host "  Seed count: $SeedCount" -ForegroundColor Cyan
Write-Host ""

if ($playwrightArgs.Count -gt 0) {
  npm run test:e2e -- @playwrightArgs
} else {
  npm run test:e2e
}

$exitCode = $LASTEXITCODE
Write-Host "`n$(if($exitCode -eq 0) { '✅ Tests passed' } else { '❌ Tests failed' })" -ForegroundColor $(if($exitCode -eq 0) { 'Green' } else { 'Red' })

exit $exitCode
