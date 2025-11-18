#!/usr/bin/env pwsh
# Stop ApplyLens dev API container

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "🛑 Stopping ApplyLens Dev API" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""

# Check if running
$container = docker ps --filter "name=applylens-api-dev" --format "{{.ID}}"
if (-not $container) {
    Write-Host "ℹ️  applylens-api-dev is not running" -ForegroundColor Yellow
    Write-Host ""

    # Check if it exists but is stopped
    $stoppedContainer = docker ps -a --filter "name=applylens-api-dev" --format "{{.ID}}"
    if ($stoppedContainer) {
        Write-Host "💡 Container exists but is already stopped" -ForegroundColor Cyan
        Write-Host "   To remove: docker rm applylens-api-dev" -ForegroundColor Cyan
    } else {
        Write-Host "💡 No dev API container found" -ForegroundColor Cyan
        Write-Host "   To start: .\scripts\start-dev-api.ps1" -ForegroundColor Cyan
    }
    Write-Host ""
    exit 0
}

# Stop the container
try {
    Write-Host "⏹️  Stopping applylens-api-dev..." -ForegroundColor Yellow
    docker stop applylens-api-dev

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Dev API stopped successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "💡 To start again: .\scripts\start-dev-api.ps1" -ForegroundColor Cyan
        Write-Host "💡 To remove:      docker rm applylens-api-dev" -ForegroundColor Cyan
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "❌ Failed to stop container" -ForegroundColor Red
        Write-Host ""
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "❌ Error stopping dev API:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    exit 1
}
