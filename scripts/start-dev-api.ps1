#!/usr/bin/env pwsh
# Start ApplyLens API in development mode using Docker
# This provides hot-reload via uvicorn --reload and uses SQLite for data

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "🚀 ApplyLens Dev API Startup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if already running
$container = docker ps --filter "name=applylens-api-dev" --format "{{.ID}}"
if ($container) {
    Write-Host "✅ applylens-api-dev is already running!" -ForegroundColor Green
    Write-Host ""
    docker ps --filter "name=applylens-api-dev" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    Write-Host ""
    Write-Host "📡 Endpoints:" -ForegroundColor Yellow
    Write-Host "   Health:     http://localhost:8003/healthz" -ForegroundColor White
    Write-Host "   Swagger:    http://localhost:8003/docs" -ForegroundColor White
    Write-Host "   ReDoc:      http://localhost:8003/redoc" -ForegroundColor White
    Write-Host ""
    Write-Host "💡 To restart: docker restart applylens-api-dev" -ForegroundColor Cyan
    Write-Host "💡 To stop:    docker stop applylens-api-dev" -ForegroundColor Cyan
    Write-Host "💡 View logs:  docker logs -f applylens-api-dev" -ForegroundColor Cyan
    Write-Host ""
    exit 0
}

# Start the dev API
Write-Host "📦 Building and starting dev API container..." -ForegroundColor Yellow
Write-Host ""

try {
    docker compose -f docker-compose.dev.api.yml up applylens-api-dev -d --build

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to start dev API container" -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "✅ Dev API container started!" -ForegroundColor Green
    Write-Host ""

    # Wait a moment for startup
    Write-Host "⏳ Waiting for API to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3

    # Check health
    $maxRetries = 10
    $retryCount = 0
    $healthy = $false

    while ($retryCount -lt $maxRetries -and -not $healthy) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8003/healthz" -Method GET -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                $healthy = $true
            }
        } catch {
            $retryCount++
            if ($retryCount -lt $maxRetries) {
                Write-Host "   Retry $retryCount/$maxRetries..." -ForegroundColor DarkGray
                Start-Sleep -Seconds 2
            }
        }
    }

    Write-Host ""

    if ($healthy) {
        Write-Host "✅ API is healthy and ready!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  API started but health check didn't respond" -ForegroundColor Yellow
        Write-Host "   Check logs: docker logs applylens-api-dev" -ForegroundColor Cyan
    }

    Write-Host ""
    Write-Host "📡 Dev API Endpoints:" -ForegroundColor Yellow
    Write-Host "   Health:     http://localhost:8003/healthz" -ForegroundColor White
    Write-Host "   Swagger:    http://localhost:8003/docs" -ForegroundColor White
    Write-Host "   ReDoc:      http://localhost:8003/redoc" -ForegroundColor White
    Write-Host "   CSRF:       http://localhost:8003/auth/csrf" -ForegroundColor White
    Write-Host ""
    Write-Host "🔧 Configuration:" -ForegroundColor Yellow
    Write-Host "   Mode:       Development (APPLYLENS_DEV=1)" -ForegroundColor White
    Write-Host "   Database:   SQLite (./services/api/dev-data/)" -ForegroundColor White
    Write-Host "   Hot-reload: Enabled (uvicorn --reload)" -ForegroundColor White
    Write-Host "   CORS:       http://localhost:5173-5177" -ForegroundColor White
    Write-Host ""
    Write-Host "💡 Useful Commands:" -ForegroundColor Yellow
    Write-Host "   View logs:  docker logs -f applylens-api-dev" -ForegroundColor Cyan
    Write-Host "   Stop:       docker stop applylens-api-dev" -ForegroundColor Cyan
    Write-Host "   Restart:    docker restart applylens-api-dev" -ForegroundColor Cyan
    Write-Host "   Shell:      docker exec -it applylens-api-dev bash" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🌐 Next: Start web dev server and point it to http://localhost:8003" -ForegroundColor Green
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "❌ Error starting dev API:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    exit 1
}
