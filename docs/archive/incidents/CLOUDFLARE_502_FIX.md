# Cloudflare Tunnel 502 Intermittent Fix

**Date**: 2025-10-30
**Issue**: Intermittent 502 Bad Gateway on https://applylens.app
**Root Cause**: Cloudflare edge caching stale 502 responses + token-based tunnel config

---

## Problem Analysis

### Evidence
1. ✅ **Docker networking is perfect** - All containers healthy, DNS resolves correctly
2. ✅ **Nginx is working** - All logs show 200 OK responses, no 502 errors
3. ✅ **Cloudflared is connected** - 4 tunnel connections to Cloudflare edge
4. ❌ **Intermittent 502 from public internet** - ~20% of requests fail with 502

### Test Results
```bash
Test 1: 200 OK
Test 2: 200 OK
Test 3: 200 OK
Test 4: 200 OK
Test 5: 502 Bad Gateway  ← Intermittent failure
```

### Root Cause
Cloudflared is running with `--token` flag, which means:
- Configuration is **managed in Cloudflare's dashboard**
- Local `config.yml` changes are **ignored**
- Cloudflare edge servers may have **cached the old 502 error**
- Health checks from Cloudflare edge may be **timing out intermittently**

---

## Immediate Fixes

### Fix 1: Purge Cloudflare Cache

**Go to Cloudflare Dashboard**:
1. Navigate to: https://dash.cloudflare.com/
2. Select domain: `applylens.app`
3. Go to: **Caching** → **Configuration**
4. Click: **Purge Everything**
5. Confirm purge

This will clear any cached 502 error pages from Cloudflare's edge.

### Fix 2: Verify Tunnel Configuration in Dashboard

1. Go to: **Zero Trust** → **Networks** → **Tunnels**
2. Find tunnel: `applylens` (ID: `08d5feee-f504-47a2-a1f2-b86564900991`)
3. Click **Configure**
4. Verify **Public Hostnames**:
   ```
   Hostname: applylens.app
   Service: http://applylens.int:80

   Hostname: www.applylens.app
   Service: http://applylens.int:80

   Hostname: api.applylens.app
   Service: http://applylens-api.int:8003
   ```

5. Check **Origin configuration**:
   - Connect Timeout: Should be at least 10s
   - TLS Verify: Disabled (we're using HTTP internally)
   - Keep-Alive Connections: 100
   - Keep-Alive Timeout: 90s

### Fix 3: Add Health Check Endpoint

In **Cloudflare Dashboard** → **Tunnel Configuration** → **Origin Configuration**:

Enable health checks to `/health` endpoint:
```
Health Check Path: /health
Health Check Interval: 30s
Health Check Timeout: 10s
Unhealthy Threshold: 3
Healthy Threshold: 2
```

This ensures Cloudflare marks the origin as healthy before routing traffic.

### Fix 4: Enable Connection Pooling

In **Origin Configuration**, enable:
- **HTTP/2 Origin**: Enabled
- **Connection Pooling**: Enabled
- **Keep-Alive**: 90s

---

## Alternative: Switch to Config File Mode

If you want to manage config locally instead of via dashboard:

### Step 1: Update docker-compose.prod.yml

Change from token-based to config-file mode:

```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  container_name: applylens-cloudflared-prod
  # OLD: command: tunnel --no-autoupdate run --token ${CLOUDFLARED_TUNNEL_TOKEN}
  # NEW:
  command: tunnel --no-autoupdate run applylens
  volumes:
    - ./infra/cloudflared:/etc/cloudflared
  depends_on:
    - nginx
  restart: unless-stopped
  networks:
    - applylens-prod
```

### Step 2: Verify config.yml has credentials

Ensure `/infra/cloudflared/config.yml` contains:
```yaml
tunnel: 08d5feee-f504-47a2-a1f2-b86564900991
credentials-file: /etc/cloudflared/08d5feee-f504-47a2-a1f2-b86564900991.json

originRequest:
  connectTimeout: 30s
  tlsTimeout: 10s
  tcpKeepAlive: 30s
  keepAliveConnections: 100
  keepAliveTimeout: 90s

ingress:
  - hostname: applylens.app
    service: http://applylens.int:80
    originRequest:
      connectTimeout: 10s
      noTLSVerify: true

  - hostname: www.applylens.app
    service: http://applylens.int:80
    originRequest:
      connectTimeout: 10s
      noTLSVerify: true

  - hostname: api.applylens.app
    service: http://applylens-api.int:8003
    originRequest:
      connectTimeout: 15s
      noTLSVerify: true

  - service: http_status:404
```

### Step 3: Restart cloudflared

```bash
docker compose -f docker-compose.prod.yml up -d cloudflared
```

---

## Verification Commands

### Test from multiple edge locations
```bash
# Test 10 times to catch intermittent failures
for ($i=1; $i -le 10; $i++) {
    $code = curl.exe -s -o $null -w "%{http_code}" https://applylens.app/health
    Write-Host "Test $i : $code"
    Start-Sleep -Milliseconds 500
}
```

**Expected**: All tests return `200` or `ok` (no 502)

### Check nginx logs for actual requests
```bash
docker logs applylens-nginx-prod --tail 50 | Select-String "applylens.app"
```

**Expected**: All requests show `200` status

### Monitor cloudflared connection
```bash
docker logs applylens-cloudflared-prod --tail 20 | Select-String "Registered|error"
```

**Expected**: 4 registered connections, no origin errors

---

## Why This Happens

### Cloudflare Edge Caching
When the site was previously down (web container issue), Cloudflare's edge servers:
1. Received 502 errors from the origin
2. Cached those 502 responses (per HTTP cache headers)
3. Continued serving cached 502 even after origin recovered
4. Different edge servers have different cache states (hence intermittent)

### Token-Based Configuration Limitation
Using `--token` means:
- Configuration is fetched from Cloudflare API on startup
- Changes in local `config.yml` are **completely ignored**
- Must update settings in Cloudflare dashboard instead
- Dashboard changes may take 2-5 minutes to propagate to edge

---

## Long-Term Prevention

### 1. Add Cache-Control Headers in Nginx

For error pages, ensure they're not cached:

```nginx
# In applylens.prod.conf, add to server block:
location @api_unavailable {
    add_header Cache-Control "no-store, no-cache, must-revalidate" always;
    add_header X-Accel-Expires 0 always;
    default_type application/json;
    return 503 '{"status":"unavailable","message":"API temporarily unavailable"}';
}
```

### 2. Enable Argo Smart Routing (Paid)

In Cloudflare Dashboard → **Traffic** → **Argo**:
- Argo Smart Routing: Reduces latency and improves reliability
- Monitors tunnel health across edge servers
- Automatically routes around unhealthy edges

### 3. Set Up Alerting

In Cloudflare Dashboard → **Analytics** → **Notifications**:
- Create alert for: **Tunnel Down**
- Create alert for: **High Error Rate (5xx > 5%)**
- Notify via: Email/Slack/PagerDuty

---

## Current Status

✅ **Docker Stack**: Fully healthy
✅ **Nginx**: Serving all requests successfully
✅ **Cloudflared**: Connected to Cloudflare edge
⚠️  **Public Access**: Intermittent 502 (~20% failure rate)

**Next Action**: Purge Cloudflare cache and verify tunnel health check settings

---

## Quick Reference

```bash
# Test site health (run 10 times)
1..10 | ForEach-Object {
    $r = curl.exe -s -o $null -w "%{http_code}" https://applylens.app/health
    Write-Host "$_ : $r"
}

# Check nginx logs
docker logs applylens-nginx-prod --tail 100 | Select-String "502|504"

# Check cloudflared status
docker logs applylens-cloudflared-prod --tail 30

# Restart cloudflared
docker restart applylens-cloudflared-prod

# Check tunnel in dashboard
https://one.dash.cloudflare.com/ → Networks → Tunnels → applylens
```
