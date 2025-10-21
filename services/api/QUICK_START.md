# Quick Start Guide - ApplyLens API with Ollama

## Prerequisites

1. **Ollama running** with `gpt-oss:20b` model:
   ```powershell
   curl http://localhost:11434/api/tags
   ```

2. **Check for port conflicts:**
   ```powershell
   netstat -ano | findstr :8000
   ```
   If port 8000 is in use, kill the process or change the port in `start_server.ps1`

## Method 1: Interactive Terminal (Recommended for Development)

Open a terminal in `services/api` and run:

```powershell
.\start_server.ps1
```

**Do not use background jobs or tasks.** Keep this terminal open.

## Method 2: Separate Window (Recommended for Demo)

```powershell
.\start_in_new_window.ps1
```

This opens a new PowerShell window that won't be auto-killed.

## Verify Server Started

Wait ~10 seconds for startup, then in a **different terminal**:

```powershell
.\check_routes.ps1
```

Expected output:
```
✓ Server is responding
✓ AI endpoint responding
✓ Found Phase 4 routes:
  - /api/ai/health
  - /api/ai/summarize
  - /api/rag/query
  - /api/security/risk-top3
✓ Ollama is running
```

## Manual Tests

```powershell
# Basic health
curl.exe http://127.0.0.1:8000/health

# AI health
curl.exe http://127.0.0.1:8000/api/ai/health

# Test summarization (requires email data)
curl.exe -X POST http://127.0.0.1:8000/api/ai/summarize `
  -H "Content-Type: application/json" `
  -d '{"thread_id": "demo-1"}'
```

## Troubleshooting

### Server exits immediately after startup

**Cause:** `--reload` flag on Windows can trigger spurious shutdowns.

**Fix:** Remove `--reload` from `start_server.ps1`:
```powershell
python -u -m uvicorn app.main:app `
  --host 127.0.0.1 `
  --port 8000 `
  --log-level debug
```

### AI routes return 404

**Check logs** for "✓ Phase 4 AI routers registered successfully"
- If missing: Import error in routers
- If present but still 404: Server running old code, restart needed

### Wrong working directory

Logs should show: `Will watch for changes in these directories: ['D:\\ApplyLens\\services\\api']`

If you see `['D:\\ApplyLens']`, the server is running from wrong directory.

**Fix:** Ensure you're running from `services/api`:
```powershell
cd d:\ApplyLens\services\api
.\start_server.ps1
```

### Ollama timeout

**Symptoms:** Request hangs for 2+ minutes

**Cause:** `gpt-oss:20b` is loading into memory (13 GB)

**Solutions:**
1. Pre-warm Ollama: `curl http://localhost:11434/api/generate -d '{"model":"gpt-oss:20b","prompt":"hi"}'`
2. Use smaller model: Change `OLLAMA_MODEL` to `llama3:latest` in `start_server.ps1`

## Configuration

Edit `start_server.ps1` to change:

```powershell
$env:OLLAMA_MODEL   = "gpt-oss:20b"     # or "llama3:latest", "qwen2.5:7b-instruct"
$env:DATABASE_URL   = "sqlite:///./test.db"  # or PostgreSQL connection string
$env:ES_ENABLED     = "false"           # Set to "true" if Elasticsearch available
$env:SCHEDULER_ENABLED = "0"            # Set to "1" to enable background jobs
```

## Stopping the Server

- **Interactive terminal:** Press `Ctrl+C`
- **Separate window:** Close the PowerShell window
- **Kill all Python:** `Get-Process python | Stop-Process -Force`
