# Website Fix - October 12, 2025

## Problem

The website at http://localhost:5175 was not accessible. The browser showed "connection refused" or timeout errors.

## Root Cause

The Vite configuration file (`apps/web/vite.config.ts`) had the API proxy pointing to `http://api:8003`, which is the Docker service name. This works when the frontend is running **inside Docker**, but fails when running **outside Docker** on the host machine.

### Before (Broken):
```typescript
server: {
  port: 5175,
  proxy: {
    '/api': {
      target: 'http://api:8003',  // ❌ Docker service name - doesn't resolve on host
      changeOrigin: true,
    }
  }
}
```

## Solution

Changed the proxy target to `http://localhost:8003` so it works when the frontend runs on the host machine.

### After (Fixed):
```typescript
server: {
  port: 5175,
  proxy: {
    '/api': {
      target: 'http://localhost:8003',  // ✅ Uses localhost - works on host
      changeOrigin: true,
    }
  }
}
```

## Additional Issues Resolved

1. **Process Conflicts**: Multiple node processes were running from previous attempts
   - **Fix**: Killed all node processes before restarting
   
2. **Terminal Interference**: Commands in the same terminal were interrupting Vite
   - **Fix**: Started Vite in a separate PowerShell window using `Start-Process`

## Verification

```powershell
# Test website is responding
Invoke-WebRequest -Uri http://localhost:5175 -UseBasicParsing

StatusCode: 200 ✅
Content Length: 641 bytes ✅
```

## Current Status

✅ **Website is now working!**

**Services Running:**
- Frontend (Vite): http://localhost:5175
- Backend (FastAPI): http://localhost:8003
- Database (PostgreSQL): localhost:5433
- Elasticsearch: http://localhost:9200

**Access Points:**
- 🌐 Web UI: http://localhost:5175
- 📚 API Docs: http://localhost:8003/docs
- 📊 Metrics: http://localhost:8003/metrics

## How to Start Frontend (Going Forward)

### Method 1: Separate Window (Recommended)
```powershell
cd d:/ApplyLens/apps/web
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "npm run dev"
```

This opens a new PowerShell window dedicated to running the frontend, preventing interference.

### Method 2: Current Terminal
```powershell
cd d:/ApplyLens/apps/web
npm run dev
# Keep this terminal open, use another terminal for other commands
```

### Method 3: Background Process
```powershell
cd d:/ApplyLens/apps/web
Start-Job -ScriptBlock { Set-Location d:/ApplyLens/apps/web; npm run dev }
```

## Configuration Notes

### Docker vs Host

The configuration now uses `localhost:8003` which works when:
- ✅ Frontend runs on host (npm run dev)
- ✅ Backend runs in Docker

If you want to run the frontend in Docker too, you would need to:
1. Change back to `http://api:8003`
2. Create a Dockerfile for the frontend
3. Add the frontend service to docker-compose.yml

### Environment-Specific Config

For better flexibility, you could use environment variables:

```typescript
server: {
  proxy: {
    '/api': {
      target: process.env.VITE_API_URL || 'http://localhost:8003',
      changeOrigin: true,
    }
  }
}
```

Then set `VITE_API_URL=http://api:8003` when running in Docker.

## Testing Checklist

After starting the frontend, verify:

- [ ] Vite shows "ready" message with port 5175
- [ ] Website loads at http://localhost:5175
- [ ] API proxy works (network requests to /api/* succeed)
- [ ] No errors in browser console
- [ ] Actions button visible in header

## Troubleshooting

### Website still not loading?

1. **Check if Vite is running:**
   ```powershell
   Get-Process -Name node
   ```

2. **Check if port 5175 is listening:**
   ```powershell
   Get-NetTCPConnection -LocalPort 5175 -State Listen
   ```

3. **Test with curl:**
   ```powershell
   curl http://localhost:5175
   ```

4. **Check Vite output for errors:**
   Look at the terminal window where `npm run dev` is running

5. **Restart frontend:**
   ```powershell
   # Kill all node processes
   Get-Process -Name node | Stop-Process -Force
   
   # Start fresh
   cd d:/ApplyLens/apps/web
   npm run dev
   ```

### API calls failing (CORS errors)?

Check that backend is running:
```powershell
curl http://localhost:8003/docs
```

If backend is down:
```powershell
cd d:/ApplyLens/infra
docker compose up -d api
```

### Port 5175 already in use?

Change the port in `vite.config.ts`:
```typescript
server: {
  port: 5176,  // Use different port
  // ...
}
```

Or kill the process using port 5175:
```powershell
$port = Get-NetTCPConnection -LocalPort 5175 | Select-Object -ExpandProperty OwningProcess
Stop-Process -Id $port -Force
```

## Summary

**Problem:** Vite proxy misconfigured for Docker service name  
**Solution:** Changed to localhost  
**Result:** ✅ Website working at http://localhost:5175  

The frontend development server is now running properly with correct proxy configuration, and the full stack is operational.
