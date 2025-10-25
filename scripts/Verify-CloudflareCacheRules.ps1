# Verify Cloudflare Cache Rules are active
# Usage: .\scripts\Verify-CloudflareCacheRules.ps1

param(
    [string]$Token = $env:CLOUDFLARE_API_TOKEN,
    [string]$ZoneId = $env:CLOUDFLARE_ZONE_ID
)

if (-not $Token -or -not $ZoneId) {
    throw "❌ CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID must be set. Run Set-CloudflareCredentials.ps1 first."
}

$api = "https://api.cloudflare.com/client/v4"
$headers = @{
    Authorization = "Bearer $Token"
    "Content-Type" = "application/json"
}

Write-Host "`n🔍 Fetching Cloudflare rulesets for zone: $ZoneId" -ForegroundColor Cyan

try {
    # List all rulesets
    $rulesets = Invoke-RestMethod -Headers $headers -Uri "$api/zones/$ZoneId/rulesets" -Method GET

    # Find cache settings ruleset
    $cacheRuleset = $rulesets.result | Where-Object { $_.phase -eq "http_request_cache_settings" }

    if (-not $cacheRuleset) {
        Write-Host "❌ No http_request_cache_settings ruleset found!" -ForegroundColor Red
        Write-Host "   Run Setup-CloudflareCache.ps1 to create cache rules" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "✅ Found http_request_cache_settings ruleset (ID: $($cacheRuleset.id))" -ForegroundColor Green
    Write-Host "`n📋 Cache Rules:" -ForegroundColor Cyan
    Write-Host "=" * 80 -ForegroundColor Gray

    if ($cacheRuleset.rules.Count -eq 0) {
        Write-Host "⚠️  No rules configured in ruleset!" -ForegroundColor Yellow
        Write-Host "   Run Setup-CloudflareCache.ps1 to add cache rules" -ForegroundColor Yellow
        exit 1
    }

    foreach ($rule in $cacheRuleset.rules) {
        Write-Host "`nRule: " -NoNewline -ForegroundColor White
        Write-Host "$($rule.description)" -ForegroundColor Cyan
        Write-Host "  Enabled: " -NoNewline -ForegroundColor Gray
        if ($rule.enabled) {
            Write-Host "✓ Yes" -ForegroundColor Green
        } else {
            Write-Host "✗ No" -ForegroundColor Red
        }
        Write-Host "  Action: " -NoNewline -ForegroundColor Gray
        Write-Host "$($rule.action)" -ForegroundColor Yellow
        Write-Host "  Expression: " -NoNewline -ForegroundColor Gray
        Write-Host "$($rule.expression)" -ForegroundColor White

        if ($rule.action_parameters.cache) {
            Write-Host "  Cache Mode: " -NoNewline -ForegroundColor Gray
            Write-Host "$($rule.action_parameters.cache)" -ForegroundColor Magenta
        }
        if ($rule.action_parameters.edge_ttl) {
            Write-Host "  Edge TTL: " -NoNewline -ForegroundColor Gray
            Write-Host "$($rule.action_parameters.edge_ttl.default) seconds" -ForegroundColor Magenta
            $days = [math]::Round($rule.action_parameters.edge_ttl.default / 86400)
            Write-Host "            ($days days)" -ForegroundColor Gray
        }
    }

    Write-Host "`n" + ("=" * 80) -ForegroundColor Gray

    # Verify expected rules exist
    $bypassRule = $cacheRuleset.rules | Where-Object { $_.description -like "*Bypass*HTML*" }
    $immutableRule = $cacheRuleset.rules | Where-Object { $_.description -like "*Immutable*assets*" }

    Write-Host "`n✓ Verification:" -ForegroundColor Cyan
    if ($bypassRule) {
        Write-Host "  ✅ Bypass HTML rule found" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Bypass HTML rule missing" -ForegroundColor Yellow
    }

    if ($immutableRule) {
        Write-Host "  ✅ Immutable assets rule found" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Immutable assets rule missing" -ForegroundColor Yellow
    }

    if ($bypassRule -and $immutableRule) {
        Write-Host "`n✅ All cache rules are properly configured!" -ForegroundColor Green
    } else {
        Write-Host "`n⚠️  Some cache rules are missing. Run Setup-CloudflareCache.ps1" -ForegroundColor Yellow
    }

} catch {
    Write-Host "❌ Error fetching cache rules: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
