#!/usr/bin/env pwsh
# Build and tag ApplyLens Docker images with proper versioning
#
# Usage:
#   .\scripts\build-and-tag.ps1 -Version "v0.4.2"
#   .\scripts\build-and-tag.ps1 -Version "v0.4.2" -Push
#
# This script:
# 1. Builds both API and Web images with version tags
# 2. Adds OCI metadata labels (git SHA, build date, source)
# 3. Tags with both :vX.Y.Z and :latest
# 4. Optionally pushes to registry
# 5. Shows digest for immutable pinning

param(
    [Parameter(Mandatory=$true)]
    [string]$Version,

    [Parameter(Mandatory=$false)]
    [switch]$Push,

    [Parameter(Mandatory=$false)]
    [switch]$SkipApi,

    [Parameter(Mandatory=$false)]
    [switch]$SkipWeb
)

$ErrorActionPreference = "Stop"

# Get build metadata
$gitSha = git rev-parse --short HEAD
$buildDate = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Building ApplyLens $Version" -ForegroundColor Cyan
Write-Host "Git SHA: $gitSha" -ForegroundColor Cyan
Write-Host "Build Date: $buildDate" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Build API
if (-not $SkipApi) {
    Write-Host "`n[1/2] Building API..." -ForegroundColor Yellow
    Push-Location services/api
    docker build `
        -t "leoklemet/applylens-api:$Version" `
        -t "leoklemet/applylens-api:latest" `
        -f Dockerfile.prod `
        --build-arg GIT_SHA=$gitSha `
        --build-arg BUILD_DATE=$buildDate `
        .
    if ($LASTEXITCODE -ne 0) { throw "API build failed" }
    Pop-Location
    Write-Host "✓ API built successfully" -ForegroundColor Green
}

# Build Web
if (-not $SkipWeb) {
    Write-Host "`n[2/2] Building Web..." -ForegroundColor Yellow
    Push-Location apps/web
    docker build `
        -t "leoklemet/applylens-web:$Version" `
        -t "leoklemet/applylens-web:latest" `
        -f Dockerfile.prod `
        --build-arg GIT_SHA=$gitSha `
        --build-arg BUILD_DATE=$buildDate `
        .
    if ($LASTEXITCODE -ne 0) { throw "Web build failed" }
    Pop-Location
    Write-Host "✓ Web built successfully" -ForegroundColor Green
}

# Show digests
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Image Digests (for immutable pinning):" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not $SkipApi) {
    $apiDigest = docker inspect --format='{{index .Id}}' "leoklemet/applylens-api:$Version"
    Write-Host "API:  $apiDigest" -ForegroundColor White
}

if (-not $SkipWeb) {
    $webDigest = docker inspect --format='{{index .Id}}' "leoklemet/applylens-web:$Version"
    Write-Host "Web:  $webDigest" -ForegroundColor White
}

# Push if requested
if ($Push) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Pushing to Registry..." -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    if (-not $SkipApi) {
        Write-Host "`nPushing API..." -ForegroundColor Yellow
        docker push "leoklemet/applylens-api:$Version"
        docker push "leoklemet/applylens-api:latest"
        Write-Host "✓ API pushed" -ForegroundColor Green
    }

    if (-not $SkipWeb) {
        Write-Host "`nPushing Web..." -ForegroundColor Yellow
        docker push "leoklemet/applylens-web:$Version"
        docker push "leoklemet/applylens-web:latest"
        Write-Host "✓ Web pushed" -ForegroundColor Green
    }

    # Show repo digests after push
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Repository Digests (use in compose):" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    if (-not $SkipApi) {
        $apiRepoDigest = docker inspect --format='{{index .RepoDigests 0}}' "leoklemet/applylens-api:$Version"
        Write-Host "API:  $apiRepoDigest" -ForegroundColor White
    }

    if (-not $SkipWeb) {
        $webRepoDigest = docker inspect --format='{{index .RepoDigests 0}}' "leoklemet/applylens-web:$Version"
        Write-Host "Web:  $webRepoDigest" -ForegroundColor White
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Update docker-compose.prod.yml with version: $Version" -ForegroundColor White
Write-Host "2. Deploy: docker-compose -f docker-compose.prod.yml up -d --force-recreate api web" -ForegroundColor White
Write-Host "3. Verify: curl http://localhost:8003/healthz && curl http://localhost:5175/" -ForegroundColor White

if (-not $Push) {
    Write-Host "`nTo push images, run with -Push flag" -ForegroundColor Yellow
}

Write-Host "`n✓ Build complete!" -ForegroundColor Green
