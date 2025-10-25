#!/usr/bin/env pwsh
# Rollback ApplyLens to a previous version
#
# Usage:
#   .\scripts\rollback.ps1 -Version "v0.4.0"
#   .\scripts\rollback.ps1 -Version "v0.4.0" -Service "web"
#   .\scripts\rollback.ps1 -Version "v0.4.0" -DryRun
#
# This script:
# 1. Backs up current docker-compose.prod.yml
# 2. Updates image tags to specified version
# 3. Recreates containers with rollback version
# 4. Verifies health checks

param(
    [Parameter(Mandatory=$true)]
    [string]$Version,

    [Parameter(Mandatory=$false)]
    [ValidateSet("api", "web", "both")]
    [string]$Service = "both",

    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ApplyLens Rollback to $Version" -ForegroundColor Cyan
Write-Host "Service: $Service" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if version exists locally
$checkApi = ($Service -eq "api" -or $Service -eq "both")
$checkWeb = ($Service -eq "web" -or $Service -eq "both")

if ($checkApi) {
    $apiImage = docker images -q "leoklemet/applylens-api:$Version"
    if (-not $apiImage) {
        Write-Host "⚠ API image $Version not found locally. Pulling..." -ForegroundColor Yellow
        docker pull "leoklemet/applylens-api:$Version"
        if ($LASTEXITCODE -ne 0) { throw "Failed to pull API image" }
    }
}

if ($checkWeb) {
    $webImage = docker images -q "leoklemet/applylens-web:$Version"
    if (-not $webImage) {
        Write-Host "⚠ Web image $Version not found locally. Pulling..." -ForegroundColor Yellow
        docker pull "leoklemet/applylens-web:$Version"
        if ($LASTEXITCODE -ne 0) { throw "Failed to pull Web image" }
    }
}

# Backup current compose file
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = "docker-compose.prod.yml.$timestamp.bak"

Write-Host "`nBacking up docker-compose.prod.yml to $backupPath" -ForegroundColor Yellow
Copy-Item docker-compose.prod.yml $backupPath

if ($DryRun) {
    Write-Host "`n[DRY RUN] Would update docker-compose.prod.yml:" -ForegroundColor Yellow
    if ($checkApi) {
        Write-Host "  - API: leoklemet/applylens-api:$Version" -ForegroundColor White
    }
    if ($checkWeb) {
        Write-Host "  - Web: leoklemet/applylens-web:$Version" -ForegroundColor White
    }
    Write-Host "`n[DRY RUN] Would recreate containers" -ForegroundColor Yellow
    Write-Host "`n✓ Dry run complete. Backup saved to $backupPath" -ForegroundColor Green
    exit 0
}

# Update docker-compose.prod.yml
Write-Host "`nUpdating docker-compose.prod.yml..." -ForegroundColor Yellow

$composeContent = Get-Content docker-compose.prod.yml -Raw

if ($checkApi) {
    $composeContent = $composeContent -replace `
        'image: leoklemet/applylens-api:v[\d.]+', `
        "image: leoklemet/applylens-api:$Version"
    Write-Host "  ✓ Updated API to $Version" -ForegroundColor Green
}

if ($checkWeb) {
    $composeContent = $composeContent -replace `
        'image: leoklemet/applylens-web:v[\d.]+', `
        "image: leoklemet/applylens-web:$Version"
    Write-Host "  ✓ Updated Web to $Version" -ForegroundColor Green
}

$composeContent | Out-File -FilePath docker-compose.prod.yml -Encoding utf8 -NoNewline

# Recreate containers
Write-Host "`nRecreating containers..." -ForegroundColor Yellow

$services = @()
if ($checkApi) { $services += "api" }
if ($checkWeb) { $services += "web" }
$serviceList = $services -join " "

docker-compose -f docker-compose.prod.yml up -d --force-recreate $serviceList
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Container recreation failed! Rolling back..." -ForegroundColor Red
    Copy-Item $backupPath docker-compose.prod.yml -Force
    throw "Rollback failed"
}

# Wait for health checks
Write-Host "`nWaiting for health checks..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Verify services
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($checkApi) {
    try {
        $healthResponse = Invoke-WebRequest -Uri "http://localhost:8003/healthz" -TimeoutSec 10
        if ($healthResponse.StatusCode -eq 200) {
            Write-Host "✓ API health check passed" -ForegroundColor Green
        }
    } catch {
        Write-Host "✗ API health check failed: $_" -ForegroundColor Red
        Write-Host "`nRolling back to backup..." -ForegroundColor Yellow
        Copy-Item $backupPath docker-compose.prod.yml -Force
        docker-compose -f docker-compose.prod.yml up -d --force-recreate $serviceList
        throw "Rollback verification failed"
    }
}

if ($checkWeb) {
    try {
        $webResponse = Invoke-WebRequest -Uri "http://localhost:5175/" -TimeoutSec 10
        if ($webResponse.StatusCode -eq 200) {
            Write-Host "✓ Web health check passed" -ForegroundColor Green
        }
    } catch {
        Write-Host "✗ Web health check failed: $_" -ForegroundColor Red
        Write-Host "`nRolling back to backup..." -ForegroundColor Yellow
        Copy-Item $backupPath docker-compose.prod.yml -Force
        docker-compose -f docker-compose.prod.yml up -d --force-recreate $serviceList
        throw "Rollback verification failed"
    }
}

# Show running containers
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Container Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
docker ps --filter "name=applylens-" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

Write-Host "`n✓ Rollback to $Version complete!" -ForegroundColor Green
Write-Host "Backup saved: $backupPath" -ForegroundColor Cyan
