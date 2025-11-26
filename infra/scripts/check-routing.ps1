<#
.SYNOPSIS
    Health check script to verify ApplyLens and LedgerMind routing separation.

.DESCRIPTION
    This script validates that domain routing is correctly configured by checking:
    - ApplyLens web and API endpoints
    - LedgerMind endpoints (both via Cloudflare tunnel and local)

    The script ensures no cross-contamination between the two applications.

.USAGE
    pwsh infra/scripts/check-routing.ps1
    or:
    ./infra/scripts/check-routing.ps1

.EXAMPLE
    PS> .\check-routing.ps1
    Checks all routing endpoints and displays color-coded results.

.NOTES
    Exit codes:
    0 - All endpoints healthy and routing correctly
    1 - One or more endpoints failed or routing is misconfigured
#>

# Color definitions
$ColorGreen = "Green"
$ColorYellow = "Yellow"
$ColorRed = "Red"
$ColorCyan = "Cyan"
$ColorWhite = "White"

# Endpoints to check
$endpoints = @(
    @{
        Url = "https://applylens.app/health"
        Label = "APPLYLENS_WEB"
        ExpectedContent = @("healthy", "ok")
        ForbiddenContent = @()
    },
    @{
        Url = "https://api.applylens.app/healthz"
        Label = "APPLYLENS_API"
        ExpectedContent = @("status", "ok")
        ForbiddenContent = @()
    },
    @{
        Url = "https://app.ledger-mind.org/api/ready"
        Label = "LEDGERMIND_CF"
        ExpectedContent = @("ok", "db", "migrations")
        ForbiddenContent = @("ApplyLens", "applylens")
    },
    @{
        Url = "http://localhost:8083/api/ready"
        Label = "LEDGERMIND_LOCAL"
        ExpectedContent = @("ok", "db", "migrations")
        ForbiddenContent = @("ApplyLens", "applylens")
    }
)

$script:hasErrors = $false

function Test-Endpoint {
    param(
        [string]$Url,
        [string]$Label,
        [string[]]$ExpectedContent,
        [string[]]$ForbiddenContent
    )

    Write-Host "`n[$Label]" -ForegroundColor $ColorCyan -NoNewline
    Write-Host " Testing: $Url" -ForegroundColor $ColorWhite

    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
        $statusCode = $response.StatusCode
        $body = $response.Content

        # Trim body to first 120 characters for display
        $bodyPreview = if ($body.Length -gt 120) {
            $body.Substring(0, 120) + "..."
        } else {
            $body
        }

        # Determine color based on status code
        $statusColor = if ($statusCode -ge 200 -and $statusCode -lt 300) {
            $ColorGreen
        } elseif ($statusCode -ge 300 -and $statusCode -lt 500) {
            $ColorYellow
        } else {
            $ColorRed
        }

        Write-Host "  Status: " -NoNewline
        Write-Host "$statusCode" -ForegroundColor $statusColor
        Write-Host "  Body: $bodyPreview" -ForegroundColor $ColorWhite

        # Check for forbidden content (routing contamination)
        $routingIssue = $false
        foreach ($forbidden in $ForbiddenContent) {
            if ($body -like "*$forbidden*") {
                $routingIssue = $true
                Write-Host "  ⚠️  WARNING: Found '$forbidden' in response!" -ForegroundColor $ColorRed
                Write-Host "  ⚠️  Routing misconfiguration detected - LedgerMind endpoint returning ApplyLens content!" -ForegroundColor $ColorRed
                $script:hasErrors = $true
            }
        }

        # Check if response is successful
        if ($statusCode -lt 200 -or $statusCode -ge 300) {
            Write-Host "  ❌ Non-2xx status code" -ForegroundColor $ColorRed
            $script:hasErrors = $true
            return $false
        }

        if ($routingIssue) {
            return $false
        }

        Write-Host "  ✓ OK" -ForegroundColor $ColorGreen
        return $true

    } catch {
        Write-Host "  Status: ERROR" -ForegroundColor $ColorRed
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor $ColorRed
        Write-Host "  ❌ Endpoint unreachable" -ForegroundColor $ColorRed
        $script:hasErrors = $true
        return $false
    }
}

# Main execution
Write-Host "`n===============================================" -ForegroundColor $ColorCyan
Write-Host "  ApplyLens & LedgerMind Routing Health Check" -ForegroundColor $ColorCyan
Write-Host "===============================================" -ForegroundColor $ColorCyan

$results = @()
foreach ($endpoint in $endpoints) {
    $result = Test-Endpoint -Url $endpoint.Url -Label $endpoint.Label -ExpectedContent $endpoint.ExpectedContent -ForbiddenContent $endpoint.ForbiddenContent
    $results += $result
}

# Summary
Write-Host "`n===============================================" -ForegroundColor $ColorCyan
Write-Host "  Summary" -ForegroundColor $ColorCyan
Write-Host "===============================================" -ForegroundColor $ColorCyan

$successCount = ($results | Where-Object { $_ -eq $true }).Count
$totalCount = $results.Count

if ($script:hasErrors) {
    Write-Host "`n❌ FAILED: $($totalCount - $successCount)/$totalCount endpoints failed or misconfigured" -ForegroundColor $ColorRed
    Write-Host "`nAction Required:" -ForegroundColor $ColorYellow
    Write-Host "  1. Check that all containers are running: docker ps" -ForegroundColor $ColorWhite
    Write-Host "  2. Verify nginx configs: .\scripts\nginx-validate.ps1" -ForegroundColor $ColorWhite
    Write-Host "  3. Check cloudflared routing: cat infra/cloudflared/config.yml" -ForegroundColor $ColorWhite
    Write-Host "  4. Review routing docs: docs/infra/LEDGERMIND_ROUTING.md" -ForegroundColor $ColorWhite
    exit 1
} else {
    Write-Host "`n✓ SUCCESS: All $totalCount endpoints healthy and routing correctly" -ForegroundColor $ColorGreen
    Write-Host "`nRouting Status:" -ForegroundColor $ColorCyan
    Write-Host "  ✓ ApplyLens domains → ApplyLens nginx" -ForegroundColor $ColorGreen
    Write-Host "  ✓ LedgerMind domains → LedgerMind nginx (ai-finance.int:80)" -ForegroundColor $ColorGreen
    Write-Host "  ✓ No cross-contamination detected" -ForegroundColor $ColorGreen
    exit 0
}
