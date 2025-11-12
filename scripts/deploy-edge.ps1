# ApplyLens Edge Deployment Script
# This script automates the migration from Cloudflare Tunnel to Edge Nginx + Let's Encrypt

param(
    [Parameter(Mandatory=$true)]
    [string]$PublicIP,

    [Parameter(Mandatory=$false)]
    [switch]$SkipDNSCheck,

    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  ApplyLens Edge Deployment - Cloudflare Tunnel → Nginx      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# Configuration
$ApplyLensRoot = "D:\ApplyLens"
$Domains = @("applylens.app", "api.applylens.app")

# Helper Functions
function Write-Step {
    param([string]$Message)
    Write-Host "`n▶ $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "  ✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "  ✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "  ℹ $Message" -ForegroundColor Cyan
}

function Test-Port {
    param([int]$Port)
    $listener = netstat -ano | Select-String ":$Port " | Select-String "LISTENING"
    return $listener.Count -gt 0
}

# Step 1: Pre-flight Checks
Write-Step "Step 1: Pre-flight Checks"

if (Test-Port -Port 80) {
    $port80 = netstat -ano | Select-String ":80 " | Select-String "LISTENING" | Select-Object -First 1
    Write-Info "Port 80 is in use:"
    Write-Host "  $port80"

    $aiFinance = docker ps --format "{{.Names}}" | Select-String "ai-finance.*nginx"
    if ($aiFinance) {
        Write-Info "Found AI finance nginx: $aiFinance"
        if (-not $DryRun) {
            Write-Info "Stopping AI finance nginx..."
            docker stop $aiFinance | Out-Null
            Write-Success "AI finance nginx stopped"
        } else {
            Write-Info "[DRY RUN] Would stop: $aiFinance"
        }
    }
}

if (Test-Port -Port 443) {
    Write-Info "Port 443 is in use"
}

# Verify Docker is running
try {
    docker ps | Out-Null
    Write-Success "Docker is running"
} catch {
    Write-Error "Docker is not running or not accessible"
    exit 1
}

# Verify applylens-prod network exists
$network = docker network ls | Select-String "applylens_applylens-prod"
if ($network) {
    Write-Success "applylens-prod network exists"
} else {
    Write-Error "applylens-prod network not found"
    Write-Info "Run: docker compose -f docker-compose.prod.yml up -d"
    exit 1
}

# Verify web and api containers are running
$web = docker ps | Select-String "applylens-web-prod"
$api = docker ps | Select-String "applylens-api-prod"
if ($web -and $api) {
    Write-Success "web and api containers are running"
} else {
    Write-Error "web or api containers not running"
    exit 1
}

# Step 2: DNS Check
if (-not $SkipDNSCheck) {
    Write-Step "Step 2: DNS Verification"
    Write-Info "Checking DNS for domains..."

    foreach ($domain in $Domains) {
        $dns = Resolve-DnsName -Name $domain -Type A -ErrorAction SilentlyContinue
        if ($dns) {
            $resolvedIP = $dns | Where-Object { $_.Type -eq "A" } | Select-Object -First 1 -ExpandProperty IPAddress
            Write-Info "$domain → $resolvedIP"

            if ($resolvedIP -ne $PublicIP) {
                Write-Error "DNS for $domain does not point to $PublicIP"
                Write-Info "Current: $resolvedIP"
                Write-Info "Expected: $PublicIP"
                Write-Info ""
                Write-Info "Please update Cloudflare DNS:"
                Write-Info "  1. Go to https://dash.cloudflare.com/"
                Write-Info "  2. DNS → Records"
                Write-Info "  3. Update A record for $domain to $PublicIP (Proxied)"
                Write-Info ""
                Write-Info "Then re-run with -SkipDNSCheck to continue"
                exit 1
            } else {
                Write-Success "DNS for $domain is correct"
            }
        } else {
            Write-Error "Could not resolve DNS for $domain"
            exit 1
        }
    }
} else {
    Write-Step "Step 2: DNS Verification (Skipped)"
}

# Step 3: Start Edge Nginx (HTTP Only)
Write-Step "Step 3: Start Edge Nginx (HTTP Only)"

if (-not $DryRun) {
    Push-Location $ApplyLensRoot
    docker compose -f docker-compose.edge.yml up -d edge-nginx
    Pop-Location

    Start-Sleep -Seconds 3

    $edgeRunning = docker ps | Select-String "applylens-edge"
    if ($edgeRunning) {
        Write-Success "Edge nginx started"
    } else {
        Write-Error "Edge nginx failed to start"
        docker logs applylens-edge 2>&1 | Select-Object -Last 20
        exit 1
    }

    # Test HTTP endpoint
    try {
        $response = Invoke-WebRequest -Uri "http://localhost/" -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "HTTP endpoint responding"
        }
    } catch {
        Write-Error "HTTP endpoint not responding"
        exit 1
    }
} else {
    Write-Info "[DRY RUN] Would start edge-nginx"
}

# Step 4: Obtain Let's Encrypt Certificates
Write-Step "Step 4: Obtain Let's Encrypt Certificates"

foreach ($domain in $Domains) {
    Write-Info "Obtaining certificate for $domain..."

    if (-not $DryRun) {
        $certPath = "$ApplyLensRoot\letsencrypt\live\$domain\fullchain.pem"

        if (Test-Path $certPath) {
            Write-Info "Certificate already exists for $domain"

            # Check expiry
            $cert = docker run --rm `
                -v "${ApplyLensRoot}\letsencrypt:/etc/letsencrypt" `
                certbot/certbot certificates -d $domain 2>&1 | Select-String "Expiry Date"
            Write-Info $cert
        } else {
            Write-Info "Requesting new certificate for $domain..."

            docker run --rm `
                -v "${ApplyLensRoot}\infra\nginx\edge\www:/var/www/certbot" `
                -v "${ApplyLensRoot}\letsencrypt:/etc/letsencrypt" `
                certbot/certbot certonly --webroot -w /var/www/certbot `
                -d $domain --register-unsafely-without-email --agree-tos

            if (Test-Path $certPath) {
                Write-Success "Certificate obtained for $domain"
            } else {
                Write-Error "Failed to obtain certificate for $domain"
                Write-Info "Common issues:"
                Write-Info "  - DNS not pointing to this server"
                Write-Info "  - Port 80 not accessible from internet"
                Write-Info "  - Cloudflare proxy blocking Let's Encrypt"
                exit 1
            }
        }
    } else {
        Write-Info "[DRY RUN] Would request certificate for $domain"
    }
}

# Step 5: Enable HTTPS Configuration
Write-Step "Step 5: Enable HTTPS Configuration"

$httpsConfig = "$ApplyLensRoot\infra\nginx\edge\conf.d\10-https.conf"
$httpsConfigDisabled = "$httpsConfig.disabled"

if (-not $DryRun) {
    if (Test-Path $httpsConfigDisabled) {
        Rename-Item -Path $httpsConfigDisabled -NewName "10-https.conf"
        Write-Success "HTTPS config enabled"
    } elseif (Test-Path $httpsConfig) {
        Write-Info "HTTPS config already enabled"
    } else {
        Write-Error "HTTPS config not found"
        exit 1
    }

    # Update HTTP config to enable redirect
    $httpConfig = "$ApplyLensRoot\infra\nginx\edge\conf.d\00-http.conf"
    $httpContent = Get-Content $httpConfig -Raw

    if ($httpContent -match "return 200") {
        Write-Info "Updating HTTP config to enable HTTPS redirect..."
        $httpContent = $httpContent -replace '(?s)# Temporary:.*?# }', '# Redirect everything else to HTTPS
  location / {
    return 301 https://$host$request_uri;
  }'
        Set-Content -Path $httpConfig -Value $httpContent
        Write-Success "HTTP redirect enabled"
    } else {
        Write-Info "HTTP redirect already enabled"
    }

    # Test and reload nginx
    Write-Info "Testing nginx configuration..."
    $testResult = docker exec applylens-edge nginx -t 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Nginx config is valid"

        Write-Info "Reloading nginx..."
        docker exec applylens-edge nginx -s reload
        Write-Success "Nginx reloaded with HTTPS config"
    } else {
        Write-Error "Nginx config test failed:"
        Write-Host $testResult
        exit 1
    }
} else {
    Write-Info "[DRY RUN] Would enable HTTPS config and reload nginx"
}

# Step 6: Start Certbot Auto-Renewal
Write-Step "Step 6: Start Certbot Auto-Renewal"

if (-not $DryRun) {
    Push-Location $ApplyLensRoot
    docker compose -f docker-compose.edge.yml up -d certbot
    Pop-Location

    Start-Sleep -Seconds 2

    $certbotRunning = docker ps | Select-String "certbot"
    if ($certbotRunning) {
        Write-Success "Certbot auto-renewal started"
    } else {
        Write-Error "Certbot failed to start"
        exit 1
    }
} else {
    Write-Info "[DRY RUN] Would start certbot container"
}

# Step 7: Verification
Write-Step "Step 7: Verification"

if (-not $DryRun) {
    Start-Sleep -Seconds 5

    foreach ($domain in $Domains) {
        Write-Info "Testing HTTPS for $domain..."

        try {
            $response = Invoke-WebRequest -Uri "https://$domain/" -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Success "HTTPS working for $domain"

                $server = $response.Headers["Server"]
                $cfRay = $response.Headers["CF-RAY"]

                if ($server -eq "cloudflare" -and $cfRay) {
                    Write-Success "Cloudflare proxy active (CF-RAY: $cfRay)"
                } else {
                    Write-Info "Note: Cloudflare headers not present (may need DNS propagation)"
                }
            }
        } catch {
            $errorMsg = $_.Exception.Message
            Write-Error "HTTPS test failed for ${domain}: $errorMsg"
        }
    }

    # Test API health
    Write-Info "Testing API health..."
    try {
        $health = Invoke-RestMethod -Uri "https://api.applylens.app/healthz"
        if ($health.status -eq "ok") {
            Write-Success "API health check passed"
        }
    } catch {
        $errorMsg = $_.Exception.Message
        Write-Error "API health check failed: $errorMsg"
    }
} else {
    Write-Info "[DRY RUN] Would verify HTTPS endpoints"
}

# Summary
Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✓ Edge Deployment Complete!                                ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "  1. Update Cloudflare SSL/TLS settings:" -ForegroundColor White
Write-Host "     - Go to: https://dash.cloudflare.com/ → SSL/TLS" -ForegroundColor Gray
Write-Host "     - Set encryption mode to: Full (strict)" -ForegroundColor Gray
Write-Host "     - Enable: Always Use HTTPS" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Remove Cloudflare Tunnel public hostnames:" -ForegroundColor White
Write-Host "     - Go to: https://one.dash.cloudflare.com/ → Networks → Tunnels" -ForegroundColor Gray
Write-Host "     - Remove: applylens.app and api.applylens.app mappings" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Configure Cloudflare cache rules (optional):" -ForegroundColor White
Write-Host "     - Cache: /assets/* (long TTL)" -ForegroundColor Gray
Write-Host "     - Bypass: /api/* and /healthz" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Monitor for 24 hours:" -ForegroundColor White
Write-Host "     - Run: .\scripts\watch-prod-health.ps1" -ForegroundColor Gray
Write-Host "     - Check: docker logs -f applylens-edge" -ForegroundColor Gray
Write-Host ""

Write-Host "Documentation: D:\ApplyLens\EDGE_DEPLOYMENT_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
