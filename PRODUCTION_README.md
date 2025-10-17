# 🚀 ApplyLens Production Deployment

This guide covers building and deploying the ApplyLens production stack configured for **`https://applylens.app/web/`**.

## 📋 Prerequisites

### 1. Server Requirements
- Linux server (Ubuntu 22.04+ recommended)
- Docker Engine 24.0+
- Docker Compose v2.20+
- 4GB RAM minimum (8GB+ recommended)
- 20GB disk space minimum

### 2. Domain & DNS
- Domain registered: `applylens.app`
- Cloudflare account with domain added
- Cloudflare Tunnel created

### 3. Google OAuth Credentials
- Google Cloud Console project created
- OAuth 2.0 credentials configured
- Authorized redirect URI: `https://applylens.app/api/auth/google/callback`

---

## 🔧 Step 1: Configure Environment

### Copy and Edit Production Environment File

```bash
cd /opt/applylens
cp infra/.env.example infra/.env.prod
nano infra/.env.prod
```

### Required Configuration

Update these values in `infra/.env.prod`:

```bash
# =============================================================================
# CRITICAL: Change ALL of these before deploying!
# =============================================================================

# Domain Configuration
APP_ENV=prod
PUBLIC_URL=https://applylens.app
DOMAIN=applylens.app

# Database (CHANGE PASSWORD!)
POSTGRES_PASSWORD=YOUR_STRONG_PASSWORD_HERE_MIN_32_CHARS

# Elasticsearch (CHANGE PASSWORD!)
ELASTIC_PASSWORD=YOUR_STRONG_PASSWORD_HERE_MIN_32_CHARS
ELASTICSEARCH_PASSWORD=YOUR_STRONG_PASSWORD_HERE_MIN_32_CHARS

# API Security (Generate random 64-char strings)
SECRET_KEY=YOUR_RANDOM_64_CHAR_STRING_HERE
JWT_SECRET_KEY=YOUR_RANDOM_64_CHAR_STRING_HERE
SESSION_SECRET=YOUR_RANDOM_64_CHAR_STRING_HERE
OAUTH_STATE_SECRET=YOUR_RANDOM_64_CHAR_STRING_HERE

# Google OAuth (from Google Cloud Console)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Cloudflare Tunnel (from Cloudflare dashboard)
CLOUDFLARED_TUNNEL_TOKEN=your-cloudflare-tunnel-token

# Monitoring (CHANGE PASSWORD!)
GRAFANA_ADMIN_PASSWORD=YOUR_STRONG_PASSWORD_HERE
```

### Generate Strong Secrets

```bash
# Generate random passwords/secrets
openssl rand -base64 48  # For passwords (32+ chars)
openssl rand -hex 32     # For secret keys (64 chars)
```

---

## 🏗️ Step 2: Build Production Stack

### Option A: Using Build Script (Recommended)

**Windows (PowerShell):**
```powershell
# Build only
.\build-prod.ps1

# Build and deploy
.\build-prod.ps1 -Deploy

# Build, deploy, and run migrations
.\build-prod.ps1 -Deploy -Migrate

# Force restart everything
.\build-prod.ps1 -Deploy -Restart -Migrate
```

**Linux/Mac:**
```bash
# Make script executable (first time only)
chmod +x build-prod.sh

# Build only
./build-prod.sh

# Build and deploy
./build-prod.sh --deploy

# Build, deploy, and run migrations
./build-prod.sh --deploy --migrate

# Force restart everything
./build-prod.sh --deploy --restart --migrate
```

### Option B: Manual Build

```bash
# 1. Build images
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod build --no-cache

# 2. Start services
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d

# 3. Run migrations
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod exec api alembic upgrade head

# 4. Check status
docker compose -f docker-compose.prod.yml ps
```

---

## ☁️ Step 3: Configure Cloudflare Tunnel

### 1. Create Tunnel in Cloudflare Dashboard

1. Go to Cloudflare Zero Trust Dashboard
2. Navigate to **Access** → **Tunnels**
3. Create a new tunnel: `applylens-prod`
4. Copy the tunnel token

### 2. Configure Tunnel

**Public Hostname Configuration:**
```yaml
Subdomain: <blank> (or @)
Domain: applylens.app
Service:
  Type: HTTP
  URL: nginx:80
```

**Advanced Options:**
- ✅ Enable WebSocket
- ✅ Enable HTTP/2
- ✅ No TLS Verify (for internal communication)

### 3. Update Environment

Add tunnel token to `infra/.env.prod`:
```bash
CLOUDFLARED_TUNNEL_TOKEN=your-tunnel-token-here
```

### 4. Restart Cloudflared Service

```bash
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod restart cloudflared
docker compose -f docker-compose.prod.yml logs -f cloudflared
```

---

## ✅ Step 4: Verification

### Quick Health Checks

```bash
# Check all services are running
docker compose -f docker-compose.prod.yml ps

# Test endpoints locally
curl http://localhost/health           # Should return "ok"
curl http://localhost/api/healthz      # Should return JSON
curl http://localhost/web/             # Should return HTML

# Test through Cloudflare
curl https://applylens.app/health
curl https://applylens.app/api/healthz
```

### Access URLs

Once deployed and Cloudflare tunnel is connected:

- **🌐 Web App:** https://applylens.app/web/
- **📚 API Docs:** https://applylens.app/docs
- **❤️ Health Check:** https://applylens.app/health
- **📊 Prometheus:** https://applylens.app/prometheus/
- **📈 Grafana:** https://applylens.app/grafana/
- **🔍 Kibana:** https://applylens.app/kibana/

### Test SPA Routing

1. Open https://applylens.app/web/
2. Navigate to any route (e.g., `/web/jobs`)
3. Hit **F5** to hard refresh
4. ✅ **Expected:** Page loads correctly (no 404)

---

## 🔄 Daily Operations

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f nginx
docker compose -f docker-compose.prod.yml logs -f cloudflared
```

### Update Deployment

```bash
# Pull latest changes
cd /opt/applylens
git pull

# Rebuild and deploy
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --build

# Run migrations
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod exec api alembic upgrade head
```

### Restart Services

```bash
# Restart all
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker compose -f docker-compose.prod.yml restart api
docker compose -f docker-compose.prod.yml restart nginx
```

### Database Backup

```bash
# Create backup
docker compose -f docker-compose.prod.yml exec db pg_dump -U applylens applylens_production > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
cat backup_20250114_120000.sql | docker compose -f docker-compose.prod.yml exec -T db psql -U applylens applylens_production
```

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check service status
docker compose -f docker-compose.prod.yml ps

# Check logs for errors
docker compose -f docker-compose.prod.yml logs <service-name> --tail=50

# Restart service
docker compose -f docker-compose.prod.yml restart <service-name>
```

### 502 Bad Gateway

```bash
# Check nginx logs
docker compose -f docker-compose.prod.yml logs nginx --tail=50

# Check if backend services are running
docker compose -f docker-compose.prod.yml exec nginx curl -f http://web:80/
docker compose -f docker-compose.prod.yml exec nginx curl -f http://api:8003/api/healthz

# Check cloudflared connection
docker compose -f docker-compose.prod.yml logs cloudflared --tail=20
```

### Blank UI / Routing Issues

```bash
# Verify environment variables
docker compose -f docker-compose.prod.yml exec web env | grep VITE

# Should show:
# VITE_API_BASE=/api
# PUBLIC_URL=https://applylens.app

# Rebuild web if needed
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --build web
```

### Database Connection Issues

```bash
# Test database connection
docker compose -f docker-compose.prod.yml exec db psql -U applylens -c "SELECT version();"

# Check API can connect
docker compose -f docker-compose.prod.yml logs api --tail=20 | grep -i database
```

---

## 📊 Monitoring

### Service Health

```bash
# Quick status check
docker compose -f docker-compose.prod.yml ps

# Resource usage
docker stats --no-stream

# Disk usage
docker system df
```

### Access Monitoring Tools

- **Grafana:** https://applylens.app/grafana/ (admin / [configured password])
- **Prometheus:** https://applylens.app/prometheus/
- **Kibana:** https://applylens.app/kibana/

---

## 🔐 Security Checklist

- [x] All secrets in `.env.prod` are strong and unique
- [x] `POSTGRES_PASSWORD` is 32+ characters
- [x] All `*_SECRET` variables are random 64-character strings
- [x] Google OAuth credentials are production-ready
- [x] Cloudflare SSL mode is "Full" or "Full (strict)"
- [x] Monitoring tools have basic auth enabled (TODO)
- [x] Database backups are automated
- [x] Only ports 80/443 exposed via Cloudflare
- [x] Container security scanning in CI/CD (TODO)
- [x] Regular dependency updates scheduled (TODO)

---

## 📚 Additional Documentation

- **Full Deployment Guide:** [`docs/PRODUCTION_DEPLOY.md`](./PRODUCTION_DEPLOY.md)
- **Quick Reference:** [`docs/PRODUCTION_QUICKREF.md`](./PRODUCTION_QUICKREF.md)
- **Nginx Configuration:** [`docs/NGINX_VITE_SUBPATH.md`](./NGINX_VITE_SUBPATH.md)

---

## 🆘 Support

**Issues?**
- Check [`docs/PRODUCTION_DEPLOY.md`](./PRODUCTION_DEPLOY.md) for detailed troubleshooting
- View logs: `docker compose -f docker-compose.prod.yml logs -f`
- Open an issue: https://github.com/leok974/ApplyLens/issues

**Need Help?**
- Review the full deployment guide in `docs/`
- Check service logs for specific error messages
- Ensure all environment variables are correctly set
