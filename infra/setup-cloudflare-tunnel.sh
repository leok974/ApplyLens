#!/bin/bash
# Cloudflare Tunnel Setup Script for ApplyLens

set -e

echo "🚀 ApplyLens Cloudflare Tunnel Setup"
echo "===================================="
echo ""

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared is not installed."
    echo ""
    echo "Please install cloudflared first:"
    echo "  - Windows: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
    echo "  - macOS: brew install cloudflared"
    echo "  - Linux: https://pkg.cloudflare.com/"
    exit 1
fi

echo "✅ cloudflared is installed"
echo ""

# Step 1: Login
echo "Step 1: Authenticate to Cloudflare"
echo "-----------------------------------"
echo "This will open a browser window to authenticate."
read -p "Press Enter to continue..."
cloudflared tunnel login

if [ ! -f ~/.cloudflared/cert.pem ]; then
    echo "❌ Authentication failed. cert.pem not found."
    exit 1
fi

echo "✅ Authenticated successfully"
echo ""

# Step 2: Create tunnel
echo "Step 2: Create Tunnel"
echo "---------------------"
TUNNEL_NAME="applylens"

# Check if tunnel already exists
if cloudflared tunnel list | grep -q "$TUNNEL_NAME"; then
    echo "⚠️  Tunnel '$TUNNEL_NAME' already exists."
    read -p "Do you want to use the existing tunnel? (y/n): " use_existing
    
    if [ "$use_existing" != "y" ]; then
        echo "Please delete the existing tunnel first:"
        echo "  cloudflared tunnel delete $TUNNEL_NAME"
        exit 1
    fi
else
    echo "Creating tunnel '$TUNNEL_NAME'..."
    cloudflared tunnel create $TUNNEL_NAME
fi

echo "✅ Tunnel created/confirmed"
echo ""

# Step 3: Get tunnel UUID
echo "Step 3: Get Tunnel UUID"
echo "-----------------------"
TUNNEL_UUID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')

if [ -z "$TUNNEL_UUID" ]; then
    echo "❌ Could not find tunnel UUID."
    exit 1
fi

echo "✅ Tunnel UUID: $TUNNEL_UUID"
echo ""

# Step 4: Copy credentials file
echo "Step 4: Copy Credentials File"
echo "------------------------------"
CREDS_SRC="$HOME/.cloudflared/$TUNNEL_UUID.json"
CREDS_DEST="$(dirname "$0")/cloudflared/$TUNNEL_UUID.json"

if [ ! -f "$CREDS_SRC" ]; then
    echo "❌ Credentials file not found at: $CREDS_SRC"
    exit 1
fi

cp "$CREDS_SRC" "$CREDS_DEST"
chmod 600 "$CREDS_DEST"

echo "✅ Credentials copied to: $CREDS_DEST"
echo ""

# Step 5: Update config.yml
echo "Step 5: Update Configuration"
echo "----------------------------"
CONFIG_FILE="$(dirname "$0")/cloudflared/config.yml"

# Replace placeholder UUID with actual UUID
sed -i.bak "s/<YOUR_TUNNEL_UUID>/$TUNNEL_UUID/g" "$CONFIG_FILE"
rm -f "$CONFIG_FILE.bak"

echo "✅ Configuration updated with UUID: $TUNNEL_UUID"
echo ""

# Step 6: Create DNS routes
echo "Step 6: Create DNS Routes"
echo "-------------------------"
echo "Please enter your domain (e.g., applylens.app):"
read -p "Domain: " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "❌ Domain cannot be empty."
    exit 1
fi

echo ""
echo "Creating DNS routes..."

# Create DNS routes
cloudflared tunnel route dns $TUNNEL_NAME $DOMAIN
cloudflared tunnel route dns $TUNNEL_NAME www.$DOMAIN

read -p "Do you want to add kibana.$DOMAIN? (y/n): " add_kibana
if [ "$add_kibana" = "y" ]; then
    cloudflared tunnel route dns $TUNNEL_NAME kibana.$DOMAIN
fi

read -p "Do you want to add grafana.$DOMAIN? (y/n): " add_grafana
if [ "$add_grafana" = "y" ]; then
    cloudflared tunnel route dns $TUNNEL_NAME grafana.$DOMAIN
fi

echo "✅ DNS routes created"
echo ""

# Step 7: Update config.yml with domain
echo "Updating config.yml with your domain..."
sed -i.bak "s/applylens\.app/$DOMAIN/g" "$CONFIG_FILE"
rm -f "$CONFIG_FILE.bak"

echo "✅ Configuration updated with domain: $DOMAIN"
echo ""

# Summary
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Tunnel Details:"
echo "  - Name: $TUNNEL_NAME"
echo "  - UUID: $TUNNEL_UUID"
echo "  - Domain: $DOMAIN"
echo ""
echo "Next Steps:"
echo "  1. Start the tunnel:"
echo "     cd $(dirname "$0")"
echo "     docker compose up -d cloudflared"
echo ""
echo "  2. Check logs:"
echo "     docker compose logs -f cloudflared"
echo ""
echo "  3. Test your endpoint:"
echo "     curl https://$DOMAIN/health"
echo ""
echo "See cloudflared/README.md for more information."
