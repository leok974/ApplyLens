# Verify Grafana Setup for ApplyLens Dashboard
# Usage: .\verify_grafana_setup.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_TOKEN"

param(
    [Parameter(Mandatory=$false)]
    [string]$GrafanaUrl = "http://localhost:3000",
    
    [Parameter(Mandatory=$false)]
    [string]$ApiKey
)

$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Grafana Setup Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check 1: Grafana is reachable
Write-Host "1️⃣  Checking Grafana connectivity..." -ForegroundColor White
try {
    $response = Invoke-WebRequest -Uri "$GrafanaUrl/api/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        $health = $response.Content | ConvertFrom-Json
        Write-Host "   ✅ Grafana is running" -ForegroundColor Green
        Write-Host "      Version: $($health.version)" -ForegroundColor Gray
        Write-Host "      Database: $($health.database)" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ Cannot reach Grafana at $GrafanaUrl" -ForegroundColor Red
    Write-Host "      Make sure Grafana is running" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
Write-Host ""

# Check 2: API key is valid (if provided)
if ($ApiKey) {
    Write-Host "2️⃣  Checking API key..." -ForegroundColor White
    try {
        $headers = @{ Authorization = "Bearer $ApiKey" }
        $response = Invoke-RestMethod -Uri "$GrafanaUrl/api/org" -Headers $headers
        Write-Host "   ✅ API key is valid" -ForegroundColor Green
        Write-Host "      Organization: $($response.name)" -ForegroundColor Gray
        Write-Host "      ID: $($response.id)" -ForegroundColor Gray
    } catch {
        Write-Host "   ❌ API key authentication failed" -ForegroundColor Red
        Write-Host "      Please check your API key" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   How to create an API key:" -ForegroundColor Cyan
        Write-Host "      1. Go to Configuration → API Keys" -ForegroundColor Gray
        Write-Host "      2. Click 'New API Key'" -ForegroundColor Gray
        Write-Host "      3. Give it 'Admin' or 'Editor' role" -ForegroundColor Gray
        Write-Host "      4. Copy the generated key" -ForegroundColor Gray
        Write-Host ""
        exit 1
    }
    Write-Host ""
    
    # Check 3: JSON API datasource plugin
    Write-Host "3️⃣  Checking for JSON API datasource plugin..." -ForegroundColor White
    try {
        $plugins = Invoke-RestMethod -Uri "$GrafanaUrl/api/plugins" -Headers $headers
        $jsonPlugin = $plugins | Where-Object { $_.id -eq "marcusolsson-json-datasource" }
        
        if ($jsonPlugin) {
            Write-Host "   ✅ JSON API datasource plugin is installed" -ForegroundColor Green
            Write-Host "      Version: $($jsonPlugin.info.version)" -ForegroundColor Gray
            Write-Host "      Enabled: $($jsonPlugin.enabled)" -ForegroundColor Gray
        } else {
            Write-Host "   ❌ JSON API datasource plugin not found" -ForegroundColor Red
            Write-Host ""
            Write-Host "   Install it with:" -ForegroundColor Yellow
            Write-Host "      grafana-cli plugins install marcusolsson-json-datasource" -ForegroundColor Cyan
            Write-Host "   Then restart Grafana" -ForegroundColor Yellow
            Write-Host ""
        }
    } catch {
        Write-Host "   ⚠️  Could not check plugins (requires Admin access)" -ForegroundColor Yellow
    }
    Write-Host ""
    
    # Check 4: Datasources
    Write-Host "4️⃣  Checking datasources..." -ForegroundColor White
    try {
        $datasources = Invoke-RestMethod -Uri "$GrafanaUrl/api/datasources" -Headers $headers
        $jsonDatasources = $datasources | Where-Object { $_.type -eq "marcusolsson-json-datasource" }
        
        if ($jsonDatasources.Count -gt 0) {
            Write-Host "   ✅ Found $($jsonDatasources.Count) JSON API datasource(s):" -ForegroundColor Green
            foreach ($ds in $jsonDatasources) {
                Write-Host "      • $($ds.name) (UID: $($ds.uid))" -ForegroundColor Gray
            }
            
            $applyLensDS = $jsonDatasources | Where-Object { $_.name -eq "ApplyLens API" }
            if ($applyLensDS) {
                Write-Host ""
                Write-Host "   ✅ 'ApplyLens API' datasource exists!" -ForegroundColor Green
                Write-Host "      UID: $($applyLensDS.uid)" -ForegroundColor Gray
                Write-Host "      URL: $($applyLensDS.url)" -ForegroundColor Gray
            } else {
                Write-Host ""
                Write-Host "   ⚠️  No datasource named 'ApplyLens API' found" -ForegroundColor Yellow
                Write-Host "      You'll need to remap the datasource after import" -ForegroundColor Yellow
                Write-Host "      Use: .\import_grafana_dashboard.ps1 -RemapDatasource -DatasourceName '$($jsonDatasources[0].name)'" -ForegroundColor Cyan
            }
        } else {
            Write-Host "   ⚠️  No JSON API datasources configured" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "   Create one:" -ForegroundColor Cyan
            Write-Host "      1. Go to Configuration → Data Sources" -ForegroundColor Gray
            Write-Host "      2. Click 'Add data source'" -ForegroundColor Gray
            Write-Host "      3. Search for 'JSON API'" -ForegroundColor Gray
            Write-Host "      4. Name it 'ApplyLens API'" -ForegroundColor Gray
            Write-Host "      5. No URL needed (uses panel-specific URLs)" -ForegroundColor Gray
            Write-Host ""
        }
    } catch {
        Write-Host "   ⚠️  Could not list datasources" -ForegroundColor Yellow
    }
    Write-Host ""
    
    # Check 5: API endpoints
    Write-Host "5️⃣  Checking API endpoints..." -ForegroundColor White
    $apiBase = "http://127.0.0.1:8000"
    $endpoints = @(
        "/api/metrics/divergence-24h",
        "/api/metrics/activity-daily",
        "/api/metrics/top-senders-30d",
        "/api/metrics/categories-30d"
    )
    
    $allGood = $true
    foreach ($endpoint in $endpoints) {
        $url = "$apiBase$endpoint"
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                Write-Host "   ✅ $endpoint" -ForegroundColor Green
            } else {
                Write-Host "   ❌ $endpoint (Status: $($response.StatusCode))" -ForegroundColor Red
                $allGood = $false
            }
        } catch {
            Write-Host "   ❌ $endpoint (Not reachable)" -ForegroundColor Red
            $allGood = $false
        }
    }
    
    if (-not $allGood) {
        Write-Host ""
        Write-Host "   ⚠️  Some API endpoints are not responding" -ForegroundColor Yellow
        Write-Host "      Make sure the API server is running on port 8000" -ForegroundColor Yellow
    }
    Write-Host ""
    
} else {
    Write-Host "2️⃣  API Key not provided - skipping authentication checks" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   To run full verification, provide an API key:" -ForegroundColor Cyan
    Write-Host "      .\verify_grafana_setup.ps1 -ApiKey 'YOUR_API_TOKEN'" -ForegroundColor Cyan
    Write-Host ""
}

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($ApiKey) {
    Write-Host "Ready to import? Run:" -ForegroundColor White
    Write-Host "  .\import_grafana_dashboard.ps1 -GrafanaUrl '$GrafanaUrl' -ApiKey 'YOUR_API_TOKEN'" -ForegroundColor Cyan
} else {
    Write-Host "Next steps:" -ForegroundColor White
    Write-Host "  1. Create a Grafana API key (Configuration → API Keys)" -ForegroundColor Gray
    Write-Host "  2. Run this script with -ApiKey parameter for full verification" -ForegroundColor Gray
    Write-Host "  3. Run import_grafana_dashboard.ps1 to import the dashboard" -ForegroundColor Gray
}
Write-Host ""
