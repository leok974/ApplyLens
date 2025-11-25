# Import ApplyLens Overview Dashboard to Grafana
# Usage:
#   .\import_grafana_dashboard.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_TOKEN"
#   .\import_grafana_dashboard.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_TOKEN" -DatasourceName "My JSON API"

param(
    [Parameter(Mandatory=$true)]
    [string]$GrafanaUrl = "http://localhost:3000",

    [Parameter(Mandatory=$true)]
    [string]$ApiKey,

    [Parameter(Mandatory=$false)]
    [string]$DatasourceName = "ApplyLens API",

    [Parameter(Mandatory=$false)]
    [switch]$RemapDatasource
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Grafana Dashboard Import Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Path to dashboard JSON
$dashboardPath = Join-Path $PSScriptRoot "phase3_grafana_dashboard.json"

if (-not (Test-Path $dashboardPath)) {
    Write-Host "❌ Error: Dashboard JSON not found at: $dashboardPath" -ForegroundColor Red
    exit 1
}

Write-Host "📄 Reading dashboard from: $dashboardPath" -ForegroundColor White

try {
    $dashContent = Get-Content $dashboardPath -Raw
    $dashboard = $dashContent | ConvertFrom-Json

    Write-Host "✅ Dashboard loaded: $($dashboard.title)" -ForegroundColor Green
    Write-Host "   UID: $($dashboard.uid)" -ForegroundColor Gray
    Write-Host "   Panels: $($dashboard.panels.Count)" -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host "❌ Error parsing dashboard JSON: $_" -ForegroundColor Red
    exit 1
}

# Optional: Remap datasource UID
if ($RemapDatasource -or $DatasourceName -ne "ApplyLens API") {
    Write-Host "🔧 Remapping datasource to: $DatasourceName" -ForegroundColor Yellow

    try {
        $dsUrl = "$GrafanaUrl/api/datasources/name/$([uri]::EscapeDataString($DatasourceName))"
        $headers = @{ Authorization = "Bearer $ApiKey" }

        $datasource = Invoke-RestMethod -Uri $dsUrl -Headers $headers -Method Get
        $dsUid = $datasource.uid

        Write-Host "   Found datasource UID: $dsUid" -ForegroundColor Gray

        # Update all panel datasource UIDs
        $patchedCount = 0
        foreach ($panel in $dashboard.panels) {
            if ($panel.datasource) {
                $panel.datasource.uid = $dsUid
                $patchedCount++
            }
        }

        Write-Host "   ✅ Patched $patchedCount panels" -ForegroundColor Green
        Write-Host ""

        # Save patched version
        $patchedPath = Join-Path $PSScriptRoot "phase3_grafana_dashboard.patched.json"
        $dashboard | ConvertTo-Json -Depth 200 | Set-Content -Path $patchedPath -Encoding utf8
        Write-Host "   💾 Saved patched version to: phase3_grafana_dashboard.patched.json" -ForegroundColor Gray
        Write-Host ""

    } catch {
        Write-Host "⚠️  Warning: Could not fetch datasource '$DatasourceName'" -ForegroundColor Yellow
        Write-Host "   Error: $_" -ForegroundColor Gray
        Write-Host "   Proceeding with original dashboard..." -ForegroundColor Yellow
        Write-Host ""
    }
}

# Import dashboard
Write-Host "📤 Importing dashboard to Grafana..." -ForegroundColor White

try {
    $importUrl = "$GrafanaUrl/api/dashboards/import"
    $headers = @{
        Authorization = "Bearer $ApiKey"
        "Content-Type" = "application/json"
    }

    $importBody = @{
        dashboard = $dashboard
        overwrite = $true
        folderId  = 0
    } | ConvertTo-Json -Depth 100

    $result = Invoke-RestMethod -Uri $importUrl -Headers $headers -Method Post -Body $importBody

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✅ Dashboard Imported Successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Dashboard Details:" -ForegroundColor White
    Write-Host "  Title:   $($result.title)" -ForegroundColor Gray
    Write-Host "  UID:     $($result.uid)" -ForegroundColor Gray
    Write-Host "  URL:     $($result.url)" -ForegroundColor Cyan
    Write-Host "  Folder:  $($result.folderTitle)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "🌐 View Dashboard: $GrafanaUrl$($result.url)" -ForegroundColor Cyan
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "❌ Import Failed!" -ForegroundColor Red
    Write-Host ""

    if ($_.ErrorDetails.Message) {
        $errorObj = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($errorObj) {
            Write-Host "Error Message: $($errorObj.message)" -ForegroundColor Red
            Write-Host "Status: $($errorObj.status)" -ForegroundColor Red
        } else {
            Write-Host "Error Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "Error: $_" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Verify Grafana is running at: $GrafanaUrl" -ForegroundColor Gray
    Write-Host "  2. Check API key has 'Admin' or 'Editor' role" -ForegroundColor Gray
    Write-Host "  3. Ensure JSON API datasource plugin is installed" -ForegroundColor Gray
    Write-Host "     (grafana-cli plugins install marcusolsson-json-datasource)" -ForegroundColor Gray
    Write-Host ""

    exit 1
}

# Verify import
Write-Host "🔍 Verifying dashboard import..." -ForegroundColor White

try {
    $searchUrl = "$GrafanaUrl/api/search?query=$([uri]::EscapeDataString('ApplyLens Overview'))"
    $headers = @{ Authorization = "Bearer $ApiKey" }

    $searchResults = Invoke-RestMethod -Uri $searchUrl -Headers $headers -Method Get

    if ($searchResults.Count -gt 0) {
        Write-Host "✅ Dashboard found in Grafana!" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "⚠️  Warning: Dashboard not found in search results" -ForegroundColor Yellow
        Write-Host ""
    }

} catch {
    Write-Host "⚠️  Warning: Could not verify import (search failed)" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Open the dashboard in Grafana" -ForegroundColor White
Write-Host "  2. Update the 'api_base' variable if needed (default: http://127.0.0.1:8000)" -ForegroundColor White
Write-Host "  3. Verify all panels load data from your API" -ForegroundColor White
Write-Host "  4. If panels show 'No Data', check datasource configuration" -ForegroundColor White
Write-Host ""
