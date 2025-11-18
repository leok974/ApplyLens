#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Smoke test for ApplyLens production deployment

.DESCRIPTION
    Performs quick health checks on the production ApplyLens deployment:
    - Main web application
    - API endpoints
    - Cloudflare tunnel connectors
    - Docker container status

.EXAMPLE
    .\check-applylens-prod.ps1

.EXAMPLE
    .\check-applylens-prod.ps1 -Verbose
#>

[CmdletBinding()]
param()

Write-Host "🔍 ApplyLens Production Smoke Test" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

$ErrorCount = 0
$WarningCount = 0

# Function to test HTTP endpoint
function Test-Endpoint {
    param(
        [string]$Url,
        [string]$Name,
        [int[]]$ExpectedStatusCodes = @(200)
    )

    Write-Host "Testing: $Name" -ForegroundColor Yellow
    Write-Host "  URL: $Url" -ForegroundColor Gray

    try {
        $response = curl.exe -I -s -H "Cache-Control: no-cache" --connect-timeout 10 $Url 2>&1
        $statusLine = $response | Select-String -Pattern "^HTTP" | Select-Object -First 1

        if ($statusLine -match "HTTP/[\d.]+ (\d+)") {
            $statusCode = [int]$matches[1]

            if ($statusCode -in $ExpectedStatusCodes) {
                Write-Host "  ✅ Status: $statusCode" -ForegroundColor Green
                return $true
            } else {
                Write-Host "  ❌ Status: $statusCode (expected: $($ExpectedStatusCodes -join ', '))" -ForegroundColor Red
                $script:ErrorCount++
                return $false
            }
        } else {
            Write-Host "  ❌ Failed to parse status code" -ForegroundColor Red
            Write-Host "  Response: $statusLine" -ForegroundColor Gray
            $script:ErrorCount++
            return $false
        }
    }
    catch {
        Write-Host "  ❌ Request failed: $_" -ForegroundColor Red
        $script:ErrorCount++
        return $false
    }
}

# Test 1: Main web application
Write-Host "`n📱 Web Application Tests" -ForegroundColor Cyan
Write-Host "-" * 60
Test-Endpoint -Url "https://applylens.app/" -Name "Main Page" | Out-Null
Test-Endpoint -Url "https://applylens.app/index.html" -Name "Index HTML" | Out-Null
Test-Endpoint -Url "https://www.applylens.app/" -Name "WWW Redirect" | Out-Null

# Test 2: API endpoints
Write-Host "`n🔌 API Endpoint Tests" -ForegroundColor Cyan
Write-Host "-" * 60
Test-Endpoint -Url "https://applylens.app/api/auth/me" -Name "Auth Endpoint" -ExpectedStatusCodes @(401, 405) | Out-Null
Test-Endpoint -Url "https://applylens.app/health" -Name "Health Check" | Out-Null

# Test 3: Direct origin test (bypass Cloudflare)
Write-Host "`n🎯 Origin Direct Access" -ForegroundColor Cyan
Write-Host "-" * 60
Write-Host "Testing: Web Container Direct" -ForegroundColor Yellow
Write-Host "  URL: http://localhost:5175/" -ForegroundColor Gray
try {
    $response = curl.exe -I -s --connect-timeout 5 http://localhost:5175/ 2>&1
    if ($response -match "200 OK") {
        Write-Host "  ✅ Origin healthy" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Origin response: $($response | Select-String '^HTTP')" -ForegroundColor Yellow
        $script:WarningCount++
    }
}
catch {
    Write-Host "  ⚠️  Origin not accessible (containers may be on different host)" -ForegroundColor Yellow
    $script:WarningCount++
}

# Test 4: Cloudflare tunnel connectors
Write-Host "`n🌐 Cloudflare Tunnel Connectors" -ForegroundColor Cyan
Write-Host "-" * 60

$connectors = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" 2>&1 | Select-String "cfd-"

if ($connectors) {
    Write-Host "Active Connectors:" -ForegroundColor Green
    $connectors | ForEach-Object {
        $line = $_ -split '\s{2,}'
        $name = $line[0]
        $status = $line[1]

        if ($status -match "Up") {
            Write-Host "  ✅ $name - $status" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $name - $status" -ForegroundColor Red
            $script:ErrorCount++
        }
    }

    # Check connector count
    $count = ($connectors | Measure-Object).Count
    if ($count -eq 2) {
        Write-Host "`n  ✅ Connector count: $count (expected: 2)" -ForegroundColor Green
    } elseif ($count -gt 2) {
        Write-Host "`n  ⚠️  Connector count: $count (expected: 2, possible duplicates)" -ForegroundColor Yellow
        $script:WarningCount++
    } else {
        Write-Host "`n  ❌ Connector count: $count (expected: 2, degraded redundancy)" -ForegroundColor Red
        $script:ErrorCount++
    }
} else {
    Write-Host "  ❌ No cloudflared connectors found!" -ForegroundColor Red
    $script:ErrorCount++
}

# Test 5: Production containers
Write-Host "`n🐳 Production Container Status" -ForegroundColor Cyan
Write-Host "-" * 60

$requiredContainers = @(
    "applylens-web-prod",
    "applylens-api-prod"
)

foreach ($containerName in $requiredContainers) {
    $container = docker ps --filter "name=$containerName" --format "{{.Names}}\t{{.Status}}" 2>&1

    if ($container -match "Up") {
        Write-Host "  ✅ $containerName - Running" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $containerName - Not running" -ForegroundColor Red
        $script:ErrorCount++
    }
}

# Test 6: Connector network configuration
Write-Host "`n🔗 Network Configuration" -ForegroundColor Cyan
Write-Host "-" * 60

$requiredNetworks = @("infra_net", "applylens_applylens-prod")

foreach ($connector in @("cfd-a", "cfd-b")) {
    Write-Host "Checking: $connector" -ForegroundColor Yellow

    $networks = docker inspect $connector --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>&1

    if ($networks) {
        $foundNetworks = $networks -split '\s+' | Where-Object { $_ }
        $missingNetworks = $requiredNetworks | Where-Object { $foundNetworks -notcontains $_ }

        if ($missingNetworks.Count -eq 0) {
            Write-Host "  ✅ Networks: $($foundNetworks -join ', ')" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Missing networks: $($missingNetworks -join ', ')" -ForegroundColor Red
            Write-Host "  Current networks: $($foundNetworks -join ', ')" -ForegroundColor Gray
            $script:ErrorCount++
        }
    } else {
        Write-Host "  ⚠️  Container not found or not running" -ForegroundColor Yellow
        $script:WarningCount++
    }
}

# Test 7: Recent connector errors
Write-Host "`n📋 Recent Connector Logs (Last 5 Minutes)" -ForegroundColor Cyan
Write-Host "-" * 60

foreach ($connector in @("cfd-a", "cfd-b")) {
    $errors = docker logs $connector --since 5m 2>&1 | Select-String "ERR|error|502|timeout"

    if ($errors) {
        $errorCount = ($errors | Measure-Object).Count
        Write-Host "  ⚠️  $connector - $errorCount error(s) found:" -ForegroundColor Yellow
        $errors | Select-Object -First 3 | ForEach-Object {
            Write-Host "    $($_ -replace '\s+', ' ')" -ForegroundColor Gray
        }
        if ($errorCount -gt 3) {
            Write-Host "    ... and $($errorCount - 3) more" -ForegroundColor Gray
        }
        $script:WarningCount++
    } else {
        Write-Host "  ✅ $connector - No errors in last 5 minutes" -ForegroundColor Green
    }
}

# Summary
Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "📊 Summary" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

if ($ErrorCount -eq 0 -and $WarningCount -eq 0) {
    Write-Host "✅ All checks passed!" -ForegroundColor Green
    exit 0
} elseif ($ErrorCount -eq 0) {
    Write-Host "⚠️  Warnings: $WarningCount" -ForegroundColor Yellow
    Write-Host "💡 Review warnings above" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "❌ Errors: $ErrorCount" -ForegroundColor Red
    if ($WarningCount -gt 0) {
        Write-Host "⚠️  Warnings: $WarningCount" -ForegroundColor Yellow
    }
    Write-Host "`n💡 Troubleshooting:" -ForegroundColor Cyan
    Write-Host "  1. Check connector logs: docker logs cfd-a --tail 50" -ForegroundColor Gray
    Write-Host "  2. Verify networks: docker inspect cfd-a --format '{{range `$k, `$v := .NetworkSettings.Networks}}{{`$k}} {{end}}'" -ForegroundColor Gray
    Write-Host "  3. Review runbook: infra\APPLYLENS_TUNNEL_RUNBOOK.md" -ForegroundColor Gray
    Write-Host "  4. Restart connectors: cd d:\ApplyLens && docker-compose -f docker-compose.tunnel.yml restart" -ForegroundColor Gray
    exit 1
}
