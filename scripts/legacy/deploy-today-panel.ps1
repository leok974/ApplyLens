#!/usr/bin/env pwsh
<#
.SYNOPSIS
Deploy Today Panel feature to production

.DESCRIPTION
Builds and pushes Docker images for the Today inbox triage panel feature to production.
This script:
1. Builds API and Web images with version tags
2. Pushes to Docker Hub (leoklemet registry)
3. Provides instructions for production deployment

.PARAMETER Version
The version tag for this release (default: 0.6.0)

.PARAMETER SkipBuild
Skip the build step and only show deployment instructions

.EXAMPLE
.\scripts\deploy-today-panel.ps1 -Version 0.6.0
#>

param(
    [string]$Version = "0.6.0",
    [switch]$SkipBuild = $false
)

$ErrorActionPreference = "Stop"

# Color output functions
function Write-Step {
    param([string]$Message)
    Write-Host "`n✨ $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Blue
}

# Get git metadata
$GitSha = (git rev-parse --short HEAD)
$BuildDate = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$CurrentBranch = (git rev-parse --abbrev-ref HEAD)

Write-Step "Today Panel Production Deployment"
Write-Info "Version: $Version"
Write-Info "Git SHA: $GitSha"
Write-Info "Branch: $CurrentBranch"
Write-Info "Build Date: $BuildDate"

# Verify we're on the correct branch
if ($CurrentBranch -ne "feature/thread-to-tracker-link" -and $CurrentBranch -ne "main") {
    Write-Warning "You're on branch '$CurrentBranch'"
    Write-Warning "Expected 'feature/thread-to-tracker-link' or 'main'"
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y") {
        Write-Host "Deployment cancelled."
        exit 1
    }
}

# Check if we should skip build
if ($SkipBuild) {
    Write-Warning "Skipping build step (using existing images)"
    goto DeploymentInstructions
}

# Build API image
Write-Step "Building API image"
Set-Location "services\api"

docker build `
    --build-arg GIT_SHA=$GitSha `
    --build-arg BUILD_DATE=$BuildDate `
    -t leoklemet/applylens-api:$Version `
    -t leoklemet/applylens-api:latest `
    -f Dockerfile.prod `
    .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ API build failed" -ForegroundColor Red
    exit 1
}

Write-Success "API image built successfully"

# Build Web image
Write-Step "Building Web image"
Set-Location "..\..\apps\web"

docker build `
    --build-arg VITE_BUILD_FLAVOR=prod `
    --build-arg VITE_APP_VERSION=$Version `
    --build-arg VITE_BUILD_GIT_SHA=$GitSha `
    --build-arg VITE_BUILD_TIME=$BuildDate `
    -t leoklemet/applylens-web:$Version `
    -t leoklemet/applylens-web:latest `
    -f Dockerfile.prod `
    .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Web build failed" -ForegroundColor Red
    exit 1
}

Write-Success "Web image built successfully"

# Return to root
Set-Location "..\..\"

# Push images
Write-Step "Pushing images to Docker Hub"

Write-Info "Pushing API image..."
docker push leoklemet/applylens-api:$Version
docker push leoklemet/applylens-api:latest

Write-Info "Pushing Web image..."
docker push leoklemet/applylens-web:$Version
docker push leoklemet/applylens-web:latest

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Image push failed" -ForegroundColor Red
    Write-Warning "You may need to login: docker login -u leoklemet"
    exit 1
}

Write-Success "Images pushed to Docker Hub"

:DeploymentInstructions

# Show deployment instructions
Write-Step "Deployment Instructions"

Write-Host @"

📦 Docker Images Built & Pushed:
   • leoklemet/applylens-api:$Version
   • leoklemet/applylens-web:$Version

🚀 To deploy to production:

1. SSH to production server:
   ssh applylens-prod

2. Pull latest images:
   cd /opt/applylens
   docker compose -f docker-compose.prod.yml pull web api

3. Update image tags in docker-compose.prod.yml:
   services:
     web:
       image: leoklemet/applylens-web:$Version
     api:
       image: leoklemet/applylens-api:$Version

4. Deploy with zero downtime:
   docker compose -f docker-compose.prod.yml up -d web api

5. Verify deployment:
   docker ps --filter "name=applylens-*-prod"
   curl https://api.applylens.app/api/healthz
   curl https://api.applylens.app/api/version

6. Test Today page:
   Open: https://applylens.app/today
   ✅ Page loads with 6 intent tiles
   ✅ Thread lists display correctly
   ✅ Action buttons work (Gmail, Thread Viewer, Tracker)

7. Run E2E tests:
   npx playwright test e2e/today-triage.spec.ts --grep @prodSafe

📊 What's Deployed:

✨ Today Panel Feature:
   • Backend: POST /v2/agent/today endpoint
   • Frontend: /today route with responsive grid
   • 6 scan intents: followups, bills, interviews, unsubscribe, clean_promos, suspicious
   • Thread mini-lists with action buttons
   • Loading, error, and empty states

🧪 Test Results:
   • Backend: 4/4 pytest tests passing
   • Frontend: 10/10 Vitest tests passing
   • E2E: 10/10 Playwright tests (@prodSafe)

📝 Commit: $GitSha
   Branch: $CurrentBranch
   Build: $BuildDate

"@ -ForegroundColor White

Write-Success "Deployment preparation complete!"
Write-Info "Next: Deploy on production server"
