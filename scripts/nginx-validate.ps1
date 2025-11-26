<#
.SYNOPSIS
    Validates and optionally reloads ApplyLens nginx configuration.

.DESCRIPTION
    This script tests the nginx configuration in the applylens-nginx container
    and optionally reloads it if valid. Use this before deploying config changes
    to production to avoid downtime.

.PARAMETER Reload
    If specified, reloads nginx after successful validation.

.PARAMETER Container
    The nginx container name to validate. Defaults to "applylens-nginx".

.EXAMPLE
    .\nginx-validate.ps1
    Tests nginx configuration without reloading.

.EXAMPLE
    .\nginx-validate.ps1 -Reload
    Tests nginx configuration and reloads if valid.

.EXAMPLE
    .\nginx-validate.ps1 -Container "applylens-nginx-prod" -Reload
    Tests and reloads configuration in a specific container.
#>

param(
    [switch]$Reload,
    [string]$Container = "applylens-nginx"
)

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Cyan = "Cyan"

Write-Host "`n=== ApplyLens nginx Configuration Validator ===" -ForegroundColor $Cyan
Write-Host "Container: $Container`n" -ForegroundColor $Cyan

# Check if container exists and is running
Write-Host "Checking container status..." -ForegroundColor $Yellow
$containerStatus = docker ps --filter "name=$Container" --format "{{.Status}}" 2>$null

if (-not $containerStatus) {
    Write-Host "❌ Error: Container '$Container' is not running or does not exist." -ForegroundColor $Red
    Write-Host "`nTip: Check running containers with: docker ps" -ForegroundColor $Yellow
    exit 1
}

Write-Host "✓ Container is running: $containerStatus`n" -ForegroundColor $Green

# Test nginx configuration
Write-Host "Testing nginx configuration..." -ForegroundColor $Yellow
$testOutput = docker exec $Container nginx -t 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ nginx configuration is valid!`n" -ForegroundColor $Green
    Write-Host $testOutput -ForegroundColor $Green

    # Show server_name directives for verification
    Write-Host "`n--- Configured Hostnames ---" -ForegroundColor $Cyan
    docker exec $Container nginx -T 2>&1 | Select-String "server_name" | ForEach-Object {
        $line = $_.Line.Trim()
        if ($line -match "server_name\s+_;") {
            Write-Host "⚠️  $line" -ForegroundColor $Yellow
            Write-Host "   WARNING: Catch-all server_name detected! This may intercept other domains." -ForegroundColor $Yellow
        } elseif ($line -match "server_name.*ledger-mind") {
            Write-Host "⚠️  $line" -ForegroundColor $Yellow
            Write-Host "   WARNING: LedgerMind domain detected! ApplyLens nginx should not handle these." -ForegroundColor $Yellow
        } else {
            Write-Host "✓  $line" -ForegroundColor $Green
        }
    }

    if ($Reload) {
        Write-Host "`nReloading nginx configuration..." -ForegroundColor $Yellow
        $reloadOutput = docker exec $Container nginx -s reload 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ nginx reloaded successfully!`n" -ForegroundColor $Green
            Write-Host "Changes are now live in the container." -ForegroundColor $Green
        } else {
            Write-Host "❌ Error reloading nginx:" -ForegroundColor $Red
            Write-Host $reloadOutput -ForegroundColor $Red
            exit 1
        }
    } else {
        Write-Host "`nℹ️  To reload nginx with these changes, run:" -ForegroundColor $Cyan
        Write-Host "   .\scripts\nginx-validate.ps1 -Reload`n" -ForegroundColor $Cyan
    }

} else {
    Write-Host "❌ nginx configuration has errors:`n" -ForegroundColor $Red
    Write-Host $testOutput -ForegroundColor $Red
    Write-Host "`nPlease fix the configuration errors before reloading." -ForegroundColor $Yellow
    exit 1
}

Write-Host "`n=== Validation Complete ===" -ForegroundColor $Cyan
exit 0
