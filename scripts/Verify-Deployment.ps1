# ApplyLens v0.4.10 Verification Script
# Run this after deploying to verify everything is working

param(
    [string]$BaseUrl = "https://applylens.app"
)

Write-Host "🔍 ApplyLens v0.4.10 Verification" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Testing: $BaseUrl" -ForegroundColor Yellow
Write-Host ""

$passed = 0
$failed = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$ExpectedHeader,
        [string]$ExpectedValue,
        [switch]$ShouldContain
    )

    Write-Host "Testing: $Name" -ForegroundColor Yellow
    Write-Host "  URL: $Url" -ForegroundColor Gray

    try {
        $response = Invoke-WebRequest -Uri $Url -Method Head -UseBasicParsing -ErrorAction Stop
        $headerValue = $response.Headers[$ExpectedHeader]

        if ($headerValue) {
            Write-Host "  ${ExpectedHeader}: $headerValue" -ForegroundColor Gray

            if ($ShouldContain) {
                if ($headerValue -like "*$ExpectedValue*") {
                    Write-Host "  ✅ PASS: Contains '$ExpectedValue'" -ForegroundColor Green
                    $script:passed++
                } else {
                    Write-Host "  ❌ FAIL: Does not contain '$ExpectedValue'" -ForegroundColor Red
                    $script:failed++
                }
            } else {
                if ($headerValue -eq $ExpectedValue) {
                    Write-Host "  ✅ PASS: Matches '$ExpectedValue'" -ForegroundColor Green
                    $script:passed++
                } else {
                    Write-Host "  ❌ FAIL: Expected '$ExpectedValue', got '$headerValue'" -ForegroundColor Red
                    $script:failed++
                }
            }
        } else {
            Write-Host "  ❌ FAIL: Header '$ExpectedHeader' not found" -ForegroundColor Red
            $script:failed++
        }
    } catch {
        Write-Host "  ❌ ERROR: $_" -ForegroundColor Red
        $script:failed++
    }

    Write-Host ""
}

# Test 1: HTML should have no-cache
Test-Endpoint `
    -Name "HTML No-Cache (/web/)" `
    -Url "$BaseUrl/web/" `
    -ExpectedHeader "Cache-Control" `
    -ExpectedValue "no-cache" `
    -ShouldContain

# Test 2: API should return JSON
Test-Endpoint `
    -Name "API Returns JSON (/api/search)" `
    -Url "$BaseUrl/api/search?q=test&limit=1" `
    -ExpectedHeader "Content-Type" `
    -ExpectedValue "application/json" `
    -ShouldContain

# Test 3: Assets should have immutable cache
Write-Host "Testing: Assets Immutable Cache" -ForegroundColor Yellow
try {
    # Try to find a JS file
    $indexHtml = Invoke-WebRequest -Uri "$BaseUrl/web/" -UseBasicParsing
    if ($indexHtml.Content -match 'src="(/assets/index-[^"]+\.js)"') {
        $jsFile = $Matches[1]
        Write-Host "  Found JS file: $jsFile" -ForegroundColor Gray

        $jsResponse = Invoke-WebRequest -Uri "$BaseUrl$jsFile" -Method Head -UseBasicParsing
        $cacheControl = $jsResponse.Headers['Cache-Control']

        Write-Host "  Cache-Control: $cacheControl" -ForegroundColor Gray

        if ($cacheControl -like "*immutable*" -and $cacheControl -like "*max-age=31536000*") {
            Write-Host "  ✅ PASS: JS has immutable cache" -ForegroundColor Green
            $script:passed++
        } else {
            Write-Host "  ❌ FAIL: JS should have 'immutable' and 'max-age=31536000'" -ForegroundColor Red
            $script:failed++
        }
    } else {
        Write-Host "  ⚠️  SKIP: Could not find JS file in HTML" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ❌ ERROR: $_" -ForegroundColor Red
    $script:failed++
}

Write-Host ""

# Summary
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  ✅ Passed: $passed" -ForegroundColor Green
Write-Host "  ❌ Failed: $failed" -ForegroundColor Red

if ($failed -eq 0) {
    Write-Host ""
    Write-Host "🎉 All tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next: Clear your browser cache and test manually:" -ForegroundColor Cyan
    Write-Host "  1. Open DevTools (F12)"
    Write-Host "  2. Application → Clear Storage → Clear site data"
    Write-Host "  3. Close all tabs"
    Write-Host "  4. Open $BaseUrl/web/search"
    Write-Host "  5. Console should show: 🔍 ApplyLens Web v0.4.10"
    Write-Host "  6. Perform search → Network tab should show /api/search (not /web/search)"
    exit 0
} else {
    Write-Host ""
    Write-Host "⚠️  Some tests failed. Check the output above." -ForegroundColor Yellow
    exit 1
}
