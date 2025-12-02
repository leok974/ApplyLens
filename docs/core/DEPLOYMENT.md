# ApplyLens Deployment Guide

**Last Updated**: 2025-12-02
**Audience**: Developers, DevOps, AI Agents

---

## Overview

ApplyLens production runs on **local Docker host** (not remote server). All commands execute directly on this machine at `D:\ApplyLens` (Windows) or `/home/leo/ApplyLens` (Linux).

**Key Principle**: Deploy via `scripts/deploy-prod.ps1` with `docker-compose.prod.yml`. Do NOT manually restart containers or invent new commands.

---

## 1. Local Development

### Backend (FastAPI)

```powershell
# Terminal 1 - Start API
cd D:\ApplyLens\services\api
uvicorn app.main:app --reload --port 8003

# API runs at: http://localhost:8003
# Health: http://localhost:8003/healthz
# Docs: http://localhost:8003/docs
```

**Environment**: Uses `.env.dev` or environment variables. See `services/api/.env.example`.

### Frontend (React/Vite)

```powershell
# Terminal 2 - Start Web
cd D:\ApplyLens\apps\web
pnpm dev

# Web runs at: http://localhost:5175
```

**Environment**: Uses `apps/web/.env.development` or `.env.local`.

### Required Environment Variables (Local Dev)

| Variable | Location | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | `services/api/.env.dev` | PostgreSQL connection string |
| `ELASTICSEARCH_URL` | `services/api/.env.dev` | Elasticsearch endpoint |
| `REDIS_URL` | `services/api/.env.dev` | Redis cache endpoint |
| `APPLYLENS_GOOGLE_CLIENT_ID` | `services/api/.env.dev` | Google OAuth client ID |
| `APPLYLENS_GOOGLE_CLIENT_SECRET` | `services/api/.env.dev` | Google OAuth secret |
| `APPLYLENS_SESSION_SECRET` | `services/api/.env.dev` | Session cookie signing key |

---

## 2. Production Stack (Docker Compose)

### Architecture

Production runs via `docker-compose.prod.yml` with these services:

| Service | Container Name | Port | Purpose |
|---------|----------------|------|---------|
| **web** | `applylens-web-prod` | 5175→80 | React/Vite frontend (nginx) |
| **api** | `applylens-api-prod` | 8003 | FastAPI backend |
| **db** | `applylens-db-prod` | 5432 (internal) | PostgreSQL 16 |
| **elasticsearch** | `applylens-es-prod` | 9200 (internal) | Elasticsearch 8.13 |
| **redis** | `applylens-redis-prod` | 6379 (internal) | Redis cache |
| **kibana** | `applylens-kibana-prod` | 5601 | Data visualization |
| **prometheus** | `applylens-prometheus-prod` | 9090 | Metrics (LEGACY) |
| **grafana** | `applylens-grafana-prod` | 3001 | Monitoring (LEGACY) |
| **cloudflared** | `applylens-cloudflared-prod` | - | Cloudflare tunnel |

**Network**: `applylens_applylens-prod` (Docker bridge network)

**Public Routes** (via Cloudflare Tunnel):
- `https://applylens.app` → `applylens-web-prod:80`
- `https://api.applylens.app` → nginx → `applylens-api-prod:8003`

**Note**: Prometheus/Grafana are LEGACY (Datadog is primary observability as of Nov 2025). Retained for historical data during transition.

---

## 3. Production Deploy Workflow

### Method 1: Build & Deploy New Version (Recommended)

```powershell
# From repo root D:\ApplyLens
.\scripts\deploy-prod.ps1 -Version "0.7.12" -Build
```

**What this does**:
1. Calls `scripts/build-prod-images.ps1` to build:
   - `leoklemet/applylens-web:0.7.12`
   - `leoklemet/applylens-api:0.7.12`
2. Tags images with git SHA (auto-detected)
3. Pushes images to Docker Hub
4. Sets environment variables:
   - `APP_VERSION=0.7.12`
   - `APP_BUILD_SHA=<git-sha>`
   - `APP_BUILD_TIME=<timestamp>`
5. Runs `docker-compose -f docker-compose.prod.yml up -d`
6. Tests `/version` endpoint
7. Shows service status

### Method 2: Deploy Existing Images

```powershell
# Deploy already-built images
.\scripts\deploy-prod.ps1 -Version "0.7.12"
```

Skips build step, pulls images from Docker Hub, and deploys.

### Method 3: Manual Deploy (Emergency Only)

```powershell
# Pull latest code (if not already done)
git pull

# Pull latest images
docker compose -f docker-compose.prod.yml pull web api

# Restart services
docker compose -f docker-compose.prod.yml up -d web api
```

**Warning**: Manual deploys skip build metadata. Prefer Method 1 or 2.

---

## 4. Post-Deploy Verification

### Automated Smoke Tests

```powershell
# Run comprehensive smoke tests
.\scripts\smoke-applylens.ps1
```

### Manual Health Checks

```powershell
# Check container status
docker ps --filter "name=applylens-*-prod"

# Test API health
curl http://localhost:8003/api/healthz
# Expected: {"status":"healthy"}

# Test API version
curl http://localhost:8003/api/version
# Expected: {"version":"0.7.12","build_sha":"abc1234",...}

# Test web (via tunnel)
curl https://applylens.app/
# Expected: HTML with <title>ApplyLens</title>

# Check logs
docker logs applylens-api-prod --tail 50
docker logs applylens-web-prod --tail 50
```

### Common Issues

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| 502 Bad Gateway | Nginx/web container stopped | `docker start applylens-web-prod applylens-nginx-prod` |
| 500 on `/api/opportunities` | Missing router or DB error | Check `docker logs applylens-api-prod` for Python traceback |
| 401 Unauthorized | Session secret mismatch | Restart API with correct `APPLYLENS_SESSION_SECRET` |
| Google OAuth fails (400) | Missing OAuth credentials | Set `APPLYLENS_GOOGLE_CLIENT_ID` and `APPLYLENS_GOOGLE_CLIENT_SECRET` |

---

## 5. Environment Variables & Secrets

### Critical Production Variables (Docker Compose)

These are set in `docker-compose.prod.yml` or `infra/.env.prod`:

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `APP_VERSION` | Version reported by `/api/version` | `0.7.12` |
| `APP_BUILD_SHA` | Git commit SHA | `abc1234` |
| `APP_BUILD_TIME` | Build timestamp (ISO 8601) | `2025-12-02T19:00:00Z` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://postgres:pass@db:5432/applylens` |
| `ELASTICSEARCH_URL` | Elasticsearch endpoint | `http://es:9200` |
| `REDIS_URL` | Redis endpoint | `redis://redis:6379/0` |
| `APPLYLENS_SESSION_SECRET` | Session cookie signing key | (secret value) |
| `APPLYLENS_GOOGLE_CLIENT_ID` | Google OAuth client ID | `813287438869-...apps.googleusercontent.com` |
| `APPLYLENS_GOOGLE_CLIENT_SECRET` | Google OAuth secret | `GOCSPX-...` |
| `APPLYLENS_OAUTH_REDIRECT_URI` | OAuth callback URL | `https://applylens.app/auth/google/callback` |
| `APPLYLENS_COOKIE_DOMAIN` | Cookie domain | `applylens.app` |
| `APPLYLENS_COOKIE_SECURE` | HTTPS-only cookies | `1` |

**Note**: `APPLYLENS_` prefix required for AgentSettings in `services/api/app/config.py`.

### Test/CI Variables

| Variable | Purpose | Where Set |
|----------|---------|-----------|
| `E2E_BASE_URL` | Playwright test target | `.github/workflows/*.yml`, `apps/web/.env.test` |
| `E2E_SHARED_SECRET` | Protected test route auth | GitHub Secrets, `docker-compose.prod.yml` |
| `E2E_PROD` | Enable prod E2E routes | `docker-compose.prod.yml` (`E2E_PROD=1`) |
| `DD_API_KEY` | Datadog metrics/traces | GitHub Secrets, host env |
| `DD_APP_KEY` | Datadog dashboards | GitHub Secrets, host env |

### Datadog (Observability)

| Variable | Purpose | Where Set |
|----------|---------|-----------|
| `DD_API_KEY` | Datadog API key | Host environment or GitHub Secrets |
| `DD_APP_KEY` | Datadog application key | Host environment or GitHub Secrets |
| `DD_SITE` | Datadog site (e.g., `datadoghq.com`) | Host environment |
| `DD_ENV` | Environment tag (e.g., `production`) | Docker labels or env vars |
| `DD_SERVICE` | Service name (e.g., `applylens-api`) | Docker labels or env vars |

See: [`hackathon/DATADOG_SETUP.md`](../../hackathon/DATADOG_SETUP.md) for full setup.

---

## 6. Deployment Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/deploy-prod.ps1` | **Main deploy entrypoint** | `.\scripts\deploy-prod.ps1 -Version "0.7.12" -Build` |
| `scripts/build-prod-images.ps1` | Build & tag Docker images | Called by `deploy-prod.ps1` or standalone |
| `scripts/smoke-applylens.ps1` | Post-deploy smoke tests | `.\scripts\smoke-applylens.ps1` |
| `infra/deploy-api-prod.ps1` | Deploy API container only | `.\infra\deploy-api-prod.ps1 -ImageTag "0.7.12"` |

---

## 7. Rollback Procedure

```powershell
# Rollback to previous version
.\scripts\deploy-prod.ps1 -Version "0.7.11"

# Or manually:
docker compose -f docker-compose.prod.yml down web api
# Edit docker-compose.prod.yml: change image tags to 0.7.11
docker compose -f docker-compose.prod.yml up -d web api
```

---

## 8. Troubleshooting

### Container Won't Start

```powershell
# Check logs for errors
docker logs applylens-api-prod
docker logs applylens-web-prod

# Check if ports are in use
netstat -an | findstr ":8003"
netstat -an | findstr ":5175"

# Restart with fresh logs
docker compose -f docker-compose.prod.yml restart api
```

### Database Issues

```powershell
# Check DB health
docker exec applylens-db-prod pg_isready -U postgres -d applylens

# Run migrations
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# Check DB logs
docker logs applylens-db-prod --tail 50
```

### Elasticsearch Issues

```powershell
# Check ES health
curl http://localhost:9200/_cluster/health

# Recreate index (DANGER: data loss)
docker compose -f docker-compose.prod.yml exec api python -m app.es
```

---

## 9. Emergency Contacts

- **On-Call Handbook**: [`docs/core/ONCALL_HANDBOOK.md`](ONCALL_HANDBOOK.md)
- **Incidents**: [`docs/core/incidents/`](incidents/)
- **Runbooks**: [`docs/core/runbooks/`](runbooks/)

---

## 10. Additional Resources

- **Architecture**: [`docs/core/ARCHITECTURE.md`](ARCHITECTURE.md)
- **Infrastructure**: [`docs/core/INFRASTRUCTURE.md`](INFRASTRUCTURE.md)
- **Cloudflare Setup**: [`docs/core/CLOUDFLARE.md`](CLOUDFLARE.md)
- **Datadog Setup**: [`hackathon/DATADOG_SETUP.md`](../../hackathon/DATADOG_SETUP.md)
- **Monitoring**: [`docs/core/MONITORING.md`](MONITORING.md)

---

**CRITICAL REMINDERS FOR AI AGENTS**:
1. ✅ **ALWAYS use `scripts/deploy-prod.ps1`** for deployments
2. ✅ **NEVER manually restart containers** without documenting why
3. ✅ **ALWAYS read this doc** before inventing new deployment commands
4. ✅ **PREFER existing scripts** over ad-hoc Docker commands
5. ✅ **DO NOT touch Cloudflare tunnel config** unless explicitly requested
6. ✅ **DO NOT change nginx routing** without reviewing [`infra/nginx/conf.d/`](../../infra/nginx/conf.d/)
