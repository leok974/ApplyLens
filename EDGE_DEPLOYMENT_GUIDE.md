# ApplyLens Edge Nginx Deployment Guide

This guide walks you through migrating from Cloudflare Tunnel to a public edge Nginx with Let's Encrypt certificates.

## Why This Migration?

**Problem**: Cloudflare Tunnel IAD POPs have 40-60% success rate (0% for assets), causing persistent 502 errors.

**Solution**: Direct Nginx edge + Let's Encrypt, keeping Cloudflare as proxy for DDoS protection and edge caching.

**Benefits**:
- ✅ No dependency on tunnel connector reliability
- ✅ Cloudflare still provides edge acceleration and protection
- ✅ Auto-renewing Let's Encrypt certificates
- ✅ Reproducible infrastructure
- ✅ Internal app topology unchanged

---

## Prerequisites

1. **Server with public IP**: Your Windows server needs a public IP address
2. **Cloudflare API Token**: Zone:Read, DNS:Edit permissions (you already have this)
3. **Ports 80/443 available**: Must be reachable from the internet for Let's Encrypt ACME challenge
4. **Existing services**: Your applylens-prod Docker network with web, api containers

---

## Architecture Overview

```
Internet → Cloudflare Edge (Proxied) → Your Server:443
                                           ↓
                                    edge-nginx (443)
                                           ↓
                                  applylens-prod network
                                      ↙          ↘
                              web:80          api:8003
```

---

## Step 1: Stop Conflicting Services

The AI finance nginx is currently using ports 80 and 443. Stop it:

```powershell
# Stop AI finance nginx
docker stop ai-finance-agent-oss-clean-nginx-1

# Verify ports are free
netstat -ano | findstr ":80 " | findstr "LISTENING"
# Should show nothing or only Docker internal services
```

---

## Step 2: Start Edge Nginx (HTTP Only)

Start the edge nginx with HTTP-only configuration for ACME challenge:

```powershell
cd D:\ApplyLens
docker compose -f docker-compose.edge.yml up -d edge-nginx
```

Verify it's running:

```powershell
docker ps | findstr applylens-edge
docker logs applylens-edge
curl http://localhost/
# Should return: "ApplyLens - HTTP endpoint active for cert acquisition"
```

---

## Step 3: Update Cloudflare DNS

**CRITICAL**: Do this BEFORE obtaining certificates so Let's Encrypt can reach your server.

### Get Your Public IP

```powershell
# Get your public IP
(Invoke-WebRequest -Uri "https://api.ipify.org").Content
```

### Update DNS in Cloudflare Dashboard

Go to: https://dash.cloudflare.com/ → Select your domain → DNS → Records

1. **Update `applylens.app`**:
   - Type: `A`
   - Name: `@` (or `applylens.app`)
   - Content: `<YOUR_PUBLIC_IP>`
   - Proxy status: **Proxied** (🟠 orange cloud)
   - TTL: Auto

2. **Create `api.applylens.app`**:
   - Type: `A`
   - Name: `api`
   - Content: `<YOUR_PUBLIC_IP>`
   - Proxy status: **Proxied** (🟠 orange cloud)
   - TTL: Auto

### Remove Tunnel Public Hostnames

Go to: https://one.dash.cloudflare.com/ → Zero Trust → Networks → Tunnels → Select your tunnel

- Remove public hostname mappings for `applylens.app` and `api.applylens.app`
- **DO NOT delete the tunnel itself** (keep it for rollback if needed)

### Verify DNS Propagation

```powershell
# Wait 2-3 minutes, then verify DNS
nslookup applylens.app
nslookup api.applylens.app

# Should show Cloudflare IPs (104.x.x.x range)
```

---

## Step 4: Obtain Let's Encrypt Certificates

Now that DNS points to your server, obtain certificates:

### For applylens.app

```powershell
docker run --rm `
  -v "${PWD}\infra\nginx\edge\www:/var/www/certbot" `
  -v "${PWD}\letsencrypt:/etc/letsencrypt" `
  certbot/certbot certonly --webroot -w /var/www/certbot `
  -d applylens.app --register-unsafely-without-email --agree-tos
```

### For api.applylens.app

```powershell
docker run --rm `
  -v "${PWD}\infra\nginx\edge\www:/var/www/certbot" `
  -v "${PWD}\letsencrypt:/etc/letsencrypt" `
  certbot/certbot certonly --webroot -w /var/www/certbot `
  -d api.applylens.app --register-unsafely-without-email --agree-tos
```

### Verify Certificates

```powershell
# Check certificates exist
Test-Path ".\letsencrypt\live\applylens.app\fullchain.pem"
Test-Path ".\letsencrypt\live\api.applylens.app\fullchain.pem"
# Both should return: True
```

---

## Step 5: Enable HTTPS Configuration

Re-enable the HTTPS config and update HTTP config to redirect:

```powershell
# Re-enable HTTPS config
Rename-Item -Path ".\infra\nginx\edge\conf.d\10-https.conf.disabled" `
            -NewName "10-https.conf"
```

Update `infra/nginx/edge/conf.d/00-http.conf` to enable HTTPS redirect:

```nginx
server {
  listen 80 default_server;
  server_name applylens.app api.applylens.app;

  # ACME challenge for certbot
  location ^~ /.well-known/acme-challenge/ {
    root /var/www/certbot;
  }

  # Redirect everything else to HTTPS
  location / {
    return 301 https://$host$request_uri;
  }
}
```

Reload nginx:

```powershell
docker exec applylens-edge nginx -t
docker exec applylens-edge nginx -s reload
```

---

## Step 6: Start Certbot Auto-Renewal

Start the certbot container for automatic certificate renewal:

```powershell
docker compose -f docker-compose.edge.yml up -d certbot
```

Certbot will automatically renew certificates every 12 hours if they're within 30 days of expiry.

---

## Step 7: Update Cloudflare SSL/TLS Settings

Go to: https://dash.cloudflare.com/ → Your domain → SSL/TLS

1. **SSL/TLS encryption mode**: Set to **Full (strict)**
2. **Edge Certificates**:
   - Always Use HTTPS: **ON**
   - Automatic HTTPS Rewrites: **ON**
   - Opportunistic Encryption: **ON**

---

## Step 8: Verification

### Test HTTP → HTTPS Redirect

```powershell
curl -I http://applylens.app/
# Should return: 301 Moved Permanently
# Location: https://applylens.app/
```

### Test HTTPS Endpoints

```powershell
# Homepage
curl -I https://applylens.app/
# Should return: 200 OK, server: cloudflare

# API health
curl https://api.applylens.app/healthz
# Should return: {"status":"ok"}
```

### Check Cloudflare Headers

```powershell
curl -I https://applylens.app/ | Select-String "CF-|server"
# Should show:
# server: cloudflare
# cf-cache-status: ...
# cf-ray: ...
```

### Check SSL Certificate

```powershell
# In browser, visit https://applylens.app/
# Click padlock → Certificate should show:
# - Issued by: Let's Encrypt
# - Valid for: applylens.app
```

---

## Step 9: Configure Cloudflare Caching (Optional)

### Cache Rules

Go to: Cloudflare Dashboard → Caching → Cache Rules

1. **Cache static assets**:
   - Rule name: "Cache Assets"
   - When: `URI Path starts with /assets/`
   - Then: Cache level = Standard, Edge TTL = 1 month

2. **Bypass API cache**:
   - Rule name: "Bypass API Cache"
   - When: `Hostname equals api.applylens.app`
   - Then: Cache level = Bypass

### Page Rules (if using Free plan)

Alternatively, use Page Rules:

1. `https://applylens.app/assets/*` → Cache Level: Cache Everything, Edge TTL: 1 month
2. `https://api.applylens.app/*` → Cache Level: Bypass

---

## Monitoring & Maintenance

### Check Container Status

```powershell
docker ps | findstr "applylens-edge\|certbot"
docker logs applylens-edge
docker logs certbot
```

### Check Certificate Expiry

```powershell
# Certificates expire in 90 days, auto-renew at 60 days
docker run --rm -v "${PWD}\letsencrypt:/etc/letsencrypt" certbot/certbot certificates
```

### Manual Certificate Renewal (if needed)

```powershell
docker compose -f docker-compose.edge.yml exec certbot certbot renew --force-renewal
docker exec applylens-edge nginx -s reload
```

### View Nginx Logs

```powershell
docker logs -f applylens-edge
```

---

## Rollback Plan

If you need to rollback to Cloudflare Tunnel:

1. **Stop edge nginx**:
   ```powershell
   docker compose -f docker-compose.edge.yml down
   ```

2. **Re-enable Tunnel in Cloudflare**:
   - Go to Zero Trust → Networks → Tunnels
   - Add public hostnames back:
     - `applylens.app` → `http://web:80`
     - `api.applylens.app` → `http://api:8003`

3. **Update DNS** (if you want to bypass Cloudflare entirely for testing):
   - Gray-cloud (DNS-only) the A records in Cloudflare DNS

4. **Restart AI finance nginx** (if needed):
   ```powershell
   docker start ai-finance-agent-oss-clean-nginx-1
   ```

---

## Troubleshooting

### Port 80/443 Still in Use

```powershell
# Find what's using the port
netstat -ano | findstr ":80 " | findstr "LISTENING"

# Identify the process
Get-Process -Id <PID>

# Stop the conflicting service
docker stop <container-name>
```

### Let's Encrypt ACME Challenge Fails

1. **Check DNS is pointing to your server**:
   ```powershell
   nslookup applylens.app
   ```

2. **Verify port 80 is accessible from internet**:
   - Test from another network or use https://canyouseeme.org/
   - Check Windows Firewall allows port 80 inbound

3. **Check nginx is serving ACME path**:
   ```powershell
   curl http://localhost/.well-known/acme-challenge/test
   # Should return 404 (path exists but file doesn't)
   ```

### Cloudflare Shows 526 Error (Invalid SSL Certificate)

- Ensure SSL/TLS mode is set to **Full (strict)** in Cloudflare
- Verify certificates exist and are valid:
  ```powershell
  docker exec applylens-edge ls -la /etc/letsencrypt/live/
  ```

### 502 Bad Gateway After Migration

1. **Check internal containers are running**:
   ```powershell
   docker ps | findstr "web-prod\|api-prod"
   ```

2. **Test internal connectivity**:
   ```powershell
   docker exec applylens-edge curl http://web:80/
   docker exec applylens-edge curl http://api:8003/healthz
   ```

3. **Check nginx logs**:
   ```powershell
   docker logs applylens-edge 2>&1 | Select-String "error"
   ```

---

## Success Metrics

After successful deployment, you should see:

- ✅ HTTPS working for `applylens.app` and `api.applylens.app`
- ✅ SSL certificate from Let's Encrypt (valid, auto-renewing)
- ✅ Cloudflare edge caching working (check `cf-cache-status` header)
- ✅ No 502 errors (eliminated IAD POP tunnel issues)
- ✅ Faster response times (no tunnel hop)
- ✅ `server: cloudflare` header present (Cloudflare protection active)

---

## Next Steps

Once stable:

1. **Add HSTS header** in nginx for additional security
2. **Configure rate limiting** in Cloudflare for API endpoints
3. **Set up monitoring** (Prometheus alerts for cert expiry, edge nginx uptime)
4. **Document runbooks** for common operations
5. **Consider moving to paid Cloudflare plan** for advanced cache rules and better support

---

## Questions?

This deployment eliminates the tunnel reliability issues while keeping all the benefits of Cloudflare's edge network. The edge nginx is simple, reproducible, and battle-tested infrastructure.
