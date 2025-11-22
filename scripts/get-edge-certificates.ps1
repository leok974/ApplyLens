# Get Certificates for All Domains
# Run this after DNS is updated and edge-nginx is running with HTTP-only config

param(
    [Parameter(Mandatory=$false)]
    [switch]$SkipApplyLens,

    [Parameter(Mandatory=$false)]
    [switch]$SkipAIFinance,

    [Parameter(Mandatory=$false)]
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Let's Encrypt Certificate Acquisition                      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# Domains to process
$domains = @()

if (-not $SkipApplyLens) {
    $domains += @{
        Name = "applylens.app"
        Description = "ApplyLens Web"
    }
    $domains += @{
        Name = "api.applylens.app"
        Description = "ApplyLens API"
    }
}

if (-not $SkipAIFinance) {
    $domains += @{
        Name = "assistant.ledger-mind.org"
        Description = "AI-finance / Ledger-Mind"
    }
}

if ($domains.Count -eq 0) {
    Write-Host "`n⚠️  No domains selected (both -SkipApplyLens and -SkipAIFinance specified)" -ForegroundColor Yellow
    exit 1
}

# Change to ApplyLens directory
$ApplyLensRoot = "D:\ApplyLens"
Push-Location $ApplyLensRoot

Write-Host "`n📋 Processing $($domains.Count) domain(s):`n" -ForegroundColor Cyan
$domains | ForEach-Object {
    Write-Host "  • $($_.Name) - $($_.Description)" -ForegroundColor White
}

# Pre-flight checks
Write-Host "`n🔍 Pre-flight Checks:" -ForegroundColor Yellow

# Check edge-nginx is running
$edgeNginx = docker ps | Select-String "edge-nginx"
if (-not $edgeNginx) {
    Write-Host "  ✗ edge-nginx is not running" -ForegroundColor Red
    Write-Host "`n  Please start edge-nginx first:" -ForegroundColor Yellow
    Write-Host "    docker compose -f docker-compose.edge.yml up -d edge-nginx" -ForegroundColor Gray
    exit 1
}
Write-Host "  ✓ edge-nginx is running" -ForegroundColor Green

# Check HTTP endpoint is accessible
try {
    $response = Invoke-WebRequest -Uri "http://localhost/" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✓ HTTP endpoint responding" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ HTTP endpoint not accessible" -ForegroundColor Red
    Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Gray
    exit 1
}

# Check DNS resolution
Write-Host "`n🌐 DNS Resolution:" -ForegroundColor Yellow
$dnsFailures = 0
foreach ($domain in $domains) {
    try {
        $dns = Resolve-DnsName -Name $domain.Name -Type A -ErrorAction Stop
        $ip = $dns | Where-Object { $_.Type -eq "A" } | Select-Object -First 1 -ExpandProperty IPAddress
        Write-Host "  ✓ $($domain.Name) → $ip" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ $($domain.Name) - DNS resolution failed" -ForegroundColor Red
        $dnsFailures++
    }
}

if ($dnsFailures -gt 0) {
    Write-Host "`n⚠️  DNS resolution failed for $dnsFailures domain(s)" -ForegroundColor Yellow
    Write-Host "  Please update Cloudflare DNS and wait 2-3 minutes for propagation" -ForegroundColor Gray

    if (-not $Force) {
        Write-Host "`n  Use -Force to continue anyway (not recommended)" -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "`n  ⚠️  Continuing anyway due to -Force flag..." -ForegroundColor Yellow
    }
}

# Process each domain
Write-Host "`n🔐 Obtaining Certificates:" -ForegroundColor Yellow

$successCount = 0
$skipCount = 0
$failCount = 0

foreach ($domain in $domains) {
    $domainName = $domain.Name
    $certPath = "$ApplyLensRoot\letsencrypt\live\$domainName\fullchain.pem"

    Write-Host "`n  📜 $domainName ($($domain.Description))..." -ForegroundColor Cyan

    # Check if certificate already exists
    if (Test-Path $certPath) {
        Write-Host "    ℹ️  Certificate already exists" -ForegroundColor Yellow

        # Check expiry
        try {
            $certInfo = docker run --rm `
                -v "${ApplyLensRoot}\letsencrypt:/etc/letsencrypt" `
                certbot/certbot certificates -d $domainName 2>&1 | Out-String

            if ($certInfo -match "Expiry Date: (.+)") {
                $expiryDate = $matches[1].Trim()
                Write-Host "    📅 Expiry: $expiryDate" -ForegroundColor Gray
            }

            if ($certInfo -match "Certificate will not expire") {
                Write-Host "    ✓ Certificate is valid" -ForegroundColor Green
            }

            if (-not $Force) {
                Write-Host "    ⏭️  Skipping (use -Force to renew)" -ForegroundColor Yellow
                $skipCount++
                continue
            } else {
                Write-Host "    🔄 Forcing renewal..." -ForegroundColor Yellow
            }
        } catch {
            Write-Host "    ⚠️  Could not check certificate status" -ForegroundColor Yellow
        }
    }

    # Request certificate
    Write-Host "    🔄 Requesting certificate from Let's Encrypt..." -ForegroundColor Cyan

    $certbotArgs = @(
        "certonly"
        "--webroot"
        "-w", "/var/www/certbot"
        "-d", $domainName
        "--register-unsafely-without-email"
        "--agree-tos"
    )

    if ($Force) {
        $certbotArgs += "--force-renewal"
    }

    try {
        $output = docker run --rm `
            -v "${ApplyLensRoot}\infra\nginx\edge\www:/var/www/certbot" `
            -v "${ApplyLensRoot}\letsencrypt:/etc/letsencrypt" `
            certbot/certbot $certbotArgs 2>&1

        if ($LASTEXITCODE -eq 0 -and (Test-Path $certPath)) {
            Write-Host "    ✓ Certificate obtained successfully" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "    ✗ Certificate request failed" -ForegroundColor Red
            Write-Host "`n$output" -ForegroundColor Gray
            $failCount++
        }
    } catch {
        Write-Host "    ✗ Certificate request failed: $($_.Exception.Message)" -ForegroundColor Red
        $failCount++
    }
}

# Summary
Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Certificate Acquisition Summary                             ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`n  ✓ Success: $successCount" -ForegroundColor Green
if ($skipCount -gt 0) {
    Write-Host "  ⏭️  Skipped: $skipCount (already exist)" -ForegroundColor Yellow
}
if ($failCount -gt 0) {
    Write-Host "  ✗ Failed:  $failCount" -ForegroundColor Red
}

if ($failCount -gt 0) {
    Write-Host "`n⚠️  Some certificate requests failed. Common issues:" -ForegroundColor Yellow
    Write-Host "  1. DNS not pointing to your server (check with: nslookup <domain>)" -ForegroundColor Gray
    Write-Host "  2. Port 80 not accessible from internet (test: https://canyouseeme.org/)" -ForegroundColor Gray
    Write-Host "  3. Windows Firewall blocking port 80" -ForegroundColor Gray
    Write-Host "  4. nginx not serving ACME challenge path correctly" -ForegroundColor Gray
    exit 1
}

if ($successCount -gt 0) {
    Write-Host "`n✅ Certificates obtained successfully!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "  1. Enable HTTPS config:" -ForegroundColor White
    Write-Host "     Rename-Item `".\infra\nginx\edge\conf.d\10-https.conf.disabled`" -NewName `"10-https.conf`"" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Enable HTTP→HTTPS redirect in 00-http.conf" -ForegroundColor White
    Write-Host ""
    Write-Host "  3. Test and reload nginx:" -ForegroundColor White
    Write-Host "     docker exec edge-nginx nginx -t" -ForegroundColor Gray
    Write-Host "     docker exec edge-nginx nginx -s reload" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  4. Start certbot auto-renewal:" -ForegroundColor White
    Write-Host "     docker compose -f docker-compose.edge.yml up -d certbot" -ForegroundColor Gray
    Write-Host ""
} elseif ($skipCount -eq $domains.Count) {
    Write-Host "`n✅ All certificates already exist!" -ForegroundColor Green
    Write-Host "`n  If HTTPS is not yet enabled, run the next steps from UNIFIED_EDGE_QUICKSTART.md" -ForegroundColor Cyan
}

Pop-Location
