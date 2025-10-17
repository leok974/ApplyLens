# 🚀 Production Deployment Guide for applylens.app

## Prerequisites Checklist

Before deploying to production, ensure you have:

- [ ] **Production Server** with SSH access
- [ ] **Docker & Docker Compose** installed on the server
- [ ] **Domain**: applylens.app configured in Cloudflare
- [ ] **Google OAuth Credentials** for production (https://console.cloud.google.com)
- [ ] **Server Resources**: Minimum 4GB RAM, 20GB disk space

## Step 1: Prepare Your Production Server

### 1.1 SSH to Your Server

```bash
ssh your-username@your-server-ip
```

### 1.2 Install Docker (if not already installed)

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 1.3 Clone the Repository

```bash
# Create directory for the application
mkdir -p ~/applylens
cd ~/applylens

# Clone the repository
git clone https://github.com/leok974/ApplyLens.git .

# Checkout the production deployment branch
git checkout chore/prod-deploy
```

## Step 2: Configure Google OAuth for Production

### 2.1 Update Google OAuth Settings

1. Go to https://console.cloud.google.com/apis/credentials
2. Select your OAuth 2.0 Client ID
3. Update **Authorized redirect URIs**:
   ```
   https://applylens.app/auth/google/callback
   ```
4. Update **Authorized JavaScript origins**:
   ```
   https://applylens.app
   ```
5. Click **Save**

### 2.2 Get Your Credentials

Copy your:
- **Client ID**: Starts with `xxxxx.apps.googleusercontent.com`
- **Client Secret**: Your secret key

## Step 3: Set Up Cloudflare Tunnel

### 3.1 Install cloudflared

```bash
# Download cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Verify installation
cloudflared --version
```

### 3.2 Authenticate with Cloudflare

```bash
# This will open a browser for authentication
cloudflared tunnel login
```

### 3.3 Create Tunnel

```bash
# Create a tunnel named "applylens"
cloudflared tunnel create applylens

# Note the Tunnel ID from the output
# Example: Created tunnel applylens with id abc123-def456-ghi789
```

### 3.4 Configure Tunnel

```bash
# Create config directory
sudo mkdir -p /etc/cloudflared

# Create config file
sudo nano /etc/cloudflared/config.yml
```

Paste this configuration (replace `YOUR_TUNNEL_ID` with your actual tunnel ID):

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /root/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: applylens.app
    service: http://localhost:80
  - hostname: www.applylens.app
    service: http://localhost:80
  - service: http_status:404
```

### 3.5 Route DNS

```bash
# Route your domain to the tunnel
cloudflared tunnel route dns applylens applylens.app
cloudflared tunnel route dns applylens www.applylens.app
```

### 3.6 Start Tunnel as Service

```bash
# Install as system service
sudo cloudflared service install

# Start the service
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

# Check status
sudo systemctl status cloudflared
```

## Step 4: Configure Production Environment

### 4.1 Create Production Environment File

```bash
cd ~/applylens
cp infra/.env.prod.example infra/.env.prod
nano infra/.env.prod
```

### 4.2 Fill in Required Variables

Update these values in `infra/.env.prod`:

```bash
# Domain Configuration
DOMAIN=applylens.app
API_URL=https://applylens.app

# Google OAuth (from Step 2)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://applylens.app/auth/google/callback

# Generate secrets (run these commands to generate):
# openssl rand -hex 32
SECRET_KEY=<generate-with-openssl>
SESSION_SECRET=<generate-with-openssl>
OAUTH_STATE_SECRET=<generate-with-openssl>

# Database
POSTGRES_USER=applylens_user
POSTGRES_PASSWORD=<generate-secure-password>
POSTGRES_DB=applylens_prod
DATABASE_URL=postgresql://applylens_user:<password>@db:5432/applylens_prod

# Elasticsearch
ELASTIC_PASSWORD=<generate-secure-password>

# Monitoring
GRAFANA_ADMIN_PASSWORD=<generate-secure-password>
PROMETHEUS_PASSWORD=<generate-secure-password>
```

### 4.3 Generate Secrets

```bash
# Generate all secrets at once
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "SESSION_SECRET=$(openssl rand -hex 32)"
echo "OAUTH_STATE_SECRET=$(openssl rand -hex 32)"
echo "POSTGRES_PASSWORD=$(openssl rand -base64 24)"
echo "ELASTIC_PASSWORD=$(openssl rand -base64 24)"
echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 16)"
```

Copy these values into your `.env.prod` file.

## Step 5: Configure Cloudflare Dashboard

### 5.1 SSL/TLS Settings

1. Go to https://dash.cloudflare.com
2. Select your domain: **applylens.app**
3. Go to **SSL/TLS** → **Overview**
4. Set encryption mode to: **Full** (not Full (strict))

### 5.2 Enable Always Use HTTPS

1. Go to **SSL/TLS** → **Edge Certificates**
2. Toggle **Always Use HTTPS**: **On**

### 5.3 Verify DNS

1. Go to **DNS** → **Records**
2. Verify CNAME records exist:
   - `applylens.app` → `abc123.cfargotunnel.com` (proxied - orange cloud)
   - `www.applylens.app` → `abc123.cfargotunnel.com` (proxied - orange cloud)

## Step 6: Deploy to Production

### 6.1 Make Deployment Script Executable

```bash
cd ~/applylens
chmod +x deploy-to-server.sh health-check.sh rollback.sh
```

### 6.2 Run Deployment

```bash
./deploy-to-server.sh
```

This script will:
1. ✅ Validate all required files exist
2. ✅ Check Docker and Docker Compose are installed
3. ✅ Validate docker-compose.prod.yml syntax
4. ✅ Build production images (API + Web)
5. ✅ Stop old containers gracefully
6. ✅ Start production stack
7. ✅ Wait for services to be healthy
8. ✅ Run database migrations
9. ✅ Perform health checks
10. ✅ Display service status

### 6.3 Monitor Deployment

The script will show progress. Watch for:
- ✅ Green "SUCCESS" messages
- ⚠️  Yellow "WARNING" messages (usually OK)
- ❌ Red "ERROR" messages (need attention)

## Step 7: Verify Deployment

### 7.1 Run Health Checks

```bash
./health-check.sh
```

This will verify:
- All 9 services are running
- Nginx is responding
- API is healthy
- Database is connected
- Elasticsearch is up
- External access via Cloudflare works

### 7.2 Manual Verification

#### Test External Access:
```bash
curl -I https://applylens.app/
curl -I https://applylens.app/docs/
curl -I https://applylens.app/web/
```

Expected: HTTP 200 or 302 responses with `cf-ray` header

#### Test OAuth Flow:
1. Open: https://applylens.app/web/
2. Click "Sign in with Google"
3. Authorize the app
4. Verify you're redirected back and logged in

### 7.3 Check Logs

```bash
# Check all services
docker compose -f docker-compose.prod.yml logs --tail=50

# Check specific service
docker compose -f docker-compose.prod.yml logs api --tail=100
docker compose -f docker-compose.prod.yml logs web --tail=100
docker compose -f docker-compose.prod.yml logs nginx --tail=100
```

## Step 8: Post-Deployment Tasks

### 8.1 Set Up Monitoring Alerts (Optional)

Access monitoring dashboards:
- **Grafana**: https://applylens.app/grafana/ (admin / your-password)
- **Kibana**: https://applylens.app/kibana/
- **Prometheus**: https://applylens.app/prometheus/

### 8.2 Set Up Automated Backups

Create a backup script:

```bash
nano ~/backup-applylens.sh
```

Add:
```bash
#!/bin/bash
BACKUP_DIR="/home/$USER/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
docker compose -f ~/applylens/docker-compose.prod.yml exec -T db \
  pg_dump -U applylens_user applylens_prod | gzip > \
  $BACKUP_DIR/db_backup_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/db_backup_$DATE.sql.gz"
```

Make executable and add to crontab:
```bash
chmod +x ~/backup-applylens.sh

# Run daily at 2 AM
crontab -e
# Add: 0 2 * * * /home/$USER/backup-applylens.sh >> /var/log/applylens-backup.log 2>&1
```

### 8.3 Configure Firewall (Recommended)

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (even though Cloudflare Tunnel handles it)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

## Troubleshooting

### Issue: Services won't start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs

# Check specific service
docker compose -f docker-compose.prod.yml logs api
```

### Issue: Can't access via domain

1. Check Cloudflare Tunnel:
   ```bash
   sudo systemctl status cloudflared
   cloudflared tunnel info applylens
   ```

2. Check nginx:
   ```bash
   docker compose -f docker-compose.prod.yml logs nginx
   ```

3. Check DNS propagation:
   ```bash
   dig applylens.app
   nslookup applylens.app
   ```

### Issue: OAuth redirect not working

1. Verify Google OAuth settings have correct redirect URI
2. Check `.env.prod` has correct `GOOGLE_REDIRECT_URI`
3. Restart API service:
   ```bash
   docker compose -f docker-compose.prod.yml restart api
   ```

### Issue: Database connection failed

```bash
# Check database is running
docker compose -f docker-compose.prod.yml exec db pg_isready

# Check connection string in .env.prod
# Verify POSTGRES_PASSWORD matches DATABASE_URL
```

## Rollback Procedure

If something goes wrong:

```bash
./rollback.sh
```

Options:
1. **Quick Restart** - Restart services without rebuild
2. **View Recent Logs** - Diagnose issues
3. **Restart Specific Service** - Selective restart
4. **Roll Back to Previous Commit** - Git reset + rebuild
5. **Full Rebuild** - Clean slate with --no-cache
6. **Stop All Services** - Complete shutdown

## Service URLs

After successful deployment:

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | https://applylens.app/web/ | Google OAuth |
| API | https://applylens.app/ | N/A |
| API Docs | https://applylens.app/docs/ | N/A |
| Grafana | https://applylens.app/grafana/ | admin / from .env.prod |
| Kibana | https://applylens.app/kibana/ | elastic / from .env.prod |
| Prometheus | https://applylens.app/prometheus/ | admin / from .env.prod |

## Support

For issues:
1. Check logs: `docker compose -f docker-compose.prod.yml logs`
2. Run health check: `./health-check.sh`
3. Review documentation:
   - `CLOUDFLARE_TUNNEL_SETUP.md`
   - `POST_DEPLOY_VERIFICATION.md`
   - `PROD_DOMAIN_QUICK_REF.md`

---

**Deployment completed!** 🎉

Your ApplyLens application should now be live at https://applylens.app/
