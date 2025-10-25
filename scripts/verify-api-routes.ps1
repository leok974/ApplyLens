#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Verify API route behavior after deployment
.DESCRIPTION
    This script tests that:
    1. Routes with trailing slashes don't redirect
    2. Routes without trailing slashes don't redirect
    3. All API responses are JSON (or 401), never HTML
#>

param(
    [string]$BaseUrl = "https://applylens.app"
)

$ErrorActionPreference = "Continue"
Write-Host "🔍 Verifying API routes at $BaseUrl" -ForegroundColor Cyan
Write-Host ""

function Test-ApiRoute {
    param(
        [string]$Path,
        [string]$Description,
        [bool]$ExpectTrailingSlash = $false
    )

    $url = "$BaseUrl$Path"
    Write-Host "Testing: $Description" -ForegroundColor Yellow
    Write-Host "  URL: $url"

    try {
        # Use curl for proper HTTP handling
        $curlOutput = curl -s -i -X GET "$url" 2>&1
        $lines = $curlOutput -split "`n"

        # Parse status line
        $statusLine = $lines[0]
        if ($statusLine -match "HTTP/\d\.\d (\d+)") {
            $status = [int]$matches[1]
        } else {
            Write-Host "  ❌ ERROR: Could not parse HTTP status" -ForegroundColor Red
            return $false
        }

        Write-Host "  Status: $status" -ForegroundColor $(if ($status -eq 200 -or $status -eq 204 -or $status -eq 401 -or $status -eq 403) { "Green" } else { "Red" })

        # Check for redirects
        if ($status -ge 300 -and $status -lt 400) {
            $locationLine = $lines | Where-Object { $_ -match "^location:" -or $_ -match "^Location:" }
            $location = if ($locationLine) { $locationLine -replace "^[Ll]ocation:\s*", "" } else { "unknown" }
            Write-Host "  ❌ REDIRECT DETECTED: $status → $location" -ForegroundColor Red
            return $false
        }

        # Parse content-type
        $contentTypeLine = $lines | Where-Object { $_ -match "^content-type:" -or $_ -match "^Content-Type:" }
        $contentType = if ($contentTypeLine) { $contentTypeLine -replace "^[Cc]ontent-[Tt]ype:\s*", "" } else { "" }
        Write-Host "  Content-Type: $contentType"

        if ($status -ne 204) {
            if ($contentType -notlike "*application/json*") {
                Write-Host "  ❌ NON-JSON RESPONSE: Expected application/json" -ForegroundColor Red
                # Show body preview
                $bodyStart = $lines | Select-Object -Skip 1 | Where-Object { $_.Trim() -eq "" } | Select-Object -First 1 -Index
                if ($bodyStart) {
                    $body = ($lines[($bodyStart+1)..($bodyStart+5)] -join "`n").Substring(0, [Math]::Min(200, ($lines[($bodyStart+1)..($bodyStart+5)] -join "`n").Length))
                    Write-Host "  Body preview: $body"
                }
                return $false
            }
        }

        # Special handling for auth errors
        if ($status -eq 401 -or $status -eq 403) {
            Write-Host "  ⚠️  AUTH REQUIRED (expected for unauthenticated request)" -ForegroundColor Yellow
            if ($contentType -like "*application/json*") {
                Write-Host "  ✅ PASS (401/403 with JSON)" -ForegroundColor Green
                return $true
            } else {
                Write-Host "  ❌ FAIL: 401/403 should return JSON error, not HTML" -ForegroundColor Red
                return $false
            }
        }

        Write-Host "  ✅ PASS" -ForegroundColor Green
        return $true

    } catch {
        Write-Host "  ❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }

    Write-Host ""
}

# Test routes
$results = @()

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Testing routes WITH trailing slash" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

$results += Test-ApiRoute -Path "/api/search/?q=Interview&limit=1" `
    -Description "Search endpoint (with trailing slash)" `
    -ExpectTrailingSlash $true

$results += Test-ApiRoute -Path "/api/emails/?limit=1" `
    -Description "Emails endpoint (with trailing slash)" `
    -ExpectTrailingSlash $true

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Testing routes WITHOUT trailing slash" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

$results += Test-ApiRoute -Path "/api/auth/me" `
    -Description "Auth me endpoint (no trailing slash)" `
    -ExpectTrailingSlash $false

$results += Test-ApiRoute -Path "/api/auth/session" `
    -Description "Auth session endpoint (no trailing slash)" `
    -ExpectTrailingSlash $false

# Summary
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

$passed = ($results | Where-Object { $_ -eq $true }).Count
$failed = ($results | Where-Object { $_ -eq $false }).Count
$total = $results.Count

Write-Host "Passed: $passed / $total" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
Write-Host "Failed: $failed / $total" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })

if ($failed -eq 0) {
    Write-Host ""
    Write-Host "✅ All API routes verified successfully!" -ForegroundColor Green
    exit 0
} else {
    Write-Host ""
    Write-Host "❌ Some API routes failed verification" -ForegroundColor Red
    exit 1
}
