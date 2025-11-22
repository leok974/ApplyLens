# Dev API Quick Start
# Usage: .\scripts\dev-api.ps1 [-Reload]

param([switch]$Reload=$true)

$here = "D:\ApplyLens\services\api"
Set-Location $here

Write-Host "🚀 Starting ApplyLens API (Dev Mode)" -ForegroundColor Green
Write-Host "   CWD: $here" -ForegroundColor Gray

# Environment
$env:APPLYLENS_DEV="1"
$env:APPLYLENS_DEV_DB="sqlite:///./dev_extension.db"
$env:ES_ENABLED="false"
$env:ALLOW_DEV_ROUTES="1"
$env:DEVDIAG_BASE="http://127.0.0.1:8080"
$env:DEVDIAG_ENABLED="1"

Write-Host "   ES_ENABLED: false" -ForegroundColor Gray
Write-Host "   DB: SQLite (dev_extension.db)" -ForegroundColor Gray
Write-Host "   Port: 8003" -ForegroundColor Gray

# Build args
$reloadArgs = @()
if ($Reload) {
    $reloadArgs = @("--reload", "--reload-dir", "app")
    Write-Host "   Reload: enabled (watching app/)" -ForegroundColor Gray
} else {
    Write-Host "   Reload: disabled" -ForegroundColor Gray
}

Write-Host ""
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 @reloadArgs
