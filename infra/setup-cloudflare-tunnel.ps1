# Cloudflare Tunnel Setup Script for ApplyLens (PowerShell)

Write-Host "🚀 ApplyLens Cloudflare Tunnel Setup" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check if cloudflared is installed
$cloudflaredPath = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflaredPath) {
    Write-Host "❌ cloudflared is not installed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install cloudflared first:"
    Write-Host "  Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
    exit 1
}

Write-Host "✅ cloudflared is installed" -ForegroundColor Green
Write-Host ""

# Step 1: Login
Write-Host "Step 1: Authenticate to Cloudflare" -ForegroundColor Yellow
Write-Host "-----------------------------------"
Write-Host "This will open a browser window to authenticate."
Read-Host "Press Enter to continue"
cloudflared tunnel login

$certPath = "$env:USERPROFILE\.cloudflared\cert.pem"
if (-not (Test-Path $certPath)) {
    Write-Host "❌ Authentication failed. cert.pem not found." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Authenticated successfully" -ForegroundColor Green
Write-Host ""

# Step 2: Create tunnel
Write-Host "Step 2: Create Tunnel" -ForegroundColor Yellow
Write-Host "---------------------"
$tunnelName = "applylens"

# Check if tunnel already exists
$existingTunnel = cloudflared tunnel list | Select-String $tunnelName
if ($existingTunnel) {
    Write-Host "⚠️  Tunnel '$tunnelName' already exists." -ForegroundColor Yellow
    $useExisting = Read-Host "Do you want to use the existing tunnel? (y/n)"
    
    if ($useExisting -ne "y") {
        Write-Host "Please delete the existing tunnel first:"
        Write-Host "  cloudflared tunnel delete $tunnelName"
        exit 1
    }
} else {
    Write-Host "Creating tunnel '$tunnelName'..."
    cloudflared tunnel create $tunnelName
}

Write-Host "✅ Tunnel created/confirmed" -ForegroundColor Green
Write-Host ""

# Step 3: Get tunnel UUID
Write-Host "Step 3: Get Tunnel UUID" -ForegroundColor Yellow
Write-Host "-----------------------"
$tunnelList = cloudflared tunnel list | Select-String $tunnelName
if (-not $tunnelList) {
    Write-Host "❌ Could not find tunnel." -ForegroundColor Red
    exit 1
}

# Extract UUID (first column)
$tunnelUUID = ($tunnelList -split '\s+')[0]
if (-not $tunnelUUID) {
    Write-Host "❌ Could not extract tunnel UUID." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Tunnel UUID: $tunnelUUID" -ForegroundColor Green
Write-Host ""

# Step 4: Copy credentials file
Write-Host "Step 4: Copy Credentials File" -ForegroundColor Yellow
Write-Host "------------------------------"
$credsSrc = "$env:USERPROFILE\.cloudflared\$tunnelUUID.json"
$credsDest = "$PSScriptRoot\cloudflared\$tunnelUUID.json"

if (-not (Test-Path $credsSrc)) {
    Write-Host "❌ Credentials file not found at: $credsSrc" -ForegroundColor Red
    exit 1
}

Copy-Item $credsSrc $credsDest -Force
Write-Host "✅ Credentials copied to: $credsDest" -ForegroundColor Green
Write-Host ""

# Step 5: Update config.yml
Write-Host "Step 5: Update Configuration" -ForegroundColor Yellow
Write-Host "----------------------------"
$configFile = "$PSScriptRoot\cloudflared\config.yml"

# Replace placeholder UUID with actual UUID
$configContent = Get-Content $configFile -Raw
$configContent = $configContent -replace '<YOUR_TUNNEL_UUID>', $tunnelUUID
Set-Content $configFile $configContent

Write-Host "✅ Configuration updated with UUID: $tunnelUUID" -ForegroundColor Green
Write-Host ""

# Step 6: Create DNS routes
Write-Host "Step 6: Create DNS Routes" -ForegroundColor Yellow
Write-Host "-------------------------"
$domain = Read-Host "Please enter your domain (e.g., applylens.app)"

if (-not $domain) {
    Write-Host "❌ Domain cannot be empty." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Creating DNS routes..."

# Create DNS routes
cloudflared tunnel route dns $tunnelName $domain
cloudflared tunnel route dns $tunnelName "www.$domain"

$addKibana = Read-Host "Do you want to add kibana.$domain? (y/n)"
if ($addKibana -eq "y") {
    cloudflared tunnel route dns $tunnelName "kibana.$domain"
}

$addGrafana = Read-Host "Do you want to add grafana.$domain? (y/n)"
if ($addGrafana -eq "y") {
    cloudflared tunnel route dns $tunnelName "grafana.$domain"
}

Write-Host "✅ DNS routes created" -ForegroundColor Green
Write-Host ""

# Step 7: Update config.yml with domain
Write-Host "Updating config.yml with your domain..."
$configContent = Get-Content $configFile -Raw
$configContent = $configContent -replace 'applylens\.app', $domain
Set-Content $configFile $configContent

Write-Host "✅ Configuration updated with domain: $domain" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "🎉 Setup Complete!" -ForegroundColor Cyan
Write-Host "=================="
Write-Host ""
Write-Host "Tunnel Details:"
Write-Host "  - Name: $tunnelName"
Write-Host "  - UUID: $tunnelUUID"
Write-Host "  - Domain: $domain"
Write-Host ""
Write-Host "Next Steps:"
Write-Host "  1. Start the tunnel:"
Write-Host "     cd $PSScriptRoot"
Write-Host "     docker compose up -d cloudflared"
Write-Host ""
Write-Host "  2. Check logs:"
Write-Host "     docker compose logs -f cloudflared"
Write-Host ""
Write-Host "  3. Test your endpoint:"
Write-Host "     curl https://$domain/health"
Write-Host ""
Write-Host "See cloudflared/README.md for more information."
