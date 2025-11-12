# Test Port Forwarding and DNS
# Run this after configuring router and disabling Cloudflare proxy

$ErrorActionPreference = "SilentlyContinue"

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🔍 Port Forwarding & DNS Test                                ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# Get public IP
$pub = (Invoke-WebRequest https://api.ipify.org -UseBasicParsing).Content
Write-Host "`n  Public IP: $pub" -ForegroundColor Cyan

# Test DNS
Write-Host "`n  📍 DNS Resolution:" -ForegroundColor Yellow
$dns1 = Resolve-DnsName applylens.app -Type A | Where-Object {$_.Type -eq 'A'} | Select-Object -First 1
$dns2 = Resolve-DnsName api.applylens.app -Type A | Where-Object {$_.Type -eq 'A'} | Select-Object -First 1

if ($dns1.IPAddress -eq $pub) {
    Write-Host "    ✓ applylens.app → $($dns1.IPAddress)" -ForegroundColor Green
} else {
    Write-Host "    ✗ applylens.app → $($dns1.IPAddress) (Expected: $pub)" -ForegroundColor Red
}

if ($dns2.IPAddress -eq $pub) {
    Write-Host "    ✓ api.applylens.app → $($dns2.IPAddress)" -ForegroundColor Green
} else {
    Write-Host "    ✗ api.applylens.app → $($dns2.IPAddress) (Expected: $pub)" -ForegroundColor Red
}

# Test ports
Write-Host "`n  📍 Port Connectivity:" -ForegroundColor Yellow
$test80 = Test-NetConnection -ComputerName $pub -Port 80 -InformationLevel Quiet -WarningAction SilentlyContinue
$test443 = Test-NetConnection -ComputerName $pub -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue

if ($test80) {
    Write-Host "    ✓ Port 80 is OPEN and reachable" -ForegroundColor Green
} else {
    Write-Host "    ✗ Port 80 is CLOSED (router not forwarding)" -ForegroundColor Red
}

if ($test443) {
    Write-Host "    ✓ Port 443 is OPEN and reachable" -ForegroundColor Green
} else {
    Write-Host "    ✗ Port 443 is CLOSED (router not forwarding)" -ForegroundColor Red
}

# Summary
Write-Host "`n  📊 Summary:" -ForegroundColor Yellow
$dnsOk = ($dns1.IPAddress -eq $pub) -and ($dns2.IPAddress -eq $pub)
$portsOk = $test80 -and $test443

if ($dnsOk -and $portsOk) {
    Write-Host "    ✓ All checks passed! Ready for certificate acquisition." -ForegroundColor Green
    Write-Host "`n  🚀 Next step: Run certificate acquisition commands" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "    ⚠️  Issues found:" -ForegroundColor Yellow
    if (-not $dnsOk) {
        Write-Host "      • DNS not resolving correctly (disable Cloudflare proxy)" -ForegroundColor Red
    }
    if (-not $portsOk) {
        Write-Host "      • Ports not open (configure router port forwarding)" -ForegroundColor Red
    }
    Write-Host "`n  ⏸️  Fix issues and run this test again" -ForegroundColor Cyan
    exit 1
}
