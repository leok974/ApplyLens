#!/usr/bin/env pwsh
# Deploy production stack with build metadata
# Usage: .\scripts\deploy-prod.ps1 -Version "0.5.2"

param(
    [Parameter(Mandatory=$true)]
    [string]$Version,

    [string]$GitSha = "",

    [switch]$Build
)

# Get git SHA if not provided
if ([string]::IsNullOrEmpty($GitSha)) {
    $GitSha = (git rev-parse --short HEAD 2>$null)
    if (-not $GitSha) {
        $GitSha = "unknown"
    }
}

# Get build timestamp
$BuildTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

Write-Host "🚀 Deploying ApplyLens Production Stack" -ForegroundColor Cyan
Write-Host "Version:   $Version" -ForegroundColor Green
Write-Host "Git SHA:   $GitSha" -ForegroundColor Green
Write-Host "Built At:  $BuildTime" -ForegroundColor Green
Write-Host ""

# Build images if requested
if ($Build) {
    Write-Host "🏗️  Building images first..." -ForegroundColor Yellow
    & .\scripts\build-prod-images.ps1 -Version $Version -GitSha $GitSha -Push

    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Build failed, aborting deployment"
        exit 1
    }
    Write-Host ""
}

# Set environment variables for API build metadata
$env:APP_VERSION = $Version
$env:APP_BUILD_SHA = $GitSha
$env:APP_BUILD_TIME = $BuildTime

Write-Host "📝 Environment variables set:" -ForegroundColor Yellow
Write-Host "  APP_VERSION=$env:APP_VERSION" -ForegroundColor Gray
Write-Host "  APP_BUILD_SHA=$env:APP_BUILD_SHA" -ForegroundColor Gray
Write-Host "  APP_BUILD_TIME=$env:APP_BUILD_TIME" -ForegroundColor Gray
Write-Host ""

# Deploy the stack
Write-Host "🐳 Starting Docker Compose..." -ForegroundColor Yellow
& docker-compose -f docker-compose.prod.yml up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    Write-Host ""

    # Wait a bit for services to start
    Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10

    # Test the version endpoint
    Write-Host ""
    Write-Host "🔍 Testing version endpoint..." -ForegroundColor Yellow

    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8003/version" -ErrorAction Stop
        Write-Host "API Version Info:" -ForegroundColor Cyan
        Write-Host ($response | ConvertTo-Json) -ForegroundColor White
    } catch {
        Write-Warning "⚠️  Could not reach version endpoint yet (service may still be starting)"
    }

    Write-Host ""
    Write-Host "📊 Service Status:" -ForegroundColor Cyan
    & docker-compose -f docker-compose.prod.yml ps

} else {
    Write-Error "❌ Deployment failed"
    exit 1
}

Write-Host ""
Write-Host "🎉 Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  • View logs:    docker-compose -f docker-compose.prod.yml logs -f" -ForegroundColor White
Write-Host "  • Check status: docker-compose -f docker-compose.prod.yml ps" -ForegroundColor White
Write-Host "  • Stop stack:   docker-compose -f docker-compose.prod.yml down" -ForegroundColor White
Write-Host "  • API version:  curl http://localhost:8003/version" -ForegroundColor White
