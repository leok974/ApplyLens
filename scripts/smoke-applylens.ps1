#!/usr/bin/env pwsh
# Smoke Test for applylens.app Production Deployment
# Tests DNS resolution, API health, CORS configuration, and static assets

param(
    [switch]$Verbose,
    [switch]$SkipDNS
)

$ErrorActionPreference = "Continue"
$testsPassed = 0
$testsFailed = 0
$warnings = @()

# Helper function to resolve DNS via Google DNS (bypasses local cache)
function Resolve-Via8888 {
    param([string]$Name)
    try {
        $result = Resolve-DnsName -Name $Name -Server 8.8.8.8 -Type A -ErrorAction Stop
        return $result.IPAddress | Select-Object -First 1
    } catch {
        return $null
    }
}

# Color output helpers
function Write-TestHeader($message) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $message -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Write-TestPass($message) {
    Write-Host "✅ PASS: $message" -ForegroundColor Green
    $script:testsPassed++
}

function Write-TestFail($message, $details = $null) {
    Write-Host "❌ FAIL: $message" -ForegroundColor Red
    if ($details) {
        Write-Host "   Details: $details" -ForegroundColor Yellow
    }
    $script:testsFailed++
}

function Write-TestWarning($message) {
    Write-Host "⚠️  WARN: $message" -ForegroundColor Yellow
    $script:warnings += $message
}

function Write-TestInfo($message) {
    if ($Verbose) {
        Write-Host "   ℹ️  $message" -ForegroundColor Gray
    }
}

# Test results summary
function Write-Summary {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Test Summary" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "✅ Passed: $testsPassed" -ForegroundColor Green
    Write-Host "❌ Failed: $testsFailed" -ForegroundColor Red
    Write-Host "⚠️  Warnings: $($warnings.Count)" -ForegroundColor Yellow
    
    if ($warnings.Count -gt 0) {
        Write-Host "`nWarnings:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "  - $warning" -ForegroundColor Yellow
        }
    }
    
    Write-Host "`n" -NoNewline
    if ($testsFailed -eq 0) {
        Write-Host "🎉 All tests passed!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "💥 Some tests failed. Review the output above." -ForegroundColor Red
        exit 1
    }
}

# ============================================================================
# Test 1: DNS Resolution (via Google DNS 8.8.8.8 to bypass cache)
# ============================================================================
if (-not $SkipDNS) {
    Write-TestHeader "Test 1: DNS Resolution"
    
    $domains = @("applylens.app", "www.applylens.app", "api.applylens.app")
    $script:resolvedIPs = @{}
    
    foreach ($domain in $domains) {
        $ip = Resolve-Via8888 -Name $domain
        if ($ip) {
            $script:resolvedIPs[$domain] = $ip
            Write-TestPass "$domain resolves to: $ip (via Google DNS 8.8.8.8)"
            Write-TestInfo "DNS query bypassed local cache"
        } else {
            Write-TestFail "$domain DNS lookup failed" "No A records found via 8.8.8.8"
        }
    }
} else {
    Write-Host "`nSkipping DNS tests (--SkipDNS flag set)" -ForegroundColor Yellow
    # Still resolve for later tests
    $script:resolvedIPs = @{
        "applylens.app" = "104.21.2.181"
        "www.applylens.app" = "104.21.2.181"
        "api.applylens.app" = "104.21.2.181"
    }
}

# ============================================================================
# Test 2: API Health Check (using resolved IP)
# ============================================================================
Write-TestHeader "Test 2: API Health Check (/ready endpoint)"

try {
    $apiIP = $script:resolvedIPs["api.applylens.app"]
    if (-not $apiIP) { $apiIP = "104.21.2.181" }
    
    $headers = @{ 'Host' = 'api.applylens.app' }
    $response = Invoke-WebRequest -Uri "https://$apiIP/ready" `
        -Headers $headers `
        -Method GET `
        -TimeoutSec 10 `
        -SkipCertificateCheck `
        -UseBasicParsing `
        -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        Write-TestPass "API /ready endpoint returns 200 OK"
        Write-TestInfo "Response: $($response.Content)"
    } else {
        Write-TestFail "API /ready returned status $($response.StatusCode)" "Expected 200"
    }
} catch {
    Write-TestFail "API /ready endpoint failed" $_.Exception.Message
}

# ============================================================================
# Test 3: CORS Preflight Request
# ============================================================================
Write-TestHeader "Test 3: CORS Preflight (OPTIONS request)"

try {
    $headers = @{
        "Origin" = "https://applylens.app"
        "Access-Control-Request-Method" = "POST"
        "Access-Control-Request-Headers" = "Content-Type"
    }
    
    $response = Invoke-WebRequest -Uri "https://api.applylens.app/emails" `
        -Method OPTIONS `
        -Headers $headers `
        -TimeoutSec 10 `
        -UseBasicParsing `
        -ErrorAction Stop
    
    # Check for CORS headers in response
    $corsOrigin = $response.Headers["Access-Control-Allow-Origin"]
    $corsMethods = $response.Headers["Access-Control-Allow-Methods"]
    $corsCredentials = $response.Headers["Access-Control-Allow-Credentials"]
    
    if ($corsOrigin) {
        Write-TestPass "CORS preflight returns Access-Control-Allow-Origin: $corsOrigin"
    } else {
        Write-TestFail "CORS preflight missing Access-Control-Allow-Origin header"
    }
    
    if ($corsMethods) {
        Write-TestPass "CORS preflight returns Access-Control-Allow-Methods: $corsMethods"
    } else {
        Write-TestWarning "CORS preflight missing Access-Control-Allow-Methods header"
    }
    
    if ($corsCredentials -eq "true") {
        Write-TestPass "CORS preflight allows credentials"
    } else {
        Write-TestWarning "CORS preflight does not allow credentials (might be intentional)"
    }
    
} catch {
    Write-TestFail "CORS preflight request failed" $_.Exception.Message
}

# ============================================================================
# Test 4: Main Domain Root Path
# ============================================================================
Write-TestHeader "Test 4: Main Domain (applylens.app)"

try {
    $response = Invoke-WebRequest -Uri "https://applylens.app/" `
        -Method HEAD `
        -TimeoutSec 10 `
        -UseBasicParsing `
        -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        Write-TestPass "applylens.app root path returns 200 OK"
    } elseif ($response.StatusCode -in 301, 302, 307, 308) {
        Write-TestWarning "applylens.app root path returns redirect ($($response.StatusCode))"
        Write-TestInfo "Location: $($response.Headers['Location'])"
    } else {
        Write-TestFail "applylens.app root path returns $($response.StatusCode)" "Expected 200"
    }
} catch {
    Write-TestFail "applylens.app root path failed" $_.Exception.Message
}

# ============================================================================
# Test 5: WWW Subdomain
# ============================================================================
Write-TestHeader "Test 5: WWW Subdomain (www.applylens.app)"

try {
    $response = Invoke-WebRequest -Uri "https://www.applylens.app/" `
        -Method HEAD `
        -MaximumRedirection 0 `
        -TimeoutSec 10 `
        -UseBasicParsing `
        -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        Write-TestPass "www.applylens.app returns 200 OK"
    } elseif ($response.StatusCode -in 301, 302, 307, 308) {
        $location = $response.Headers['Location']
        if ($location -like "https://applylens.app*") {
            Write-TestPass "www.applylens.app redirects to apex domain (expected)"
        } else {
            Write-TestWarning "www.applylens.app redirects to: $location"
        }
    } else {
        Write-TestFail "www.applylens.app returns $($response.StatusCode)"
    }
} catch {
    # PowerShell throws on 3xx by default with -MaximumRedirection 0
    if ($_.Exception.Response.StatusCode -in 301, 302, 307, 308) {
        $location = $_.Exception.Response.Headers['Location']
        Write-TestPass "www.applylens.app redirects (status: $($_.Exception.Response.StatusCode))"
        Write-TestInfo "Location: $location"
    } else {
        Write-TestFail "www.applylens.app request failed" $_.Exception.Message
    }
}

# ============================================================================
# Test 6: robots.txt
# ============================================================================
Write-TestHeader "Test 6: robots.txt"

try {
    $response = Invoke-WebRequest -Uri "https://applylens.app/robots.txt" `
        -Method GET `
        -TimeoutSec 10 `
        -UseBasicParsing `
        -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        Write-TestPass "robots.txt returns 200 OK"
        Write-TestInfo "Content length: $($response.Content.Length) bytes"
    } else {
        Write-TestFail "robots.txt returns $($response.StatusCode)" "Expected 200"
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-TestWarning "robots.txt not found (404) - consider adding one"
    } else {
        Write-TestFail "robots.txt request failed" $_.Exception.Message
    }
}

# ============================================================================
# Test 7: sitemap.xml
# ============================================================================
Write-TestHeader "Test 7: sitemap.xml"

try {
    $response = Invoke-WebRequest -Uri "https://applylens.app/sitemap.xml" `
        -Method GET `
        -TimeoutSec 10 `
        -UseBasicParsing `
        -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        Write-TestPass "sitemap.xml returns 200 OK"
        Write-TestInfo "Content length: $($response.Content.Length) bytes"
    } else {
        Write-TestFail "sitemap.xml returns $($response.StatusCode)" "Expected 200"
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-TestWarning "sitemap.xml not found (404) - consider adding one for SEO"
    } else {
        Write-TestFail "sitemap.xml request failed" $_.Exception.Message
    }
}

# ============================================================================
# Test 8: API Documentation
# ============================================================================
Write-TestHeader "Test 8: API Documentation (/docs)"

try {
    $response = Invoke-WebRequest -Uri "https://api.applylens.app/docs" `
        -Method HEAD `
        -TimeoutSec 10 `
        -UseBasicParsing `
        -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        Write-TestPass "API /docs endpoint returns 200 OK"
    } else {
        Write-TestWarning "API /docs returns $($response.StatusCode) - docs might be disabled"
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-TestWarning "API /docs not found (might be disabled in production)"
    } else {
        Write-TestFail "API /docs request failed" $_.Exception.Message
    }
}

# ============================================================================
# Test 9: Security Headers
# ============================================================================
Write-TestHeader "Test 9: Security Headers"

try {
    $response = Invoke-WebRequest -Uri "https://applylens.app/" `
        -Method HEAD `
        -TimeoutSec 10 `
        -UseBasicParsing `
        -ErrorAction Stop
    
    # Check for common security headers
    $securityHeaders = @{
        "X-Frame-Options" = $response.Headers["X-Frame-Options"]
        "X-Content-Type-Options" = $response.Headers["X-Content-Type-Options"]
        "Referrer-Policy" = $response.Headers["Referrer-Policy"]
        "Strict-Transport-Security" = $response.Headers["Strict-Transport-Security"]
    }
    
    foreach ($header in $securityHeaders.GetEnumerator()) {
        if ($header.Value) {
            Write-TestPass "$($header.Key) header present: $($header.Value)"
        } else {
            Write-TestWarning "$($header.Key) header missing"
        }
    }
    
} catch {
    Write-TestFail "Security headers check failed" $_.Exception.Message
}

# ============================================================================
# Test 10: SSL/TLS Certificate
# ============================================================================
Write-TestHeader "Test 10: SSL/TLS Certificate"

try {
    $uri = [System.Uri]"https://applylens.app"
    $request = [System.Net.HttpWebRequest]::Create($uri)
    $request.Timeout = 10000
    $response = $request.GetResponse()
    $cert = $request.ServicePoint.Certificate
    
    if ($cert) {
        $cert2 = [System.Security.Cryptography.X509Certificates.X509Certificate2]$cert
        $expiryDate = $cert2.NotAfter
        $daysUntilExpiry = ($expiryDate - (Get-Date)).Days
        
        Write-TestPass "SSL certificate valid"
        Write-TestInfo "Issued to: $($cert2.Subject)"
        Write-TestInfo "Issued by: $($cert2.Issuer)"
        Write-TestInfo "Expires: $expiryDate ($daysUntilExpiry days)"
        
        if ($daysUntilExpiry -lt 30) {
            Write-TestWarning "SSL certificate expires in less than 30 days!"
        }
    } else {
        Write-TestFail "Could not retrieve SSL certificate"
    }
    
    $response.Close()
} catch {
    Write-TestFail "SSL certificate check failed" $_.Exception.Message
}

# ============================================================================
# Final Summary
# ============================================================================
Write-Summary
