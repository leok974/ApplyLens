# Test All Grafana Dashboard API Endpoints
# Quick verification that all dashboard endpoints return valid data

param(
    [Parameter(Mandatory=$false)]
    [string]$ApiBase = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Dashboard API Endpoint Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Testing endpoints at: $ApiBase" -ForegroundColor White
Write-Host ""

# Define endpoints
$endpoints = @(
    @{
        Name = "Divergence (24h)"
        Path = "/api/metrics/divergence-24h"
        ExpectedFields = @("divergence_pct", "status", "message")
    },
    @{
        Name = "Activity Daily"
        Path = "/api/metrics/activity-daily"
        ExpectedFields = @()  # Array of objects
        IsArray = $true
    },
    @{
        Name = "Top Senders (30d)"
        Path = "/api/metrics/top-senders-30d"
        ExpectedFields = @()  # Array of objects
        IsArray = $true
    },
    @{
        Name = "Categories (30d)"
        Path = "/api/metrics/categories-30d"
        ExpectedFields = @()  # Array of objects
        IsArray = $true
    }
)

$passed = 0
$failed = 0

foreach ($endpoint in $endpoints) {
    $url = "$ApiBase$($endpoint.Path)"
    $name = $endpoint.Name
    
    Write-Host "Testing: $name" -ForegroundColor Yellow
    Write-Host "  URL: $url" -ForegroundColor Gray
    
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
        
        if ($response.StatusCode -eq 200) {
            $data = $response.Content | ConvertFrom-Json
            
            # Validate structure
            if ($endpoint.IsArray) {
                if ($data -is [array]) {
                    Write-Host "  ✅ Status: 200 OK" -ForegroundColor Green
                    Write-Host "  📊 Records: $($data.Count)" -ForegroundColor Gray
                    
                    if ($data.Count -gt 0) {
                        $firstItem = $data[0]
                        $fields = ($firstItem | Get-Member -MemberType NoteProperty).Name
                        Write-Host "  📋 Fields: $($fields -join ', ')" -ForegroundColor Gray
                        
                        # Show sample
                        Write-Host "  🔍 Sample:" -ForegroundColor Gray
                        $firstItem | ConvertTo-Json -Compress | ForEach-Object {
                            $sample = $_
                            if ($sample.Length -gt 100) {
                                $sample = $sample.Substring(0, 97) + "..."
                            }
                            Write-Host "     $sample" -ForegroundColor DarkGray
                        }
                    }
                    
                    $passed++
                } else {
                    Write-Host "  ❌ Expected array but got: $($data.GetType().Name)" -ForegroundColor Red
                    $failed++
                }
            } else {
                Write-Host "  ✅ Status: 200 OK" -ForegroundColor Green
                
                # Check expected fields
                $missingFields = @()
                foreach ($field in $endpoint.ExpectedFields) {
                    if (-not ($data.PSObject.Properties.Name -contains $field)) {
                        $missingFields += $field
                    }
                }
                
                if ($missingFields.Count -eq 0) {
                    Write-Host "  ✅ All expected fields present" -ForegroundColor Green
                    
                    # Show values
                    foreach ($field in $endpoint.ExpectedFields) {
                        $value = $data.$field
                        if ($value -is [string] -and $value.Length -gt 50) {
                            $value = $value.Substring(0, 47) + "..."
                        }
                        Write-Host "     • $field = $value" -ForegroundColor DarkGray
                    }
                    
                    $passed++
                } else {
                    Write-Host "  ⚠️  Missing fields: $($missingFields -join ', ')" -ForegroundColor Yellow
                    Write-Host "     Available: $($data.PSObject.Properties.Name -join ', ')" -ForegroundColor DarkGray
                    $failed++
                }
            }
        } else {
            Write-Host "  ❌ Status: $($response.StatusCode)" -ForegroundColor Red
            $failed++
        }
        
    } catch {
        Write-Host "  ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
        
        if ($_.Exception.Response) {
            Write-Host "     Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor DarkRed
        }
        
        $failed++
    }
    
    Write-Host ""
}

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$total = $passed + $failed
$percentage = if ($total -gt 0) { [math]::Round(($passed / $total) * 100, 1) } else { 0 }

Write-Host "Total Tests:  $total" -ForegroundColor White
Write-Host "Passed:       $passed" -ForegroundColor Green
Write-Host "Failed:       $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host "Success Rate: $percentage%" -ForegroundColor $(if ($percentage -eq 100) { "Green" } elseif ($percentage -ge 75) { "Yellow" } else { "Red" })
Write-Host ""

if ($failed -eq 0) {
    Write-Host "✅ All endpoints ready for Grafana!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next step:" -ForegroundColor Cyan
    Write-Host "  .\import_grafana_dashboard.ps1 -GrafanaUrl 'http://localhost:3000' -ApiKey 'YOUR_TOKEN'" -ForegroundColor White
} else {
    Write-Host "⚠️  Some endpoints failed" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Cyan
    Write-Host "  1. Make sure API server is running: .\start_server.ps1" -ForegroundColor White
    Write-Host "  2. Check server logs for errors" -ForegroundColor White
    Write-Host "  3. Verify database has data" -ForegroundColor White
}

Write-Host ""

# Return exit code
exit $(if ($failed -eq 0) { 0 } else { 1 })
