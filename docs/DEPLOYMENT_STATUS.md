# Deployment Status & Configuration

Last Updated: 2025-10-30

## Production Stack Overview

ApplyLens production environment runs on Docker with the following architecture:

```
Internet → Cloudflare Edge
         ↓
    Cloudflare Tunnel (applylens-cloudflared-prod)
         ↓
    Nginx Reverse Proxy (applylens-nginx-prod)
         ↓
    ├─→ Web Frontend (applylens-web-prod)
    └─→ API Backend (applylens-api-prod)
             ↓
        ├─→ PostgreSQL (applylens-db-prod)
        ├─→ Elasticsearch (applylens-es-prod)
        └─→ Redis (applylens-redis-prod)
```

## Hostname → Service Mapping

### Cloudflare Tunnel Configuration
Defined in: `infra/cloudflared/config.yml`

| Public Hostname | Cloudflare Routes To | Nginx Routes To | Final Service |
|----------------|---------------------|-----------------|---------------|
| `https://applylens.app` | `http://applylens.int:80` | `/` → `web:80` | Web Frontend (SPA) |
| `https://applylens.app/api/*` | `http://applylens.int:80` | `/api/*` → `api:8003` | API Backend |
| `https://www.applylens.app` | `http://applylens.int:80` | Same as above | Web Frontend (SPA) |
| `https://api.applylens.app` | `http://applylens-api.int:8003` | Direct | API Backend |

### Service-to-Hostname Mapping (Canonical Reference)

**CRITICAL**: If you ever rename an alias, you MUST change it in all three locations in ONE atomic change:
1. `docker-compose.prod.yml` (network aliases)
2. `infra/nginx/conf.d/applylens.prod.conf` (upstream server names)
3. `infra/cloudflared/config.yml` (service targets)

#### Nginx Upstreams (Production)
```nginx
# File: infra/nginx/conf.d/applylens.prod.conf

upstream applylens_api_upstream {
    server api:8003;           # Docker service 'api' on port 8003
}

upstream applylens_web_upstream {
    server web:80;             # Docker service 'web' on port 80
}
```

#### Cloudflare Tunnel Ingress Rules
```yaml
# File: infra/cloudflared/config.yml

ingress:
  - hostname: applylens.app
    service: http://applylens.int:80        # → Nginx container

  - hostname: www.applylens.app
    service: http://applylens.int:80        # → Nginx container

  - hostname: api.applylens.app
    service: http://applylens-api.int:8003  # → API direct (bypasses nginx)
```

#### Network Aliases (Docker Compose)
```yaml
# File: docker-compose.prod.yml

services:
  nginx:
    container_name: applylens-nginx-prod
    networks:
      applylens-prod:
        aliases:
          - applylens.internal  # Legacy alias (unused)
          - applylens.int       # ACTIVE - used by cloudflared

  api:
    container_name: applylens-api-prod
    networks:
      applylens-prod:
        aliases:
          - applylens-api.internal  # Legacy alias (unused)
          - api                     # ACTIVE - used by nginx upstream

  web:
    container_name: applylens-web-prod
    networks:
      applylens-prod:
        aliases:
          - web  # ACTIVE - used by nginx upstream (implicit, matches service name)
```

#### Traffic Flow Diagram
```
Public Request → Cloudflare Edge
                      ↓
            Cloudflare Tunnel
          (applylens-cloudflared-prod)
                      ↓
         Routes to: applylens.int:80
                      ↓
              Nginx Container
         (applylens-nginx-prod)
         Network alias: applylens.int
                      ↓
         ├─ / → web:80 → Web Container (applylens-web-prod)
         └─ /api/* → api:8003 → API Container (applylens-api-prod)
```

### Required Network Aliases
These aliases MUST exist for the stack to function:

| Alias | Container | Used By | Purpose |
|-------|-----------|---------|---------|
| `applylens.int` | `applylens-nginx-prod` | Cloudflared tunnel | Main ingress point |
| `applylens-api.int` | `applylens-api-prod` | Cloudflared (direct API route) | Direct API access |
| `api` | `applylens-api-prod` | Nginx upstream | Internal API routing |
| `web` | `applylens-web-prod` | Nginx upstream | Internal web routing |
| `db` | `applylens-db-prod` | API container | Database connection |
| `elasticsearch` | `applylens-es-prod` | API container | Search engine |
| `redis` | `applylens-redis-prod` | API container | Cache layer |

### Docker Network Aliases
Defined in: `docker-compose.prod.yml`

| Container Name | Docker Network | Network Aliases | Service Purpose |
|---------------|----------------|-----------------|-----------------|
| `applylens-nginx-prod` | `applylens-prod` | `applylens.internal`, `applylens.int` | Reverse proxy & SSL termination |
| `applylens-api-prod` | `applylens-prod` | `applylens-api.internal`, `api` | FastAPI backend |
| `applylens-web-prod` | `applylens-prod` | `web` | React/Vite frontend |
| `applylens-es-prod` | `applylens-prod` | `elasticsearch` | Search engine |
| `applylens-db-prod` | `applylens-prod` | `db` | PostgreSQL database |
| `applylens-redis-prod` | `applylens-prod` | `redis` | Cache layer |
| `applylens-cloudflared-prod` | `applylens-prod` | - | Cloudflare Tunnel client |

## Recent Issues & Resolutions

### 2025-10-30: Intermittent 502 Bad Gateway - Cloudflare Edge Cache

**Issue**: https://applylens.app returned 502 errors intermittently (~20% of requests)

**Root Cause**:
- Cloudflare edge servers cached 502 error pages from previous outage
- Cloudflared running in token mode (config managed via dashboard, not local file)
- Different edge servers had different cache states

**Symptoms**:
- Docker stack fully healthy (all containers up, nginx serving 200 OK)
- Requests to https://applylens.app/health returned 502 intermittently
- Direct Docker network tests succeeded 100%
- Nginx logs showed NO 502 errors (all requests successful)

**Diagnosis**:
```bash
# Test revealed intermittent failures
Test 1: 200 OK
Test 2: 200 OK
Test 3: 200 OK
Test 4: 200 OK
Test 5: 502 Bad Gateway ← Cached at Cloudflare edge
```

**Resolution**:
1. **Purge Cloudflare cache** - Clear all cached content
2. **Verify tunnel health checks** - Ensure `/health` endpoint is monitored
3. **Add cache headers** - Prevent error page caching
4. **Monitor with alerts** - Set up Cloudflare notifications for tunnel/5xx issues

**Prevention**:
- Added `Cache-Control: no-store` headers for error responses
- Documented that cloudflared uses `--token` mode (dashboard-managed config)
- Created monitoring alert rules for high 5xx rate
- See full details in: `docs/CLOUDFLARE_502_FIX.md`

### 2025-10-30: 502 Bad Gateway - Web Container Down

**Issue**: https://applylens.app returned 502 errors

**Root Cause**:
- The `applylens-web-prod` container had exited 2 days prior
- Nginx was unable to resolve the upstream `web:80` hostname
- This caused nginx to enter a restart loop, failing health checks

**Resolution**:
```bash
# Restart web container
docker compose -f docker-compose.prod.yml up -d web

# Restart nginx to detect web service
docker compose -f docker-compose.prod.yml restart nginx

# Restart cloudflared to refresh tunnel connections
docker compose -f docker-compose.prod.yml restart cloudflared
```

**Prevention**:
- Monitor container health with Prometheus/Grafana alerts
- Set restart policies to `restart: unless-stopped` (already configured)
- Investigate why web container exited originally
- Consider adding depends_on health checks in nginx service

**Verification Commands**:
```bash
# Check all containers are running
docker ps --filter "name=applylens" --format "table {{.Names}}\t{{.Status}}"

# Test nginx health endpoint
curl http://localhost/health

# Test API health endpoint through nginx
curl http://localhost/api/healthz

# Check public site
curl -I https://applylens.app/
```

## Health Check Endpoints

| Endpoint | Service | Expected Response |
|----------|---------|-------------------|
| `/health` | Nginx | `200 ok` (static) |
| `/healthz` | Nginx | `200 ok` (static) |
| `/api/healthz` | API through Nginx | `200 {"status":"ok"}` |

## Configuration Files

### Nginx Production Config
- **File**: `infra/nginx/conf.d/applylens.prod.conf`
- **Mounted as**: `/etc/nginx/conf.d/default.conf` in container
- **Upstreams**:
  - `applylens_api_upstream` → `api:8003`
  - `applylens_web_upstream` → `web:80`

### Cloudflare Tunnel Config
- **File**: `infra/cloudflared/config.yml`
- **Tunnel ID**: `08d5feee-f504-47a2-a1f2-b86564900991`
- **Credentials**: `infra/cloudflared/08d5feee-f504-47a2-a1f2-b86564900991.json`

### Docker Compose
- **Production**: `docker-compose.prod.yml` (root directory)
- **Development**: `infra/docker-compose.yml`

## Monitoring & Observability

### Prometheus
- URL: http://localhost:9090
- Metrics scraped from: API `/metrics` endpoint

### Grafana
- URL: http://localhost:3000
- Dashboards: API health, traffic, security metrics

### Kibana
- URL: http://localhost:5601
- Elasticsearch indices: `gmail_emails`, application logs

## Emergency Rollback

If a deployment causes issues:

1. **Identify last working image**:
   ```bash
   docker images | grep applylens
   ```

2. **Rollback web container**:
   ```bash
   # In docker-compose.prod.yml, change image tag
   image: leoklemet/applylens-web:0.4.63  # Previous working version
   docker compose -f docker-compose.prod.yml up -d web
   ```

3. **Rollback API container**:
   ```bash
   # In docker-compose.prod.yml, change image tag
   image: leoklemet/applylens-api:v0.4.50  # Previous working version
   docker compose -f docker-compose.prod.yml up -d api
   ```

4. **Verify health**:
   ```bash
   curl -I https://applylens.app/
   curl https://applylens.app/api/healthz
   ```

## Contact & Support

For production issues:
- Check Grafana dashboards for metrics
- Review container logs: `docker logs <container_name>`
- Check Cloudflare Tunnel status in dashboard
- Verify DNS propagation if hostname issues persist
