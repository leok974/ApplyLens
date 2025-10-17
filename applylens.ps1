# ApplyLens Unified CLI - One-stop shop for local development
# Usage: .\applylens.ps1 [command]
# Commands: build, run-dbt, verify, status, all, help

param(
    [Parameter(Position=0)]
    [ValidateSet("build", "run-dbt", "verify", "status", "all", "help")]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host "`nApplyLens CLI - Unified Development Commands" -ForegroundColor Cyan
    Write-Host "============================================`n" -ForegroundColor Cyan
    Write-Host "Usage: .\applylens.ps1 [command]`n"
    Write-Host "Commands:" -ForegroundColor Yellow
    Write-Host "  build      Build & restart API (docker compose)"
    Write-Host "  run-dbt    Run full dbt pipeline (deps + run + test)"
    Write-Host "  verify     Run comprehensive verification checks"
    Write-Host "  status     Show one-line system status"
    Write-Host "  all        Run everything: build → dbt → verify → status"
    Write-Host "  help       Show this help message`n"
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\applylens.ps1 build          # Just rebuild API"
    Write-Host "  .\applylens.ps1 run-dbt        # Just run dbt"
    Write-Host "  .\applylens.ps1 all            # Full rebuild + verify`n"
}

function Build-API {
    Write-Host "`n=== BUILDING API ===" -ForegroundColor Cyan
    Write-Host "Stopping existing containers..." -ForegroundColor Gray
    docker compose -f docker-compose.prod.yml --env-file infra/.env.prod down api 2>$null
    
    Write-Host "Building fresh image..." -ForegroundColor Gray
    docker compose -f docker-compose.prod.yml --env-file infra/.env.prod build api
    
    Write-Host "Starting API..." -ForegroundColor Gray
    docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d api
    
    Write-Host "Waiting for API to be ready..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
    
    try {
        $health = Invoke-RestMethod 'http://localhost:8003/health' -ErrorAction Stop
        Write-Host "✅ API is running!" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ API may not be ready yet - check docker logs" -ForegroundColor Yellow
    }
}

function Run-DBT {
    Write-Host "`n=== RUNNING DBT ===" -ForegroundColor Cyan
    & "$PSScriptRoot\analytics\ops\run-all.ps1"
}

function Run-Verification {
    Write-Host "`n=== RUNNING VERIFICATION ===" -ForegroundColor Cyan
    & "$PSScriptRoot\analytics\ops\run-verification.ps1"
}

function Show-Status {
    Write-Host "`n=== SYSTEM STATUS ===" -ForegroundColor Cyan
    
    # API Status
    try {
        $freshness = Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/freshness' -ErrorAction Stop -TimeoutSec 3
        $apiStatus = if ($freshness.is_fresh) { "🟢" } else { "🟡" }
        $lag = $freshness.minutes_since_sync
    } catch {
        $apiStatus = "🔴"
        $lag = "N/A"
    }
    
    # Docker Services
    $dockerServices = @("applylens-api-prod", "applylens-elasticsearch-prod", "applylens-redis-prod")
    $dockerUp = 0
    foreach ($svc in $dockerServices) {
        $status = docker ps --filter "name=$svc" --format "{{.Status}}" 2>$null
        if ($status -match "Up") { $dockerUp++ }
    }
    $dockerStatus = if ($dockerUp -eq 3) { "🟢" } elseif ($dockerUp -gt 0) { "🟡" } else { "🔴" }
    
    # GitHub Actions
    try {
        $runs = gh run list --workflow "Warehouse Nightly" --limit 1 --json conclusion 2>$null | ConvertFrom-Json
        $ghStatus = if ($runs[0].conclusion -eq "success") { "🟢" } elseif ($runs[0].conclusion -eq "failure") { "🔴" } else { "🟡" }
    } catch {
        $ghStatus = "⚪"
    }
    
    # Print one-line status
    Write-Host "`nAPI: $apiStatus ($lag min) | Docker: $dockerStatus ($dockerUp/3) | GitHub: $ghStatus | Warehouse: Ready`n" -ForegroundColor White
}

# Execute command
try {
    switch ($Command) {
        "build" {
            Build-API
        }
        "run-dbt" {
            Run-DBT
        }
        "verify" {
            Run-Verification
        }
        "status" {
            Show-Status
        }
        "all" {
            Write-Host "`n🚀 RUNNING FULL PIPELINE" -ForegroundColor Cyan
            Write-Host "========================`n" -ForegroundColor Cyan
            Build-API
            Run-DBT
            Run-Verification
            Show-Status
            Write-Host "`n🎉 PIPELINE COMPLETE!" -ForegroundColor Green
        }
        "help" {
            Show-Help
        }
    }
} catch {
    Write-Host "`n❌ Error: $_" -ForegroundColor Red
    Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Gray
    exit 1
}
