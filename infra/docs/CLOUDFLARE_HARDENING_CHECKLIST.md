# Cloudflare Hardening Checklist for applylens.app

This checklist covers security hardening, performance optimization, and observability improvements for your Cloudflare Tunnel deployment.

## 🔒 SSL/TLS Security

### 1. Enable Full (Strict) Mode

**Status:** ⏳ To Do  
**Priority:** High  
**Location:** Cloudflare Dashboard → SSL/TLS → Overview

**Steps:**

1. Go to: <https://dash.cloudflare.com/> → Select `applylens.app`
2. Navigate to: **SSL/TLS** → **Overview**
3. Change encryption mode from "Flexible" or "Full" to **"Full (strict)"**
4. Verify: Your tunnel handles the origin certificate automatically

**Why:** Ensures end-to-end encryption. Your Cloudflare Tunnel already provides a secure connection from Cloudflare to your origin, so "Full (strict)" adds no complexity but maximum security.

### 2. Enable Always Use HTTPS

**Status:** ⏳ To Do  
**Priority:** High  
**Location:** Cloudflare Dashboard → SSL/TLS → Edge Certificates

**Steps:**

1. Go to: **SSL/TLS** → **Edge Certificates**
2. Toggle **"Always Use HTTPS"** to **ON**
3. This forces HTTP → HTTPS redirects at the edge

**Test:**

```powershell
curl -I http://applylens.app/ | Select-String Location
# Should see: Location: https://applylens.app/
```

### 3. Enable HSTS (HTTP Strict Transport Security)

**Status:** ⏳ To Do  
**Priority:** Medium (do after HTTPS is working everywhere)  
**Location:** Nginx configuration

**Steps:**

1. Edit `infra/nginx/snippets/security-headers.conf` (or create it)
2. Add:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

3. Restart nginx:

```bash
docker compose restart nginx
```

**Test:**

```powershell
curl -I https://applylens.app/ | Select-String Strict-Transport
# Should see: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**⚠️ Warning:** Only enable after you're certain ALL subdomains support HTTPS. HSTS tells browsers to NEVER access your site over HTTP for 1 year (max-age=31536000).

### 4. Enable Minimum TLS Version 1.2

**Status:** ⏳ To Do  
**Priority:** Medium  
**Location:** Cloudflare Dashboard → SSL/TLS → Edge Certificates

**Steps:**

1. Go to: **SSL/TLS** → **Edge Certificates**
2. Set **Minimum TLS Version** to **TLS 1.2** or higher
3. Disables insecure TLS 1.0 and 1.1

---

## 🚀 Performance & Caching

### 5. Configure Cache Rules

**Status:** ⏳ To Do  
**Priority:** Medium  
**Location:** Cloudflare Dashboard → Caching → Cache Rules

**Rules to Create:**

#### Rule 1: Cache Static Assets

- **Name:** Cache Web App Static Assets
- **When incoming requests match:**
  - Hostname equals `applylens.app` OR `www.applylens.app`
  - URI Path starts with `/web/`
- **Then:**
  - Cache Level: **Cache Everything**
  - Edge TTL: **4 hours** (14400 seconds)
  - Browser TTL: **1 hour** (3600 seconds)

#### Rule 2: Bypass API Caching

- **Name:** Bypass API and Services
- **When incoming requests match:**
  - Hostname equals `applylens.app` OR `www.applylens.app`
  - URI Path starts with `/api/` OR `/grafana/` OR `/kibana/` OR `/prometheus/`
- **Then:**
  - Cache Level: **Bypass**

#### Rule 3: Cache API Documentation

- **Name:** Cache API Docs (optional)
- **When incoming requests match:**
  - Hostname equals `api.applylens.app`
  - URI Path equals `/docs` OR `/openapi.json`
- **Then:**
  - Cache Level: **Cache Everything**
  - Edge TTL: **1 hour** (3600 seconds)

**Test:**

```powershell
# Check cache headers
curl -I https://applylens.app/web/assets/index.js | Select-String cf-cache-status
# Should see: cf-cache-status: HIT (after first request)

curl -I https://api.applylens.app/ready | Select-String cf-cache-status
# Should see: cf-cache-status: DYNAMIC (not cached)
```

### 6. Enable Brotli Compression

**Status:** ⏳ To Do  
**Priority:** Low  
**Location:** Cloudflare Dashboard → Speed → Optimization

**Steps:**

1. Go to: **Speed** → **Optimization**
2. Enable **Brotli** compression
3. Automatically compresses text-based responses

---

## 🛡️ Security & WAF

### 7. Enable Bot Fight Mode

**Status:** ⏳ To Do  
**Priority:** Medium  
**Location:** Cloudflare Dashboard → Security → Bots

**Steps:**

1. Go to: **Security** → **Bots**
2. Enable **Bot Fight Mode** (free tier)
3. Automatically challenges suspicious bots

**For Pro+ (optional):**

- Enable **Super Bot Fight Mode** for more granular control

### 8. Create Rate Limiting Rules

**Status:** ⏳ To Do  
**Priority:** High  
**Location:** Cloudflare Dashboard → Security → WAF → Rate limiting rules

**Rules to Create:**

#### Rule 1: Protect API Endpoints

- **Name:** API Rate Limit
- **When incoming requests match:**
  - Hostname equals `api.applylens.app`
  - URI Path starts with `/api/`
- **With the same characteristics:**
  - IP Address
- **Then:**
  - Requests: **200** per **10 seconds**
  - Action: **Block** for **60 seconds**
  - HTTP Status Code: **429** (Too Many Requests)

#### Rule 2: Protect Auth Endpoints (strict)

- **Name:** Auth Rate Limit
- **When incoming requests match:**
  - Hostname equals `api.applylens.app`
  - URI Path starts with `/auth/`
- **With the same characteristics:**
  - IP Address
- **Then:**
  - Requests: **5** per **60 seconds**
  - Action: **Block** for **300 seconds** (5 minutes)

**Test:**

```powershell
# Spam the API to trigger rate limit
1..250 | ForEach-Object { curl -s https://api.applylens.app/ready -o $null -w "%{http_code} " }
# Should see mostly 200s, then 429s after ~200 requests
```

### 9. Enable Security Level

**Status:** ⏳ To Do  
**Priority:** Low  
**Location:** Cloudflare Dashboard → Security → Settings

**Steps:**

1. Go to: **Security** → **Settings**
2. Set **Security Level** to **"Medium"** (default) or **"High"** if you're seeing attacks
3. Challenges more visitors but blocks malicious traffic

---

## 🔀 Redirects & URL Normalization

### 10. Configure WWW Redirect (Optional)

**Status:** ⏳ To Do  
**Priority:** Low (only if you prefer canonical root domain)  
**Location:** Cloudflare Dashboard → Rules → Redirect Rules

**Option A: WWW → Root (Recommended)**

- **Name:** Redirect WWW to Root
- **When incoming requests match:**
  - Hostname equals `www.applylens.app`
- **Then:**
  - Type: **Dynamic**
  - Expression: `concat("https://applylens.app", http.request.uri.path)`
  - Status Code: **301** (Permanent)
  - Preserve query string: **Yes**

**Option B: Root → WWW**

- **Name:** Redirect Root to WWW
- **When incoming requests match:**
  - Hostname equals `applylens.app`
- **Then:**
  - Type: **Dynamic**
  - Expression: `concat("https://www.applylens.app", http.request.uri.path)`
  - Status Code: **301** (Permanent)

**Test:**

```powershell
curl -I https://www.applylens.app/ | Select-String Location
# Should see: Location: https://applylens.app/ (if redirecting www → root)
```

---

## 🔧 Nginx Configuration Improvements

### 11. Add WebSocket Support

**Status:** ⏳ To Do  
**Priority:** Medium (needed for Grafana, Kibana live updates)  
**File:** `infra/nginx/conf.d/default.conf`

**Add at top of file:**

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
```

**Then in each proxied location block:**

```nginx
location /grafana/ {
    proxy_pass http://grafana:3000/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade    $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host  $host;
    proxy_set_header X-Forwarded-Prefix /grafana;
}
```

### 12. Add Security Headers

**Status:** ⏳ To Do  
**Priority:** Medium  
**File:** `infra/nginx/snippets/security-headers.conf`

**Create file:**

```nginx
# Security Headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# Content Security Policy (adjust as needed)
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://api.applylens.app; frame-ancestors 'self';" always;

# Remove server version
server_tokens off;
```

**Include in main config:**

```nginx
http {
    include /etc/nginx/snippets/security-headers.conf;
    # ... rest of config
}
```

### 13. Enable Nginx Status Page (for monitoring)

**Status:** ⏳ To Do  
**Priority:** Low  
**File:** `infra/nginx/conf.d/default.conf`

**Add location block:**

```nginx
location /nginx_status {
    stub_status on;
    access_log off;
    allow 127.0.0.1;
    allow 172.24.0.0/16;  # Docker network
    deny all;
}
```

**Test:**

```bash
docker exec applylens-nginx curl http://localhost/nginx_status
```

---

## 📊 Observability & Monitoring

### 14. Monitor Cloudflared Logs

**Status:** ✅ Already Available  
**Command:**

```bash
docker compose -f infra/docker-compose.yml logs -f cloudflared
```

**Look for:**

- `Registered tunnel connection` - Confirms tunnel is up
- `Updated to new configuration` - Confirms config changes applied
- `ERR` lines - Indicates problems

### 15. Set Up Cloudflare Analytics Alerts (Optional)

**Status:** ⏳ To Do  
**Priority:** Low  
**Location:** Cloudflare Dashboard → Analytics

**Create alerts for:**

- Spike in 5xx errors (> 10 in 5 minutes)
- Traffic spike (> 1000 requests/minute)
- DDoS attack detected

### 16. Add Prometheus Nginx Exporter (Optional)

**Status:** ⏳ To Do  
**Priority:** Low  
**File:** `infra/docker-compose.yml`

**Add service:**

```yaml
  nginx-exporter:
    image: nginx/nginx-prometheus-exporter:latest
    command:
      - '-nginx.scrape-uri=http://nginx/nginx_status'
    ports:
      - "9113:9113"
    depends_on:
      - nginx
```

**Then add to Prometheus scrape config:**

```yaml
scrape_configs:
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx-exporter:9113']
```

---

## ✅ Final Verification Checklist

After implementing the above, verify with these commands:

### SSL/TLS Verification

```powershell
# Check HTTPS redirect
curl -I http://applylens.app/ | Select-String Location

# Check HSTS header
curl -I https://applylens.app/ | Select-String Strict-Transport

# Check TLS version
openssl s_client -connect applylens.app:443 -tls1_2 2>&1 | Select-String "Protocol"
```

### Security Headers

```powershell
curl -I https://applylens.app/ | Select-String "X-Frame-Options|X-Content-Type-Options|X-XSS-Protection"
```

### Caching

```powershell
# First request (MISS)
curl -I https://applylens.app/web/assets/index.js | Select-String cf-cache-status

# Second request (HIT)
curl -I https://applylens.app/web/assets/index.js | Select-String cf-cache-status
```

### Rate Limiting

```powershell
# Spam API to trigger rate limit
1..250 | ForEach-Object { 
    $status = curl -s https://api.applylens.app/ready -o $null -w "%{http_code}"
    Write-Host "Request $_: $status"
}
# Should see 429 after ~200 requests
```

### Bot Protection

```powershell
# Check for CF bot challenge headers
curl -I https://applylens.app/ -A "BadBot/1.0" | Select-String cf-mitigated
```

---

## 📝 Implementation Priority Order

**Phase 1: Security Essentials (Do First)**

1. ✅ Enable Full (Strict) SSL mode
2. ✅ Enable Always Use HTTPS
3. ✅ Create API rate limiting rules
4. ✅ Enable Bot Fight Mode

**Phase 2: Performance (Do Second)**
5. ✅ Configure cache rules (static assets, API bypass)
6. ✅ Enable Brotli compression
7. ✅ Add WebSocket support to Nginx

**Phase 3: Hardening (Do Third)**
8. ✅ Enable HSTS (after HTTPS is stable)
9. ✅ Add security headers to Nginx
10. ✅ Set minimum TLS version 1.2

**Phase 4: Polish (Optional)**
11. ✅ Configure WWW redirect (if desired)
12. ✅ Enable Nginx status page
13. ✅ Set up monitoring alerts

---

## 🔄 Maintenance

**Weekly:**

- Review Cloudflare Analytics for anomalies
- Check cloudflared logs for errors: `docker logs --tail 100 infra-cloudflared`

**Monthly:**

- Review rate limiting effectiveness
- Update Nginx and cloudflared images: `docker compose pull && docker compose up -d`
- Review security headers best practices

**Quarterly:**

- Review and update CSP policy
- Test disaster recovery (revert to previous tunnel config)
- Review and update this checklist

---

## 📚 Resources

- [Cloudflare SSL/TLS Docs](https://developers.cloudflare.com/ssl/)
- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [Cloudflare WAF Docs](https://developers.cloudflare.com/waf/)
- [Nginx Security Headers](https://nginx.org/en/docs/http/ngx_http_headers_module.html)
- [OWASP Security Headers](https://owasp.org/www-project-secure-headers/)
