# Production Deployment Quick Reference - applylens.app

## 🚀 Quick Start

### On Your Production Server:

```bash
# 1. Clone repository
git clone https://github.com/leok974/ApplyLens.git
cd ApplyLens

# 2. Make setup script executable
chmod +x setup-production.sh

# 3. Run automated setup
./setup-production.sh
```

The script will guide you through:
- Environment configuration
- SSL certificate setup (Let's Encrypt)
- Secret generation
- Docker image building
- Service deployment
- Health checks

---

## 📋 Pre-Deployment Checklist

### DNS Configuration
```dns
applylens.app         A    <YOUR_SERVER_IP>
www.applylens.app     A    <YOUR_SERVER_IP>
```

### Google OAuth Setup
1. Go to: https://console.cloud.google.com/apis/credentials
2. Edit your OAuth 2.0 Client ID
3. Add Authorized Redirect URIs:
   ```
   https://applylens.app/auth/google/callback
   https://www.applylens.app/auth/google/callback
   ```
4. Add Authorized JavaScript Origins:
   ```
   https://applylens.app
   https://www.applylens.app
   ```

### Required Secrets
Generate with these commands:
```bash
# OAuth State Secret
openssl rand -hex 32

# Secret Keys
openssl rand -base64 32

# Strong Passwords
openssl rand -base64 24
```

---

## 🔐 SSL Certificate Setup

### Option 1: Let's Encrypt (Automated)
```bash
# Stop nginx if running
docker-compose -f docker-compose.prod.yml stop nginx

# Obtain certificate
sudo certbot certonly --standalone \
  -d applylens.app \
  -d www.applylens.app \
  --email your-email@example.com \
  --agree-tos

# Copy certificates
sudo cp /etc/letsencrypt/live/applylens.app/fullchain.pem infra/nginx/ssl/
sudo cp /etc/letsencrypt/live/applylens.app/privkey.pem infra/nginx/ssl/
sudo chown -R $USER:$USER infra/nginx/ssl/
chmod 600 infra/nginx/ssl/privkey.pem
```

### Option 2: Manual Certificate
```bash
# Place your certificates in:
infra/nginx/ssl/fullchain.pem    # Certificate + CA bundle
infra/nginx/ssl/privkey.pem      # Private key
chmod 600 infra/nginx/ssl/privkey.pem
```

---

## ⚙️ Environment Configuration

### Create Production Environment File
```bash
# Copy template
cp infra/.env.prod.example infra/.env.prod

# Edit with your values
nano infra/.env.prod
```

### Required Environment Variables
```bash
# Database
POSTGRES_PASSWORD=<STRONG_PASSWORD>

# OAuth Secrets
OAUTH_STATE_SECRET=<GENERATED_HEX_32>
GOOGLE_CLIENT_ID=<YOUR_CLIENT_ID>
GOOGLE_CLIENT_SECRET=<YOUR_CLIENT_SECRET>

# Security
SECRET_KEY=<GENERATED_BASE64_32>
SESSION_SECRET=<GENERATED_BASE64_32>

# Monitoring
GRAFANA_ADMIN_PASSWORD=<STRONG_PASSWORD>
```

---

## 🚢 Manual Deployment

### Build and Start Services
```bash
# Build images
docker-compose -f docker-compose.prod.yml build --no-cache

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Check status
docker-compose -f docker-compose.prod.yml ps
```

### Or Use Deployment Script
```bash
# Make executable
chmod +x deploy-prod.sh

# Run deployment
./deploy-prod.sh

# Select option:
# 1) Fresh deployment (wipes data)
# 2) Update deployment (keeps data)
# 3) Quick restart
```

---

## 🌐 Service URLs

After deployment, access your services at:

| Service | URL | Notes |
|---------|-----|-------|
| **Frontend** | https://applylens.app/web/ | Main application |
| **API** | https://applylens.app/ | Backend API |
| **API Docs** | https://applylens.app/docs/ | Interactive API documentation |
| **Grafana** | https://applylens.app/grafana/ | Monitoring dashboard (Basic Auth) |
| **Kibana** | https://applylens.app/kibana/ | Log analytics (Basic Auth) |
| **Prometheus** | https://applylens.app/prometheus/ | Metrics (Basic Auth) |

---

## 🔧 Common Commands

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f nginx
```

### Restart Services
```bash
# All services
docker-compose -f docker-compose.prod.yml restart

# Specific service
docker-compose -f docker-compose.prod.yml restart api
```

### Stop/Start Services
```bash
# Stop
docker-compose -f docker-compose.prod.yml stop

# Start
docker-compose -f docker-compose.prod.yml start
```

### Check Status
```bash
docker-compose -f docker-compose.prod.yml ps
```

### Run Migrations
```bash
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Access Container Shell
```bash
docker-compose -f docker-compose.prod.yml exec api bash
```

---

## 🔍 Health Checks

### Test Endpoints
```bash
# Health check
curl https://applylens.app/health

# API health
curl https://applylens.app/api/healthz

# SSL certificate
openssl s_client -connect applylens.app:443 -servername applylens.app
```

### Check SSL Rating
Visit: https://www.ssllabs.com/ssltest/analyze.html?d=applylens.app

---

## 📊 Monitoring Setup

### Create Basic Auth for Monitoring Tools
```bash
# Install htpasswd
sudo apt install apache2-utils

# Create password file
htpasswd -c infra/nginx/.htpasswd admin

# Add more users
htpasswd infra/nginx/.htpasswd user2
```

### Access Monitoring Tools
- **Grafana:** https://applylens.app/grafana/ (use basic auth)
- **Kibana:** https://applylens.app/kibana/ (use basic auth)
- **Prometheus:** https://applylens.app/prometheus/ (use basic auth)

---

## 💾 Backup & Restore

### Manual Database Backup
```bash
# Backup
docker-compose -f docker-compose.prod.yml exec db \
  pg_dump -U applylens_prod applylens_production | \
  gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore
gunzip < backup_20250101_120000.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T db \
  psql -U applylens_prod applylens_production
```

### Automated Backup Script
```bash
# Create backup script
sudo tee /usr/local/bin/backup-applylens.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/applylens"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
docker-compose -f /opt/applylens/docker-compose.prod.yml exec -T db \
  pg_dump -U applylens_prod applylens_production | \
  gzip > $BACKUP_DIR/db_$DATE.sql.gz
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
EOF

# Make executable
sudo chmod +x /usr/local/bin/backup-applylens.sh

# Add to crontab (daily at 2am)
(crontab -l; echo "0 2 * * * /usr/local/bin/backup-applylens.sh") | crontab -
```

---

## 🆘 Troubleshooting

### Container Not Starting
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs <service-name>

# Inspect container
docker inspect applylens-api-prod

# Check resources
docker stats
```

### SSL Issues
```bash
# Test certificate
openssl x509 -in infra/nginx/ssl/fullchain.pem -text -noout

# Test SSL handshake
curl -vI https://applylens.app

# Check nginx config
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```

### DNS Not Resolving
```bash
# Check DNS
dig applylens.app
nslookup applylens.app 8.8.8.8

# Test from multiple locations
dig @1.1.1.1 applylens.app
```

### OAuth Callback Issues
1. Verify Google Cloud Console redirect URIs match exactly
2. Check environment variables:
   ```bash
   docker-compose -f docker-compose.prod.yml exec api env | grep REDIRECT
   ```
3. Check nginx logs:
   ```bash
   docker-compose -f docker-compose.prod.yml logs nginx | grep oauth
   ```

---

## 📚 Documentation

- **Complete Setup Guide:** [PRODUCTION_DOMAIN_SETUP.md](PRODUCTION_DOMAIN_SETUP.md)
- **General Deployment:** [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- **Quick Start:** [PRODUCTION_QUICK_START.md](PRODUCTION_QUICK_START.md)
- **Docker Compose:** [docker-compose.prod.yml](docker-compose.prod.yml)

---

## 🔄 Update Deployment

### Pull Latest Changes
```bash
# Pull from GitHub
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## 📞 Support

### Verify Installation
```bash
# Check all services healthy
docker-compose -f docker-compose.prod.yml ps

# Test API
curl https://applylens.app/api/healthz

# Test Web
curl https://applylens.app/web/

# Check SSL
curl -vI https://applylens.app 2>&1 | grep SSL
```

### Common Issues
1. **Port 443 blocked:** Check firewall rules
2. **DNS not resolving:** Wait up to 48h for propagation
3. **SSL errors:** Verify certificate paths and permissions
4. **OAuth fails:** Double-check Google Cloud Console settings

---

**Last Updated:** October 14, 2025  
**Domain:** applylens.app  
**Version:** 1.0.0
