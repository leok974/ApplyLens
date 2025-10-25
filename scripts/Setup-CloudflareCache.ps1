# Cloudflare Cache Rules Setup for ApplyLens (PowerShell)
# Purpose: Bypass cache for HTML, cache assets forever

param(
    [Parameter(Mandatory=$true)]
    [string]$CF_API_TOKEN,

    [Parameter(Mandatory=$true)]
    [string]$CF_ZONE_ID
)

$ErrorActionPreference = "Stop"

Write-Host "🔧 ApplyLens Cloudflare Cache Rules Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$CF_API = "https://api.cloudflare.com/client/v4"

Write-Host "✅ Environment variables configured" -ForegroundColor Green
Write-Host "   Zone ID: $CF_ZONE_ID"
Write-Host ""

# Step 1: Find or create the cache rules ruleset
Write-Host "📋 Step 1: Finding cache rules ruleset..." -ForegroundColor Yellow

$headers = @{
    "Authorization" = "Bearer $CF_API_TOKEN"
    "Content-Type" = "application/json"
}

$rulesets = Invoke-RestMethod -Uri "$CF_API/zones/$CF_ZONE_ID/rulesets" -Headers $headers -Method Get
$ruleset = $rulesets.result | Where-Object { $_.phase -eq "http_request_cache_settings" } | Select-Object -First 1

if (-not $ruleset) {
    Write-Host "   → No cache rules ruleset found. Creating one..." -ForegroundColor Yellow

    $createBody = @{
        name = "default"
        kind = "zone"
        phase = "http_request_cache_settings"
        rules = @()
    } | ConvertTo-Json -Depth 10

    $ruleset = Invoke-RestMethod -Uri "$CF_API/zones/$CF_ZONE_ID/rulesets" `
        -Headers $headers -Method Post -Body $createBody -ContentType "application/json"

    if (-not $ruleset.result.id) {
        Write-Host "❌ Failed to create ruleset" -ForegroundColor Red
        exit 1
    }
    Write-Host "   ✅ Created ruleset: $($ruleset.result.id)" -ForegroundColor Green
    $RULESET_ID = $ruleset.result.id
} else {
    Write-Host "   ✅ Found existing ruleset: $($ruleset.id)" -ForegroundColor Green
    $RULESET_ID = $ruleset.id
}

Write-Host ""

# Step 2: Update cache rules
Write-Host "📝 Step 2: Updating cache rules..." -ForegroundColor Yellow

$cacheRules = @{
    name = "default"
    phase = "http_request_cache_settings"
    rules = @(
        @{
            description = "Bypass cache for HTML entry points (always fetch fresh asset hashes)"
            action = "set_cache_settings"
            expression = "(http.request.uri.path eq `"/`" or starts_with(http.request.uri.path, `"/web/`") or ends_with(http.request.uri.path, `"/index.html`"))"
            action_parameters = @{
                cache = $false
            }
            enabled = $true
        },
        @{
            description = "Immutable cache for hashed assets (1 year for js/css/fonts/images)"
            action = "set_cache_settings"
            expression = "(starts_with(http.request.uri.path, `"/assets/`") or ends_with(http.request.uri.path, `".js`") or ends_with(http.request.uri.path, `".css`") or ends_with(http.request.uri.path, `".woff2`") or ends_with(http.request.uri.path, `".woff`") or ends_with(http.request.uri.path, `".svg`") or ends_with(http.request.uri.path, `".png`") or ends_with(http.request.uri.path, `".jpg`") or ends_with(http.request.uri.path, `".jpeg`") or ends_with(http.request.uri.path, `".webp`"))"
            action_parameters = @{
                cache = $true
                edge_ttl = @{
                    mode = "override_origin"
                    default = 31536000
                }
                browser_ttl = @{
                    mode = "respect_origin"
                }
            }
            enabled = $true
        }
    )
} | ConvertTo-Json -Depth 10

try {
    $result = Invoke-RestMethod -Uri "$CF_API/zones/$CF_ZONE_ID/rulesets/$RULESET_ID" `
        -Headers $headers -Method Put -Body $cacheRules

    if ($result.success) {
        Write-Host "   ✅ Cache rules updated successfully" -ForegroundColor Green
        Write-Host ""
        Write-Host "   Rules created:" -ForegroundColor Cyan
        foreach ($rule in $result.result.rules) {
            Write-Host "     - $($rule.description)" -ForegroundColor Gray
        }
    } else {
        Write-Host "   ❌ Failed to update cache rules" -ForegroundColor Red
        Write-Host ($result.errors | ConvertTo-Json) -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "   ❌ Error updating cache rules: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: Purge cache
Write-Host "🗑️  Step 3: Purging Cloudflare cache..." -ForegroundColor Yellow

$purgeBody = @{
    files = @(
        "https://applylens.app/",
        "https://applylens.app/web/",
        "https://applylens.app/web/index.html",
        "https://applylens.app/index.html"
    )
} | ConvertTo-Json

try {
    $purgeResult = Invoke-RestMethod -Uri "$CF_API/zones/$CF_ZONE_ID/purge_cache" `
        -Headers $headers -Method Post -Body $purgeBody

    if ($purgeResult.success) {
        Write-Host "   ✅ Cache purged successfully" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Cache purge failed (may need manual purge)" -ForegroundColor Yellow
        Write-Host ($purgeResult.errors | ConvertTo-Json) -ForegroundColor Red
    }
} catch {
    Write-Host "   ⚠️  Error purging cache: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Configuration complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Wait 30-60 seconds for Cloudflare to propagate changes"
Write-Host "   2. Clear your browser cache (DevTools → Application → Clear Storage)"
Write-Host "   3. Visit https://applylens.app/web/search"
Write-Host "   4. Open Console and verify: '🔍 ApplyLens Web v0.4.10'"
Write-Host "   5. Perform a search and check Network tab for /api/search requests"
Write-Host ""
Write-Host "📊 Verification commands:" -ForegroundColor Cyan
Write-Host '   curl.exe -sI "https://applylens.app/web/" | Select-String "cache-control|cf-cache-status"'
Write-Host '   curl.exe -sI "https://applylens.app/api/search?q=test&limit=1" | Select-String "content-type"'
Write-Host ""
