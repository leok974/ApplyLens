#!/usr/bin/env pwsh
# OAuth Configuration Verification Script
# Tests OAuth endpoints and configuration

param(
    [switch]$Local,
    [switch]$Production
)

$ErrorActionPreference = "Continue"
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  OAuth Configuration Verification" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Determine which environment to test
if ($Production) {
    $baseUrl = "https://api.applylens.app"
    $hostname = "api.applylens.app"
    $expectedRedirectUri = "https://api.applylens.app/auth/google/callback"
    Write-Host "🌐 Testing: PRODUCTION" -ForegroundColor Yellow
} else {
    $baseUrl = "http://localhost:8003"
    $hostname = "localhost"
    $expectedRedirectUri = "http://localhost:8003/auth/google/callback"
    Write-Host "🖥️  Testing: LOCAL DEVELOPMENT" -ForegroundColor Yellow
}

Write-Host "   Base URL: $baseUrl" -ForegroundColor Gray
Write-Host "   Expected redirect_uri: $expectedRedirectUri" -ForegroundColor Gray
Write-Host ""

# Test 1: Check environment variables in container
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Test 1: Environment Variables" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

try {
    $envCheck = docker compose -f infra/docker-compose.yml exec -T api python -c @"
from app.settings import settings
import sys
print(f'CLIENT_ID: {settings.GOOGLE_CLIENT_ID[:20]}...' if settings.GOOGLE_CLIENT_ID else 'CLIENT_ID: NOT SET')
print(f'CLIENT_SECRET: {settings.GOOGLE_CLIENT_SECRET[:10]}...' if settings.GOOGLE_CLIENT_SECRET else 'CLIENT_SECRET: NOT SET')
print(f'REDIRECT_URI: {settings.effective_redirect_uri}')
print(f'OAUTH_SCOPES: {settings.GOOGLE_OAUTH_SCOPES}')
sys.exit(0 if settings.GOOGLE_CLIENT_ID and settings.effective_redirect_uri else 1)
"@
    
    Write-Host $envCheck -ForegroundColor Green
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Environment variables configured correctly" -ForegroundColor Green
    } else {
        Write-Host "❌ Environment variables missing or incomplete" -ForegroundColor Red
        Write-Host "   Run: docker compose restart api" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ Could not check environment variables" -ForegroundColor Red
    Write-Host "   Error: $_" -ForegroundColor Yellow
    Write-Host "   Make sure API container is running: docker compose up -d api" -ForegroundColor Yellow
}

Write-Host ""

# Test 2: OAuth Login Redirect
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Test 2: OAuth Login Redirect" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

try {
    $response = $null
    try {
        $response = Invoke-WebRequest `
            -Uri "$baseUrl/auth/google/login" `
            -Method GET `
            -MaximumRedirection 0 `
            -SkipCertificateCheck `
            -UseBasicParsing `
            -ErrorAction SilentlyContinue
    } catch {
        if ($_.Exception.Response) {
            $response = $_.Exception.Response
        }
    }
    
    if ($response) {
        $statusCode = if ($response.StatusCode) { $response.StatusCode.value__ } else { $response.StatusCode }
        
        if ($statusCode -in 301,302,303,307,308) {
            Write-Host "✅ Login endpoint returns redirect (HTTP $statusCode)" -ForegroundColor Green
            
            $location = $response.Headers.Location
            Write-Host "   Location: $location" -ForegroundColor Gray
            
            if ($location -match "accounts\.google\.com") {
                Write-Host "✅ Redirects to Google OAuth" -ForegroundColor Green
            } else {
                Write-Host "❌ Does not redirect to Google" -ForegroundColor Red
            }
            
            # Check for redirect_uri parameter
            if ($location -match "redirect_uri=([^&]+)") {
                $foundRedirectUri = [System.Web.HttpUtility]::UrlDecode($matches[1])
                Write-Host "   Found redirect_uri: $foundRedirectUri" -ForegroundColor Gray
                
                if ($foundRedirectUri -eq $expectedRedirectUri) {
                    Write-Host "✅ redirect_uri matches expected value" -ForegroundColor Green
                } else {
                    Write-Host "⚠️  redirect_uri mismatch!" -ForegroundColor Red
                    Write-Host "   Expected: $expectedRedirectUri" -ForegroundColor Yellow
                    Write-Host "   Found:    $foundRedirectUri" -ForegroundColor Yellow
                }
            } else {
                Write-Host "❌ redirect_uri parameter not found in URL" -ForegroundColor Red
            }
            
            # Check for client_id parameter
            if ($location -match "client_id=([^&]+)") {
                $clientId = [System.Web.HttpUtility]::UrlDecode($matches[1])
                Write-Host "   Found client_id: $($clientId.Substring(0, [Math]::Min(20, $clientId.Length)))..." -ForegroundColor Gray
                Write-Host "✅ client_id parameter present" -ForegroundColor Green
            } else {
                Write-Host "❌ client_id parameter not found" -ForegroundColor Red
            }
        } else {
            Write-Host "❌ Login endpoint returned unexpected status: $statusCode" -ForegroundColor Red
        }
    } else {
        Write-Host "❌ No response from login endpoint" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Login redirect test failed" -ForegroundColor Red
    Write-Host "   Error: $_" -ForegroundColor Yellow
}

Write-Host ""

# Test 3: Callback Route Accessibility
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Test 3: Callback Route Accessibility" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

try {
    $response = $null
    try {
        $response = Invoke-WebRequest `
            -Uri "$baseUrl/auth/google/callback?error=test" `
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
            Write-Host "❌ Callback route returns 404 - route not configured properly" -ForegroundColor Red
            Write-Host "   Check Nginx configuration and restart: docker compose restart nginx" -ForegroundColor Yellow
        } elseif ($statusCode -in 400,401,403) {
            Write-Host "✅ Callback route is accessible (HTTP $statusCode is expected without valid code)" -ForegroundColor Green
        } elseif ($statusCode -eq 200) {
            Write-Host "✅ Callback route responds successfully" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Callback route returned status: $statusCode" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ No response from callback endpoint" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Callback route test failed" -ForegroundColor Red
    Write-Host "   Error: $_" -ForegroundColor Yellow
}

Write-Host ""

# Test 4: Nginx Configuration
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Test 4: Nginx Configuration" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

try {
    $nginxTest = docker compose -f infra/docker-compose.yml exec -T nginx nginx -t 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Nginx configuration is valid" -ForegroundColor Green
    } else {
        Write-Host "❌ Nginx configuration has errors:" -ForegroundColor Red
        Write-Host $nginxTest -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not check Nginx configuration" -ForegroundColor Yellow
}

Write-Host ""

# Summary
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Summary & Next Steps" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 Google Cloud Console Configuration:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   Add this to Authorized redirect URIs:" -ForegroundColor White
Write-Host "   $expectedRedirectUri" -ForegroundColor Green
Write-Host ""
Write-Host "   Add these to Authorized JavaScript origins:" -ForegroundColor White
if ($Production) {
    Write-Host "   https://applylens.app" -ForegroundColor Green
    Write-Host "   https://www.applylens.app" -ForegroundColor Green
} else {
    Write-Host "   http://localhost:5175" -ForegroundColor Green
    Write-Host "   http://localhost:8003" -ForegroundColor Green
}
Write-Host ""

Write-Host "🔧 If you see redirect_uri_mismatch:" -ForegroundColor Yellow
Write-Host "   1. Add the EXACT redirect_uri shown above to Google Cloud Console" -ForegroundColor White
Write-Host "   2. Make sure you're editing the correct OAuth client" -ForegroundColor White
Write-Host "   3. Restart services: docker compose restart api nginx" -ForegroundColor White
Write-Host "   4. Try in Incognito/Private browsing mode" -ForegroundColor White
Write-Host ""

Write-Host "🧪 Manual Test:" -ForegroundColor Yellow
Write-Host "   Open: $baseUrl/auth/google/login" -ForegroundColor White
Write-Host "   Should redirect to Google OAuth consent screen" -ForegroundColor White
Write-Host ""

Write-Host "📚 Documentation:" -ForegroundColor Yellow
Write-Host "   See: infra/docs/OAUTH_SETUP.md" -ForegroundColor White
Write-Host "   Quick ref: OAUTH_QUICK_REF.md" -ForegroundColor White
Write-Host ""
