# 🚨 Incident Runbook: 503 from Nginx but API is Healthy

**Symptom:** Frontend calls to `/api/*` fail with HTTP 503
**Root Cause:** Nginx cached stale upstream IP address after API container restart
**Time to Resolve:** 2-5 minutes
**Severity:** P1 (Production Down)

---

## Symptoms

- ❌ Frontend shows connection errors
- ❌ Browser console: `[LoginGuard] Backend error 503`
- ❌ All `/api/*` endpoints return 503
- ✅ API container shows healthy status
- ✅ Direct curl to API port works fine

---

## Step-by-Step Triage

### 1. Check API Container Health

```powershell
# Check container status
docker ps -a --filter "name=applylens-api-prod" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check recent logs
docker logs applylens-api-prod --tail 50
```

**Expected:** Status shows "Up X minutes (healthy)"

### 2. Test API Directly (Bypass Nginx)

```powershell
# Test health endpoint
Invoke-RestMethod -Uri "http://localhost:8003/ready" -Method Get

# Should return: status=ready, db=ok, es=ok
```

**If 200/OK → API is healthy, problem is in nginx**

### 3. Check Nginx Container

```powershell
# Check nginx status
docker ps --filter "name=applylens-nginx-prod" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check error logs
docker logs applylens-nginx-prod --tail 100 | Select-String "503"
```

**Look for:** `connect() failed (111: Connection refused) while connecting to upstream`

### 4. Confirm Stale IP Issue

```powershell
# Get current API container IP
docker inspect applylens-api-prod -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# Compare with IP in nginx error logs (e.g., "upstream: http://172.25.0.4:8003")
```

**If IPs don't match → This is the bug**

Example:
- Nginx trying to reach: `172.25.0.4:8003` ❌
- API actually at: `172.25.0.8:8003` ✅

---

## Remediation (Break-Glass Fix)

```powershell
# Restart nginx to force IP resolution refresh
docker restart applylens-nginx-prod

# Wait for healthy status
Start-Sleep -Seconds 5
docker ps --filter "name=applylens-nginx-prod" --format "{{.Status}}"
```

### Verify Resolution

```powershell
# Test through nginx
Invoke-RestMethod -Uri "https://applylens.app/api/ready" -Method Get

# Or reload the UI - 503 errors should be gone
```

**Expected:** All endpoints work again ✅

---

## Root Cause

**Problem:** Nginx resolves upstream container names to IP addresses at startup and caches them. When Docker recreates the API container, it assigns a new IP, but nginx still tries to connect to the old (dead) IP.

**Timeline:**
1. API container restarts → Docker assigns new IP (e.g., `172.25.0.8`)
2. Nginx still has cached old IP (e.g., `172.25.0.4`)
3. Nginx tries to connect to dead IP → Connection Refused
4. Nginx returns 503 to all clients

---

## Prevention (Permanent Fix)

**Status:** ✅ IMPLEMENTED (see nginx configuration below)

### Solution: Use Container Names Instead of IPs

Nginx should use Docker's embedded DNS to resolve container names dynamically:

```nginx
# infra/nginx/conf.d/applylens.prod.conf
upstream applylens_api_upstream {
    server applylens-api-prod:8003;  # ✅ Container name (auto-resolves)
    # NOT: server 172.25.0.4:8003;   # ❌ Static IP (breaks on restart)
    keepalive 32;
}

server {
    listen 443 ssl;
    server_name applylens.app;

    location /api/ {
        proxy_pass         http://applylens_api_upstream;
        proxy_http_version 1.1;
        proxy_set_header   Connection "";
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

### How This Works

- ✅ Docker's embedded DNS automatically resolves `applylens-api-prod` to current IP
- ✅ If API container restarts with new IP, nginx auto-discovers it on next request
- ✅ No manual nginx restart needed
- ✅ Both containers must be on same Docker network (already configured)

### Verify Configuration

```powershell
# Check nginx config uses container name
docker exec applylens-nginx-prod cat /etc/nginx/conf.d/default.conf | Select-String "server.*applylens-api-prod"

# Should output: server applylens-api-prod:8003;
```

---

## Related Documentation

- `docker-compose.prod.yml` - Network configuration
- `infra/nginx/conf.d/applylens.prod.conf` - Nginx upstream config
- `DEPLOY.md` - Production deployment procedures

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-26 | System | Initial runbook creation after 503 incident |
| 2025-10-26 | System | Verified nginx config uses container names (prevention implemented) |

---

## Tags

`#production` `#incident` `#nginx` `#503` `#docker` `#networking` `#p1`
