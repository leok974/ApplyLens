# Set Cloudflare credentials for this PowerShell session
# Usage: . .\scripts\Set-CloudflareCredentials.ps1

param(
    [string]$Token,
    [string]$ZoneId
)

# If parameters not provided, prompt or use existing env vars
if (-not $Token) {
    if ($env:CLOUDFLARE_API_TOKEN -and $env:CLOUDFLARE_API_TOKEN.Length -gt 40) {
        $Token = $env:CLOUDFLARE_API_TOKEN
        Write-Host "✓ Using existing CLOUDFLARE_API_TOKEN from environment" -ForegroundColor Green
    } else {
        Write-Host "Enter your Cloudflare API Token (from https://dash.cloudflare.com/profile/api-tokens):" -ForegroundColor Yellow
        $Token = Read-Host "API Token"
    }
}

if (-not $ZoneId) {
    if ($env:CLOUDFLARE_ZONE_ID -and $env:CLOUDFLARE_ZONE_ID.Length -eq 32) {
        $ZoneId = $env:CLOUDFLARE_ZONE_ID
        Write-Host "✓ Using existing CLOUDFLARE_ZONE_ID from environment" -ForegroundColor Green
    } else {
        Write-Host "Enter your Cloudflare Zone ID (from https://dash.cloudflare.com -> Select domain -> Zone ID in sidebar):" -ForegroundColor Yellow
        $ZoneId = Read-Host "Zone ID"
    }
}

# Validate credentials format
if ($Token.Length -lt 40) {
    throw "❌ Cloudflare API Token looks invalid. Should be 40+ characters, got $($Token.Length) chars."
}

if ($ZoneId.Length -ne 32) {
    throw "❌ Cloudflare Zone ID looks invalid. Should be 32 characters, got $($ZoneId.Length) chars."
}

# Set environment variables
$env:CLOUDFLARE_API_TOKEN = $Token
$env:CLOUDFLARE_ZONE_ID = $ZoneId

Write-Host "`n✅ Cloudflare credentials set successfully!" -ForegroundColor Green
Write-Host "   Token length: $($Token.Length) chars" -ForegroundColor Gray
Write-Host "   Zone ID: $ZoneId" -ForegroundColor Gray
Write-Host "`nTo make these permanent (user-level):" -ForegroundColor Cyan
Write-Host "  [Environment]::SetEnvironmentVariable('CLOUDFLARE_API_TOKEN', `$env:CLOUDFLARE_API_TOKEN, 'User')" -ForegroundColor Gray
Write-Host "  [Environment]::SetEnvironmentVariable('CLOUDFLARE_ZONE_ID', `$env:CLOUDFLARE_ZONE_ID, 'User')" -ForegroundColor Gray
