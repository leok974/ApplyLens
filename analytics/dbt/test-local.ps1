# Local dbt Testing Script for ApplyLens
# Run this to test dbt models locally with BigQuery

# IMPORTANT: Set your BigQuery credentials first!
# You need to set these environment variables before running dbt:

Write-Host "🔧 ApplyLens dbt Local Testing Setup" -ForegroundColor Cyan
Write-Host ""

# Check if environment variables are set
$bqProjectSet = [bool]$env:BQ_PROJECT
$bqJsonSet = [bool]$env:BQ_SA_JSON

if (-not $bqProjectSet) {
    Write-Host "❌ BQ_PROJECT not set" -ForegroundColor Red
    Write-Host ""
    Write-Host "Set it with:" -ForegroundColor Yellow
    Write-Host '  $env:BQ_PROJECT = "applylens-gmail-1759983601"' -ForegroundColor Gray
    Write-Host ""
}
else {
    Write-Host "✅ BQ_PROJECT is set ($($env:BQ_PROJECT.Length) chars)" -ForegroundColor Green
}

if (-not $bqJsonSet) {
    Write-Host "❌ BQ_SA_JSON not set" -ForegroundColor Red
    Write-Host ""
    Write-Host "Set it with:" -ForegroundColor Yellow
    Write-Host '  $env:BQ_SA_JSON = Get-Content "path\to\applylens-ci.json" -Raw' -ForegroundColor Gray
    Write-Host ""
    Write-Host "Or if you have the JSON in a variable:" -ForegroundColor Yellow
    Write-Host '  $env:BQ_SA_JSON = ''{ "type": "service_account", ... }''' -ForegroundColor Gray
    Write-Host ""
}
else {
    Write-Host "✅ BQ_SA_JSON is set ($($env:BQ_SA_JSON.Length) chars)" -ForegroundColor Green
}

# Add dbt to PATH if not already there
if (-not ($env:PATH -like "*Python313\Scripts*")) {
    Write-Host ""
    Write-Host "📦 Adding dbt to PATH..." -ForegroundColor Yellow
    $env:PATH = "C:\Users\$env:USERNAME\AppData\Roaming\Python\Python313\Scripts;$env:PATH"
}

Write-Host ""
Write-Host "📋 Available Commands:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Check dbt setup:" -ForegroundColor White
Write-Host "    dbt debug --profiles-dir ." -ForegroundColor Gray
Write-Host ""
Write-Host "  List models:" -ForegroundColor White
Write-Host "    dbt list --profiles-dir . --target prod" -ForegroundColor Gray
Write-Host ""
Write-Host "  Run ML forecasting models:" -ForegroundColor White
Write-Host "    dbt run --select 'ml:pred_*' --target prod --profiles-dir ." -ForegroundColor Gray
Write-Host ""
Write-Host "  Run anomaly detection:" -ForegroundColor White
Write-Host "    dbt run --select ml:anomaly_detection --target prod --profiles-dir ." -ForegroundColor Gray
Write-Host ""
Write-Host "  Run training models:" -ForegroundColor White
Write-Host "    dbt run --select 'ml:m_*' --target prod --profiles-dir ." -ForegroundColor Gray
Write-Host ""

# If credentials are set, offer to run debug
if ($bqProjectSet -and $bqJsonSet) {
    Write-Host "🚀 Ready to test! Run:" -ForegroundColor Green
    Write-Host "    cd D:\ApplyLens\analytics\dbt" -ForegroundColor Gray
    Write-Host "    dbt debug --profiles-dir ." -ForegroundColor Gray
    Write-Host ""
}
else {
    Write-Host "⚠️  Set the environment variables above, then run this script again." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "💡 Tips:" -ForegroundColor Cyan
Write-Host "  - Use --target dev for development (uses dev profile with 1GB limit)" -ForegroundColor Gray
Write-Host "  - Use --target prod for production (8 threads, 10GB limit, 600s timeout)" -ForegroundColor Gray
Write-Host "  - Use --target ci for CI/CD testing" -ForegroundColor Gray
Write-Host ""
