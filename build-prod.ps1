#!/usr/bin/env pwsh
# =============================================================================
# ApplyLens Production Stack Builder
# =============================================================================
# This script builds and optionally starts the production stack
#
# Usage:
#   .\build-prod.ps1                    # Build only
#   .\build-prod.ps1 -Deploy            # Build and deploy
#   .\build-prod.ps1 -Deploy -Restart   # Build, deploy and restart all
# =============================================================================

param(
    [switch]$Deploy,
    [switch]$Restart,
    [switch]$Migrate,
    [switch]$Help
)

if ($Help) {
    Write-Host @"

ApplyLens Production Stack Builder

Usage:
  .\build-prod.ps1 [OPTIONS]

Options:
  -Deploy       Build and start the production stack
  -Restart      Force restart all services after deployment
  -Migrate      Run database migrations after deployment
  -Help         Show this help message

Examples:
  .\build-prod.ps1                      # Build only
  .\build-prod.ps1 -Deploy              # Build and start
  .\build-prod.ps1 -Deploy -Migrate     # Build, start, and migrate
  .\build-prod.ps1 -Deploy -Restart     # Build and force restart

Environment:
  Requires: infra/.env.prod with all secrets configured

"@
    exit 0
}

# =============================================================================
# Configuration
# =============================================================================
$ErrorActionPreference = "Stop"
$ComposeFile = "docker-compose.prod.yml"
$EnvFile = "infra/.env.prod"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Change to project root
Set-Location $ProjectRoot

Write-Host "`n=====================================================================" -ForegroundColor Cyan
Write-Host "  ApplyLens Production Stack Builder" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

# =============================================================================
# Pre-flight Checks
# =============================================================================
Write-Host "`n[1/5] Pre-flight checks..." -ForegroundColor Yellow

if (-not (Test-Path $EnvFile)) {
    Write-Host "❌ Error: $EnvFile not found!" -ForegroundColor Red
    Write-Host "   Copy infra/.env.example to infra/.env.prod and configure all secrets" -ForegroundColor Red
    exit 1
}

# Check for required secrets
Write-Host "   ✓ Environment file found: $EnvFile" -ForegroundColor Green

$RequiredSecrets = @(
    "POSTGRES_PASSWORD",
    "CLOUDFLARED_TUNNEL_TOKEN",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET"
)

$EnvContent = Get-Content $EnvFile -Raw
$MissingSecrets = @()

foreach ($secret in $RequiredSecrets) {
    if ($EnvContent -match "$secret=CHANGE_ME" -or $EnvContent -match "$secret=your-") {
        $MissingSecrets += $secret
    }
}

if ($MissingSecrets.Count -gt 0) {
    Write-Host "`n⚠️  WARNING: The following secrets need to be configured:" -ForegroundColor Yellow
    foreach ($secret in $MissingSecrets) {
        Write-Host "   - $secret" -ForegroundColor Yellow
    }
    Write-Host "`n   Edit $EnvFile before deploying to production!" -ForegroundColor Yellow
    
    if ($Deploy) {
        Write-Host "`n   Continue anyway? (y/N): " -NoNewline -ForegroundColor Yellow
        $response = Read-Host
        if ($response -ne 'y' -and $response -ne 'Y') {
            Write-Host "   Deployment cancelled." -ForegroundColor Red
            exit 1
        }
    }
}

# =============================================================================
# Build Images
# =============================================================================
Write-Host "`n[2/5] Building production images..." -ForegroundColor Yellow

$BuildArgs = @(
    "-f", $ComposeFile,
    "--env-file", $EnvFile,
    "build",
    "--no-cache"
)

Write-Host "   Command: docker compose $($BuildArgs -join ' ')" -ForegroundColor Gray

try {
    docker compose @BuildArgs
    Write-Host "   ✓ Build completed successfully" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Build failed: $_" -ForegroundColor Red
    exit 1
}

# =============================================================================
# Deployment
# =============================================================================
if ($Deploy) {
    Write-Host "`n[3/5] Deploying production stack..." -ForegroundColor Yellow
    
    if ($Restart) {
        Write-Host "   Stopping existing containers..." -ForegroundColor Gray
        docker compose -f $ComposeFile --env-file $EnvFile down
    }
    
    Write-Host "   Starting services..." -ForegroundColor Gray
    docker compose -f $ComposeFile --env-file $EnvFile up -d
    
    Write-Host "   ✓ Services started" -ForegroundColor Green
    
    # Wait for services to be ready
    Write-Host "`n   Waiting for services to be healthy..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
    
} else {
    Write-Host "`n[3/5] Skipping deployment (build only)" -ForegroundColor Gray
}

# =============================================================================
# Database Migrations
# =============================================================================
if ($Deploy -and $Migrate) {
    Write-Host "`n[4/5] Running database migrations..." -ForegroundColor Yellow
    
    try {
        docker compose -f $ComposeFile --env-file $EnvFile exec -T api alembic upgrade head
        Write-Host "   ✓ Migrations completed" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠️  Warning: Migrations failed: $_" -ForegroundColor Yellow
        Write-Host "   You may need to run migrations manually:" -ForegroundColor Yellow
        Write-Host "   docker compose -f $ComposeFile --env-file $EnvFile exec api alembic upgrade head" -ForegroundColor Gray
    }
} else {
    Write-Host "`n[4/5] Skipping database migrations" -ForegroundColor Gray
}

# =============================================================================
# Status Check
# =============================================================================
Write-Host "`n[5/5] Status check..." -ForegroundColor Yellow

if ($Deploy) {
    Write-Host "`n   Service Status:" -ForegroundColor Gray
    docker compose -f $ComposeFile ps
    
    Write-Host "`n   Testing endpoints..." -ForegroundColor Gray
    
    $Tests = @(
        @{Name="Health Check"; Url="http://localhost/health"},
        @{Name="API Health"; Url="http://localhost/api/healthz"}
    )
    
    foreach ($test in $Tests) {
        try {
            $response = Invoke-WebRequest -Uri $test.Url -Method GET -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Host "   ✓ $($test.Name): OK" -ForegroundColor Green
            } else {
                Write-Host "   ⚠️  $($test.Name): HTTP $($response.StatusCode)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "   ❌ $($test.Name): Failed" -ForegroundColor Red
        }
    }
}

# =============================================================================
# Summary
# =============================================================================
Write-Host "`n=====================================================================" -ForegroundColor Cyan
Write-Host "  Build Complete!" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

if ($Deploy) {
    Write-Host "`n✅ Production stack is running!" -ForegroundColor Green
    Write-Host "`nAccess URLs:" -ForegroundColor Cyan
    Write-Host "  • Web:        http://localhost/web/" -ForegroundColor White
    Write-Host "  • API Docs:   http://localhost/docs" -ForegroundColor White
    Write-Host "  • Health:     http://localhost/health" -ForegroundColor White
    Write-Host "  • Prometheus: http://localhost/prometheus/" -ForegroundColor White
    Write-Host "  • Grafana:    http://localhost/grafana/" -ForegroundColor White
    Write-Host "  • Kibana:     http://localhost/kibana/" -ForegroundColor White
    
    Write-Host "`nUseful Commands:" -ForegroundColor Cyan
    Write-Host "  • View logs:    docker compose -f $ComposeFile logs -f" -ForegroundColor Gray
    Write-Host "  • Stop stack:   docker compose -f $ComposeFile down" -ForegroundColor Gray
    Write-Host "  • Migrations:   docker compose -f $ComposeFile exec api alembic upgrade head" -ForegroundColor Gray
    
    if (-not $Migrate) {
        Write-Host "`n⚠️  Don't forget to run migrations!" -ForegroundColor Yellow
        Write-Host "   docker compose -f $ComposeFile --env-file $EnvFile exec api alembic upgrade head" -ForegroundColor Gray
    }
} else {
    Write-Host "`n✅ Images built successfully!" -ForegroundColor Green
    Write-Host "`nTo deploy:" -ForegroundColor Cyan
    Write-Host "  .\build-prod.ps1 -Deploy" -ForegroundColor White
    Write-Host "`nOr manually:" -ForegroundColor Cyan
    Write-Host "  docker compose -f $ComposeFile --env-file $EnvFile up -d" -ForegroundColor Gray
}

Write-Host ""
