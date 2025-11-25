#!/usr/bin/env pwsh
# Quick start script for ApplyLens hackathon demo
# Starts all services and verifies health

Write-Host "🚀 ApplyLens Hackathon Quick Start" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env.hackathon exists
if (-not (Test-Path "services/api/.env.hackathon")) {
    Write-Host "❌ Missing services/api/.env.hackathon" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create .env.hackathon with your credentials:" -ForegroundColor Yellow
    Write-Host "  - GOOGLE_CLOUD_PROJECT" -ForegroundColor Yellow
    Write-Host "  - DD_API_KEY" -ForegroundColor Yellow
    Write-Host "  - GOOGLE_APPLICATION_CREDENTIALS path" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "See services/api/.env.hackathon for template" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Found .env.hackathon" -ForegroundColor Green

# Check Docker is running
try {
    docker ps | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
    exit 1
}

# Start services
Write-Host ""
Write-Host "📦 Starting services with docker-compose..." -ForegroundColor Cyan
docker-compose -f docker-compose.hackathon.yml up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start services" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Services started" -ForegroundColor Green

# Wait for API to be healthy
Write-Host ""
Write-Host "⏳ Waiting for API to be ready..." -ForegroundColor Cyan

$maxAttempts = 30
$attempt = 0
$healthy = $false

while ($attempt -lt $maxAttempts) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health/live" -ErrorAction Stop
        if ($response.status -eq "ok") {
            $healthy = $true
            break
        }
    } catch {
        # API not ready yet
    }

    $attempt++
    Start-Sleep -Seconds 2
    Write-Host "." -NoNewline
}

Write-Host ""

if (-not $healthy) {
    Write-Host "❌ API did not become healthy" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check logs:" -ForegroundColor Yellow
    Write-Host "  docker logs applylens-api-hackathon" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ API is healthy" -ForegroundColor Green

# Check Gemini status
Write-Host ""
Write-Host "🤖 Checking Gemini integration..." -ForegroundColor Cyan

try {
    $llmStatus = Invoke-RestMethod -Uri "http://localhost:8000/debug/llm" -ErrorAction Stop

    if ($llmStatus.provider_active -eq "gemini") {
        Write-Host "✓ Gemini is active" -ForegroundColor Green
        Write-Host "  Model: $($llmStatus.gemini_model)" -ForegroundColor Gray
        Write-Host "  Project: $($llmStatus.google_cloud_project)" -ForegroundColor Gray
    } elseif ($llmStatus.provider_active -eq "heuristic_only") {
        Write-Host "⚠ Running in heuristic mode (Gemini not configured)" -ForegroundColor Yellow
        Write-Host "  This is OK for testing, but Gemini won't be used" -ForegroundColor Yellow
    } else {
        Write-Host "❌ Gemini status unknown: $($llmStatus.provider_active)" -ForegroundColor Red
    }
} catch {
    Write-Host "⚠ Could not check Gemini status" -ForegroundColor Yellow
}

# Check Datadog agent
Write-Host ""
Write-Host "📊 Checking Datadog agent..." -ForegroundColor Cyan

try {
    $agentRunning = docker ps --filter "name=applylens-datadog-agent" --format "{{.Status}}" | Select-String "Up"

    if ($agentRunning) {
        Write-Host "✓ Datadog agent is running" -ForegroundColor Green
    } else {
        Write-Host "⚠ Datadog agent not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Could not check Datadog agent" -ForegroundColor Yellow
}

# Print summary
Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "✅ Hackathon environment is ready!" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Test Gemini classification:" -ForegroundColor White
Write-Host '   Invoke-RestMethod -Uri "http://localhost:8000/hackathon/classify" -Method POST -Body ''{"subject":"Interview invitation","snippet":"Let''s schedule a call","sender":"hr@example.com"}'' -ContentType "application/json"' -ForegroundColor Gray
Write-Host ""
Write-Host "2. View debug status:" -ForegroundColor White
Write-Host "   Start-Process http://localhost:8000/debug/llm" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Generate traffic:" -ForegroundColor White
Write-Host "   python scripts/traffic_generator.py --mode normal_traffic --rate 10 --duration 60" -ForegroundColor Gray
Write-Host ""
Write-Host "4. View logs:" -ForegroundColor White
Write-Host "   docker logs -f applylens-api-hackathon" -ForegroundColor Gray
Write-Host ""
Write-Host "5. Access Datadog:" -ForegroundColor White
Write-Host "   Open your Datadog dashboard" -ForegroundColor Gray
Write-Host ""
Write-Host "6. Stop services:" -ForegroundColor White
Write-Host "   docker-compose -f docker-compose.hackathon.yml down" -ForegroundColor Gray
Write-Host ""
