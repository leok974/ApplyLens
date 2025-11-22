<#
.SYNOPSIS
  Create a Cloudflare Cache Rule to bypass caching for /health endpoint.

.DESCRIPTION
  Creates a cache rule that forces Cloudflare to never cache the /health endpoint,
  preventing stale 502 errors from being served.

.PARAMETER ZoneId
  Cloudflare Zone ID

.EXAMPLE
  $env:CF_API_TOKEN = "your_token_here"
  .\cf-create-health-bypass-rule.ps1 -ZoneId "8b18d6fe5e67a5507f4db885748fbfe6"
#>

param(
  [Parameter(Mandatory)][string]$ZoneId
)

if (-not $env:CF_API_TOKEN) {
  Write-Host "❌ Error: CF_API_TOKEN environment variable not set" -ForegroundColor Red
  exit 1
}

$headers = @{
  "Authorization" = "Bearer $env:CF_API_TOKEN"
  "Content-Type"  = "application/json"
}

Write-Host "`n🔧 Creating Cache Rule to bypass /health..." -ForegroundColor Cyan

# Create a cache rule using the Rulesets API
# This rule will bypass cache for any request to /health or /healthz
$rulePayload = @{
  name = "Bypass health checks"
  kind = "zone"
  phase = "http_request_cache_settings"
  rules = @(
    @{
      action = "set_cache_settings"
      expression = '(http.request.uri.path eq "/health") or (http.request.uri.path eq "/healthz")'
      description = "Never cache health check endpoints to prevent stale 502 errors"
      enabled = $true
      action_parameters = @{
        cache = $false
      }
    }
  )
} | ConvertTo-Json -Depth 10

try {
  $url = "https://api.cloudflare.com/client/v4/zones/$ZoneId/rulesets/phases/http_request_cache_settings/entrypoint"

  # Try to update existing entrypoint, or create new one
  try {
    $resp = Invoke-RestMethod -Method PUT -Headers $headers -Uri $url -Body $rulePayload
  } catch {
    # If no entrypoint exists, create it
    $resp = Invoke-RestMethod -Method POST -Headers $headers -Uri $url -Body $rulePayload
  }

  if ($resp.success) {
    Write-Host "✅ Cache bypass rule created successfully!" -ForegroundColor Green
    Write-Host "`nRule details:" -ForegroundColor Cyan
    Write-Host "  ID: $($resp.result.id)" -ForegroundColor Gray
    Write-Host "  Phase: $($resp.result.phase)" -ForegroundColor Gray
    Write-Host "  Rules: $($resp.result.rules.Count)" -ForegroundColor Gray
    Write-Host "`nThe /health and /healthz endpoints will now NEVER be cached." -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "  1. Wait 30-60 seconds for rule to propagate" -ForegroundColor Gray
    Write-Host "  2. Run: .\scripts\watch-prod-health.ps1" -ForegroundColor Gray
    Write-Host "  3. Expect 95%+ success rate" -ForegroundColor Gray
  } else {
    Write-Host "❌ Failed to create rule" -ForegroundColor Red
    Write-Host "Response: $($resp | ConvertTo-Json -Depth 5)" -ForegroundColor Red
  }
} catch {
  Write-Host "❌ Error: $_" -ForegroundColor Red
  Write-Host "`nThis might be a permissions issue. Ensure your API token has:" -ForegroundColor Yellow
  Write-Host "  - Zone → Cache Rules → Edit" -ForegroundColor Gray
  Write-Host "  - Or use a token with Zone Settings → Edit permission" -ForegroundColor Gray
}
