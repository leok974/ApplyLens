#!/usr/bin/env pwsh
# dbt Run All - PowerShell
# Usage: .\analytics\dbt\run_all.ps1
#
# Runs full dbt pipeline: deps → seed → run → test
# Sets working directory to analytics/dbt automatically

param(
    [switch]$SkipTests,
    [switch]$FullRefresh
)

$ErrorActionPreference = "Stop"
$dbtDir = Join-Path $PSScriptRoot "."

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "dbt Run All - ApplyLens Analytics" -ForegroundColor Cyan
Write-Host "Working directory: $dbtDir" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Push-Location $dbtDir

try {
    # Step 1: Install dependencies
    Write-Host "[1/4] Installing dbt dependencies..." -ForegroundColor Yellow
    dbt deps
    if ($LASTEXITCODE -ne 0) {
        throw "dbt deps failed"
    }
    Write-Host "✓ Dependencies installed`n" -ForegroundColor Green

    # Step 2: Load seed data
    Write-Host "[2/4] Loading seed data..." -ForegroundColor Yellow
    if ($FullRefresh) {
        dbt seed --full-refresh
    } else {
        dbt seed
    }
    if ($LASTEXITCODE -ne 0) {
        throw "dbt seed failed"
    }
    Write-Host "✓ Seeds loaded`n" -ForegroundColor Green

    # Step 3: Run models
    Write-Host "[3/4] Running dbt models..." -ForegroundColor Yellow
    if ($FullRefresh) {
        dbt run --full-refresh
    } else {
        dbt run
    }
    if ($LASTEXITCODE -ne 0) {
        throw "dbt run failed"
    }
    Write-Host "✓ Models built`n" -ForegroundColor Green

    # Step 4: Run tests (unless skipped)
    if (!$SkipTests) {
        Write-Host "[4/4] Running dbt tests..." -ForegroundColor Yellow
        dbt test
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Some tests failed (non-blocking)"
        } else {
            Write-Host "✓ All tests passed`n" -ForegroundColor Green
        }
    } else {
        Write-Host "[4/4] Skipping tests (--SkipTests flag)`n" -ForegroundColor Gray
    }

    Write-Host "========================================" -ForegroundColor Green
    Write-Host "dbt pipeline complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green

} catch {
    Write-Host "`n========================================" -ForegroundColor Red
    Write-Host "dbt pipeline failed: $_" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}
