# Purge specific files from Cloudflare cache
# Usage: .\scripts\Purge-CloudflareCache.ps1
# Usage: .\scripts\Purge-CloudflareCache.ps1 -PurgeEverything

param(
    [string]$Token = $env:CLOUDFLARE_API_TOKEN,
    [string]$Zone = $env:CLOUDFLARE_ZONE_ID,
    [string[]]$Files = @(
        "https://applylens.app/",
        "https://applylens.app/index.html",
        "https://applylens.app/web/",
        "https://applylens.app/web/index.html"
    ),
    [switch]$PurgeEverything
)

if (-not $Token -or -not $Zone) {
    throw "❌ CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID must be set. Run Set-CloudflareCredentials.ps1 first."
}

$api = "https://api.cloudflare.com/client/v4"
$headers = @{
    Authorization = "Bearer $Token"
    "Content-Type" = "application/json"
}

try {
    if ($PurgeEverything) {
        Write-Host "🗑️  Purging EVERYTHING from Cloudflare cache..." -ForegroundColor Yellow
        Write-Host "   This will clear ALL cached files for the zone" -ForegroundColor Gray

        $body = @{ purge_everything = $true } | ConvertTo-Json
        $res = Invoke-RestMethod -Headers $headers -Uri "$api/zones/$Zone/purge_cache" -Method POST -Body $body

        if ($res.success) {
            Write-Host "✅ Successfully purged all cache!" -ForegroundColor Green
        } else {
            Write-Host "❌ Cache purge failed!" -ForegroundColor Red
            $res.errors | ForEach-Object { Write-Host "   Error: $($_.message)" -ForegroundColor Red }
        }
    } else {
        Write-Host "🗑️  Purging specific files from Cloudflare cache..." -ForegroundColor Cyan
        Write-Host "`n📋 Files to purge:" -ForegroundColor Gray
        $Files | ForEach-Object { Write-Host "   • $_" -ForegroundColor White }

        $body = @{ files = $Files } | ConvertTo-Json
        $res = Invoke-RestMethod -Headers $headers -Uri "$api/zones/$Zone/purge_cache" -Method POST -Body $body

        if ($res.success) {
            Write-Host "`n✅ Successfully purged $($Files.Count) files!" -ForegroundColor Green
            Write-Host "   Wait 30-60 seconds for changes to propagate globally" -ForegroundColor Gray
        } else {
            Write-Host "`n❌ Cache purge failed!" -ForegroundColor Red
            $res.errors | ForEach-Object { Write-Host "   Error: $($_.message)" -ForegroundColor Red }
        }
    }

    Write-Host "`n📊 Response details:" -ForegroundColor Cyan
    $res | ConvertTo-Json -Depth 5

} catch {
    Write-Host "❌ Error purging cache: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
