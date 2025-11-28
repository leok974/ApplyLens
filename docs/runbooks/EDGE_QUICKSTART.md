# ApplyLens Edge Migration - Quick Reference

## 🚀 Automated Deployment (Recommended)

```powershell
cd D:\ApplyLens

# Get your public IP
$publicIP = (Invoke-WebRequest -Uri "https://api.ipify.org").Content

# Run deployment script
.\scripts\deploy-edge.ps1 -PublicIP $publicIP

# Or dry run first to see what will happen
.\scripts\deploy-edge.ps1 -PublicIP $publicIP -DryRun
```

## 📋 Manual Deployment Steps

### 1. Stop Conflicting Services
```powershell
docker stop ai-finance-agent-oss-clean-nginx-1
```

### 2. Update Cloudflare DNS
- `applylens.app` → A → `<YOUR_IP>` (Proxied 🟠)
- `api.applylens.app` → A → `<YOUR_IP>` (Proxied 🟠)

### 3. Start Edge Nginx (HTTP Only)
```powershell
cd D:\ApplyLens
docker compose -f docker-compose.edge.yml up -d edge-nginx
```

### 4. Obtain Certificates
```powershell
# For applylens.app
docker run --rm `
  -v "${PWD}\infra\nginx\edge\www:/var/www/certbot" `
  -v "${PWD}\letsencrypt:/etc/letsencrypt" `
  certbot/certbot certonly --webroot -w /var/www/certbot `
  -d applylens.app --register-unsafely-without-email --agree-tos

# For api.applylens.app
docker run --rm `
  -v "${PWD}\infra\nginx\edge\www:/var/www/certbot" `
  -v "${PWD}\letsencrypt:/etc/letsencrypt" `
  certbot/certbot certonly --webroot -w /var/www/certbot `
  -d api.applylens.app --register-unsafely-without-email --agree-tos
```

### 5. Enable HTTPS
```powershell
# Enable HTTPS config
Rename-Item ".\infra\nginx\edge\conf.d\10-https.conf.disabled" -NewName "10-https.conf"

# Enable HTTP→HTTPS redirect in 00-http.conf (uncomment the redirect)

# Test and reload
docker exec applylens-edge nginx -t
docker exec applylens-edge nginx -s reload
```

### 6. Start Certbot Auto-Renewal
```powershell
docker compose -f docker-compose.edge.yml up -d certbot
```

## 🔍 Verification Commands

```powershell
# Check containers
docker ps | findstr "applylens-edge\|certbot"

# Test HTTP→HTTPS redirect
curl -I http://applylens.app/

# Test HTTPS endpoints
curl -I https://applylens.app/
curl https://api.applylens.app/healthz

# Check Cloudflare headers
curl -I https://applylens.app/ | Select-String "CF-|server"

# Check certificate expiry
docker run --rm -v "${PWD}\letsencrypt:/etc/letsencrypt" certbot/certbot certificates
```

## 🛠️ Maintenance Commands

```powershell
# View nginx logs
docker logs -f applylens-edge

# View certbot logs
docker logs certbot

# Manual cert renewal (if needed)
docker compose -f docker-compose.edge.yml exec certbot certbot renew --force-renewal
docker exec applylens-edge nginx -s reload

# Restart edge nginx
docker restart applylens-edge

# Stop edge stack
docker compose -f docker-compose.edge.yml down

# Start edge stack
docker compose -f docker-compose.edge.yml up -d
```

## 🔄 Rollback to Tunnel

```powershell
# Stop edge stack
cd D:\ApplyLens
docker compose -f docker-compose.edge.yml down

# Re-enable tunnel in Cloudflare dashboard:
# Zero Trust → Networks → Tunnels → Public Hostnames
# Add: applylens.app → http://web:80
# Add: api.applylens.app → http://api:8003

# Restart AI finance nginx (if needed)
docker start ai-finance-agent-oss-clean-nginx-1
```

## 📊 Cloudflare Post-Deployment Configuration

### SSL/TLS Settings
- Go to: https://dash.cloudflare.com/ → SSL/TLS
- Encryption mode: **Full (strict)**
- Always Use HTTPS: **ON**

### Cache Rules (Optional)
1. **Cache assets**: `/assets/*` → Cache Everything, Edge TTL: 1 month
2. **Bypass API**: `/api/*` → Bypass cache

### Remove Tunnel Public Hostnames
- Go to: https://one.dash.cloudflare.com/ → Networks → Tunnels
- Remove public hostnames for `applylens.app` and `api.applylens.app`
- **Keep the tunnel** (for potential rollback)

## 📁 File Locations

- **Edge compose**: `D:\ApplyLens\docker-compose.edge.yml`
- **HTTP config**: `D:\ApplyLens\infra\nginx\edge\conf.d\00-http.conf`
- **HTTPS config**: `D:\ApplyLens\infra\nginx\edge\conf.d\10-https.conf`
- **Certificates**: `D:\ApplyLens\letsencrypt\live\`
- **ACME webroot**: `D:\ApplyLens\infra\nginx\edge\www\`
- **Full guide**: `D:\ApplyLens\EDGE_DEPLOYMENT_GUIDE.md`
- **Deploy script**: `D:\ApplyLens\scripts\deploy-edge.ps1`

## ⚠️ Troubleshooting

### Port 80/443 in use
```powershell
netstat -ano | findstr ":80 " | findstr "LISTENING"
# Stop the conflicting container
```

### Certificate acquisition fails
1. Check DNS points to your server: `nslookup applylens.app`
2. Test port 80 from internet: https://canyouseeme.org/
3. Check Windows Firewall allows port 80 inbound

### 526 Invalid SSL Certificate
- Set Cloudflare SSL/TLS to **Full (strict)**
- Verify certificates exist: `docker exec applylens-edge ls -la /etc/letsencrypt/live/`

### 502 Bad Gateway
```powershell
# Check internal containers
docker ps | findstr "web-prod\|api-prod"

# Test internal connectivity
docker exec applylens-edge curl http://web:80/
docker exec applylens-edge curl http://api:8003/healthz

# Check logs
docker logs applylens-edge 2>&1 | Select-String "error"
```

## 📈 Success Metrics

After deployment, you should see:
- ✅ 100% success rate (no more IAD POP 502s)
- ✅ `server: cloudflare` header present
- ✅ Valid Let's Encrypt certificate
- ✅ HTTP→HTTPS redirect working
- ✅ Auto-renewal enabled

## 📖 Documentation

Full guide: `D:\ApplyLens\EDGE_DEPLOYMENT_GUIDE.md`
