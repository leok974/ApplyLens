# Production Health Monitor
# Runs continuous health checks and exits non-zero if success rate < 95%
# Usage: .\watch-prod-health.ps1 [-Url "https://applylens.app/health"] [-Tries 30]

param(
    [string]$Url = "https://applylens.app/health",
    [int]$Tries = 30
)

Write-Host "Monitoring: $Url" -ForegroundColor Cyan
Write-Host "Running $Tries health checks..." -ForegroundColor Gray

$ok = 0
$failures = @()

1..$Tries | ForEach-Object {
    $attempt = $_
    $code = (& curl.exe -s -o $null -w "%{http_code}" $Url 2>&1)

    # Check for success - curl returns "200" or "ok" for successful requests
    if ($code -eq "200" -or $code -eq "ok") {
        $ok++
        Write-Host "." -NoNewline -ForegroundColor Green
    } else {
        $failures += "Attempt $attempt : $code"
        Write-Host "x" -NoNewline -ForegroundColor Red
    }

    Start-Sleep -Milliseconds 500
}

$rate = [math]::Round(($ok/$Tries)*100)

Write-Host "`n"
Write-Host "=== Health Check Results ===" -ForegroundColor Cyan
Write-Host "Success rate: $ok/$Tries ($rate%)" -ForegroundColor $(if($rate -ge 95){"Green"}elseif($rate -ge 80){"Yellow"}else{"Red"})

if ($failures.Count -gt 0) {
    Write-Host "`nFailures:" -ForegroundColor Yellow
    $failures | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
}

Write-Host ""

if ($rate -lt 95) {
    Write-Host "⚠ Health check failed - success rate below 95%" -ForegroundColor Red
    Write-Host "Action: Check Cloudflare cache and tunnel status" -ForegroundColor Yellow
    exit 2
} else {
    Write-Host "✓ Health check passed - all systems operational" -ForegroundColor Green
    exit 0
}
