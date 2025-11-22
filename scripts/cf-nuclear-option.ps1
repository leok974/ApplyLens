<#
.SYNOPSIS
  Nuclear Option: Toggle Cloudflare proxy off/on to force cache rebuild.

.DESCRIPTION
  Temporarily disables Cloudflare proxy (orange cloud → gray) for a DNS record,
  waits for propagation, then re-enables it. This forces all edge POPs to rebuild
  their cache from the origin, eliminating stale cached errors.

.PARAMETER Domain
  The domain name (e.g., "applylens.app")

.PARAMETER RecordName
  The specific DNS record to toggle (e.g., "applylens.app" for apex)

.PARAMETER WaitSeconds
  How long to wait with proxy disabled (default: 75 seconds)

.EXAMPLE
  $env:CF_API_TOKEN = "your_token_here"
  .\cf-nuclear-option.ps1 -Domain "applylens.app" -RecordName "applylens.app"
#>

param(
  [Parameter(Mandatory)][string]$Domain,
  [Parameter(Mandatory)][string]$RecordName,
  [int]$WaitSeconds = 75
)

# Load the CF DNS tools
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$scriptPath\cf-dns-tools.ps1"

if (-not $env:CF_API_TOKEN) {
  Write-Host "❌ Error: CF_API_TOKEN environment variable not set" -ForegroundColor Red
  Write-Host "Set it with: `$env:CF_API_TOKEN = `"your_token_here`"" -ForegroundColor Yellow
  exit 1
}

Write-Host "`n⚠️  NUCLEAR OPTION: Proxy Toggle" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host "This will:" -ForegroundColor White
Write-Host "  1. Disable Cloudflare proxy (orange → gray cloud)" -ForegroundColor Gray
Write-Host "  2. Wait $WaitSeconds seconds for DNS propagation" -ForegroundColor Gray
Write-Host "  3. Re-enable Cloudflare proxy (gray → orange cloud)" -ForegroundColor Gray
Write-Host "`nDuring step 2, your site will have:" -ForegroundColor Yellow
Write-Host "  ✓ Direct origin access (no edge caching)" -ForegroundColor Green
Write-Host "  ✗ No DDoS protection" -ForegroundColor Red
Write-Host "  ✗ No edge performance optimization" -ForegroundColor Red
Write-Host "`nRecord: $RecordName" -ForegroundColor Cyan
Write-Host ""

$confirmation = Read-Host "Continue? (yes/no)"
if ($confirmation -ne "yes") {
  Write-Host "Aborted." -ForegroundColor Yellow
  exit 0
}

try {
  # Step 1: Disable proxy
  Write-Host "`n[1/3] Disabling proxy (orange → gray)..." -ForegroundColor Cyan
  $result = Toggle-CFProxy -Domain $Domain -RecordName $RecordName -Proxied:$false
  Write-Host "✅ Proxy disabled" -ForegroundColor Green
  Write-Host "   Zone: $($result.zone_name) ($($result.zone_id))" -ForegroundColor Gray
  Write-Host "   Record: $($result.record_name) → $($result.content)" -ForegroundColor Gray
  Write-Host "   Proxied: $($result.new_proxied)" -ForegroundColor Gray

  # Step 2: Wait
  Write-Host "`n[2/3] Waiting $WaitSeconds seconds for DNS propagation..." -ForegroundColor Cyan
  Write-Host "   (Direct origin access active during this period)" -ForegroundColor Yellow

  for ($i = $WaitSeconds; $i -gt 0; $i--) {
    Write-Host "`r   Time remaining: $i seconds  " -NoNewline -ForegroundColor Gray
    Start-Sleep -Seconds 1
  }
  Write-Host ""

  # Step 3: Re-enable proxy
  Write-Host "`n[3/3] Re-enabling proxy (gray → orange)..." -ForegroundColor Cyan
  $result = Toggle-CFProxy -Domain $Domain -RecordName $RecordName -Proxied:$true
  Write-Host "✅ Proxy re-enabled" -ForegroundColor Green
  Write-Host "   Proxied: $($result.new_proxied)" -ForegroundColor Gray
  Write-Host "   All edge POPs will now rebuild cache from origin" -ForegroundColor Gray

  Write-Host "`n✅ Nuclear option complete!" -ForegroundColor Green
  Write-Host "`nNext steps:" -ForegroundColor Cyan
  Write-Host "  1. Wait 60-90 seconds for edge POPs to rebuild cache" -ForegroundColor Gray
  Write-Host "  2. Run: .\scripts\watch-prod-health.ps1" -ForegroundColor Gray
  Write-Host "  3. Expect success rate ≥95%" -ForegroundColor Gray

} catch {
  Write-Host "`n❌ Error: $_" -ForegroundColor Red
  Write-Host "`nIf proxy was disabled, manually re-enable it in Cloudflare dashboard!" -ForegroundColor Yellow
  exit 1
}
