# ApplyLens Deployment Cheatsheet

**Last Updated**: 2025-12-02

> **One-liner**: ApplyLens production runs via `docker-compose.prod.yml` with images `leoklemet/applylens-web` and `leoklemet/applylens-api`, deployed by `scripts/deploy-prod.ps1`.

---

## Dev vs Prod Quick Commands

### Local Development

```powershell
# Backend (FastAPI)
cd D:\ApplyLens\services\api
uvicorn app.main:app --reload --port 8003

# Frontend (React/Vite)
cd D:\ApplyLens\apps\web
pnpm dev

# Access:
# API: http://localhost:8003
# Web: http://localhost:5175
```

### Production Deploy

```powershell
# Build & deploy new version
cd D:\ApplyLens
.\scripts\deploy-prod.ps1 -Version "0.7.12" -Build

# Deploy existing images
.\scripts\deploy-prod.ps1 -Version "0.7.12"

# Smoke test
.\scripts\smoke-applylens.ps1
```

---

## Quick Diagnostics

```powershell
# Check container status
docker ps --filter "name=applylens-*-prod"

# Test API
curl http://localhost:8003/api/healthz
curl http://localhost:8003/api/version

# Check logs
docker logs applylens-api-prod --tail 50
docker logs applylens-web-prod --tail 50
```

---

## Emergency Fixes

| Problem | Fix |
|---------|-----|
| 502 Bad Gateway | `docker start applylens-web-prod applylens-nginx-prod` |
| 500 Server Error | `docker logs applylens-api-prod` → check traceback |
| 401 Unauthorized | Restart API with `APPLYLENS_SESSION_SECRET` |
| Google OAuth fails | Set `APPLYLENS_GOOGLE_CLIENT_ID` + `APPLYLENS_GOOGLE_CLIENT_SECRET` |

---

## Where to Look When Confused

1. **[`docs/core/DEPLOYMENT.md`](DEPLOYMENT.md)** – Full deployment guide
2. **`scripts/deploy-prod.ps1`** – Actual deploy script (source of truth for commands)
3. **`docker-compose.prod.yml`** – Canonical prod stack definition
4. **[`docs/core/ARCHITECTURE.md`](ARCHITECTURE.md)** – System architecture
5. **[`docs/agents/AGENT_READING_GUIDE.md`](../agents/AGENT_READING_GUIDE.md)** – How to navigate docs

---

## Key Production Services

| Service | Container | Port | URL |
|---------|-----------|------|-----|
| Frontend | `applylens-web-prod` | 80 | https://applylens.app |
| API | `applylens-api-prod` | 8003 | https://api.applylens.app (via nginx) |
| Database | `applylens-db-prod` | 5432 (internal) | - |
| Elasticsearch | `applylens-es-prod` | 9200 (internal) | - |
| Redis | `applylens-redis-prod` | 6379 (internal) | - |

---

## Environment Variables (Must-Know)

| Variable | Purpose |
|----------|---------|
| `APP_VERSION` | Version shown in `/api/version` |
| `DATABASE_URL` | PostgreSQL connection string |
| `APPLYLENS_SESSION_SECRET` | Session cookie signing (CRITICAL) |
| `APPLYLENS_GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `APPLYLENS_GOOGLE_CLIENT_SECRET` | Google OAuth secret |
| `E2E_SHARED_SECRET` | Test route authentication |

See full list in [`docs/core/DEPLOYMENT.md`](DEPLOYMENT.md#5-environment-variables--secrets).

---

**For AI Agents**: Always read [`docs/core/DEPLOYMENT.md`](DEPLOYMENT.md) and [`docs/agents/AGENT_READING_GUIDE.md`](../agents/AGENT_READING_GUIDE.md) before deploying or inventing new commands.
