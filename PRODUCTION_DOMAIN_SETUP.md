# Production Domain Setup Guide - applylens.app

Complete guide to deploy ApplyLens to your production domain `applylens.app`.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [DNS Configuration](#dns-configuration)
3. [SSL/TLS Certificate Setup](#ssltls-certificate-setup)
4. [Environment Configuration](#environment-configuration)
5. [Deployment Options](#deployment-options)
6. [Post-Deployment Steps](#post-deployment-steps)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisites

### Server Requirements
- **VPS/Cloud Server** with public IP address
- **Minimum specs:** 2 vCPU, 4GB RAM, 50GB SSD
- **Recommended:** 4 vCPU, 8GB RAM, 100GB SSD
- **OS:** Ubuntu 22.04 LTS or similar Linux distribution

### Software Requirements
- Docker Engine 24.0+
- Docker Compose v2.20+
- Domain name: `applylens.app` pointing to your server

### Access Requirements
- SSH access to your server
- Domain DNS management access
- Google Cloud Console access (for OAuth)

---

## 🌐 DNS Configuration

Configure your DNS records to point to your server:

### Required DNS Records

```dns
# A Records (replace X.X.X.X with your server's public IP)
applylens.app         A    X.X.X.X
www.applylens.app     A    X.X.X.X
api.applylens.app     A    X.X.X.X  (optional - subdomain routing)

# Optional: Wildcard for subdomains
*.applylens.app       A    X.X.X.X
```

### Verify DNS Propagation

```bash
# Check A record
dig applylens.app +short

# Check from multiple locations
nslookup applylens.app 8.8.8.8
```

⏱️ **DNS propagation can take 1-48 hours**

---

## 🔐 SSL/TLS Certificate Setup

### Option 1: Let's Encrypt with Certbot (Recommended)

**Install Certbot:**
```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

**Obtain Certificate:**
```bash
# Stop nginx temporarily if running
docker-compose -f docker-compose.prod.yml stop nginx

# Obtain certificate
sudo certbot certonly --standalone \
  -d applylens.app \
  -d www.applylens.app \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive

# Certificates will be saved to:
# /etc/letsencrypt/live/applylens.app/fullchain.pem
# /etc/letsencrypt/live/applylens.app/privkey.pem
```

**Copy Certificates to Project:**
```bash
# Create SSL directory
mkdir -p infra/nginx/ssl

# Copy certificates (run as root or with sudo)
sudo cp /etc/letsencrypt/live/applylens.app/fullchain.pem infra/nginx/ssl/
sudo cp /etc/letsencrypt/live/applylens.app/privkey.pem infra/nginx/ssl/
sudo chown -R $USER:$USER infra/nginx/ssl/
chmod 600 infra/nginx/ssl/privkey.pem
```

**Auto-Renewal Setup:**
```bash
# Test renewal
sudo certbot renew --dry-run

# Add renewal script
cat > /usr/local/bin/renew-applylens-certs.sh << 'EOF'
#!/bin/bash
certbot renew --quiet --deploy-hook "
  cp /etc/letsencrypt/live/applylens.app/fullchain.pem /path/to/ApplyLens/infra/nginx/ssl/
  cp /etc/letsencrypt/live/applylens.app/privkey.pem /path/to/ApplyLens/infra/nginx/ssl/
  docker-compose -f /path/to/ApplyLens/docker-compose.prod.yml exec nginx nginx -s reload
"
EOF

sudo chmod +x /usr/local/bin/renew-applylens-certs.sh

# Add to crontab (runs daily at 3am)
(crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/renew-applylens-certs.sh") | crontab -
```

### Option 2: Cloudflare SSL (Alternative)

If using Cloudflare as your DNS provider, you can use Cloudflare's SSL:

1. **Set SSL/TLS mode to "Full (strict)"** in Cloudflare dashboard
2. **Generate Origin Certificate** in Cloudflare dashboard
3. **Save certificate files** to `infra/nginx/ssl/`

### Option 3: Manual Certificate

Place your SSL certificate files:
```
infra/nginx/ssl/fullchain.pem    # Certificate + CA bundle
infra/nginx/ssl/privkey.pem      # Private key
```

---

## ⚙️ Environment Configuration

### 1. Create Production Environment File

```bash
# Copy example to production config
cp infra/.env.example infra/.env.prod

# Edit with your production values
nano infra/.env.prod
```

### 2. Configure Production Variables

**infra/.env.prod:**
```bash
# Database Configuration
POSTGRES_USER=applylens_prod
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD_HERE_MIN_32_CHARS
POSTGRES_DB=applylens_production

# Server Configuration
DOMAIN=applylens.app
API_URL=https://applylens.app
VITE_API_URL=https://applylens.app

# Ports (internal - nginx handles external routing)
API_PORT=8003
WEB_PORT=5175

# Elasticsearch Configuration
ES_ENABLED=true
ES_URL=http://es:9200
KIBANA_PORT=5601
ES_RECREATE_ON_START=false  # Important: false in production!

# Gmail OAuth Configuration
GOOGLE_CREDENTIALS=/secrets/google.json
GOOGLE_OAUTH_SCOPES=https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email openid
OAUTH_STATE_SECRET=$(openssl rand -hex 32)  # Generate: openssl rand -hex 32

# Google OAuth Client Credentials
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# OAuth Redirect URIs - PRODUCTION
GOOGLE_REDIRECT_URI=https://applylens.app/auth/google/callback
OAUTH_REDIRECT_URI=https://applylens.app/auth/google/callback

# Elasticsearch Index
ELASTICSEARCH_INDEX=gmail_emails_prod

# Security
DEFAULT_USER_EMAIL=admin@applylens.app
SECRET_KEY=$(openssl rand -base64 32)  # Generate: openssl rand -base64 32

# Optional: Monitoring
GRAFANA_ADMIN_PASSWORD=CHANGE_ME_STRONG_PASSWORD
PROMETHEUS_RETENTION=30d
```

### 3. Update Google OAuth Credentials

1. **Go to Google Cloud Console** → APIs & Services → Credentials
2. **Edit your OAuth 2.0 Client ID**
3. **Add Authorized Redirect URIs:**
   ```
   https://applylens.app/auth/google/callback
   https://www.applylens.app/auth/google/callback
   ```
4. **Add Authorized JavaScript Origins:**
   ```
   https://applylens.app
   https://www.applylens.app
   ```

### 4. Update Nginx SSL Configuration

Create `infra/nginx/conf.d/applylens-ssl.conf`:

```nginx
# SSL/TLS Configuration for applylens.app

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name applylens.app www.applylens.app;
    
    # Allow certbot verification
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name applylens.app www.applylens.app;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    # Modern SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    
    # SSL Session
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    
    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/nginx/ssl/fullchain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self' https:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; style-src 'self' 'unsafe-inline' https:; img-src 'self' data: https:; font-src 'self' data: https:; connect-src 'self' https:; frame-ancestors 'self'" always;
    
    # Basic Settings
    client_max_body_size 25m;
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    
    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml font/truetype font/opentype application/vnd.ms-fontobject image/svg+xml;

    # Health Check
    location = /health {
        access_log off;
        add_header Content-Type text/plain;
        return 200 "ok\n";
    }

    # Robots & SEO
    location = /robots.txt {
        add_header Content-Type text/plain;
        return 200 "User-agent: *\nAllow: /\n";
    }

    # Redirect root to web app
    location = / {
        return 302 /web/;
    }

    # Web Application (React/Vite SPA)
    location /web/ {
        if ($request_uri = "/web") {
            return 301 /web/;
        }
        proxy_pass http://web:5175/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
    }

    # API - OAuth Callback (must not be rewritten)
    location /auth/google/ {
        proxy_pass http://api:8003/auth/google/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API Documentation
    location /docs/ {
        proxy_pass http://api:8003/docs/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /openapi.json {
        proxy_pass http://api:8003/openapi.json;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API Root (catch-all for API routes)
    location / {
        proxy_pass http://api:8003/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Monitoring Tools (Optional - remove if not needed in production)
    location /grafana/ {
        auth_basic "Monitoring Access";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://grafana:3000/;
        proxy_set_header X-Forwarded-Prefix /grafana;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /kibana/ {
        auth_basic "Analytics Access";
        auth_basic_user_file /etc/nginx/.htpasswd;
        rewrite ^/kibana/(.*)$ /$1 break;
        proxy_pass http://kibana:5601/kibana/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /prometheus/ {
        auth_basic "Metrics Access";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://prometheus:9090/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# WebSocket upgrade map
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
```

### 5. Create Basic Auth for Monitoring Tools

```bash
# Install apache2-utils for htpasswd
sudo apt install -y apache2-utils

# Create password file (replace 'admin' with your username)
sudo htpasswd -c infra/nginx/.htpasswd admin

# Add more users (without -c flag)
sudo htpasswd infra/nginx/.htpasswd user2
```

---

## 🚀 Deployment Options

### Option A: Direct Deployment (Simple)

**1. Upload Project to Server:**
```bash
# From your local machine
rsync -avz --exclude='node_modules' --exclude='.git' \
  /path/to/ApplyLens/ user@your-server-ip:/opt/applylens/
```

**2. SSH to Server:**
```bash
ssh user@your-server-ip
cd /opt/applylens
```

**3. Set Environment:**
```bash
# Use production environment file
export ENV_FILE=infra/.env.prod

# Or create symlink
ln -sf infra/.env.prod infra/.env
```

**4. Deploy:**
```bash
# Make deployment script executable
chmod +x deploy-prod.sh

# Run deployment
./deploy-prod.sh

# Select: "1) Fresh deployment"
```

### Option B: CI/CD with GitHub Actions (Recommended)

Create `.github/workflows/deploy-production.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
    tags: ['v*']
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/applylens
            git pull origin main
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d --build
            docker-compose -f docker-compose.prod.yml exec -T api alembic upgrade head
```

**Required GitHub Secrets:**
- `SERVER_HOST`: Your server IP or domain
- `SERVER_USER`: SSH username
- `SSH_PRIVATE_KEY`: Private SSH key for authentication

### Option C: Manual Docker Compose

```bash
# 1. Build images
docker-compose -f docker-compose.prod.yml build

# 2. Start services
docker-compose -f docker-compose.prod.yml up -d

# 3. Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# 4. Check status
docker-compose -f docker-compose.prod.yml ps
```

---

## ✅ Post-Deployment Steps

### 1. Verify Services

```bash
# Check all containers are running
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Test health endpoints
curl https://applylens.app/health
curl https://applylens.app/api/healthz
```

### 2. Test SSL Certificate

```bash
# Check SSL certificate
openssl s_client -connect applylens.app:443 -servername applylens.app

# Test SSL rating
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=applylens.app
```

### 3. Test OAuth Flow

1. Visit https://applylens.app/web/
2. Click "Sign in with Google"
3. Verify redirect works and authentication succeeds

### 4. Setup Monitoring Alerts

Configure Prometheus alerts in `infra/prometheus/alerts/`:
- High CPU/Memory usage
- Database connection failures
- API response time degradation
- SSL certificate expiration

### 5. Setup Backups

**Database Backup Script** (`/usr/local/bin/backup-applylens-db.sh`):
```bash
#!/bin/bash
BACKUP_DIR="/backup/applylens"
DATE=$(date +%Y%m%d_%H%M%S)
CONTAINER="applylens-db-prod"

mkdir -p $BACKUP_DIR

docker exec $CONTAINER pg_dump -U applylens_prod applylens_production \
  | gzip > $BACKUP_DIR/applylens_db_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

**Add to crontab:**
```bash
# Daily backup at 2am
0 2 * * * /usr/local/bin/backup-applylens-db.sh
```

### 6. Setup Log Rotation

Create `/etc/logrotate.d/applylens`:
```
/var/lib/docker/volumes/applylens_nginx_logs_prod/_data/*.log
/var/lib/docker/volumes/applylens_api_logs_prod/_data/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        docker-compose -f /opt/applylens/docker-compose.prod.yml exec nginx nginx -s reload
    endscript
}
```

---

## 🔍 Troubleshooting

### SSL Certificate Issues

```bash
# Check certificate validity
openssl x509 -in infra/nginx/ssl/fullchain.pem -text -noout

# Test SSL handshake
openssl s_client -connect applylens.app:443

# Check nginx SSL configuration
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```

### DNS Not Resolving

```bash
# Check DNS propagation
dig applylens.app
nslookup applylens.app

# Test from different DNS servers
dig @8.8.8.8 applylens.app
dig @1.1.1.1 applylens.app
```

### OAuth Redirect Issues

1. **Check Google Cloud Console** redirect URIs match exactly
2. **Verify environment variables:**
   ```bash
   docker-compose -f docker-compose.prod.yml exec api env | grep REDIRECT
   ```
3. **Check nginx proxy headers:**
   ```bash
   docker-compose -f docker-compose.prod.yml logs nginx | grep "X-Forwarded"
   ```

### Container Not Starting

```bash
# Check container logs
docker-compose -f docker-compose.prod.yml logs <service-name>

# Check specific container
docker logs applylens-api-prod

# Inspect container
docker inspect applylens-api-prod
```

### Database Connection Issues

```bash
# Test database connectivity
docker-compose -f docker-compose.prod.yml exec api python -c "
from app.database import engine
conn = engine.connect()
print('Database connection successful!')
conn.close()
"

# Check database logs
docker-compose -f docker-compose.prod.yml logs db
```

---

## 📚 Additional Resources

- **SSL Best Practices:** https://ssl-config.mozilla.org/
- **Nginx Security:** https://nginx.org/en/docs/http/ngx_http_ssl_module.html
- **Let's Encrypt Docs:** https://letsencrypt.org/docs/
- **Docker Security:** https://docs.docker.com/engine/security/
- **Prometheus Monitoring:** https://prometheus.io/docs/

---

## 🆘 Support

If you encounter issues:

1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Review documentation: See `PRODUCTION_DEPLOYMENT.md`
3. Test locally first: Use `docker-compose.yml` for local testing
4. Check firewall rules: Ensure ports 80, 443 are open
5. Verify DNS: Wait for full DNS propagation (up to 48h)

---

**Last Updated:** October 14, 2025
**Version:** 1.0.0
