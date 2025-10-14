# Cloudflare Tunnel Quick Start

**Goal:** Get applylens.app routing traffic through Cloudflare Tunnel in 10 minutes.

## Prerequisites

- [ ] Production server running docker-compose.prod.yml
- [ ] Domain (applylens.app) managed in Cloudflare
- [ ] SSH access to production server

## Steps

### 1. Install cloudflared (5 min)

```bash
# SSH to production server
ssh user@your-server

# Install cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Verify installation
cloudflared --version
```

### 2. Create Tunnel (3 min)

```bash
# Login (opens browser for auth)
cloudflared tunnel login

# Create tunnel named "applylens"
cloudflared tunnel create applylens

# Note the Tunnel ID from output
# Example: "Created tunnel applylens with id abc123-def456-..."
```

### 3. Configure Tunnel (2 min)

```bash
# Create config directory
sudo mkdir -p /etc/cloudflared

# Create config file
sudo nano /etc/cloudflared/config.yml
```

Paste this config:

```yaml
tunnel: YOUR_TUNNEL_ID_HERE
credentials-file: /root/.cloudflared/YOUR_TUNNEL_ID_HERE.json

ingress:
  - hostname: applylens.app
    service: http://localhost:80
  - hostname: www.applylens.app
    service: http://localhost:80
  - service: http_status:404
```

Replace `YOUR_TUNNEL_ID_HERE` with the actual tunnel ID from step 2.

### 4. Route DNS (1 min)

```bash
# Route your domain to the tunnel
cloudflared tunnel route dns applylens applylens.app
cloudflared tunnel route dns applylens www.applylens.app
```

This creates CNAME records in Cloudflare pointing to your tunnel.

### 5. Start Everything (1 min)

```bash
# Navigate to project directory
cd /path/to/applylens

# Start production stack with Cloudflare tunnel
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

Alternatively, start tunnel as system service:

```bash
# Install as service
sudo cloudflared service install

# Start service
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

### 6. Verify (1 min)

```bash
# Check tunnel status
cloudflared tunnel info applylens

# Test internal nginx
curl -I http://localhost/

# Test external access
curl -I https://applylens.app/
```

✅ Look for `cf-ray` header in the external test - this confirms Cloudflare routing!

## Cloudflare Dashboard Settings

Go to https://dash.cloudflare.com/ → Select your domain:

1. **SSL/TLS Mode:** Set to "Full" (not Full (strict))
2. **Always Use HTTPS:** Enable
3. **DNS:** Verify CNAME records exist for applylens.app and www.applylens.app

## Docker Compose Method

If using docker-compose.prod.yml's cloudflared service:

```bash
# Create cloudflared config directory
mkdir -p infra/cloudflared

# Copy credentials
sudo cp /root/.cloudflared/YOUR_TUNNEL_ID_HERE.json infra/cloudflared/credentials.json

# Create config
cat > infra/cloudflared/config.yml << EOF
tunnel: YOUR_TUNNEL_ID_HERE
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - hostname: applylens.app
    service: http://nginx:80
  - hostname: www.applylens.app
    service: http://nginx:80
  - service: http_status:404
EOF

# Start with Cloudflare profile
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

Note: When using docker-compose, the service is `http://nginx:80` (Docker network), not `http://localhost:80`.

## Common Issues

### Issue: Tunnel won't start
**Check:** Credentials file path in config.yml
```bash
# List credentials files
ls -la ~/.cloudflared/
sudo ls -la /root/.cloudflared/
```

### Issue: 502 Bad Gateway
**Check:** nginx is running and accessible
```bash
docker compose -f docker-compose.prod.yml ps nginx
curl http://localhost/
```

### Issue: DNS not resolving
**Check:** DNS propagation (can take a few minutes)
```bash
dig applylens.app
nslookup applylens.app
```

### Issue: OAuth callback 404
**Fix:** Update Google OAuth redirect URI to `https://applylens.app/auth/google/callback`

## Service URLs

Once running:

- 🌐 Frontend: https://applylens.app/web/
- 📡 API: https://applylens.app/
- 📚 API Docs: https://applylens.app/docs/
- 📊 Grafana: https://applylens.app/grafana/
- 🔍 Kibana: https://applylens.app/kibana/
- 📈 Prometheus: https://applylens.app/prometheus/

## Architecture

```
User Browser
    ↓
Cloudflare Edge (SSL termination)
    ↓
Cloudflare Tunnel (encrypted)
    ↓
nginx:80 (reverse proxy)
    ↓
    ├── web:5175 (React frontend)
    ├── api:8003 (FastAPI backend)
    ├── grafana:3000 (monitoring)
    ├── kibana:5601 (analytics)
    └── prometheus:9090 (metrics)
```

## Next Steps

- [ ] Configure Google OAuth with https://applylens.app redirect
- [ ] Set up basic auth for monitoring tools (see PRODUCTION_DOMAIN_SETUP.md)
- [ ] Enable Cloudflare firewall rules
- [ ] Set up automated backups
- [ ] Configure Grafana dashboards

## Full Documentation

For detailed configuration, troubleshooting, and security settings:
- See `CLOUDFLARE_TUNNEL_SETUP.md`
- See `PRODUCTION_DOMAIN_SETUP.md`
- See `PROD_DOMAIN_QUICK_REF.md`

---

**Done!** 🚀 Your production deployment should now be accessible at https://applylens.app/
