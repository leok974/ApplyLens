#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Show Cloudflare tunnel connector status

.DESCRIPTION
    Quick utility to display all cloudflared tunnel connectors and their status

.EXAMPLE
    .\show-tunnel-connectors.ps1

.EXAMPLE
    .\show-tunnel-connectors.ps1 -Detailed
#>

[CmdletBinding()]
param(
    [switch]$Detailed
)

Write-Host "🌐 Cloudflare Tunnel Connectors" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Get all cloudflared containers
$connectors = docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.CreatedAt}}" | Select-String "cloudflared"

if (-not $connectors) {
    Write-Host "❌ No cloudflared connectors found" -ForegroundColor Red
    exit 1
}

# Display table
Write-Host "Active Connectors:" -ForegroundColor Green
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}" | Select-String "cloudflared|NAMES"

Write-Host ""

# Count by status
$runningNames = docker ps --format "{{.Names}}" 2>&1
$totalNames = docker ps -a --format "{{.Names}}" 2>&1

$running = ($runningNames | Where-Object { $_ -match "cloudflared|cfd-" } | Measure-Object).Count
$total = ($totalNames | Where-Object { $_ -match "cloudflared|cfd-" } | Measure-Object).Count

Write-Host "Status: $running running / $total total" -ForegroundColor $(if ($running -eq 2) { "Green" } elseif ($running -gt 0) { "Yellow" } else { "Red" })

if ($Detailed) {
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host "📋 Detailed Information" -ForegroundColor Cyan
    Write-Host "=" * 80 -ForegroundColor Cyan

    $cloudflaredContainers = docker ps --format "{{.Names}}" | Select-String "cloudflared"

    foreach ($container in $cloudflaredContainers) {
        Write-Host ""
        Write-Host "Container: $container" -ForegroundColor Yellow
        Write-Host "-" * 80

        # Networks
        Write-Host "Networks:" -ForegroundColor Cyan
        $networks = docker inspect $container --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>&1
        if ($networks) {
            $networks -split '\s+' | Where-Object { $_ } | ForEach-Object {
                Write-Host "  - $_" -ForegroundColor Green
            }
        }

        # Tunnel info from logs
        Write-Host "`nRecent Activity (last 10 entries):" -ForegroundColor Cyan
        docker logs $container --tail 10 2>&1 | ForEach-Object {
            if ($_ -match "ERR") {
                Write-Host "  $_" -ForegroundColor Red
            } elseif ($_ -match "tunnel") {
                Write-Host "  $_" -ForegroundColor Green
            } else {
                Write-Host "  $_" -ForegroundColor Gray
            }
        }
    }
}

Write-Host ""
Write-Host "💡 Tips:" -ForegroundColor Cyan
Write-Host "  • View logs: docker logs cfd-a --tail 50 -f" -ForegroundColor Gray
Write-Host "  • Restart: docker-compose -f docker-compose.tunnel.yml restart" -ForegroundColor Gray
Write-Host "  • Full smoke test: .\scripts\check-applylens-prod.ps1" -ForegroundColor Gray
Write-Host ""
