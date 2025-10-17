# Run all dbt models with production configuration
# Usage: .\run-all.ps1

# Set defaults
$env:GCP_PROJECT = if ($env:GCP_PROJECT) { $env:GCP_PROJECT } else { "applylens-gmail-1759983601" }
$env:RAW_DATASET = if ($env:RAW_DATASET) { $env:RAW_DATASET } else { "gmail" }
$env:GOOGLE_APPLICATION_CREDENTIALS = if ($env:GOOGLE_APPLICATION_CREDENTIALS) { $env:GOOGLE_APPLICATION_CREDENTIALS } else { "$PSScriptRoot\..\..\secrets\applylens-warehouse-key.json" }

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "  dbt Warehouse - Full Run" -ForegroundColor Cyan
Write-Host "==================================================`n" -ForegroundColor Cyan

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  GCP_PROJECT: $env:GCP_PROJECT"
Write-Host "  RAW_DATASET: $env:RAW_DATASET"
Write-Host "  CREDENTIALS: $env:GOOGLE_APPLICATION_CREDENTIALS`n"

# Change to dbt directory
Push-Location "$PSScriptRoot\..\dbt"

try {
    Write-Host "1. Installing dependencies..." -ForegroundColor Cyan
    dbt deps --target prod
    
    Write-Host "`n2. Running models..." -ForegroundColor Cyan
    dbt run --target prod --vars "raw_dataset: $env:RAW_DATASET" --select +marts.warehouse.*
    
    Write-Host "`n3. Running tests..." -ForegroundColor Cyan
    dbt test --target prod --vars "raw_dataset: $env:RAW_DATASET" --select +marts.warehouse.*
    
    Write-Host "`n==================================================" -ForegroundColor Green
    Write-Host "  ✅ Complete!" -ForegroundColor Green
    Write-Host "==================================================`n" -ForegroundColor Green
}
catch {
    Write-Host "`n❌ Error: $_" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
