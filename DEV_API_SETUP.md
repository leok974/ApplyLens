# ApplyLens Development API Setup

This directory contains scripts and configuration for running the ApplyLens API in development mode using Docker.

## Quick Start

### 1. Start the Dev API

```powershell
.\scripts\start-dev-api.ps1
```

This will:
- Build the API Docker image (if needed)
- Start `applylens-api-dev` container on port 8003
- Enable hot-reload via `uvicorn --reload`
- Use SQLite database (no Postgres needed)
- Configure CORS for all common Vite dev ports

### 2. Start the Web Dev Server

```powershell
cd apps\web
npm run dev
```

The web app will automatically connect to `http://localhost:8003/api` based on `.env.development`.

### 3. Develop!

- **API Swagger**: http://localhost:8003/docs
- **Web UI**: http://localhost:5175 (or whatever port Vite assigns)
- **Health Check**: http://localhost:8003/healthz

Any changes to `services/api/**/*.py` files will trigger automatic reload in the container.

## Management Commands

### View Logs
```powershell
docker logs -f applylens-api-dev
```

### Stop Dev API
```powershell
.\scripts\stop-dev-api.ps1
```
or
```powershell
docker stop applylens-api-dev
```

### Restart Dev API
```powershell
docker restart applylens-api-dev
```

### Access Container Shell
```powershell
docker exec -it applylens-api-dev bash
```

### Remove Container
```powershell
docker rm applylens-api-dev
```

### Rebuild (after dependency changes)
```powershell
docker compose -f docker-compose.dev.api.yml up applylens-api-dev -d --build
```

## Configuration Files

- **`docker-compose.dev.api.yml`**: Docker Compose configuration for dev API
- **`services/api/.env.dev`**: Environment variables for dev mode
- **`apps/web/.env.development`**: Web app dev config (points to localhost:8003)
- **`scripts/start-dev-api.ps1`**: Startup script
- **`scripts/stop-dev-api.ps1`**: Shutdown script

## Dev vs Prod

| Aspect | Development | Production |
|--------|-------------|------------|
| Container | `applylens-api-dev` | `applylens-api-prod` |
| Port | 8003 | 8003 (internal: 8000) |
| Database | SQLite (`dev-data/`) | PostgreSQL (container) |
| Hot-reload | ✅ Yes (`uvicorn --reload`) | ❌ No (gunicorn) |
| Elasticsearch | ❌ Disabled | ✅ Enabled |
| Auth | 🔓 Dev/bypass mode | 🔒 Real OAuth |
| Network | `applylens-dev` | `applylens_applylens-prod` |

## Data Persistence

Dev database is stored in `services/api/dev-data/dev_extension.db` and persists across container restarts.

To reset the database:
```powershell
docker stop applylens-api-dev
Remove-Item services\api\dev-data\*.db
.\scripts\start-dev-api.ps1
```

## Troubleshooting

### Port 8003 already in use

If production API is running:
```powershell
docker stop applylens-api-prod
```

Or change the dev API port in `docker-compose.dev.api.yml`.

### CORS errors in web app

Check that `CORS_ALLOW_ORIGINS` in `docker-compose.dev.api.yml` includes your Vite dev server port.

### Hot-reload not working

Ensure the volume mount is working:
```powershell
docker exec applylens-api-dev ls -la /app/app
```

### API not responding

Check logs:
```powershell
docker logs applylens-api-dev
```

Check health:
```powershell
curl http://localhost:8003/healthz
```

## Architecture

```
┌─────────────────┐
│   Web Browser   │
│  localhost:5175 │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Vite Dev Server│      │ applylens-api-dev│
│  (apps/web)     │─────▶│  localhost:8003  │
│  Port 5175      │ CORS │  uvicorn --reload│
└─────────────────┘      └────────┬─────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  SQLite DB      │
                         │  dev-data/*.db  │
                         └─────────────────┘
```

## Testing with Dev API

The Playwright test suite uses the dev API on port 8888 for isolated testing. The dev API container (8003) is for manual development and web UI testing.

If you need tests to use the containerized dev API, update `playwright.config.ts` to use port 8003.
