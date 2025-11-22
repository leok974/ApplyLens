<#
.SYNOPSIS
  Cloudflare cache and development mode management script.

.DESCRIPTION
  One-tap cache purge and development mode toggle for Cloudflare zones.
  Requires: CF_API_TOKEN environment variable with Cache Purge and Zone Settings permissions.

.PARAMETER ZoneId
  Cloudflare Zone ID (get from CF-PrintIds in cf-dns-tools.ps1)

.PARAMETER EnableDev
  Enable Development Mode (bypasses cache for 3 hours)

.PARAMETER DisableDev
  Disable Development Mode

.PARAMETER PurgeAll
  Purge all cached files for the zone

.EXAMPLE
  $env:CF_API_TOKEN = "your_token_here"
  .\cf-cache-tools.ps1 -ZoneId "abc123" -PurgeAll
  .\cf-cache-tools.ps1 -ZoneId "abc123" -EnableDev
  .\cf-cache-tools.ps1 -ZoneId "abc123" -DisableDev
#>

param(
  [Parameter(Mandatory)][string]$ZoneId,
  [switch]$EnableDev,
  [switch]$DisableDev,
  [switch]$PurgeAll
)

if (-not $env:CF_API_TOKEN) {
  Write-Host "❌ Error: CF_API_TOKEN environment variable not set" -ForegroundColor Red
  Write-Host "Set it with: `$env:CF_API_TOKEN = `"your_token_here`"" -ForegroundColor Yellow
  exit 1
}

$headers = @{
  "Authorization" = "Bearer $env:CF_API_TOKEN"
  "Content-Type"  = "application/json"
}

if ($EnableDev) {
  Write-Host "`n🔧 Enabling Development Mode..." -ForegroundColor Cyan
  try {
    $resp = Invoke-RestMethod -Method PATCH -Headers $headers `
      -Uri "https://api.cloudflare.com/client/v4/zones/$ZoneId/settings/development_mode" `
      -Body '{"value":"on"}'

    if ($resp.success) {
      Write-Host "✅ Development Mode enabled (active for 3 hours)" -ForegroundColor Green
      Write-Host "   All caching will be bypassed for this period" -ForegroundColor Gray
    } else {
      Write-Host "❌ Failed: $($resp.errors | ConvertTo-Json)" -ForegroundColor Red
    }
  } catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
  }
}

if ($DisableDev) {
  Write-Host "`n🔧 Disabling Development Mode..." -ForegroundColor Cyan
  try {
    $resp = Invoke-RestMethod -Method PATCH -Headers $headers `
      -Uri "https://api.cloudflare.com/client/v4/zones/$ZoneId/settings/development_mode" `
      -Body '{"value":"off"}'

    if ($resp.success) {
      Write-Host "✅ Development Mode disabled" -ForegroundColor Green
      Write-Host "   Normal caching rules now apply" -ForegroundColor Gray
    } else {
      Write-Host "❌ Failed: $($resp.errors | ConvertTo-Json)" -ForegroundColor Red
    }
  } catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
  }
}

if ($PurgeAll) {
  Write-Host "`n🧹 Purging all cache..." -ForegroundColor Cyan
  Write-Host "   This will clear ALL cached content for the zone" -ForegroundColor Yellow

  try {
    $resp = Invoke-RestMethod -Method POST -Headers $headers `
      -Uri "https://api.cloudflare.com/client/v4/zones/$ZoneId/purge_cache" `
      -Body '{"purge_everything":true}'

    if ($resp.success) {
      Write-Host "✅ Cache purged successfully" -ForegroundColor Green
      Write-Host "   Propagation to all edge POPs: 3-5 minutes (typical)" -ForegroundColor Gray
    } else {
      Write-Host "❌ Failed: $($resp.errors | ConvertTo-Json)" -ForegroundColor Red
    }
  } catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
  }
}

if (-not ($EnableDev -or $DisableDev -or $PurgeAll)) {
  Write-Host "❌ No action specified. Use -EnableDev, -DisableDev, or -PurgeAll" -ForegroundColor Red
  Write-Host "`nExamples:" -ForegroundColor Cyan
  Write-Host "  .\cf-cache-tools.ps1 -ZoneId `"abc123`" -PurgeAll" -ForegroundColor Gray
  Write-Host "  .\cf-cache-tools.ps1 -ZoneId `"abc123`" -EnableDev" -ForegroundColor Gray
  exit 1
}
