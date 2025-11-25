# Start Grafana in Docker with JSON API Plugin
# This script starts the Grafana service from docker-compose

param(
    [Parameter(Mandatory=$false)]
    [switch]$Rebuild,

    [Parameter(Mandatory=$false)]
    [switch]$StopFirst
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Start Grafana (Docker)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "1️⃣  Checking Docker..." -ForegroundColor White

try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ❌ Docker is not running" -ForegroundColor Red
        Write-Host ""
        Write-Host "   Please start Docker Desktop and try again" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
    Write-Host "   ✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Docker is not available: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Please install Docker Desktop: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host ""

# Navigate to infra directory
$infraPath = "D:\ApplyLens\infra"

if (-not (Test-Path $infraPath)) {
    Write-Host "❌ Error: infra directory not found at: $infraPath" -ForegroundColor Red
    exit 1
}

Set-Location $infraPath
Write-Host "2️⃣  Working directory: $infraPath" -ForegroundColor White
Write-Host ""

# Check docker-compose file
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "❌ Error: docker-compose.yml not found" -ForegroundColor Red
    exit 1
}

# Stop existing container if requested
if ($StopFirst) {
    Write-Host "3️⃣  Stopping existing Grafana container..." -ForegroundColor White
    docker-compose stop grafana 2>&1 | Out-Null
    docker-compose rm -f grafana 2>&1 | Out-Null
    Write-Host "   ✅ Stopped" -ForegroundColor Green
    Write-Host ""
}

# Start Grafana
Write-Host "3️⃣  Starting Grafana..." -ForegroundColor White

if ($Rebuild) {
    Write-Host "   Rebuilding container..." -ForegroundColor Gray
    docker-compose up -d --build grafana
} else {
    docker-compose up -d grafana
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Failed to start Grafana" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Try with -Rebuild flag:" -ForegroundColor Yellow
    Write-Host "     .\start_grafana_docker.ps1 -Rebuild" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host "   ✅ Grafana container started" -ForegroundColor Green
Write-Host ""

# Wait for Grafana to be ready
Write-Host "4️⃣  Waiting for Grafana to be ready..." -ForegroundColor White

$maxAttempts = 30
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts -and -not $ready) {
    Start-Sleep -Seconds 2
    $attempt++

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $ready = $true
        }
    } catch {
        Write-Host "   Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
    }
}

if ($ready) {
    Write-Host "   ✅ Grafana is ready!" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "   ⚠️  Grafana may still be starting..." -ForegroundColor Yellow
    Write-Host "   Check logs: docker-compose logs grafana" -ForegroundColor Gray
    Write-Host ""
}

# Check container status
Write-Host "5️⃣  Container status:" -ForegroundColor White

$containerInfo = docker ps --filter "name=infra-grafana" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

if ($containerInfo) {
    $containerInfo | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
    Write-Host ""
} else {
    Write-Host "   ⚠️  Container not found in running state" -ForegroundColor Yellow
    Write-Host ""
}

# Verify plugin installation
Write-Host "6️⃣  Verifying JSON API plugin..." -ForegroundColor White

Start-Sleep -Seconds 3

try {
    $pluginCheck = docker exec infra-grafana grafana-cli plugins ls 2>&1

    if ($pluginCheck -match "marcusolsson-json-datasource") {
        Write-Host "   ✅ JSON API plugin is installed" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  JSON API plugin not found" -ForegroundColor Yellow
        Write-Host "   Plugin list:" -ForegroundColor Gray
        $pluginCheck | ForEach-Object { Write-Host "     $_" -ForegroundColor DarkGray }
    }
} catch {
    Write-Host "   ⚠️  Could not verify plugins: $_" -ForegroundColor Yellow
}

Write-Host ""

# Test API access
Write-Host "7️⃣  Testing Grafana API..." -ForegroundColor White

try {
    $health = Invoke-RestMethod -Uri "http://localhost:3000/api/health" -TimeoutSec 5
    Write-Host "   ✅ Grafana API is accessible" -ForegroundColor Green
    Write-Host "      Version: $($health.version)" -ForegroundColor Gray
    Write-Host "      Database: $($health.database)" -ForegroundColor Gray
} catch {
    Write-Host "   ⚠️  Could not connect to Grafana API" -ForegroundColor Yellow
}

Write-Host ""

# Final instructions
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ Grafana is Running!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Access Grafana:" -ForegroundColor Cyan
Write-Host "  URL:      http://localhost:3000" -ForegroundColor White
Write-Host "  Username: admin" -ForegroundColor White
Write-Host "  Password: admin" -ForegroundColor White
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host ""

Write-Host "1️⃣  Create JSON API Datasource:" -ForegroundColor Yellow
Write-Host "   • Go to: Configuration → Data Sources → Add data source" -ForegroundColor Gray
Write-Host "   • Search: 'JSON API'" -ForegroundColor Gray
Write-Host "   • Name: 'ApplyLens API'" -ForegroundColor Gray
Write-Host "   • Save & Test" -ForegroundColor Gray
Write-Host ""

Write-Host "2️⃣  Get API Key:" -ForegroundColor Yellow
Write-Host "   • Go to: Configuration → API Keys → New API Key" -ForegroundColor Gray
Write-Host "   • Role: Admin" -ForegroundColor Gray
Write-Host "   • Copy the generated key" -ForegroundColor Gray
Write-Host ""

Write-Host "3️⃣  Import Dashboard:" -ForegroundColor Yellow
Write-Host "   cd D:\ApplyLens\docs" -ForegroundColor Gray
Write-Host "   .\import_grafana_dashboard.ps1 -GrafanaUrl 'http://localhost:3000' -ApiKey 'YOUR_KEY'" -ForegroundColor Gray
Write-Host ""

Write-Host "Useful Commands:" -ForegroundColor Cyan
Write-Host "  View logs:      docker-compose logs -f grafana" -ForegroundColor Gray
Write-Host "  Stop:           docker-compose stop grafana" -ForegroundColor Gray
Write-Host "  Restart:        docker-compose restart grafana" -ForegroundColor Gray
Write-Host "  Remove:         docker-compose down grafana" -ForegroundColor Gray
Write-Host ""

Write-Host "Troubleshooting:" -ForegroundColor Cyan
Write-Host "  .\start_grafana_docker.ps1 -Rebuild       # Rebuild container" -ForegroundColor Gray
Write-Host "  .\start_grafana_docker.ps1 -StopFirst     # Stop and restart" -ForegroundColor Gray
Write-Host "  docker-compose logs grafana               # Check logs" -ForegroundColor Gray
Write-Host ""
