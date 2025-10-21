# Infrastructure Status Check

## Summary

Your ApplyLens infrastructure uses **Docker Compose** for core services (DB, Elasticsearch, API, Web) but **Ollama runs separately** on the host machine for AI features.

## Current Status

### ✅ Running Services (from your check_routes.ps1 output):
- **API Server**: Running on port 8000 (local test mode with SQLite)
- **AI Routes**: Registered and responding
  - `/api/ai/health` ✓
  - `/api/ai/summarize` ✓
  - `/api/rag/query` ✓
  - `/api/security/risk-top3` ✓

### ❌ Not Running:
- **Ollama Service**: Not started (health check shows "unavailable")

## Infrastructure Architecture

### Docker Compose Services (infra/docker-compose.yml):
```
┌─────────────┐
│   nginx     │ :8888 → Reverse proxy
└──────┬──────┘
       │
   ────┴────────────────────
   │         │         │
┌──▼──┐  ┌──▼──┐  ┌──▼───┐
│ web │  │ api │  │grafana│
│:5175│  │:8003│  │ :3000 │
└─────┘  └──┬──┘  └───────┘
            │
   ─────────┴─────────
   │                 │
┌──▼──┐         ┌───▼──┐
│ db  │         │  es  │
│:5433│         │:9200 │
└─────┘         └──────┘
```

### Host Services (run separately):
```
┌──────────┐
│ Ollama   │ :11434 → AI inference
└──────────┘
```

## How to Start Full Infrastructure

### Option 1: Docker Compose (Production-like)

```powershell
# 1. Start Docker services
cd d:\ApplyLens\infra
docker-compose up -d

# 2. Start Ollama separately
ollama serve

# 3. Verify all services
docker-compose ps
curl http://localhost:11434/api/tags  # Ollama
curl http://localhost:8003/health      # API
```

### Option 2: Local Development (Current Setup)

```powershell
# 1. Start Ollama
ollama serve
# Keep this terminal open

# 2. In a NEW terminal, start API server
cd d:\ApplyLens\services\api
.\start_server.ps1
# Keep this terminal open

# 3. In a THIRD terminal, verify
cd d:\ApplyLens\services\api
.\check_routes.ps1
```

## Quick Fix for Current Issue

### The Problem:
- ✅ API server is running with AI routes registered
- ❌ Ollama is not running, so AI features return "unavailable"
- ❌ httpx library can't connect to Ollama (even when it's running)

### The Solution:

**Step 1: Start Ollama**
```powershell
ollama serve
```
Leave this terminal open.

**Step 2: Test Ollama**
```powershell
# In a new terminal
curl http://localhost:11434/api/tags
```

Expected output:
```json
{
  "models": [
    {"name": "gpt-oss:20b", "size": 12830000000},
    {"name": "llama3:latest", "size": 4340000000},
    {"name": "nomic-embed-text:latest", "size": 260000000}
  ]
}
```

**Step 3: Restart API Server** (in your existing server window)
- Press `Ctrl+C` to stop
- Run `.\start_server.ps1` again

**Step 4: Verify AI Health**
```powershell
curl http://127.0.0.1:8000/api/ai/health
```

Expected:
```json
{
  "ollama": "available",
  "features": {
    "summarize": true
  }
}
```

## Known Issue: httpx Connection Problem

The Python `httpx` library (used by the API) has trouble connecting to Ollama on Windows even when it's running. I've added a fix to replace `localhost` with `127.0.0.1` in `app/providers/ollama.py`.

If the issue persists, try:

```powershell
# Check if httpx can connect
python -c "import requests; print(requests.get('http://127.0.0.1:11434/api/tags').json())"
```

If `requests` works but `httpx` doesn't, we may need to use `requests` instead of `httpx` for Ollama calls.

## Environment Configuration

### Current Setup (Local Dev):
- **Database**: SQLite (test.db)
- **Elasticsearch**: Disabled
- **Scheduler**: Disabled  
- **Ollama**: `gpt-oss:20b` model

### Docker Compose Setup (.env):
- **Database**: PostgreSQL on port 5433
- **Elasticsearch**: Enabled on port 9200
- **Kibana**: Port 5601
- **Ollama**: Must start separately

## Next Steps

1. **Start Ollama**: `ollama serve` (keep terminal open)
2. **Verify it's running**: `curl http://localhost:11434/api/tags`
3. **Check if httpx can connect**: Run diagnostic
4. **If httpx fails**: Switch to `requests` library for Ollama
5. **Test AI endpoint**: `curl http://127.0.0.1:8000/api/ai/health`

## Diagnostic Commands

```powershell
# Check what's running
docker-compose ps                    # Docker services
Get-Process ollama                   # Ollama process
Get-Process python                   # API server
netstat -ano | findstr :11434        # Ollama port
netstat -ano | findstr :8000         # API port

# Check connectivity
curl http://localhost:11434/api/tags # Ollama
curl http://127.0.0.1:8000/health    # API basic
curl http://127.0.0.1:8000/api/ai/health  # AI health
```

## Files Created for Easy Management

1. **start_server.ps1** - Start API with all env vars
2. **start_in_new_window.ps1** - Start API in separate window
3. **check_routes.ps1** - Verify all endpoints
4. **diagnose.ps1** - Pre-flight checks
5. **QUICK_START.md** - Complete startup guide
