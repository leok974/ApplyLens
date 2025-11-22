#!/usr/bin/env pwsh
# Build production Docker images with build metadata
# Usage: .\scripts\build-prod-images.ps1 -Version "0.5.2" [-Push]

param(
    [Parameter(Mandatory=$true)]
    [string]$Version,

    [switch]$Push,

    [string]$GitSha = "",

    [string]$Registry = "leoklemet"
)

# Get git SHA if not provided
if ([string]::IsNullOrEmpty($GitSha)) {
    $GitSha = (git rev-parse --short HEAD 2>$null)
    if (-not $GitSha) {
        $GitSha = "unknown"
    }
}

# Get build timestamp in ISO format
$BuildTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

Write-Host "🏗️  Building ApplyLens Production Images" -ForegroundColor Cyan
Write-Host "Version:   $Version" -ForegroundColor Green
Write-Host "Git SHA:   $GitSha" -ForegroundColor Green
Write-Host "Built At:  $BuildTime" -ForegroundColor Green
Write-Host "Registry:  $Registry" -ForegroundColor Green
Write-Host ""

# =============================================================================
# Build Web Image
# =============================================================================
Write-Host "📦 Building Web Image..." -ForegroundColor Yellow

$webArgs = @(
    "--build-arg", "VITE_BUILD_FLAVOR=prod",
    "--build-arg", "VITE_BUILD_VERSION=$Version",
    "--build-arg", "VITE_BUILD_GIT_SHA=$GitSha",
    "--build-arg", "VITE_BUILD_TIME=$BuildTime",
    "--build-arg", "GIT_SHA=$GitSha",
    "--build-arg", "BUILD_DATE=$BuildTime",
    "--build-arg", "APP_VERSION=$Version",
    "-t", "$Registry/applylens-web:$Version",
    "-t", "$Registry/applylens-web:latest",
    "-f", "apps/web/Dockerfile.prod",
    "apps/web"
)

& docker build @webArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Web build failed"
    exit 1
}

Write-Host "✅ Web image built successfully" -ForegroundColor Green
Write-Host ""

# =============================================================================
# Build API Image
# =============================================================================
Write-Host "📦 Building API Image..." -ForegroundColor Yellow

$apiArgs = @(
    "--build-arg", "GIT_SHA=$GitSha",
    "--build-arg", "BUILD_DATE=$BuildTime",
    "-t", "$Registry/applylens-api:$Version",
    "-t", "$Registry/applylens-api:latest",
    "-f", "services/api/Dockerfile.prod",
    "services/api"
)

& docker build @apiArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ API build failed"
    exit 1
}

Write-Host "✅ API image built successfully" -ForegroundColor Green
Write-Host ""

# =============================================================================
# Push to Registry (if requested)
# =============================================================================
if ($Push) {
    Write-Host "📤 Pushing images to registry..." -ForegroundColor Yellow

    & docker push "$Registry/applylens-web:$Version"
    & docker push "$Registry/applylens-web:latest"
    & docker push "$Registry/applylens-api:$Version"
    & docker push "$Registry/applylens-api:latest"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Images pushed successfully" -ForegroundColor Green
    } else {
        Write-Error "❌ Push failed"
        exit 1
    }
} else {
    Write-Host "ℹ️  Skipping push (use -Push to push to registry)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "🎉 Build complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Images created:" -ForegroundColor Cyan
Write-Host "  • $Registry/applylens-web:$Version" -ForegroundColor White
Write-Host "  • $Registry/applylens-web:latest" -ForegroundColor White
Write-Host "  • $Registry/applylens-api:$Version" -ForegroundColor White
Write-Host "  • $Registry/applylens-api:latest" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Update docker-compose.prod.yml to use version $Version" -ForegroundColor White
Write-Host "  2. Deploy: docker-compose -f docker-compose.prod.yml up -d" -ForegroundColor White
Write-Host "  3. Verify: curl http://localhost:8003/version" -ForegroundColor White
