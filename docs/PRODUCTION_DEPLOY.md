# ApplyLens Production Deployment Guide

## 🚀 One-Shot Deploy (Copy/Paste Ready)

Run this on your production server shell (no prompts required):

```bash
set -euo pipefail

# 1) Get latest code
cd /opt/applylens || mkdir -p /opt/applylens && cd /opt/applylens
if [ -d .git ]; then
  git fetch --all -q && git checkout main && git pull -q
else
  git clone -q https://github.com/leok974/ApplyLens.git . && git checkout main
fi

# 2) Setup environment file
cp -n infra/.env.example infra/.env.prod 2>/dev/null || true

# ---- EDIT ONCE: Configure infra/.env.prod with production values ----
# Required variables (examples):
# POSTGRES_PASSWORD=supersecret
# APP_ENV=prod
# PUBLIC_URL=https://applylens.app
# VITE_API_BASE=/api
# CLOUDFLARED_TUNNEL_TOKEN=<your Cloudflare tunnel token>
# ----------------------------------------------------------------------

# 3) Build production images
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod build

# 4) Start all services
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d

# 5) Run database migrations
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod exec api alembic upgrade head

# 6) Health checks
curl -fsSL https://applylens.app/api/healthz && echo " ✓ API healthy"
curl -I -s https://applylens.app/ | head -n1
```

---

## ☁️ Cloudflare Configuration

### Tunnel Setup

**WebSocket & HTTP/2:**
- ✅ Enabled by default - no changes needed
- Tunnel automatically handles WebSocket upgrades for HMR

**Cache Rules (Important):**
```
Bypass cache for:
- /api/*
- /docs/*
- /@vite/*
- /__vite_ping
```

**SSL/TLS Mode:**
- **Recommended:** Full (strict) if nginx has valid certs
- **Alternative:** Full if using self-signed certs
- **Internal:** Cloudflare terminates SSL, nginx serves HTTP internally

**Origin Configuration:**
```yaml
# Cloudflare Tunnel config (cloudflared)
ingress:
  - hostname: applylens.app
    service: http://nginx:80
    originRequest:
      noTLSVerify: true  # If nginx uses self-signed
      connectTimeout: 30s
      keepAliveTimeout: 90s
```

### CORS Prevention

Your web app should call **relative URLs** only:
- ✅ `/api/...` (same-origin, no CORS)
- ❌ `http://localhost:8003/api/...` (cross-origin, CORS issues)

**Environment Variable:**
```bash
VITE_API_BASE=/api  # Already configured in .env.prod
```

Nginx proxies `/api/*` to the FastAPI backend internally → no CORS needed.

---

## ✅ Verification Checklist

Run these from your local machine after deployment:

```bash
# 1. Check HTTPS redirect
curl -I https://applylens.app
# Expected: HTTP/2 200 OK

# 2. Verify API health
curl -s https://applylens.app/api/healthz
# Expected: {"status":"healthy"}

# 3. Open FastAPI docs
open https://applylens.app/docs
# Expected: Interactive API documentation loads

# 4. Open frontend
open https://applylens.app/
# Expected: React application loads

# 5. Check service status
ssh your-server "cd /opt/applylens && docker compose -f docker-compose.prod.yml ps"
# Expected: All services "Up" and healthy
```

---

## 🔧 Common "First Run" Fixes

### 1. **Blank UI / Routing Issues**

**Problem:** Frontend shows blank page or routes don't work

**Solution:**
```bash
# Verify build environment
docker compose -f docker-compose.prod.yml exec web env | grep VITE
# Should show: VITE_API_BASE=/api

# Rebuild if needed
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --build web
```

### 2. **CORS Errors**

**Problem:** Browser console shows CORS errors

**Root Cause:** UI calling absolute URLs (e.g., `http://localhost:8003`)

**Solution:**
```bash
# 1. Verify API base in .env.prod
grep VITE_API_BASE infra/.env.prod
# Should be: VITE_API_BASE=/api

# 2. Check API client configuration
# In web/src/lib/api.ts, base URL should be:
# const baseURL = import.meta.env.VITE_API_BASE || '/api'

# 3. Rebuild web container
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --build web
```

### 3. **502/504 Gateway Errors**

**Problem:** Cloudflare returns 502 Bad Gateway or 504 Timeout

**Solution:**
```bash
# Check nginx logs
docker compose -f docker-compose.prod.yml logs nginx --tail=50

# Check cloudflared connection
docker compose -f docker-compose.prod.yml logs cloudflared --tail=50

# Check if services are healthy
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml exec nginx curl -f http://web:5173/ || echo "Web unreachable"
docker compose -f docker-compose.prod.yml exec nginx curl -f http://api:8003/api/healthz || echo "API unreachable"
```

### 4. **Database Authentication Errors**

**Problem:** API can't connect to PostgreSQL

**Solution:**
```bash
# 1. Verify password consistency
grep POSTGRES_PASSWORD infra/.env.prod
# Must match in both POSTGRES_PASSWORD and DATABASE_URL

# 2. Test database connection
docker compose -f docker-compose.prod.yml exec db psql -U applylens -c "SELECT version();"

# 3. Check API database connection
docker compose -f docker-compose.prod.yml logs api --tail=20 | grep -i "database\|connection"
```

### 5. **Elasticsearch Connection Issues**

**Problem:** API can't reach Elasticsearch

**Solution:**
```bash
# Check Elasticsearch health
docker compose -f docker-compose.prod.yml exec api curl -f http://es:9200/_cluster/health

# Verify ES password
grep ELASTIC_PASSWORD infra/.env.prod
# Must match ELASTICSEARCH_PASSWORD in API config

# Restart with fresh ES data (DANGER: deletes data)
docker compose -f docker-compose.prod.yml down -v
docker volume rm applylens_es-data
docker compose -f docker-compose.prod.yml up -d
```

---

## 📦 Daily Operations

### Re-deploy New Version

```bash
cd /opt/applylens
git pull
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --build
```

### Check All Services

```bash
# Service status
docker compose -f docker-compose.prod.yml ps

# Live logs (all services)
docker compose -f docker-compose.prod.yml logs -f

# Specific service logs
docker compose -f docker-compose.prod.yml logs -f nginx
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f cloudflared
```

### Database Migrations

```bash
# Run pending migrations
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod exec api alembic upgrade head

# Create new migration (after model changes)
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod exec api alembic revision --autogenerate -m "description"

# Rollback one migration
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod exec api alembic downgrade -1

# View migration history
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod exec api alembic history
```

### Database Backup & Restore

```bash
# Backup
docker compose -f docker-compose.prod.yml exec db pg_dump -U applylens applylens > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
cat backup_20250114_120000.sql | docker compose -f docker-compose.prod.yml exec -T db psql -U applylens applylens
```

### View Resource Usage

```bash
# Container stats
docker compose -f docker-compose.prod.yml stats

# Disk usage
docker system df -v

# Cleanup unused resources
docker system prune -a --volumes  # DANGER: removes unused volumes
```

### Restart Services

```bash
# Restart all
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker compose -f docker-compose.prod.yml restart nginx
docker compose -f docker-compose.prod.yml restart api

# Force recreate (config changes)
docker compose -f docker-compose.prod.yml up -d --force-recreate nginx
```

### Update Secrets/Environment

```bash
# 1. Edit environment file
nano infra/.env.prod

# 2. Recreate affected services
docker compose -f docker-compose.prod.yml up -d --force-recreate api web

# 3. Verify new config
docker compose -f docker-compose.prod.yml exec api env | grep YOUR_VAR
```

---

## 🔍 Monitoring & Health Checks

### Quick Health Dashboard

```bash
#!/bin/bash
# Save as /opt/applylens/health-check.sh

cd /opt/applylens

echo "=== Service Status ==="
docker compose -f docker-compose.prod.yml ps

echo -e "\n=== API Health ==="
curl -sf https://applylens.app/api/healthz && echo "✓ API OK" || echo "✗ API FAIL"

echo -e "\n=== Database ==="
docker compose -f docker-compose.prod.yml exec -T db pg_isready -U applylens && echo "✓ DB OK" || echo "✗ DB FAIL"

echo -e "\n=== Elasticsearch ==="
docker compose -f docker-compose.prod.yml exec -T api curl -sf http://es:9200/_cluster/health | jq -r '.status' && echo "✓ ES OK" || echo "✗ ES FAIL"

echo -e "\n=== Disk Usage ==="
df -h /var/lib/docker

echo -e "\n=== Container Memory ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Setup Automated Health Checks (Optional)

```bash
# Add to crontab
crontab -e

# Check every 5 minutes
*/5 * * * * /opt/applylens/health-check.sh >> /var/log/applylens-health.log 2>&1
```

---

## 🚨 Emergency Procedures

### Complete Stack Restart

```bash
cd /opt/applylens
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f
```

### Rollback to Previous Version

```bash
cd /opt/applylens
git log --oneline -10  # Find previous commit
git checkout <commit-hash>
docker compose -f docker-compose.prod.yml up -d --build
```

### Emergency Shutdown

```bash
cd /opt/applylens
docker compose -f docker-compose.prod.yml down
```

### Factory Reset (DANGER: Deletes ALL data)

```bash
cd /opt/applylens
docker compose -f docker-compose.prod.yml down -v
docker volume prune -f
docker image prune -af
# Then re-run one-shot deploy from top of this document
```

---

## 📊 Performance Tuning

### Production Environment Variables

Add to `infra/.env.prod` for optimal performance:

```bash
# API
WORKERS=4                    # Number of Gunicorn workers (2-4x CPU cores)
LOG_LEVEL=INFO              # Production logging
ENABLE_CORS=false           # Disable if same-origin only
MAX_CONNECTIONS_PER_CHILD=1000

# Database
POSTGRES_MAX_CONNECTIONS=100
POSTGRES_SHARED_BUFFERS=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=1GB

# Elasticsearch
ES_JAVA_OPTS=-Xms512m -Xmx1g  # Heap size (50% of ES memory)

# Nginx
NGINX_WORKER_CONNECTIONS=1024
NGINX_KEEPALIVE_TIMEOUT=65
```

### Resource Limits (docker-compose.prod.yml)

Ensure you have appropriate resource limits set:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          memory: 512M

  db:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          memory: 1G

  es:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          memory: 1G
```

---

## 📝 Maintenance Windows

### Planned Downtime Procedure

```bash
# 1. Announce (set maintenance page)
echo "maintenance" > /opt/applylens/maintenance.txt

# 2. Stop services gracefully
docker compose -f docker-compose.prod.yml stop web api

# 3. Perform maintenance (DB backups, migrations, etc.)
docker compose -f docker-compose.prod.yml exec db pg_dump -U applylens applylens > backup.sql

# 4. Restart services
docker compose -f docker-compose.prod.yml start web api

# 5. Remove maintenance flag
rm /opt/applylens/maintenance.txt
```

---

## 🔐 Security Checklist

- [ ] All secrets in `.env.prod` (never commit)
- [ ] Strong `POSTGRES_PASSWORD` (minimum 32 chars)
- [ ] Strong `ELASTIC_PASSWORD` (minimum 32 chars)
- [ ] Cloudflare SSL mode: Full (strict)
- [ ] API rate limiting enabled
- [ ] Database backups automated
- [ ] Container security scanning in CI/CD
- [ ] Regular dependency updates
- [ ] Monitoring and alerting configured
- [ ] Firewall rules: only ports 80/443 exposed

---

## 📞 Support & Troubleshooting

**Common Issues:** See "Common First Run Fixes" section above

**Logs Location:**
- Application: `docker compose logs`
- System: `/var/log/syslog` or `journalctl -u docker`

**Performance Issues:**
```bash
# Check resource usage
docker stats

# Check slow queries (if DB issues)
docker compose -f docker-compose.prod.yml exec db psql -U applylens -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

**Need Help?**
- GitHub Issues: https://github.com/leok974/ApplyLens/issues
- Check documentation: `/opt/applylens/docs/`
