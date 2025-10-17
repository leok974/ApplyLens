#!/usr/bin/env pwsh
# Sanity check script for dbt setup
# Verifies clean state and runs local builds

$ErrorActionPreference = "Stop"

Write-Host "`n🔍 dbt Sanity Check" -ForegroundColor Cyan
Write-Host "==================`n" -ForegroundColor Cyan

# Check current directory
$currentDir = Get-Location
if (-not $currentDir.Path.EndsWith("ApplyLens")) {
    Write-Host "⚠️  Run this script from the ApplyLens root directory" -ForegroundColor Yellow
    exit 1
}

# 1. Verify dbt_packages is not tracked
Write-Host "1️⃣  Checking git tracking..." -ForegroundColor Blue
$trackedPackages = git ls-files analytics/dbt/dbt_packages/ | Measure-Object -Line
if ($trackedPackages.Lines -gt 0) {
    Write-Host "   ❌ dbt_packages/ is tracked in git ($($trackedPackages.Lines) files)" -ForegroundColor Red
    Write-Host "   Run: git rm -r --cached analytics/dbt/dbt_packages/" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "   ✅ dbt_packages/ not tracked" -ForegroundColor Green
}

# 2. Verify .gitignore exists and is complete
Write-Host "`n2️⃣  Checking .gitignore..." -ForegroundColor Blue
$gitignoreChecks = @(
    "analytics/dbt/dbt_packages/",
    "analytics/dbt/target/",
    "analytics/dbt/package-lock.yml"
)

foreach ($pattern in $gitignoreChecks) {
    $found = Select-String -Path .gitignore -Pattern ([regex]::Escape($pattern)) -Quiet
    if ($found) {
        Write-Host "   ✅ $pattern" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Missing: $pattern" -ForegroundColor Red
        exit 1
    }
}

# 3. Verify packages.yml has pinned versions
Write-Host "`n3️⃣  Checking packages.yml..." -ForegroundColor Blue
$packagesYml = Get-Content analytics/dbt/packages.yml -Raw
if ($packagesYml -match 'version:\s+"\[') {
    Write-Host "   ❌ Found version ranges (use exact versions)" -ForegroundColor Red
    exit 1
} else {
    Write-Host "   ✅ Using pinned versions" -ForegroundColor Green
}

# 4. Clean and reinstall deps
Write-Host "`n4️⃣  Cleaning dbt artifacts..." -ForegroundColor Blue
Push-Location analytics/dbt
Remove-Item -Path dbt_packages, package-lock.yml, target, logs -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "   ✅ Cleaned: dbt_packages, package-lock.yml, target, logs" -ForegroundColor Green

Write-Host "`n5️⃣  Installing dbt packages..." -ForegroundColor Blue
try {
    $dbtPath = Get-Command dbt -ErrorAction Stop
    & dbt deps --target prod 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ❌ dbt deps failed" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Write-Host "   ✅ dbt deps successful" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  dbt not found in PATH (install with: pip install dbt-bigquery)" -ForegroundColor Yellow
    Write-Host "   ⏭️  Skipping dbt deps check" -ForegroundColor Yellow
}

# 5. Optional: Run dbt build
if ($dbtPath) {
    $runBuild = Read-Host "`n6️⃣  Run dbt build? (y/N)"
    if ($runBuild -eq 'y' -or $runBuild -eq 'Y') {
        Write-Host "`n   Running dbt run..." -ForegroundColor Blue
        & dbt run --target prod --select models/staging/fivetran models/marts/warehouse
        if ($LASTEXITCODE -ne 0) {
            Write-Host "   ❌ dbt run failed" -ForegroundColor Red
            Pop-Location
            exit 1
        }
        Write-Host "   ✅ dbt run successful" -ForegroundColor Green

        Write-Host "`n   Running dbt test..." -ForegroundColor Blue
        & dbt test --target prod --select models/staging/fivetran models/marts/warehouse
        if ($LASTEXITCODE -ne 0) {
            Write-Host "   ❌ dbt test failed" -ForegroundColor Red
            Pop-Location
            exit 1
        }
        Write-Host "   ✅ dbt test successful" -ForegroundColor Green
    }
}

Pop-Location

Write-Host "`n✅ All checks passed!" -ForegroundColor Green
Write-Host "`n📋 Quick commands:" -ForegroundColor Cyan
Write-Host "   Clean deps:  cd analytics/dbt && rm -rf dbt_packages package-lock.yml && dbt deps" -ForegroundColor White
Write-Host "   Local build: cd analytics/dbt && dbt run --target prod && dbt test --target prod" -ForegroundColor White
Write-Host "   CI trigger:  gh workflow run 'Warehouse Nightly'" -ForegroundColor White
Write-Host ""
