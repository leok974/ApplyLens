# Production Infrastructure Overview

## Infrastructure Diagram

```
Internet
    ↓
Cloudflare Edge (DNS + CDN + DDoS protection)
    ↓
Cloudflare Tunnel (infra-cloudflared)
    ↓
┌─────────────────────────────────────────────────────────────┐
│                    Docker Host Server                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         applylens_applylens-prod network             │  │
│  │                                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │  │
│  │  │   web-prod  │  │   api-prod  │  │     db     │  │  │
│  │  │   (nginx)   │  │  (FastAPI)  │  │ (Postgres) │  │  │
│  │  │   Port 80   │  │  Port 8000  │  │  Port 5432 │  │  │
│  │  └─────────────┘  └─────────────┘  └────────────┘  │  │
│  │                                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │  │
│  │  │     es      │  │    redis    │  │  prometheus│  │  │
│  │  │    (ES)     │  │   (cache)   │  │  (metrics) │  │  │
│  │  │  Port 9200  │  │  Port 6379  │  │  Port 9090 │  │  │
│  │  └─────────────┘  └─────────────┘  └────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              infra_net network                       │  │
│  │                                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │  │
│  │  │cloudflared  │  │    nginx    │  │   grafana  │  │  │
│  │  │  (tunnel)   │  │   (proxy)   │  │ (dashboards)│  │  │
│  │  │             │  │   Port 80   │  │  Port 3001 │  │  │
│  │  └─────────────┘  └─────────────┘  └────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Docker Services

### Production Services (applylens_applylens-prod network)

#### 1. applylens-web-prod

**Container Name**: `applylens-web-prod`
**Image**: `leoklemet/applylens-web:latest`
**Port Mapping**: `5175:80`
**Restart Policy**: `unless-stopped`

**Purpose**:
- Serves React SPA static files
- nginx reverse proxy for `/api/*` endpoints
- SPA routing for `/extension`, `/profile`, etc.

**Key Files**:
- `/usr/share/nginx/html/` - Static assets (JS, CSS, images)
- `/etc/nginx/conf.d/default.conf` - nginx configuration
- `/usr/share/nginx/html/index.html` - SPA entry point

**Environment Variables**:
- Build-time Vite variables embedded in JS bundle
- No runtime environment variables

**Health Check**:
```bash
curl http://localhost:5175/
# Expected: 200 OK with HTML
```

**Logs**:
```bash
docker logs applylens-web-prod --tail 100 -f
```

#### 2. applylens-api-prod

**Container Name**: `applylens-api-prod`
**Image**: `leoklemet/applylens-api:0.6.0-phase6`
**Port Mapping**: `8003:8000`
**Restart Policy**: `unless-stopped`

**Purpose**:
- FastAPI backend server
- Handles auth, search, extension endpoints
- LLM integration for AI features
- Prometheus metrics at `/metrics`

**Environment Variables**:
```bash
APPLYLENS_BASE_URL=https://applylens.app
DATABASE_URL=postgresql://postgres:***@db:5432/applylens
ELASTICSEARCH_URL=http://es:9200
REDIS_URL=redis://redis:6379/0
OAUTH_REDIRECT_URI=https://applylens.app/api/auth/google/callback
GOOGLE_OAUTH_SECRETS_PATH=/secrets/google.json
COMPANION_BANDIT_ENABLED=true
CORS_ALLOW_ORIGINS=https://applylens.app,https://www.applylens.app
```

**Volumes**:
- `./secrets/google.json:/secrets/google.json:ro` - OAuth credentials

**Health Check**:
```bash
curl http://localhost:8003/ready
# Expected: {"status":"ready","db":"ok","es":"ok"}
```

**Logs**:
```bash
docker logs applylens-api-prod --tail 100 -f
```

#### 3. db (PostgreSQL)

**Container Name**: `db`
**Image**: `postgres:17-alpine`
**Port Mapping**: `5432:5432` (internal only)
**Restart Policy**: `unless-stopped`

**Purpose**:
- Relational database for users, sessions, applications
- Stores bandit stats, learning events, tracker data

**Environment Variables**:
```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=***
POSTGRES_DB=applylens
```

**Volumes**:
- `postgres_data:/var/lib/postgresql/data` - Persistent storage

**Health Check**:
```bash
docker exec db pg_isready -U postgres
# Expected: postgres:5432 - accepting connections
```

**Backup**:
```bash
docker exec db pg_dump -U postgres applylens > backup.sql
```

#### 4. es (Elasticsearch)

**Container Name**: `es`
**Image**: `elasticsearch:8.16.1`
**Port Mapping**: `9200:9200` (internal only)
**Restart Policy**: `unless-stopped`

**Purpose**:
- Full-text search for emails
- Stores indexed Gmail messages
- Vector search for semantic queries

**Environment Variables**:
```bash
discovery.type=single-node
xpack.security.enabled=false
ES_JAVA_OPTS=-Xms512m -Xmx512m
```

**Volumes**:
- `es_data:/usr/share/elasticsearch/data` - Index storage

**Health Check**:
```bash
curl http://localhost:9200/_cluster/health
# Expected: {"status":"green"}
```

**Indexes**:
- `gmail_emails` - Email messages
- `applications` - Job applications

#### 5. redis

**Container Name**: `redis`
**Image**: `redis:7-alpine`
**Port Mapping**: `6379:6379` (internal only)
**Restart Policy**: `unless-stopped`

**Purpose**:
- Session storage for authentication
- Rate limiting counters
- Temporary cache for API responses

**Health Check**:
```bash
docker exec redis redis-cli ping
# Expected: PONG
```

**Monitor**:
```bash
docker exec redis redis-cli INFO stats
```

#### 6. prometheus

**Container Name**: `prometheus`
**Image**: `prom/prometheus:latest`
**Port Mapping**: `9090:9090`
**Restart Policy**: `unless-stopped`

**Purpose**:
- Collects metrics from API `/metrics` endpoint
- Stores time-series data
- Provides PromQL query interface

**Volumes**:
- `./prometheus.yml:/etc/prometheus/prometheus.yml:ro` - Config
- `prometheus_data:/prometheus` - Metric storage

**Access**: http://localhost:9090

**Key Queries**:
```promql
# Total API requests
sum(rate(http_requests_total[5m]))

# Autofill policy distribution
sum(rate(autofill_policy_total[1h])) by (policy)

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Infrastructure Services (infra_net network)

#### 7. infra-cloudflared

**Container Name**: `infra-cloudflared`
**Image**: `cloudflare/cloudflared:latest`
**Command**: `tunnel --no-autoupdate run --token <token>`
**Restart Policy**: `unless-stopped`

**Purpose**:
- Cloudflare Tunnel client
- Exposes services to internet without open ports
- Routes traffic to containers

**Networks**:
- `infra_net` - Connect to infrastructure nginx
- `applylens_applylens-prod` - Direct access to ApplyLens containers

**Tunnel ID**: `08d5feee-f504-47a2-a1f2-b86564900991`

**Configuration**:
- Managed via Cloudflare Zero Trust Dashboard
- Routes configured in dashboard (not local config.yml)

**Hostnames**:
- `applylens.app` → `http://applylens-web-prod:80`
- `www.applylens.app` → `http://applylens-web-prod:80`
- `api.applylens.app` → `http://applylens-api-prod:8000`

**Health Check**:
```bash
docker logs infra-cloudflared | grep "registered tunnel connection"
# Expected: Connection registered
```

#### 8. applylens-nginx

**Container Name**: `applylens-nginx`
**Image**: `nginx:1.27-alpine`
**Port Mapping**: `8888:80`
**Restart Policy**: `unless-stopped`

**Purpose**:
- **NOT in ApplyLens request path** (simplified architecture)
- Serves other services: SiteAgent, LedgerMind, portfolio
- Legacy reverse proxy

**Config**: `infra/nginx/dev.conf`

**Note**: ApplyLens traffic goes directly from tunnel to containers, bypassing this nginx.

#### 9. grafana

**Container Name**: `grafana`
**Image**: `grafana/grafana:latest`
**Port Mapping**: `3001:3000`
**Restart Policy**: `unless-stopped`

**Purpose**:
- Visualization dashboards for Prometheus metrics
- Pre-built dashboards for bandit, API performance

**Access**: http://localhost:3001

**Default Credentials**:
- Username: `admin`
- Password: `admin` (change on first login)

**Dashboards**:
- ApplyLens - Companion Bandit (Phase 6)
- ApplyLens - API Performance
- ApplyLens - Email Search

## Docker Networks

### applylens_applylens-prod

**Type**: Bridge network
**Subnet**: Auto-assigned (typically `172.25.0.0/16`)

**Connected Services**:
- applylens-web-prod
- applylens-api-prod
- db
- es
- redis
- prometheus
- cloudflared (external network)

**Purpose**: Isolated network for production services

**DNS**: Containers can resolve each other by name
- `applylens-web-prod` → `172.25.0.x`
- `applylens-api-prod` → `172.25.0.y`
- `db` → `172.25.0.z`

### infra_net (also infra_default)

**Type**: Bridge network
**Subnet**: Auto-assigned (typically `172.23.0.0/16`)

**Connected Services**:
- cloudflared
- applylens-nginx
- grafana
- Other infrastructure services

**Purpose**: Infrastructure and monitoring services

## Special nginx Behaviors

### Web Container nginx (`applylens-web-prod`)

Located at: `/etc/nginx/conf.d/default.conf`

#### SPA Routing

Ensures React Router works correctly:

```nginx
# Extension pages
location = /extension {
    try_files /index.html =404;
}

location /extension/ {
    try_files $uri $uri/ /index.html;
}

# Main app
location / {
    try_files $uri $uri/ /index.html;
}
```

**Why**: Single-page apps need all routes to serve `index.html` for client-side routing.

#### API Proxy

Proxies `/api/*` to backend:

```nginx
location ^~ /api/ {
    proxy_pass http://applylens-api-prod:8000/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 5s;
    proxy_send_timeout 180s;
    proxy_read_timeout 180s;
}
```

**Note**: The `^~` prefix means "priority prefix match" - overrides regex locations.

**Strip Path**: `proxy_pass http://...8000/;` (trailing slash) strips `/api` from path
- Request: `/api/auth/me`
- Proxied to: `http://applylens-api-prod:8000/auth/me`

#### Chat Streaming

Special handling for SSE endpoints:

```nginx
location /api/chat/stream {
    limit_req zone=api_rl burst=10 nodelay;

    proxy_pass http://applylens-api-prod:8000/chat/stream;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # SSE-specific settings
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    chunked_transfer_encoding on;
}
```

**Why**: Server-Sent Events need unbuffered streaming.

#### Asset Caching

Aggressive caching for static assets:

```nginx
location ~* ^/assets/.*\.(js|css|woff|woff2|ttf|eot|otf)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

location ~* \.(png|jpg|jpeg|gif|ico|svg|webp)$ {
    expires 30d;
    add_header Cache-Control "public";
}
```

**Why**: Vite generates fingerprinted filenames (e.g., `index-.C7y0IheO.js`), safe to cache forever.

#### Rate Limiting

Prevents abuse of expensive endpoints:

```nginx
# Define rate limit zones in http block
limit_req_zone $binary_remote_addr zone=api_rl:10m rate=60r/m;

# Apply to chat endpoints
location /api/chat {
    limit_req zone=api_rl burst=30 nodelay;
    # ... proxy config
}
```

**Limits**:
- `/api/chat`: 60 requests/minute per IP
- `/api/chat/stream`: 60 requests/minute per IP, burst 10

#### Security Headers

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

#### Health Endpoint

```nginx
location /health {
    access_log off;
    return 200 "healthy\n";
    add_header Content-Type text/plain;
}
```

**Usage**: Uptime monitors, load balancer health checks

### Infrastructure nginx (`applylens-nginx`)

Located at: `infra/nginx/dev.conf`

**NOT in ApplyLens request path** - serves other projects:

```nginx
server {
    listen 80;
    server_name siteagent.local;

    location / {
        proxy_pass http://siteagent-web:3000;
        # ...
    }
}

server {
    listen 80;
    server_name ledgermind.local;

    location / {
        proxy_pass http://ledgermind-web:5173;
        # ...
    }
}
```

## Volume Management

### List All Volumes

```bash
docker volume ls | grep applylens
```

**Expected**:
- `applylens_postgres_data`
- `applylens_es_data`
- `applylens_prometheus_data`

### Backup Postgres

```bash
docker exec db pg_dump -U postgres applylens | gzip > backup-$(date +%Y%m%d).sql.gz
```

### Restore Postgres

```bash
gunzip -c backup-20251117.sql.gz | docker exec -i db psql -U postgres applylens
```

### Backup Elasticsearch

```bash
# Create snapshot repository (one-time setup)
curl -X PUT "http://localhost:9200/_snapshot/backups" \
  -H 'Content-Type: application/json' \
  -d '{"type":"fs","settings":{"location":"/usr/share/elasticsearch/backups"}}'

# Create snapshot
curl -X PUT "http://localhost:9200/_snapshot/backups/snapshot_$(date +%Y%m%d)"
```

### Clean Old Volumes

```bash
# Remove unused volumes (CAREFUL!)
docker volume prune

# Remove specific volume (will delete data!)
docker volume rm applylens_postgres_data
```

## Deployment Procedures

### Standard Deployment

```bash
cd D:\ApplyLens\infra

# Pull latest images
docker compose -f docker-compose.prod.yml pull

# Restart services
docker compose -f docker-compose.prod.yml up -d

# Check health
docker ps --filter "name=applylens"
docker logs applylens-api-prod --tail 50
```

### Zero-Downtime Deployment

```bash
# 1. Build new image with different tag
docker build -t leoklemet/applylens-web:0.5.2 .

# 2. Update docker-compose.prod.yml
#    image: leoklemet/applylens-web:0.5.2

# 3. Pull new image
docker compose -f docker-compose.prod.yml pull web

# 4. Restart only web service
docker compose -f docker-compose.prod.yml up -d web

# 5. Check logs for errors
docker logs applylens-web-prod --tail 50

# 6. If successful, tag as latest
docker tag leoklemet/applylens-web:0.5.2 leoklemet/applylens-web:latest
docker push leoklemet/applylens-web:latest
```

### Rollback

```bash
# 1. Update docker-compose.prod.yml to previous version
#    image: leoklemet/applylens-web:0.5.1

# 2. Restart service
docker compose -f docker-compose.prod.yml up -d web

# 3. Verify
curl https://applylens.app/
```

### Database Migration

```bash
# 1. Backup database
docker exec db pg_dump -U postgres applylens > pre-migration-backup.sql

# 2. Run migration
docker exec applylens-api-prod alembic upgrade head

# 3. Verify
docker exec applylens-api-prod alembic current

# 4. If failed, rollback
docker exec applylens-api-prod alembic downgrade -1
```

## Monitoring & Troubleshooting

### Check Service Health

```bash
# All containers status
docker ps --filter "name=applylens" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Web health
curl -s http://localhost:5175/health

# API health
curl -s http://localhost:8003/ready | jq

# Database
docker exec db pg_isready -U postgres

# Elasticsearch
curl -s http://localhost:9200/_cluster/health | jq

# Redis
docker exec redis redis-cli ping
```

### View Logs

```bash
# Recent logs
docker logs applylens-api-prod --tail 100

# Follow logs
docker logs applylens-api-prod -f

# With timestamps
docker logs applylens-api-prod -t

# Last hour
docker logs applylens-api-prod --since 1h

# Search logs
docker logs applylens-api-prod 2>&1 | grep ERROR
```

### Resource Usage

```bash
# Container stats
docker stats --no-stream --filter "name=applylens"

# Disk usage
docker system df

# Volume sizes
docker volume ls -q | xargs docker volume inspect --format '{{ .Name }}: {{ .Mountpoint }}' | xargs -I {} sh -c 'du -sh {}'
```

### Network Debugging

```bash
# Inspect network
docker network inspect applylens_applylens-prod

# Test connectivity from web to api
docker exec applylens-web-prod wget -qO- http://applylens-api-prod:8000/ready

# DNS resolution
docker exec applylens-web-prod nslookup applylens-api-prod

# Check Cloudflare tunnel
docker logs infra-cloudflared | tail -50
```

### Common Issues

#### Issue: 502 Bad Gateway

**Debug**:
```bash
# 1. Check if backend is running
docker ps | grep applylens-api-prod

# 2. Test backend directly
curl http://localhost:8003/ready

# 3. Check nginx logs
docker logs applylens-web-prod | grep error

# 4. Test from inside web container
docker exec applylens-web-prod wget -qO- http://applylens-api-prod:8000/ready
```

#### Issue: Database connection failed

**Debug**:
```bash
# 1. Check database is running
docker exec db pg_isready

# 2. Check environment variable
docker exec applylens-api-prod printenv DATABASE_URL

# 3. Test connection
docker exec applylens-api-prod python -c "
from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    print('Connected!')
"
```

#### Issue: Elasticsearch unavailable

**Debug**:
```bash
# 1. Check ES health
curl http://localhost:9200/_cluster/health

# 2. Check ES logs
docker logs es --tail 100

# 3. Restart ES
docker restart es

# 4. Wait for green status
watch -n 2 'curl -s http://localhost:9200/_cluster/health | jq .status'
```

#### Issue: Cloudflare tunnel disconnected

**Debug**:
```bash
# 1. Check tunnel logs
docker logs infra-cloudflared --tail 100

# 2. Look for connection errors
docker logs infra-cloudflared 2>&1 | grep -i error

# 3. Restart tunnel
docker restart infra-cloudflared

# 4. Verify reconnection
docker logs infra-cloudflared --tail 20 | grep "registered tunnel connection"
```

## Security Best Practices

### Secrets Management

- ✅ OAuth secrets in `/secrets/google.json` (not in image)
- ✅ Database password in environment variables (not in code)
- ✅ Session secret in `OAUTH_STATE_SECRET`
- ❌ Don't commit secrets to git
- ❌ Don't log sensitive data

### Network Security

- ✅ Database not exposed to internet (no port mapping)
- ✅ Elasticsearch not exposed to internet
- ✅ Redis not exposed to internet
- ✅ Cloudflare tunnel for zero-trust access
- ❌ Don't expose internal ports (5432, 9200, 6379)

### Update Policy

```bash
# Update base images monthly
docker pull postgres:17-alpine
docker pull elasticsearch:8.16.1
docker pull redis:7-alpine
docker pull nginx:1.27-alpine

# Rebuild with updated bases
docker compose -f docker-compose.prod.yml build --pull
```

### Access Control

- Grafana: Change default password
- Prometheus: No auth (internal only)
- Database: Strong password, localhost binding
- API: OAuth required for all endpoints
