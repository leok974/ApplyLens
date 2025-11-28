Write-Host "=== ApplyLens E2E Runner (Thread Viewer Phases 1–5.1) ===" -ForegroundColor Cyan

# ---------- 0. Cleanup ----------
Write-Host "`n[0/6] Cleaning up stray processes..." -ForegroundColor Yellow

Get-Process python -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -like "*uvicorn*" } |
  ForEach-Object { Write-Host "Stopping Python/uvicorn PID $($_.Id)"; Stop-Process -Id $_.Id -Force }

Get-Process node -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match "preview" } |
  ForEach-Object { Write-Host "Stopping Node/preview PID $($_.Id)"; Stop-Process -Id $_.Id -Force }

# ---------- 1. Infra (DB + ES via docker-compose) ----------
Write-Host "`n[1/6] Ensuring Elasticsearch and Postgres are up..." -ForegroundColor Yellow
Push-Location "$PSScriptRoot\infra"
docker-compose up -d es db
Start-Sleep -Seconds 3
docker-compose ps es db
Pop-Location

# ---------- 2. Start backend (uvicorn) with real env ----------
Write-Host "`n[2/6] Starting backend API (FastAPI + dev routes)..." -ForegroundColor Yellow

# Set env vars in parent shell BEFORE spawning the process
$env:ALLOW_DEV_ROUTES = "1"
$env:ES_ENABLED = "true"
$env:ES_URL = "http://localhost:9200"
$env:DATABASE_URL = "postgresql://postgres:4c9248fc7d7d477d919ccc431b1bbd36!PgA1@localhost:5433/applylens"

$backendArgs = @(
    "-m", "uvicorn",
    "app.main:app",
    "--host", "127.0.0.1",
    "--port", "8003"
)

$backendProcess = Start-Process `
    -FilePath "python" `
    -ArgumentList $backendArgs `
    -WorkingDirectory "$PSScriptRoot\services\api" `
    -NoNewWindow `
    -PassThru

Start-Sleep -Seconds 4

# Quick readiness check
try {
    $ready = Invoke-RestMethod -Uri "http://127.0.0.1:8003/ready" -Method Get -TimeoutSec 3
    Write-Host "[OK] Backend responded: $($ready | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Warning "[WARN] Backend /ready did not respond yet. Continuing..."
}

# ---------- 3. Start web preview server (on fixed port) ----------
Write-Host "`n[3/6] Starting web preview server..." -ForegroundColor Yellow
$webPort = 5175

# Use PowerShell job for npm since Start-Process has issues with npm on Windows
$webJob = Start-Job -ScriptBlock {
    param($webDir, $port)
    Set-Location $webDir
    npm run preview -- --port $port
} -ArgumentList "$PSScriptRoot\apps\web", $webPort

Start-Sleep -Seconds 10

# Check if job failed
$jobState = Get-Job $webJob | Select-Object -ExpandProperty State
if ($jobState -eq "Failed") {
    Write-Host "[ERROR] Web job failed to start!" -ForegroundColor Red
    Receive-Job $webJob | Write-Host
}

try {
    $webCheck = Invoke-WebRequest -Uri "http://127.0.0.1:$webPort" -Method Get -TimeoutSec 3 -UseBasicParsing
    Write-Host "[OK] Web server responding (status: $($webCheck.StatusCode))" -ForegroundColor Green
} catch {
    Write-Warning "[WARN] Web server not responding yet. Continuing..."
}


# ---------- 4. Run Playwright tests ----------
Write-Host "`n[4/6] Running Playwright tests..." -ForegroundColor Yellow

Push-Location $PSScriptRoot

# These affect the test runner itself (Playwright process):
$env:PROD = "0"                 # allow destructive bulk triage tests
$env:ALLOW_DEV_ROUTES = "1"     # so seedInboxThreads() doesn't early-exit
$env:USE_EXTERNAL_SERVERS = "1" # tell config to NOT spawn its own dev server
$env:E2E_BASE_URL = "http://127.0.0.1:$webPort"

Write-Host "`nTest Environment:" -ForegroundColor Cyan
Write-Host "  PROD = $env:PROD" -ForegroundColor Gray
Write-Host "  ALLOW_DEV_ROUTES = $env:ALLOW_DEV_ROUTES" -ForegroundColor Gray
Write-Host "  E2E_BASE_URL = $env:E2E_BASE_URL" -ForegroundColor Gray
Write-Host "  API: http://127.0.0.1:8003" -ForegroundColor Gray
Write-Host "  Web: http://127.0.0.1:$webPort" -ForegroundColor Gray
Write-Host ""

# Run thread viewer tests
npx playwright test thread-viewer --config=playwright.config.ts --reporter=list

$testExitCode = $LASTEXITCODE

Pop-Location

# ---------- 5. Cleanup ----------
Write-Host "`n[5/6] Shutting down preview and backend..." -ForegroundColor Yellow

if ($webJob) {
    Stop-Job $webJob -ErrorAction SilentlyContinue
    Remove-Job $webJob -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped web job"
}
if ($backendProcess -and !$backendProcess.HasExited) {
    Stop-Process -Id $backendProcess.Id -Force
    Write-Host "Stopped backend process (PID $($backendProcess.Id))"
}

# We DO NOT `docker-compose down` here because you may want DB/ES to persist for debugging.
# If you want to tear down infra after each run, uncomment:
# Push-Location "$PSScriptRoot\infra"
# docker-compose stop es db
# Pop-Location

Write-Host "`n[6/6] Done." -ForegroundColor Cyan

if ($testExitCode -eq 0) {
    Write-Host "✅ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "❌ Some tests failed (exit code: $testExitCode)" -ForegroundColor Red
    exit $testExitCode
}
