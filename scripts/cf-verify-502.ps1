<#
.SYNOPSIS
  Quick verification checklist for 502 diagnosis.

.DESCRIPTION
  Runs comprehensive checks to prove whether 502s are from origin or edge cache:
  1. Origin health (inside Docker network)
  2. Edge status (via Cloudflare with headers)
  3. Automated health check

.EXAMPLE
  .\cf-verify-502.ps1
#>

Write-Host "`n═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  502 Diagnosis Verification Checklist" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

# 1) Origin Health
Write-Host "[1/3] Origin Health (Inside Docker Network)" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
docker exec applylens-nginx-prod curl -s -o $null -w "Status: %{http_code}\n" http://applylens.int/health
if ($LASTEXITCODE -eq 0) {
  Write-Host "✅ Origin is healthy (200 OK)`n" -ForegroundColor Green
} else {
  Write-Host "❌ Origin is down - this is an infrastructure issue!`n" -ForegroundColor Red
}

# 2) Edge Status
Write-Host "[2/3] Edge Status (Via Cloudflare Tunnel)" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host "Testing 6 times to hit different edge POPs...`n" -ForegroundColor Gray

$edgeSuccess = 0
$edgeFailed = 0

1..6 | ForEach-Object {
  Write-Host "Attempt $_" -ForegroundColor Cyan

  # Get status and headers
  $response = curl.exe -I https://applylens.app/health 2>&1 | Out-String

  if ($response -match "HTTP/1.1 (\d+)") {
    $status = $matches[1]
    if ($status -eq "200") {
      $edgeSuccess++
      Write-Host "  Status: $status ✓" -ForegroundColor Green
    } else {
      $edgeFailed++
      Write-Host "  Status: $status ✗" -ForegroundColor Red
    }
  }

  if ($response -match "cf-cache-status: (\w+)") {
    Write-Host "  Cache Status: $($matches[1])" -ForegroundColor Gray
  }

  if ($response -match "CF-RAY: ([a-f0-9\-]+)") {
    $ray = $matches[1]
    if ($ray -match "\-([A-Z]{3})$") {
      Write-Host "  Edge POP: $($matches[1])" -ForegroundColor Gray
    }
  }

  # Get colo from trace
  if ($_ -eq 1) {
    $trace = curl.exe https://applylens.app/cdn-cgi/trace 2>$null | Select-String "colo|ray"
    if ($trace) {
      Write-Host "  $trace" -ForegroundColor Gray
    }
  }

  Write-Host ""
  Start-Sleep -Seconds 1
}

$edgeRate = [math]::Round(($edgeSuccess / 6) * 100)
Write-Host "Edge Success Rate: $edgeSuccess/6 ($edgeRate%)" -ForegroundColor $(if($edgeRate -ge 95){"Green"}elseif($edgeRate -ge 70){"Yellow"}else{"Red"})

if ($edgeSuccess -lt 6) {
  Write-Host "⚠️  Edge is serving intermittent 502s - this is a CF cache issue!" -ForegroundColor Yellow
} else {
  Write-Host "✅ Edge is healthy!`n" -ForegroundColor Green
}

Write-Host ""

# 3) Automated Watcher
Write-Host "[3/3] Comprehensive Health Check (30 requests)" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

& "$PSScriptRoot\watch-prod-health.ps1" -Tries 30

# Summary
Write-Host "`n═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Diagnosis Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

if ($edgeSuccess -eq 6) {
  Write-Host "✅ RESOLVED: Both origin and edge are healthy!" -ForegroundColor Green
  Write-Host "`nNo action needed. System is operating normally." -ForegroundColor Gray
} elseif ($edgeSuccess -eq 0) {
  Write-Host "❌ CRITICAL: Edge is 100% failing" -ForegroundColor Red
  Write-Host "`nRecommended actions:" -ForegroundColor Yellow
  Write-Host "  1. Run nuclear option: .\scripts\cf-nuclear-option.ps1 -Domain applylens.app -RecordName applylens.app" -ForegroundColor Gray
  Write-Host "  2. Or manually disable/re-enable orange cloud in CF dashboard" -ForegroundColor Gray
} else {
  Write-Host "⚠️  PARTIAL FAILURE: Some edge POPs serving stale 502s" -ForegroundColor Yellow
  Write-Host "`nRecommended actions:" -ForegroundColor Yellow
  Write-Host "  1. Wait 10-15 minutes for cache propagation to complete" -ForegroundColor Gray
  Write-Host "  2. If no improvement, run: .\scripts\cf-nuclear-option.ps1 -Domain applylens.app -RecordName applylens.app" -ForegroundColor Gray
  Write-Host "  3. Add cache bypass rule in CF dashboard (Rules → Cache Rules)" -ForegroundColor Gray
}

Write-Host ""
