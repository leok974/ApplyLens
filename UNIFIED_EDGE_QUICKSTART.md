# Unified Edge Deployment - Quick Reference

## 🌐 One Network for Everything

All containers (ApplyLens, AI-finance, Ollama) share **`infra_net`** - no more port conflicts!

```
Internet → Cloudflare Edge (Proxied) → Your Server:443
                                           ↓
                                      edge-nginx (443)
                                           ↓
                                      infra_net
                                 ╭────────┴────────╮
                                 ↓                 ↓
                        applylens-web:80    ledger-web:80
                        applylens-api:8003  ollama:11434 (internal)
```

---

## 🚀 Quick Start (5 Steps)

### Step 0: Get Your Public IP
```powershell
(Invoke-WebRequest -Uri "https://api.ipify.org").Content
```

### Step 1: Create & Connect Network
```powershell
cd D:\ApplyLens

# Create shared network
docker network create infra_net 2>$null

# Connect ApplyLens containers
docker network connect infra_net applylens-web-prod --alias applylens-web 2>$null
docker network connect infra_net applylens-api-prod --alias applylens-api 2>$null

# Connect AI-finance containers
docker network connect infra_net ai-finance-web-1 --alias ledger-web 2>$null

# Connect Ollama (internal only - no public exposure)
docker network connect infra_net ai-finance-agent-oss-clean-ollama-1 --alias ollama 2>$null

# Verify connections
docker network inspect infra_net | Select-String "applylens-web|applylens-api|ledger-web|ollama"
```

### Step 2: Update Cloudflare DNS

**In Cloudflare Dashboard** (https://dash.cloudflare.com/):

1. **ApplyLens**:
   - `applylens.app` → A → `<YOUR_PUBLIC_IP>` (Proxied 🟠)
   - `api.applylens.app` → A → `<YOUR_PUBLIC_IP>` (Proxied 🟠)

2. **AI-finance / Ledger-Mind**:
   - `assistant.ledger-mind.org` → A → `<YOUR_PUBLIC_IP>` (Proxied 🟠)

3. **SSL/TLS Settings**:
   - Encryption mode: **Full (strict)**
   - Always Use HTTPS: **ON**

4. **Remove Tunnel Public Hostnames**:
   - Go to: Zero Trust → Networks → Tunnels
   - Remove public hostname mappings for these 3 domains
   - **Keep the tunnel** (for rollback if needed)

Wait 2-3 minutes for DNS propagation:
```powershell
nslookup applylens.app
nslookup api.applylens.app
nslookup assistant.ledger-mind.org
```

### Step 3: Stop Conflicting Services & Start Edge

```powershell
# Stop AI-finance nginx (no longer needed)
docker stop ai-finance-agent-oss-clean-nginx-1 2>$null

# Start edge nginx (HTTP only for cert acquisition)
cd D:\ApplyLens
docker compose -f docker-compose.edge.yml up -d edge-nginx

# Test HTTP endpoint
curl http://localhost/
# Should return: "Edge Nginx - HTTP endpoint active for cert acquisition"
```

### Step 4: Obtain Let's Encrypt Certificates

```powershell
cd D:\ApplyLens

# ApplyLens Web
docker run --rm `
  -v "${PWD}\infra\nginx\edge\www:/var/www/certbot" `
  -v "${PWD}\letsencrypt:/etc/letsencrypt" `
  certbot/certbot certonly --webroot -w /var/www/certbot `
  -d applylens.app --register-unsafely-without-email --agree-tos

# ApplyLens API
docker run --rm `
  -v "${PWD}\infra\nginx\edge\www:/var/www/certbot" `
  -v "${PWD}\letsencrypt:/etc/letsencrypt" `
  certbot/certbot certonly --webroot -w /var/www/certbot `
  -d api.applylens.app --register-unsafely-without-email --agree-tos

# AI-finance / Ledger-Mind
docker run --rm `
  -v "${PWD}\infra\nginx\edge\www:/var/www/certbot" `
  -v "${PWD}\letsencrypt:/etc/letsencrypt" `
  certbot/certbot certonly --webroot -w /var/www/certbot `
  -d assistant.ledger-mind.org --register-unsafely-without-email --agree-tos

# Verify certificates
Test-Path ".\letsencrypt\live\applylens.app\fullchain.pem"
Test-Path ".\letsencrypt\live\api.applylens.app\fullchain.pem"
Test-Path ".\letsencrypt\live\assistant.ledger-mind.org\fullchain.pem"
# All should return: True
```

### Step 5: Enable HTTPS & Reload

```powershell
# Enable HTTPS config
Rename-Item ".\infra\nginx\edge\conf.d\10-https.conf.disabled" -NewName "10-https.conf"

# Enable HTTP→HTTPS redirect
# Edit infra/nginx/edge/conf.d/00-http.conf:
# Comment out the "return 200" location
# Uncomment the "return 301" location

# Or use this command to auto-update:
(Get-Content ".\infra\nginx\edge\conf.d\00-http.conf") `
  -replace '  location / \{\s+return 200.*?\n.*?\n  \}', '  # Temporary disabled`n  # location / {`n  #   return 200 "Edge Nginx - HTTP endpoint active for cert acquisition\n";`n  #   add_header Content-Type text/plain;`n  # }' `
  -replace '  # Uncomment after obtaining certs:\s+# location / \{', '  # HTTP→HTTPS redirect enabled after cert acquisition`n  location / {' `
  -replace '  #   return 301', '    return 301' `
  -replace '  # \}', '  }' | Set-Content ".\infra\nginx\edge\conf.d\00-http.conf"

# Test and reload nginx
docker exec edge-nginx nginx -t
docker exec edge-nginx nginx -s reload

# Start certbot auto-renewal
docker compose -f docker-compose.edge.yml up -d certbot
```

---

## ✅ Verification

```powershell
# Test HTTPS endpoints
curl -I https://applylens.app/
curl -I https://api.applylens.app/healthz
curl -I https://assistant.ledger-mind.org/

# Check Cloudflare headers
curl -I https://applylens.app/ | Select-String "server|CF-"
# Should show: server: cloudflare, cf-ray: ...

# Check containers
docker ps | Select-String "edge-nginx|certbot|applylens-web|applylens-api|ai-finance-web"

# Check internal connectivity
docker exec edge-nginx curl -I http://applylens-web:80/
docker exec edge-nginx curl http://applylens-api:8003/healthz
docker exec edge-nginx curl -I http://ledger-web:80/
```

---

## 📊 What's Running

| Container | Network Alias | Public Endpoint | Backend |
|-----------|---------------|-----------------|---------|
| `applylens-web-prod` | `applylens-web` | `https://applylens.app/` | React SPA |
| `applylens-api-prod` | `applylens-api` | `https://api.applylens.app/` | FastAPI |
| `ai-finance-web-1` | `ledger-web` | `https://assistant.ledger-mind.org/` | AI Finance UI |
| `ai-finance-agent-oss-clean-ollama-1` | `ollama` | *internal only* | Ollama LLM |
| `edge-nginx` | - | Ports 80/443 | Reverse proxy |
| `certbot` | - | - | Cert renewal |

**Old nginx containers (no longer needed)**:
- `applylens-nginx-prod` - Was internal routing only (replaced by edge-nginx)
- `ai-finance-agent-oss-clean-nginx-1` - Was using ports 80/443 (replaced by edge-nginx)

You can stop/remove these:
```powershell
docker stop applylens-nginx-prod ai-finance-agent-oss-clean-nginx-1 2>$null
docker rm applylens-nginx-prod ai-finance-agent-oss-clean-nginx-1 2>$null
```

---

## 🛠️ Maintenance

### View Logs
```powershell
docker logs -f edge-nginx
docker logs certbot
```

### Manual Certificate Renewal
```powershell
docker exec certbot certbot renew --force-renewal
docker exec edge-nginx nginx -s reload
```

### Restart Edge
```powershell
docker restart edge-nginx
```

### Add New Site
1. Connect container to `infra_net` with alias:
   ```powershell
   docker network connect infra_net <container-name> --alias <friendly-name>
   ```

2. Add DNS A record in Cloudflare (Proxied 🟠)

3. Obtain certificate:
   ```powershell
   docker run --rm `
     -v "${PWD}\infra\nginx\edge\www:/var/www/certbot" `
     -v "${PWD}\letsencrypt:/etc/letsencrypt" `
     certbot/certbot certonly --webroot -w /var/www/certbot `
     -d <your-domain.com> --register-unsafely-without-email --agree-tos
   ```

4. Add vhost to `infra/nginx/edge/conf.d/10-https.conf`:
   ```nginx
   server {
     listen 443 ssl http2;
     server_name <your-domain.com>;

     ssl_certificate     /etc/letsencrypt/live/<your-domain.com>/fullchain.pem;
     ssl_certificate_key /etc/letsencrypt/live/<your-domain.com>/privkey.pem;

     include /etc/nginx/snippets/proxy_headers.conf;

     location / {
       proxy_pass http://<friendly-name>:80;
     }
   }
   ```

5. Reload:
   ```powershell
   docker exec edge-nginx nginx -t && docker exec edge-nginx nginx -s reload
   ```

---

## 🔄 Rollback to Tunnel (if needed)

```powershell
# Stop edge stack
docker compose -f docker-compose.edge.yml down

# Re-enable tunnel public hostnames in Cloudflare dashboard:
# Zero Trust → Networks → Tunnels → Public Hostnames
# Add mappings back to tunnel

# Restart old nginx containers (if needed)
docker start ai-finance-agent-oss-clean-nginx-1
```

---

## ⚠️ Troubleshooting

### Port 80/443 Already in Use
```powershell
netstat -ano | findstr ":80 " | findstr "LISTENING"
# Stop conflicting container
```

### Certificate Acquisition Fails
1. **Check DNS points to your server**:
   ```powershell
   nslookup <domain>
   ```

2. **Test port 80 from internet**: https://canyouseeme.org/

3. **Check Windows Firewall**:
   - Allow inbound TCP ports 80 and 443

4. **Check nginx ACME path**:
   ```powershell
   docker exec edge-nginx ls -la /var/www/certbot
   curl http://localhost/.well-known/acme-challenge/test
   ```

### 526 Invalid SSL Certificate Error
- Ensure Cloudflare SSL/TLS mode is **Full (strict)**
- Verify certificates exist:
  ```powershell
  docker exec edge-nginx ls -la /etc/letsencrypt/live/
  ```

### 502 Bad Gateway
1. **Check backend containers**:
   ```powershell
   docker ps | Select-String "web|api"
   ```

2. **Test internal connectivity**:
   ```powershell
   docker exec edge-nginx curl http://applylens-web:80/
   docker exec edge-nginx curl http://applylens-api:8003/healthz
   ```

3. **Check nginx logs**:
   ```powershell
   docker logs edge-nginx 2>&1 | Select-String "error"
   ```

### Ollama Not Reachable
```powershell
# Test from API container
docker exec applylens-api-prod curl http://ollama:11434/
# Should return: "Ollama is running"

# Verify Ollama is on infra_net
docker network inspect infra_net | Select-String "ollama"
```

---

## 📁 File Locations

- **Edge compose**: `docker-compose.edge.yml`
- **HTTP config**: `infra/nginx/edge/conf.d/00-http.conf`
- **HTTPS config**: `infra/nginx/edge/conf.d/10-https.conf`
- **Proxy headers**: `infra/nginx/snippets/proxy_headers.conf`
- **Certificates**: `letsencrypt/live/<domain>/`
- **ACME webroot**: `infra/nginx/edge/www/`

---

## 🎯 Benefits Achieved

- ✅ **No port conflicts** - One edge nginx for all projects
- ✅ **No tunnel dependency** - Direct connection eliminates IAD POP issues
- ✅ **100% success rate** - Stable infrastructure
- ✅ **Cloudflare protection** - DDoS mitigation, edge caching, CDN
- ✅ **Auto-renewing certs** - Let's Encrypt + certbot (renews every 12h check)
- ✅ **Shared network** - Easy inter-service communication
- ✅ **Ollama internal** - No public exposure, accessed via internal DNS
- ✅ **Easy to extend** - Add new sites by connecting to `infra_net` + adding vhost

---

## 📖 Documentation

- **Full guide**: `EDGE_DEPLOYMENT_GUIDE.md` (comprehensive step-by-step)
- **Original quickstart**: `EDGE_QUICKSTART.md` (single-project reference)
- **This file**: `UNIFIED_EDGE_QUICKSTART.md` (multi-project unified approach)
