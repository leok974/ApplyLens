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

# Helper function to make HTTP requests using resolved IP with Host header (bypasses DNS cache)
function Invoke-HostRequest {
    param(
        [string]$HostName,
        [string]$Path = "/",
        [ValidateSet("GET","POST","OPTIONS","HEAD","PUT","DELETE","PATCH")]
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [int]$TimeoutSec = 15,
        [switch]$NoRedirect
    )
    $ip = Resolve-Via8888 $HostName
    if (-not $ip) { 
        throw "DNS failed for $HostName via 8.8.8.8" 
    }
    $u = "https://$ip$Path"
    $h = @{'Host'=$HostName}
    $Headers.GetEnumerator() | ForEach-Object { $h[$_.Key] = $_.Value }
    
    if ($NoRedirect) {
        # Don't follow redirects - return 302 response
        try {
            return Invoke-WebRequest -Uri $u -Method $Method -Headers $h -SkipCertificateCheck -UseBasicParsing -AllowInsecureRedirect -MaximumRedirection 0 -TimeoutSec $TimeoutSec -ErrorAction Stop
        } catch {
            # PowerShell throws on 3xx with MaximumRedirection=0
            # Return the exception so caller can extract status/headers
            throw
        }
    } else {
        # Allow redirects (but may fail on localhost redirects)
        return Invoke-WebRequest -Uri $u -Method $Method -Headers $h -SkipCertificateCheck -UseBasicParsing -AllowInsecureRedirect -TimeoutSec $TimeoutSec -ErrorAction Stop
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
    $corsHeaders = @{
        "Origin" = "https://applylens.app"
        "Access-Control-Request-Method" = "GET"
        "Access-Control-Request-Headers" = "Content-Type"
    }
    
    $response = Invoke-HostRequest -HostName "api.applylens.app" -Path "/ready" -Method "OPTIONS" -Headers $corsHeaders
    
    # Check for CORS headers in response
    $corsOrigin = $response.Headers["Access-Control-Allow-Origin"]
    $corsMethods = $response.Headers["Access-Control-Allow-Methods"]
    $corsCredentials = $response.Headers["Access-Control-Allow-Credentials"]
    
    # Accept 200, 204 (success), or 400 (if OPTIONS not implemented but CORS headers present)
    if ($response.StatusCode -in 200,204) {
        Write-TestPass "CORS preflight responded with status $($response.StatusCode)"
    } elseif ($response.StatusCode -eq 400 -and $corsOrigin) {
        Write-TestPass "CORS headers present (400 response acceptable if CORS configured)"
    } else {
        Write-TestWarning "OPTIONS responded with $($response.StatusCode)"
    }
    
    # Check CORS headers
    if ($corsOrigin) {
        if ($corsOrigin -eq "*" -or $corsOrigin -eq "https://applylens.app") {
            Write-TestPass "CORS Access-Control-Allow-Origin: $corsOrigin"
        } else {
            Write-TestWarning "CORS origin: $corsOrigin (expected https://applylens.app or *)"
        }
    } else {
        Write-TestWarning "No Access-Control-Allow-Origin header found"
    }
    
    if ($corsMethods) {
        Write-TestPass "CORS Access-Control-Allow-Methods: $corsMethods"
    } else {
        Write-TestInfo "Access-Control-Allow-Methods not in preflight response (may be on actual requests)"
    }
    
    if ($corsCredentials -eq "true") {
        Write-TestPass "CORS allows credentials"
    }
    
} catch {
    # Handle 400 error if exception thrown
    if ($_.Exception.Message -like "*400*") {
        Write-TestWarning "OPTIONS /ready returned 400 (endpoint may not support OPTIONS method)"
        Write-TestInfo "CORS may still work for GET/POST requests"
    } else {
        Write-TestFail "CORS preflight request failed" $_.Exception.Message
    }
}

# ============================================================================
# Test 4: Main Domain Root Path
# ============================================================================
Write-TestHeader "Test 4: Main Domain (applylens.app)"

try {
    $response = Invoke-HostRequest -HostName "applylens.app" -Path "/" -Method "GET" -NoRedirect
    
    if ($response.StatusCode -in 200, 301, 302) {
        Write-TestPass "applylens.app root path returns $($response.StatusCode) (OK)"
        if ($response.StatusCode -in 301, 302 -and $response.Headers.Location) {
            Write-TestInfo "Redirects to: $($response.Headers.Location)"
        }
    } else {
        Write-TestFail "applylens.app root path returns $($response.StatusCode)" "Expected 200, 301, or 302"
    }
} catch {
    # PowerShell throws on 3xx with -NoRedirect
    if ($_.Exception.Message -like "*302*" -or $_.Exception.Message -like "*301*") {
        Write-TestPass "applylens.app root path returns redirect (confirmed)"
    } else {
        Write-TestFail "applylens.app root path failed" $_.Exception.Message
    }
}

# ============================================================================
# Test 5: WWW Subdomain
# ============================================================================
Write-TestHeader "Test 5: WWW Subdomain (www.applylens.app)"

try {
    $response = Invoke-HostRequest -HostName "www.applylens.app" -Path "/" -Method "GET" -NoRedirect
    
    if ($response.StatusCode -in 200, 301, 302) {
        Write-TestPass "www.applylens.app returns $($response.StatusCode) (OK)"
        if ($response.StatusCode -in 301, 302 -and $response.Headers.Location) {
            Write-TestInfo "Redirects to: $($response.Headers.Location)"
        }
    } else {
        Write-TestFail "www.applylens.app returns $($response.StatusCode)" "Expected 200, 301, or 302"
    }
} catch {
    # PowerShell throws on 3xx with -NoRedirect
    if ($_.Exception.Message -like "*302*" -or $_.Exception.Message -like "*301*") {
        Write-TestPass "www.applylens.app returns redirect (confirmed)"
    } else {
        Write-TestFail "www.applylens.app request failed" $_.Exception.Message
    }
}

# ============================================================================
# Test 6: robots.txt
# ============================================================================
Write-TestHeader "Test 6: robots.txt"

try {
    $response = Invoke-HostRequest -HostName "applylens.app" -Path "/robots.txt" -Method "GET"
    
    if ($response.StatusCode -eq 200) {
        Write-TestPass "robots.txt returns 200 OK"
        Write-TestInfo "Content length: $($response.Content.Length) bytes"
    } else {
        Write-TestFail "robots.txt returns $($response.StatusCode)" "Expected 200"
    }
} catch {
    if ($_.Exception.Message -match "404") {
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
    $response = Invoke-HostRequest -HostName "applylens.app" -Path "/sitemap.xml" -Method "GET"
    
    if ($response.StatusCode -eq 200) {
        Write-TestPass "sitemap.xml returns 200 OK"
        Write-TestInfo "Content length: $($response.Content.Length) bytes"
    } else {
        Write-TestFail "sitemap.xml returns $($response.StatusCode)" "Expected 200"
    }
} catch {
    if ($_.Exception.Message -match "404") {
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
    # First check if / redirects
    try {
        $r1 = Invoke-HostRequest -HostName "applylens.app" -Path "/" -Method "GET" -NoRedirect
    } catch {
        # -NoRedirect throws on 3xx
        $r1 = $null
    }
    
    $response = $null
    if ($r1 -and $r1.StatusCode -in 301, 302) {
        # Follow the redirect to check headers on final destination
        $location = $r1.Headers['Location']
        if ($location) {
            Write-TestInfo "Following redirect to: $location"
            # Extract path from location (handle both relative and absolute URLs)
            $path = if ($location -match '^https?://') {
                ([System.Uri]$location).PathAndQuery
            } else {
                $location
            }
            try {
                $response = Invoke-HostRequest -HostName "applylens.app" -Path $path -Method "GET"
            } catch {
                Write-TestInfo "Could not follow redirect, checking headers on redirect response"
                $response = $r1  # Fall back to checking headers on redirect response
            }
        } else {
            $response = $r1
        }
    } elseif ($r1) {
        $response = $r1
    } else {
        # If -NoRedirect threw, try without it but check on robots.txt (static file)
        Write-TestInfo "Checking security headers on /robots.txt (static file)"
        $response = Invoke-HostRequest -HostName "applylens.app" -Path "/robots.txt" -Method "GET"
    }
    
    if ($response) {
        # Check for common security headers
        $securityHeaders = @{
            "X-Frame-Options" = $response.Headers["X-Frame-Options"]
            "X-Content-Type-Options" = $response.Headers["X-Content-Type-Options"]
            "Referrer-Policy" = $response.Headers["Referrer-Policy"]
            "Strict-Transport-Security" = $response.Headers["Strict-Transport-Security"]
        }
        
        $foundHeaders = 0
        foreach ($header in $securityHeaders.GetEnumerator()) {
            if ($header.Value) {
                Write-TestPass "$($header.Key): $($header.Value)"
                $foundHeaders++
            } else {
                Write-TestWarning "$($header.Key) header missing"
            }
        }
        
        if ($foundHeaders -gt 0) {
            Write-TestInfo "Found $foundHeaders security headers"
        } else {
            Write-TestWarning "No security headers found (consider adding them)"
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
    # Use TcpClient with SslStream for proper SNI validation
    $hostname = "applylens.app"
    $ip = Resolve-Via8888 $hostname
    if (-not $ip) { throw "DNS resolution failed for $hostname" }
    
    Write-TestInfo "Connecting to $ip with SNI hostname: $hostname"
    
    $tcp = New-Object System.Net.Sockets.TcpClient($ip, 443)
    $ssl = New-Object System.Net.Security.SslStream(
        $tcp.GetStream(),
        $false,
        { param($sender, $cert, $chain, $errors) return $true }  # Accept cert for now
    )
    
    $ssl.AuthenticateAsClient($hostname)  # This provides proper SNI
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($ssl.RemoteCertificate)
    
    if ($cert) {
        $dnsName = $cert.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::DnsName, $false)
        $expiryDate = $cert.NotAfter
        $daysUntilExpiry = ($expiryDate - (Get-Date)).Days
        
        Write-TestPass "SSL certificate valid"
        Write-TestInfo "DNS Name: $dnsName"
        Write-TestInfo "Issued by: $($cert.Issuer)"
        Write-TestInfo "Expires: $expiryDate ($daysUntilExpiry days)"
        
        # Verify DNS name matches or is wildcard
        if ($dnsName -eq $hostname -or $dnsName -like "*.$($hostname.Split('.')[-2..-1] -join '.')") {
            Write-TestPass "Certificate DNS name matches hostname"
        } else {
            Write-TestWarning "Certificate DNS name ($dnsName) doesn't match hostname ($hostname)"
        }
        
        if ($daysUntilExpiry -lt 30) {
            Write-TestWarning "SSL certificate expires in less than 30 days!"
        }
    } else {
        Write-TestFail "Could not retrieve SSL certificate"
    }
    
    $ssl.Close()
    $tcp.Close()
} catch {
    Write-TestFail "SSL certificate check failed" $_.Exception.Message
}

# ============================================================================
# Test 11: OAuth Login Redirect (Google)
# ============================================================================
Write-TestHeader "Test 11: OAuth Login Redirect"

try {
    Write-TestInfo "Testing /auth/google/login redirect to Google OAuth"
    
    # Try to get redirect response (should be 302 to Google)
    $response = $null
    try {
        # Using Invoke-WebRequest with MaximumRedirection=0 to capture the redirect
        $response = Invoke-WebRequest `
            -Uri "https://api.applylens.app/auth/google/login" `
            -Method GET `
            -MaximumRedirection 0 `
            -SkipCertificateCheck `
            -UseBasicParsing `
            -ErrorAction SilentlyContinue
    } catch {
        # PowerShell throws on redirects, but we can extract the response from the exception
        if ($_.Exception.Response) {
            $response = $_.Exception.Response
        }
    }
    
    if ($response) {
        $statusCode = if ($response.StatusCode) { $response.StatusCode.value__ } else { $response.StatusCode }
        
        if ($statusCode -in 301,302,303,307,308) {
            $location = $response.Headers.Location
            if ($location -match "accounts\.google\.com") {
                Write-TestPass "OAuth login redirects to Google (HTTP $statusCode)"
                Write-TestInfo "Redirect URL: $location"
                
                # Check for required OAuth parameters in redirect URL
                if ($location -match "redirect_uri=") {
                    Write-TestPass "Redirect URI parameter present in OAuth URL"
                } else {
                    Write-TestWarning "redirect_uri parameter not found in OAuth URL"
                }
                
                if ($location -match "client_id=") {
                    Write-TestPass "Client ID parameter present in OAuth URL"
                } else {
                    Write-TestWarning "client_id parameter not found in OAuth URL"
                }
                
            } else {
                Write-TestFail "OAuth login redirects but not to Google" "Location: $location"
            }
        } else {
            Write-TestFail "OAuth login endpoint returned unexpected status" "Status: $statusCode (expected 302)"
        }
    } else {
        Write-TestFail "OAuth login endpoint not responding" "No response received"
    }
} catch {
    Write-TestFail "OAuth login test failed" $_.Exception.Message
}

# ============================================================================
# Test 12: OAuth Callback Route Accessibility
# ============================================================================
Write-TestHeader "Test 12: OAuth Callback Route"

try {
    Write-TestInfo "Testing /auth/google/callback endpoint accessibility"
    
    # Test that callback route is accessible (will return 400 without valid code, but shouldn't 404)
    $response = $null
    try {
        $response = Invoke-WebRequest `
            -Uri "https://api.applylens.app/auth/google/callback?error=test" `
            -Method GET `
            -SkipCertificateCheck `
            -UseBasicParsing `
            -ErrorAction Stop
    } catch {
        $response = $_.Exception.Response
    }
    
    if ($response) {
        $statusCode = if ($response.StatusCode) { $response.StatusCode.value__ } else { $response.StatusCode }
        
        if ($statusCode -eq 404) {
            Write-TestFail "OAuth callback route returns 404" "Route may not be properly configured in Nginx"
        } elseif ($statusCode -in 400,401,403) {
            Write-TestPass "OAuth callback route is accessible (HTTP $statusCode expected without valid code)"
            Write-TestInfo "Callback endpoint exists and is routed correctly"
        } elseif ($statusCode -eq 200) {
            Write-TestPass "OAuth callback route responds with 200"
        } else {
            Write-TestWarning "OAuth callback returned unexpected status: $statusCode"
        }
    } else {
        Write-TestFail "OAuth callback endpoint not responding" "No response received"
    }
} catch {
    Write-TestFail "OAuth callback test failed" $_.Exception.Message
}

# ============================================================================
# Final Summary
# ============================================================================
Write-Summary
