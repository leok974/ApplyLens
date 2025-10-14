# Cloudflare Tunnel Configuration for ApplyLens Production

This document describes how to configure Cloudflare Tunnel to route traffic from **applylens.app** to your production deployment.

## Overview

```
Internet → Cloudflare Edge → Cloudflare Tunnel → nginx:80 → api/web services
```

**Key Points:**
- Cloudflare handles SSL/TLS termination
- Tunnel connects to nginx service (not directly to API/web)
- nginx reverse-proxies to internal services based on path

## Configuration

### 1. Cloudflare Tunnel Setup

If you haven't already created a tunnel:

```bash
# Install cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Login to Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create applylens

# Save the tunnel ID and credentials
```

### 2. Configure Tunnel Routing

Create or update `infra/cloudflared/config.yml`:

```yaml
tunnel: <YOUR_TUNNEL_ID>
credentials-file: /etc/cloudflared/credentials.json

ingress:
  # Route all traffic from applylens.app to nginx
  - hostname: applylens.app
    service: http://nginx:80
    originRequest:
      noTLSVerify: true
      connectTimeout: 30s
      
  # Route www subdomain
  - hostname: www.applylens.app
    service: http://nginx:80
    originRequest:
      noTLSVerify: true
      connectTimeout: 30s
  
  # Catch-all rule (required)
  - service: http_status:404
```

**Important:** The tunnel connects to `nginx:80` which is the nginx service name in docker-compose.prod.yml.

### 3. DNS Configuration

Route your domain through Cloudflare Tunnel:

```bash
# Add DNS route for main domain
cloudflared tunnel route dns applylens applylens.app

# Add DNS route for www subdomain
cloudflared tunnel route dns applylens www.applylens.app
```

This creates CNAME records in Cloudflare DNS pointing to your tunnel.

### 4. Verify Tunnel Configuration

```bash
# List tunnels
cloudflared tunnel list

# Check tunnel info
cloudflared tunnel info applylens

# Verify DNS routes
cloudflared tunnel route dns list
```

Expected output:
```
Tunnel ID: <your-tunnel-id>
Name: applylens
Status: active
Routes:
  - applylens.app → <tunnel-id>.cfargotunnel.com
  - www.applylens.app → <tunnel-id>.cfargotunnel.com
```

### 5. Start Tunnel

#### Option A: Using docker-compose.prod.yml (Recommended)

The tunnel service is already configured in docker-compose.prod.yml under the `cloudflare` profile:

```bash
# Start with Cloudflare tunnel
docker compose -f docker-compose.prod.yml --profile cloudflare up -d

# Or enable the cloudflared service separately
docker compose -f docker-compose.prod.yml up -d cloudflared
```

Make sure the `infra/cloudflared` directory contains:
- `config.yml` - Tunnel configuration
- `credentials.json` - Tunnel credentials

#### Option B: System Service

Run cloudflared as a system service:

```bash
# Install as service
sudo cloudflared service install

# Start service
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

# Check status
sudo systemctl status cloudflared
```

## Nginx Reverse Proxy Configuration

The nginx service (`infra/nginx/conf.d/applylens.conf` or `applylens-ssl.conf`) handles routing:

```nginx
server {
    listen 80;
    server_name applylens.app www.applylens.app;

    # Redirect root to web app
    location = / {
        return 302 /web/;
    }

    # Web Application (React/Vite SPA)
    location /web/ {
        proxy_pass http://web:5175/;
        # ... proxy headers ...
    }

    # API - OAuth Callback
    location /auth/google/ {
        proxy_pass http://api:8003/auth/google/;
        # ... proxy headers ...
    }

    # API Documentation
    location /docs/ {
        proxy_pass http://api:8003/docs/;
        # ... proxy headers ...
    }

    # API Root (catch-all)
    location / {
        proxy_pass http://api:8003/;
        # ... proxy headers ...
    }

    # Monitoring tools (protected)
    location /grafana/ { ... }
    location /kibana/ { ... }
    location /prometheus/ { ... }
}
```

## Service URLs (via Cloudflare)

Once configured, your services will be accessible at:

| Service | URL | Routed To |
|---------|-----|-----------|
| Frontend | https://applylens.app/web/ | nginx → web:5175 |
| API | https://applylens.app/ | nginx → api:8003 |
| API Docs | https://applylens.app/docs/ | nginx → api:8003/docs |
| OAuth Callback | https://applylens.app/auth/google/callback | nginx → api:8003/auth/google/callback |
| Grafana | https://applylens.app/grafana/ | nginx → grafana:3000 |
| Kibana | https://applylens.app/kibana/ | nginx → kibana:5601 |
| Prometheus | https://applylens.app/prometheus/ | nginx → prometheus:9090 |

## Verification Steps

### 1. Test Internal Nginx

```bash
# From the production server
curl -I http://localhost/
curl -I http://localhost/docs/
curl -I http://localhost/health
```

Expected: HTTP 200 or 302 responses

### 2. Test Cloudflare Tunnel

```bash
# Check tunnel status
cloudflared tunnel info applylens

# Should show: Status: active
```

### 3. Test External Access

```bash
# From any machine (not just the server)
curl -I https://applylens.app/
curl -I https://applylens.app/docs/
curl -I https://applylens.app/web/
```

Expected: HTTP 200 or 302 responses with Cloudflare headers (cf-ray, etc.)

### 4. Verify Headers

```bash
curl -I https://applylens.app/ | grep -i "cf-ray"
```

If you see a `cf-ray` header, traffic is flowing through Cloudflare.

## Troubleshooting

### Tunnel Not Connecting

```bash
# Check tunnel logs (if using docker-compose)
docker compose -f docker-compose.prod.yml logs cloudflared

# Or system service
sudo journalctl -u cloudflared -f
```

Common issues:
- Credentials file path incorrect
- Tunnel ID mismatch
- Network connectivity to Cloudflare edge

### 502 Bad Gateway

This means Cloudflare can reach the tunnel, but nginx isn't responding:

```bash
# Check nginx status
docker compose -f docker-compose.prod.yml ps nginx

# Check nginx logs
docker compose -f docker-compose.prod.yml logs nginx --tail=100

# Verify nginx is listening
docker compose -f docker-compose.prod.yml exec nginx netstat -tlnp | grep :80
```

### 404 Not Found

Nginx is working but routing is incorrect:

```bash
# Test nginx routing directly
curl -H "Host: applylens.app" http://localhost/web/

# Check nginx configuration
docker compose -f docker-compose.prod.yml exec nginx nginx -t

# Reload nginx config
docker compose -f docker-compose.prod.yml restart nginx
```

### OAuth Redirect Not Working

Verify Google OAuth settings:

1. Go to https://console.cloud.google.com/apis/credentials
2. Edit your OAuth 2.0 Client
3. Ensure redirect URI is: `https://applylens.app/auth/google/callback`
4. Ensure JS origin is: `https://applylens.app`

## Cloudflare Dashboard Settings

### SSL/TLS Mode

Set to **Full** (not Full (strict)):
- Cloudflare → SSL/TLS → Overview → Full

This allows Cloudflare to connect to your origin (nginx) via HTTP.

### Always Use HTTPS

Enable to force HTTPS:
- Cloudflare → SSL/TLS → Edge Certificates → Always Use HTTPS: On

### HSTS

Optional but recommended:
- Cloudflare → SSL/TLS → Edge Certificates → HTTP Strict Transport Security: Enabled

### Firewall Rules

Consider adding these rules:
- Allow traffic only from Cloudflare IPs
- Rate limiting for API endpoints
- Bot fight mode

## Docker Compose Network

Ensure cloudflared can reach nginx on the same network:

```yaml
# In docker-compose.prod.yml
networks:
  applylens-prod:
    driver: bridge

services:
  nginx:
    networks:
      - applylens-prod
  
  cloudflared:
    networks:
      - applylens-prod
```

## Backup: Direct DNS (No Tunnel)

If you prefer not to use Cloudflare Tunnel, you can use direct DNS:

1. Add A record in Cloudflare DNS: `applylens.app` → Your server IP
2. Enable Cloudflare proxy (orange cloud icon)
3. Configure SSL certificates on nginx (see PRODUCTION_DOMAIN_SETUP.md)
4. Expose port 443 in docker-compose.prod.yml

## Summary

✅ Cloudflare Tunnel connects to **nginx:80**  
✅ Nginx reverse-proxies to **api:8003** and **web:5175**  
✅ All SSL/TLS handled by Cloudflare  
✅ No need to expose ports directly to internet  
✅ Protected by Cloudflare DDoS protection  

For more information:
- Cloudflare Tunnel Docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- Quick Start: See `infra/CLOUDFLARE_TUNNEL_QUICKSTART.md`
