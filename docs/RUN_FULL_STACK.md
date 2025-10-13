# 🚀 Run ApplyLens Full Stack

Quick reference for starting and managing the complete ApplyLens application.

---

## Quick Start (One Command)

```powershell
# Start everything
cd d:/ApplyLens/infra && docker compose up -d && cd ../apps/web && npm run dev
```text

---

## Step-by-Step

### 1. Start Backend Services

```powershell
cd d:/ApplyLens/infra
docker compose up -d
```text

**Services started:**

- ✅ API (FastAPI) - Port 8003
- ✅ Database (PostgreSQL) - Port 5433
- ✅ Elasticsearch - Port 9200
- ✅ Ollama (LLM) - Port 11434
- ✅ pgvector - Port 5432

**Verify:**

```powershell
docker compose ps
```text

### 2. Start Frontend

```powershell
cd d:/ApplyLens/apps/web
npm run dev
```text

**Service started:**

- ✅ Web UI (Vite) - Port 5175

**Access:** <http://localhost:5175>

---

## Check Status

### All Services

```powershell
# Backend
cd d:/ApplyLens/infra
docker compose ps

# Frontend
Get-Process -Name node -ErrorAction SilentlyContinue
```text

### Health Checks

```powershell
# API
curl http://localhost:8003/docs

# Database
docker compose exec db pg_isready -U applylens

# Elasticsearch
curl http://localhost:9200/_cluster/health

# Frontend
curl http://localhost:5175
```text

---

## Stop Services

### Stop Frontend

```powershell
# Press Ctrl+C in terminal where npm run dev is running
# Or kill process:
Get-Process -Name node | Stop-Process -Force
```text

### Stop Backend

```powershell
cd d:/ApplyLens/infra
docker compose down
```text

### Stop All (Clean Shutdown)

```powershell
# Stop frontend first
Get-Process -Name node | Stop-Process -Force

# Then backend
cd d:/ApplyLens/infra
docker compose down
```text

---

## Restart Services

### Restart API Only

```powershell
cd d:/ApplyLens/infra
docker compose restart api
```text

### Restart All Backend

```powershell
cd d:/ApplyLens/infra
docker compose restart
```text

### Restart Frontend

```powershell
# Stop frontend (Ctrl+C or kill process)
# Then restart:
cd d:/ApplyLens/apps/web
npm run dev
```text

---

## View Logs

### Backend Logs

```powershell
cd d:/ApplyLens/infra

# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f db
docker compose logs -f es
```text

### Frontend Logs

Check the terminal where `npm run dev` is running.

---

## Common Issues

### Port Already in Use

**Problem:** `Port 8003 is already allocated`

**Solution:**

```powershell
# Find process using port
Get-NetTCPConnection -LocalPort 8003 | Select-Object OwningProcess
Get-Process -Id <PID> | Stop-Process -Force

# Then restart
docker compose restart api
```text

### Database Connection Failed

**Problem:** `Connection refused: db:5432`

**Solution:**

```powershell
# Check if db is running
docker compose ps db

# If not running
docker compose up -d db

# Wait 10 seconds, then restart API
Start-Sleep -Seconds 10
docker compose restart api
```text

### Frontend Proxy Errors

**Problem:** `http proxy error: /api/...`

**Solution:**

```powershell
# Check API is running
curl http://localhost:8003/docs

# If not, start it
cd d:/ApplyLens/infra
docker compose up -d api

# Check vite.config.ts proxy settings
```text

### Out of Memory (Elasticsearch)

**Problem:** ES container keeps restarting

**Solution:**

```powershell
# Check logs
docker compose logs es

# If memory issue, increase Docker memory:
# Docker Desktop → Settings → Resources → Memory: 8GB+

# Or disable ES for minimal stack:
docker compose -f docker-compose.minimal.yml up -d
```text

---

## Access Points

### Web Applications

- 🌐 **Web UI:** <http://localhost:5175>
- 📚 **API Docs:** <http://localhost:8003/docs>
- 🔍 **OpenAPI:** <http://localhost:8003/openapi.json>

### Monitoring

- 📊 **Metrics:** <http://localhost:8003/metrics>
- 🔎 **Elasticsearch:** <http://localhost:9200>
- 🧠 **Ollama:** <http://localhost:11434>

### Database

- 🐘 **PostgreSQL:** localhost:5433
  - User: `applylens`
  - Database: `applylens`
  - Password: (check `.env` file)

---

## Phase 4 Features

### Test "Always Do This"

1. **Create test policy:**

```powershell
cd d:/ApplyLens
pwsh ./scripts/create-test-policy.ps1
```text

2. **Open UI:** <http://localhost:5175>

3. **Click "Actions" button** (top-right)

4. **Try "Always do this"** on an action

### View Metrics

```powershell
curl http://localhost:8003/metrics | Select-String -Pattern "actions_"
```text

### Run Full Test Suite

```powershell
cd d:/ApplyLens
pwsh ./scripts/test-always-feature.ps1
```text

---

## Development Workflow

### 1. Morning Startup

```powershell
# Start backend
cd d:/ApplyLens/infra
docker compose up -d

# Start frontend
cd ../apps/web
npm run dev

# Open browser
start http://localhost:5175
```text

### 2. Code Changes

**Backend changes:**

```powershell
# Changes are auto-reloaded (uvicorn --reload)
# If not, restart:
docker compose restart api
```text

**Frontend changes:**

```powershell
# Changes are auto-reloaded (HMR)
# Already running in terminal
```text

### 3. Testing

```powershell
# Backend tests
cd d:/ApplyLens/services/api
pytest

# Frontend tests
cd d:/ApplyLens/apps/web
npm test
```text

### 4. End of Day

```powershell
# Stop frontend (Ctrl+C)

# Stop backend (optional, can leave running)
cd d:/ApplyLens/infra
docker compose down
```text

---

## Production Deployment

### Build Frontend

```powershell
cd d:/ApplyLens/apps/web
npm run build

# Output: dist/ folder
```text

### Run Production Stack

```powershell
cd d:/ApplyLens/infra
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```text

### Health Check

```powershell
# Check all services healthy
docker compose ps

# Test endpoints
curl http://localhost:8003/docs
curl http://localhost:5175
```text

---

## Quick Commands

### One-Liners

```powershell
# Start everything
cd d:/ApplyLens/infra && docker compose up -d && cd ../apps/web && start cmd /k npm run dev

# Stop everything
Get-Process -Name node | Stop-Process -Force; cd d:/ApplyLens/infra && docker compose down

# Restart API
cd d:/ApplyLens/infra && docker compose restart api

# View API logs
cd d:/ApplyLens/infra && docker compose logs -f api

# Check status
cd d:/ApplyLens/infra && docker compose ps

# Run migrations
cd d:/ApplyLens/infra && docker compose exec api alembic upgrade head

# Seed policies
cd d:/ApplyLens/infra && docker compose exec api python -c "from app.seeds.policies import seed_policies; seed_policies()"

# Create test data
cd d:/ApplyLens && pwsh ./scripts/create-test-policy.ps1

# Test Phase 4
cd d:/ApplyLens && pwsh ./scripts/test-always-feature.ps1
```text

---

## Monitoring Dashboard

### Service Status

```powershell
# Show all service URLs
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  Web UI:    http://localhost:5175" -ForegroundColor Green
Write-Host "  API:       http://localhost:8003" -ForegroundColor Green
Write-Host "  API Docs:  http://localhost:8003/docs" -ForegroundColor Green
Write-Host "  Metrics:   http://localhost:8003/metrics" -ForegroundColor Green
Write-Host "  ES:        http://localhost:9200" -ForegroundColor Green
Write-Host "  Ollama:    http://localhost:11434" -ForegroundColor Green
```text

### Phase 4 Status

```powershell
# Show Phase 4 stats
$policies = curl -s http://localhost:8003/api/actions/policies | jq '. | length'
$pending = curl -s http://localhost:8003/api/actions/tray | jq '. | length'
Write-Host "Phase 4:" -ForegroundColor Cyan
Write-Host "  Policies:  $policies" -ForegroundColor Yellow
Write-Host "  Pending:   $pending" -ForegroundColor Yellow
```text

---

## Troubleshooting Checklist

- [ ] Docker Desktop is running
- [ ] Docker services are up: `docker compose ps`
- [ ] API is responding: `curl http://localhost:8003/docs`
- [ ] Database is healthy: `docker compose exec db pg_isready`
- [ ] Frontend is running: `Get-Process -Name node`
- [ ] Frontend accessible: `curl http://localhost:5175`
- [ ] No port conflicts: Check ports 5175, 8003, 5433, 9200
- [ ] Logs show no errors: `docker compose logs`

---

## Summary

**Full Stack Running:**
✅ Backend (Docker) - API + DB + ES + Ollama  
✅ Frontend (npm) - Vite dev server  
✅ Phase 4 Features - Always do this + Metrics  

**Quick Start:**

```powershell
cd d:/ApplyLens/infra && docker compose up -d && cd ../apps/web && npm run dev
```text

**Access:**

- Web UI: <http://localhost:5175>
- API Docs: <http://localhost:8003/docs>

**Test:**

```powershell
cd d:/ApplyLens && pwsh ./scripts/test-always-feature.ps1
```text

🎉 **You're all set!**
