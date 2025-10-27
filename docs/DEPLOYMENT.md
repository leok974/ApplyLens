# ApplyLens Deployment & Rollback Guide

## Quick Reference

### Current Production Version
**v0.4.1** (2025-10-23)
- CSRF exemptions for UX metrics (heartbeat, chat/opened)
- Fixed heartbeat payload format
- Git SHA: `461336d`

### Image Digests (Immutable Pinning)
```yaml
api:  leoklemet/applylens-api@sha256:99a07206dfb3987c7c8f3775af0f61a405b298d4db54c9877ac567528ab1bc7a
web:  leoklemet/applylens-web@sha256:f069ea49758048488766ee191b423b27bb4d8c02920084d0154aca560772d61e
```

---

## Building New Versions

### Automated Build (Recommended)
```powershell
# Build and tag both services
.\scripts\build-and-tag.ps1 -Version "v0.4.2"

# Build, tag, and push to registry
.\scripts\build-and-tag.ps1 -Version "v0.4.2" -Push

# Build only specific service
.\scripts\build-and-tag.ps1 -Version "v0.4.2" -SkipApi   # Web only
.\scripts\build-and-tag.ps1 -Version "v0.4.2" -SkipWeb   # API only
```

### Manual Build
```powershell
# Get build metadata
$GIT_SHA = git rev-parse --short HEAD
$BUILD_DATE = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

# Build API
cd services/api
docker build `
  -t leoklemet/applylens-api:v0.4.2 `
  -t leoklemet/applylens-api:latest `
  -f Dockerfile.prod `
  --build-arg GIT_SHA=$GIT_SHA `
  --build-arg BUILD_DATE=$BUILD_DATE `
  .

# Build Web
cd ../../apps/web
docker build `
  -t leoklemet/applylens-web:v0.4.2 `
  -t leoklemet/applylens-web:latest `
  -f Dockerfile.prod `
  --build-arg GIT_SHA=$GIT_SHA `
  --build-arg BUILD_DATE=$BUILD_DATE `
  .
```

---

## Deploying New Versions

### 1. Update docker-compose.prod.yml
```yaml
api:
  image: leoklemet/applylens-api:v0.4.2  # Update version

web:
  image: leoklemet/applylens-web:v0.4.2  # Update version
```

### 2. Deploy
```powershell
cd D:\ApplyLens

# Deploy both services
docker-compose -f docker-compose.prod.yml up -d --force-recreate api web

# Deploy single service
docker-compose -f docker-compose.prod.yml up -d --force-recreate api
docker-compose -f docker-compose.prod.yml up -d --force-recreate web
```

### 3. Verify Deployment
```powershell
# Check container status
docker ps --filter "name=applylens-" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

# Verify health endpoints
curl http://localhost:8003/healthz
curl http://localhost:5175/

# Check logs
docker logs applylens-api-prod --tail 50
docker logs applylens-web-prod --tail 50

# View image metadata
docker inspect leoklemet/applylens-api:v0.4.2 --format='{{json .Config.Labels}}' | ConvertFrom-Json
docker inspect leoklemet/applylens-web:v0.4.2 --format='{{json .Config.Labels}}' | ConvertFrom-Json
```

---

## Rollback Procedures

### Fast Rollback (30 seconds)

#### Automated Rollback (Recommended)
```powershell
# Rollback both services
.\scripts\rollback.ps1 -Version "v0.4.0"

# Rollback specific service
.\scripts\rollback.ps1 -Version "v0.4.0" -Service "api"
.\scripts\rollback.ps1 -Version "v0.4.0" -Service "web"

# Dry run (preview changes)
.\scripts\rollback.ps1 -Version "v0.4.0" -DryRun
```

#### Manual Rollback
```powershell
# 1. Backup current config
Copy-Item docker-compose.prod.yml docker-compose.prod.yml.bak

# 2. Update versions in docker-compose.prod.yml
# Change: leoklemet/applylens-api:v0.4.1
# To:     leoklemet/applylens-api:v0.4.0

# 3. Recreate containers
docker-compose -f docker-compose.prod.yml up -d --force-recreate api web

# 4. Verify
curl http://localhost:8003/healthz
```

### Emergency Rollback (Image not available)
```powershell
# List available versions
docker images | grep applylens

# Pull previous version if needed
docker pull leoklemet/applylens-api:v0.4.0
docker pull leoklemet/applylens-web:v0.4.0

# Then follow rollback procedure above
```

---

## Version History

### v0.4.1 (2025-10-23) - **CURRENT**
- **API Changes:**
  - CSRF exemptions: `/ux/heartbeat`, `/ux/chat/opened` (+ `/api/*` variants)
  - Added OCI metadata labels
- **Web Changes:**
  - Fixed heartbeat payload: `{page: "/chat", ts: timestamp}`
  - Added OCI metadata labels
- **Git SHA:** `461336d`
- **Digests:**
  - API: `sha256:99a07206dfb3987c7c8f3775af0f61a405b298d4db54c9877ac567528ab1bc7a`
  - Web: `sha256:f069ea49758048488766ee191b423b27bb4d8c02920084d0154aca560772d61e`

### v0.4.0 (2025-10-22) - Previous Stable
- Production baseline before UX metrics fixes
- Known issues: 403/422 errors on UX endpoints

---

## Image Management

### List All Versions
```powershell
# Show all ApplyLens images
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}" | Select-String "applylens"
```

### Cleanup Old Images
```powershell
# Remove untagged images
docker image prune -f

# Remove specific old version
docker rmi leoklemet/applylens-api:v0.3.0
docker rmi leoklemet/applylens-web:v0.3.0

# Remove all unused images (DANGEROUS)
docker image prune -a
```

### Push to Registry
```powershell
# Push specific version
docker push leoklemet/applylens-api:v0.4.1
docker push leoklemet/applylens-web:v0.4.1

# Push latest
docker push leoklemet/applylens-api:latest
docker push leoklemet/applylens-web:latest

# Pull from registry
docker pull leoklemet/applylens-api:v0.4.1
docker pull leoklemet/applylens-web:v0.4.1
```

---

## Immutable Digest Pinning (Advanced)

### Why Use Digests?
- **Immutable**: Content-addressable, can't be overwritten
- **Security**: Prevents tag hijacking
- **Compliance**: Audit trail for deployed code

### Using Digests in docker-compose.prod.yml
```yaml
api:
  # Tag-based (can be overwritten)
  image: leoklemet/applylens-api:v0.4.1

  # Digest-based (immutable, recommended for production)
  image: leoklemet/applylens-api@sha256:99a07206dfb3987c7c8f3775af0f61a405b298d4db54c9877ac567528ab1bc7a
```

### Get Digest After Push
```powershell
# Get repository digest (after push)
docker inspect --format='{{index .RepoDigests 0}}' leoklemet/applylens-api:v0.4.1

# Get image ID (local only)
docker inspect --format='{{.Id}}' leoklemet/applylens-api:v0.4.1
```

---

## Troubleshooting

### Container Won't Start
```powershell
# Check logs
docker logs applylens-api-prod --tail 100
docker logs applylens-web-prod --tail 100

# Check health status
docker inspect applylens-api-prod --format='{{.State.Health.Status}}'

# Restart single container
docker restart applylens-api-prod
```

### Wrong Version Running
```powershell
# Check running image
docker ps --filter "name=applylens-api-prod" --format "{{.Image}}"

# Check image labels
docker exec applylens-api-prod cat /proc/1/environ | tr '\0' '\n' | grep -E "(GIT_SHA|BUILD_DATE)"

# Force recreate with new image
docker-compose -f docker-compose.prod.yml up -d --force-recreate --pull always api
```

### Image Build Failures
```powershell
# Clear build cache
docker builder prune -f

# Build without cache
docker build --no-cache -t leoklemet/applylens-api:v0.4.2 -f Dockerfile.prod .

# Check Dockerfile syntax
docker build --check -f Dockerfile.prod .
```

---

## CI/CD Integration (Future)

### GitHub Actions Workflow (Example)
```yaml
name: Build and Deploy
on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set version
        id: version
        run: echo "version=${GITHUB_REF#refs/tags/}" >> $GITHUB_OUTPUT

      - name: Build images
        run: |
          GIT_SHA=$(git rev-parse --short HEAD)
          BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

          docker build \
            -t leoklemet/applylens-api:${{ steps.version.outputs.version }} \
            -t leoklemet/applylens-api:latest \
            --build-arg GIT_SHA=$GIT_SHA \
            --build-arg BUILD_DATE=$BUILD_DATE \
            services/api

      - name: Push to registry
        run: |
          docker push leoklemet/applylens-api:${{ steps.version.outputs.version }}
          docker push leoklemet/applylens-api:latest
```

---

## Best Practices

1. **Always tag with semantic versions** (`v0.4.1`, not `latest`)
2. **Test in staging** before deploying to production
3. **Backup docker-compose.prod.yml** before changes
4. **Keep old versions** for at least 2 releases
5. **Document changes** in version history
6. **Use digests** for critical production deploys
7. **Monitor logs** for 5-10 minutes after deployment
8. **Have rollback plan** ready before deploying

---

## Health Check URLs

- **API Health**: http://localhost:8003/healthz
- **API Docs**: http://localhost:8003/docs
- **Web Frontend**: http://localhost:5175/
- **Prometheus**: http://localhost:9090/
- **Grafana**: http://localhost:3000/

---

## Support

For issues or questions:
1. Check logs: `docker logs applylens-api-prod --tail 100`
2. Review this guide's troubleshooting section
3. Check Git history: `git log --oneline -10`
4. Contact: [Your support channel]

---

## Production Deployment to applylens.app

### Prerequisites Checklist

Before deploying to production, ensure you have:

- [ ] **Production Server** with SSH access
- [ ] **Docker & Docker Compose** installed on the server
- [ ] **Domain**: applylens.app configured in Cloudflare
- [ ] **Google OAuth Credentials** for production
- [ ] **Server Resources**: Minimum 4GB RAM, 20GB disk space

### Cloudflare Tunnel Setup

#### Install cloudflared

```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
cloudflared --version
```

#### Create and Configure Tunnel

```bash
# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create applylens

# Configure tunnel
sudo mkdir -p /etc/cloudflared
sudo nano /etc/cloudflared/config.yml
```

Tunnel configuration:
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

#### Route DNS and Start Service

```bash
# Route DNS
cloudflared tunnel route dns applylens applylens.app
cloudflared tunnel route dns applylens www.applylens.app

# Install as service
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

### Production Environment Configuration

Create `infra/.env.prod`:

```bash
# Domain
DOMAIN=applylens.app
API_URL=https://applylens.app

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://applylens.app/auth/google/callback

# Secrets (generate with: openssl rand -hex 32)
SECRET_KEY=<generate>
SESSION_SECRET=<generate>
OAUTH_STATE_SECRET=<generate>

# Database
POSTGRES_USER=applylens_user
POSTGRES_PASSWORD=<generate-secure-password>
POSTGRES_DB=applylens_prod
DATABASE_URL=postgresql://applylens_user:<password>@db:5432/applylens_prod

# Elasticsearch
ELASTIC_PASSWORD=<generate>

# Monitoring
GRAFANA_ADMIN_PASSWORD=<generate>
PROMETHEUS_PASSWORD=<generate>
```

### Deploy to Production

```bash
# Make scripts executable
chmod +x deploy-to-server.sh health-check.sh rollback.sh

# Run deployment
./deploy-to-server.sh
```

The deployment script will:
1. Validate all required files
2. Check Docker installation
3. Build production images
4. Stop old containers
5. Start production stack
6. Run database migrations
7. Perform health checks

### Verify Deployment

```bash
# Run automated health checks
./health-check.sh

# Manual verification
curl -I https://applylens.app/
curl -I https://applylens.app/docs/
curl -I https://applylens.app/web/
```

### Post-Deployment Tasks

#### Set Up Automated Backups

Create `~/backup-applylens.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/home/$USER/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker compose -f ~/applylens/docker-compose.prod.yml exec -T db \
  pg_dump -U applylens_user applylens_prod | gzip > \
  $BACKUP_DIR/db_backup_$DATE.sql.gz

find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete
```

Add to crontab (daily at 2 AM):
```bash
chmod +x ~/backup-applylens.sh
crontab -e
# Add: 0 2 * * * /home/$USER/backup-applylens.sh >> /var/log/applylens-backup.log 2>&1
```

#### Configure Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### Production Troubleshooting

#### Services won't start
```bash
docker compose -f docker-compose.prod.yml logs
docker compose -f docker-compose.prod.yml logs api
```

#### Can't access via domain
```bash
# Check Cloudflare Tunnel
sudo systemctl status cloudflared
cloudflared tunnel info applylens

# Check DNS propagation
dig applylens.app
```

#### OAuth not working
1. Verify Google OAuth redirect URI: `https://applylens.app/auth/google/callback`
2. Check `.env.prod` has correct `GOOGLE_REDIRECT_URI`
3. Restart API: `docker compose -f docker-compose.prod.yml restart api`

### Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | https://applylens.app/web/ | Google OAuth |
| API | https://applylens.app/ | N/A |
| API Docs | https://applylens.app/docs/ | N/A |
| Grafana | https://applylens.app/grafana/ | admin / from .env.prod |
| Kibana | https://applylens.app/kibana/ | elastic / from .env.prod |
| Prometheus | https://applylens.app/prometheus/ | admin / from .env.prod |

For complete production deployment guide, see `DEPLOY_TO_PRODUCTION.md`.
