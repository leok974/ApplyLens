# Quick setup script - Run this first!
# Usage: . .\scripts\Quick-CloudflareSetup.ps1

Write-Host "`n🚀 ApplyLens v0.4.10 - Cloudflare Cache Setup" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray

# Step 1: Set credentials
Write-Host "`n📝 Step 1: Set Cloudflare Credentials" -ForegroundColor Yellow

$env:CLOUDFLARE_ZONE_ID = "8b18d6fe5e67a5507f4db885748fbfe6"
Write-Host "✓ Zone ID set: 8b18d6fe5e67a5507f4db885748fbfe6" -ForegroundColor Green

if ($env:CLOUDFLARE_API_TOKEN -and $env:CLOUDFLARE_API_TOKEN.Length -gt 40) {
    Write-Host "✓ API Token already set (length: $($env:CLOUDFLARE_API_TOKEN.Length) chars)" -ForegroundColor Green
} else {
    Write-Host "`nYou need to set your Cloudflare API Token:" -ForegroundColor Yellow
    Write-Host "  1. Go to: https://dash.cloudflare.com/profile/api-tokens" -ForegroundColor White
    Write-Host "  2. Click 'Create Token'" -ForegroundColor White
    Write-Host "  3. Use template 'Edit zone DNS' or create custom with:" -ForegroundColor White
    Write-Host "     - Permission: Zone > Cache Rules > Edit" -ForegroundColor Gray
    Write-Host "     - Permission: Zone > Cache Purge > Purge" -ForegroundColor Gray
    Write-Host "     - Zone Resources: Include > Specific zone > applylens.app" -ForegroundColor Gray
    Write-Host "`n  4. Then run:" -ForegroundColor White
    Write-Host '     $env:CLOUDFLARE_API_TOKEN = "YOUR_TOKEN_HERE"' -ForegroundColor Cyan
    Write-Host "`n  5. Re-run this script" -ForegroundColor White
    exit
}

# Validate
if ($env:CLOUDFLARE_API_TOKEN.Length -lt 40) {
    throw "❌ API Token too short (got $($env:CLOUDFLARE_API_TOKEN.Length) chars, need 40+)"
}

Write-Host "`n✅ Credentials validated!" -ForegroundColor Green

# Step 2: Verify cache rules exist
Write-Host "`n📋 Step 2: Verify Cache Rules" -ForegroundColor Yellow
& "$PSScriptRoot\Verify-CloudflareCacheRules.ps1"

# Step 3: Purge HTML files
Write-Host "`n🗑️  Step 3: Purge HTML Entry Points" -ForegroundColor Yellow
& "$PSScriptRoot\Purge-CloudflareCache.ps1"

# Step 4: Verify headers from edge
Write-Host "`n🌐 Step 4: Verify Headers from Cloudflare" -ForegroundColor Yellow
Write-Host "Checking HTML headers..." -ForegroundColor Gray
try {
    $htmlResponse = Invoke-WebRequest -Uri "https://applylens.app/web/" -Method Head -UseBasicParsing
    Write-Host "`n✓ HTML Response:" -ForegroundColor Cyan
    Write-Host "  Status: $($htmlResponse.StatusCode)" -ForegroundColor White
    Write-Host "  Content-Type: $($htmlResponse.Headers['Content-Type'])" -ForegroundColor White
    Write-Host "  Cache-Control: $($htmlResponse.Headers['Cache-Control'])" -ForegroundColor White
    if ($htmlResponse.Headers['CF-Cache-Status']) {
        Write-Host "  CF-Cache-Status: $($htmlResponse.Headers['CF-Cache-Status'])" -ForegroundColor White
    }
} catch {
    Write-Host "⚠️  Could not fetch HTML headers: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`nChecking API headers..." -ForegroundColor Gray
try {
    $apiResponse = Invoke-WebRequest -Uri "https://applylens.app/api/search?q=test&limit=1" -Method Head -UseBasicParsing
    Write-Host "`n✓ API Response:" -ForegroundColor Cyan
    Write-Host "  Status: $($apiResponse.StatusCode)" -ForegroundColor White
    Write-Host "  Content-Type: $($apiResponse.Headers['Content-Type'])" -ForegroundColor White
} catch {
    Write-Host "⚠️  API returned: $($_.Exception.Response.StatusCode) (might need auth)" -ForegroundColor Yellow
}

# Step 5: Browser instructions
Write-Host "`n🌐 Step 5: Browser Verification" -ForegroundColor Yellow
Write-Host @"

Now in your browser:
1. Open Chrome DevTools (F12)
2. Go to Network tab → Check "Disable cache"
3. Go to: https://applylens.app/web/?v=after-purge
4. Open Console - you should see: 🔍 ApplyLens Web v0.4.10
5. Paste this to intercept fetches:

(function(){
  const orig = window.fetch;
  window.fetch = async function(i, init){
    const url = typeof i==='string'?i:i.url;
    console.info('[FETCH]', url, init?.method||'GET');
    return orig.apply(this, arguments);
  };
})();

6. Click Search - should show: [FETCH] https://applylens.app/api/search?...
   NOT: /web/search/...

"@ -ForegroundColor White

Write-Host "`n✅ Setup complete! Follow browser instructions above." -ForegroundColor Green
