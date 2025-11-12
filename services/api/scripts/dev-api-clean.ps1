# Dev API Clean Boot Script
# Nukes stale processes and cache, then launches fresh Uvicorn instance
# Usage: .\scripts\dev-api-clean.ps1

# 0) Stop anything on 8003 and kill stale python/uvicorn
Write-Host "🔧 Killing processes on :8003 and stale python..." -ForegroundColor Yellow
$portProcess = (Get-NetTCPConnection -LocalPort 8003 -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
if ($portProcess) {
    Write-Host "   Found process $portProcess on port 8003, terminating..." -ForegroundColor Gray
    Stop-Process -Id $portProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
}
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# 1) Clear pyc caches (prevents weird reload issues)
Write-Host "🧹 Clearing __pycache__..." -ForegroundColor Yellow
Get-ChildItem "D:\ApplyLens\services\api" -Recurse -Directory -Filter "__pycache__" `
  | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 2) Export env explicitly for this session (dev-only)
Write-Host "🌱 Setting dev env..." -ForegroundColor Yellow
$env:APPLYLENS_DEV="1"
$env:APPLYLENS_DEV_DB="sqlite:///./dev_extension.db"
$env:ES_ENABLED="false"  # Disable ES in dev mode
$env:ALLOW_DEV_ROUTES="1"
# DevDiag configuration
if (-not $env:DEVDIAG_BASE) { $env:DEVDIAG_BASE="http://127.0.0.1:8080" }
$env:DEVDIAG_ENABLED="1"
$env:DEVDIAG_TIMEOUT_S="120"
$env:DEVDIAG_ALLOW_HOSTS="applylens.app,.applylens.app,api.applylens.app"
# M2M API keys (optional - leave empty to disable)
# $env:BACKFILL_API_KEY=""  # Uncomment and set for production

Write-Host "   APPLYLENS_DEV=$env:APPLYLENS_DEV" -ForegroundColor Gray
Write-Host "   APPLYLENS_DEV_DB=$env:APPLYLENS_DEV_DB" -ForegroundColor Gray
Write-Host "   ES_ENABLED=$env:ES_ENABLED" -ForegroundColor Gray
Write-Host "   DEVDIAG_BASE=$env:DEVDIAG_BASE" -ForegroundColor Gray

# 3) Launch uvicorn from the API folder (ensures correct CWD & module resolution)
Write-Host "🚀 Starting Uvicorn on :8003..." -ForegroundColor Green
Set-Location D:\ApplyLens\services\api

# Use python -m to ensure correct module resolution
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload --reload-dir app
