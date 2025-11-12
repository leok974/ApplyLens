# Development Scripts

This directory contains PowerShell scripts for common development tasks.

## 🚀 Quick Start Scripts

### `dev-api-clean.ps1`

**One-shot "nuke & boot" script** - Cleanly restarts the API server with a fresh environment.

**What it does:**
1. Kills any process on port 8003
2. Terminates stale Python/Uvicorn processes
3. Clears all `__pycache__` directories (prevents reload issues)
4. Sets development environment variables
5. Launches Uvicorn with auto-reload

**Usage:**
```powershell
.\services\api\scripts\dev-api-clean.ps1
```

**When to use:**
- Server feels "stuck" or not reloading changes
- Routes returning 404 after code changes
- Environment variables not being picked up
- After major code refactoring

### `verify-api-routes.ps1`

**API verification script** - Tests that the running server has correct routes and environment.

**What it checks:**
1. ✅ Server is running and responding
2. 📋 OpenAPI spec includes DevDiag and Extension routes
3. 🏥 DevDiag health endpoint status
4. 👤 Profile endpoint functionality
5. 🔒 CSRF metrics for failures

**Usage:**
```powershell
.\services\api\scripts\verify-api-routes.ps1
```

**When to use:**
- After starting the server to verify it's working
- Debugging route registration issues
- Checking CSRF exemptions are working
- Before running integration tests

## 🎮 VS Code Integration

### F5 Debug Launch

Press **F5** to launch the API server with debugging enabled.

**Features:**
- Automatically kills old Python processes (30m+) before starting
- Sets all required environment variables
- Uses `module: uvicorn` for proper debugging
- Console output in integrated terminal

**Configuration:** `.vscode/launch.json`

### Ctrl+Shift+B Build Task

Press **Ctrl+Shift+B** to start the dev server as a background task.

**Features:**
- Kills old Python processes before starting
- Runs in background with auto-reload
- Sets development environment variables
- Shows output in VS Code terminal

**Configuration:** `.vscode/tasks.json`

## 🔧 Environment Variables

All scripts set these environment variables:

```powershell
APPLYLENS_DEV=1                    # Enable dev mode
APPLYLENS_DEV_DB=sqlite:///./dev_extension.db  # Use SQLite for dev
ES_URL=http://localhost:9200       # Elasticsearch
ALLOW_DEV_ROUTES=1                 # Enable dev-only routes

# DevDiag configuration
DEVDIAG_BASE=http://127.0.0.1:8080
DEVDIAG_ENABLED=1
DEVDIAG_TIMEOUT_S=120
DEVDIAG_ALLOW_HOSTS=applylens.app,.applylens.app,api.applylens.app
```

## 📝 Common Workflows

### Starting Development

```powershell
# Option 1: Clean boot (recommended)
.\services\api\scripts\dev-api-clean.ps1

# Option 2: VS Code task
# Press Ctrl+Shift+B

# Option 3: F5 debug
# Press F5 in VS Code
```

### Verifying Server

```powershell
# After server starts, verify routes
.\services\api\scripts\verify-api-routes.ps1

# Manual verification
curl http://localhost:8003/openapi.json | Select-String "/api/ops/diag|/api/extension"
```

### Testing Endpoints

```powershell
# DevDiag health
curl http://localhost:8003/api/ops/diag/health

# Profile endpoint
curl http://localhost:8003/api/profile/me

# Run diagnostics
$body='{"url":"https://applylens.app","preset":"app","tenant":"applylens"}'
curl -X POST http://localhost:8003/api/ops/diag -H "content-type: application/json" -d $body

# Extension test suite
.\services\api\test_extension_endpoints.ps1
```

## 🐛 Troubleshooting

### Routes return 404 after code changes

**Symptom:** New routes not appearing, server returns 404
**Cause:** Stale Python bytecode or old server process
**Fix:**
```powershell
.\services\api\scripts\dev-api-clean.ps1
```

### Environment variables not loaded

**Symptom:** Wrong database, DEVDIAG_BASE not set
**Cause:** Environment not set before server start
**Fix:**
```powershell
# Verify env vars are set
$env:APPLYLENS_DEV
$env:DEVDIAG_BASE

# If empty, use dev-api-clean.ps1 which sets them
.\services\api\scripts\dev-api-clean.ps1
```

### CSRF blocking extension endpoints

**Symptom:** 403 "CSRF token missing" on POST requests
**Cause:** CSRF exemptions not applied
**Fix:**
```powershell
# Check CSRF metrics
curl http://localhost:8003/metrics | Select-String "csrf_fail.*extension"

# Should show no failures for /api/extension/* or /api/ops/diag*
# If failures exist, check app/core/csrf.py exemptions
```

### Port 8003 already in use

**Symptom:** "Address already in use" on port 8003
**Cause:** Old server still running
**Fix:**
```powershell
# Find and kill process on port 8003
$pid = (Get-NetTCPConnection -LocalPort 8003).OwningProcess
Stop-Process -Id $pid -Force

# Or use clean boot script which handles this
.\services\api\scripts\dev-api-clean.ps1
```

## 🔍 Advanced Usage

### Custom DevDiag URL

If running DevDiag on a different port or host:

```powershell
# Set before running scripts
$env:DEVDIAG_BASE="http://localhost:9090"
.\services\api\scripts\dev-api-clean.ps1
```

### Using PostgreSQL instead of SQLite

```powershell
# Set database URL before starting
$env:APPLYLENS_DEV_DB="postgresql://postgres:postgres@localhost:5433/applylens"
.\services\api\scripts\dev-api-clean.ps1
```

### Debugging startup issues

```powershell
# Run with explicit Python path
cd D:\ApplyLens\services\api
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload --reload-dir app

# Check startup logs for environment variable confirmation
# Look for: "🔧 Runtime config: APPLYLENS_DEV=1, DATABASE_URL=..."
```

## 📚 Related Documentation

- [DevDiag Integration Guide](../../../docs/DEVDIAG_INTEGRATION.md)
- [Extension API Test Suite](../test_extension_endpoints.ps1)
- [VS Code Tasks Configuration](../.vscode/tasks.json)
- [VS Code Launch Configuration](../.vscode/launch.json)
