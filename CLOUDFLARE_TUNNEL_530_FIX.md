# Cloudflare Tunnel - Error 530 Diagnosis & Fix

**Date**: October 22, 2025
**Error**: `GET https://applylens.app/welcome 530`
**Status**: ✅ **RESOLVED** - Tunnel now running

---

## 🔍 Error Analysis

### What is HTTP 530?

**Error 530** is a **Cloudflare-specific error** that means:
> **"Origin DNS Error" or "1XXX Cloudflare Error"**

Common causes:
1. **Cloudflare Tunnel not running** ✅ This was the issue
2. DNS misconfiguration pointing to wrong origin
3. Origin server (nginx) is down
4. Network connectivity issues between Cloudflare and origin

---

## 🐛 Root Cause

### Problem Discovered
The **Cloudflare Tunnel container was NOT running**.

```bash
$ docker ps --filter "name=cloudflared"
NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS
# Empty - no container running!
```

### Why It Wasn't Running

The `cloudflared` service in `docker-compose.prod.yml` requires the environment variable `CLOUDFLARED_TUNNEL_TOKEN`, but:

1. ✅ Token exists in `.env` file
2. ❌ Docker Compose wasn't loading it automatically
3. ❌ Service was defined but never started

---

## ✅ Solution Applied

### Step 1: Verify Token Exists
```bash
$ Get-Content .env | Select-String "CLOUDFLARED"
CLOUDFLARED_TUNNEL_TOKEN=eyJhIjoiNDMzYz...
```

### Step 2: Start Cloudflare Tunnel
```bash
$ docker-compose -f docker-compose.prod.yml up -d cloudflared
```

### Step 3: Verify Tunnel Connected
```bash
$ docker logs applylens-cloudflared-prod --tail 20

✅ 2025-10-22T14:12:35Z INF Registered tunnel connection connIndex=0
✅ 2025-10-22T14:12:35Z INF Registered tunnel connection connIndex=1
✅ 2025-10-22T14:12:36Z INF Registered tunnel connection connIndex=2
✅ 2025-10-22T14:12:37Z INF Registered tunnel connection connIndex=3
```

**Result**: 4 tunnel connections established to Cloudflare edge (iad03, iad09, iad11, iad12)

---

## 📊 Current Status

### Containers Running
```bash
$ docker ps --filter "name=applylens-" --format "table {{.Names}}\t{{.Status}}"

NAMES                          STATUS
✅ applylens-cloudflared-prod   Up 10 minutes (healthy)
✅ applylens-nginx-prod         Up 10 hours (healthy)
✅ applylens-web-prod           Up 10 hours (healthy)
✅ applylens-api-prod           Up 10 hours (healthy)
✅ applylens-db-prod            Up 10 hours (healthy)
✅ applylens-es-prod            Up 10 hours (healthy)
✅ applylens-redis-prod         Up 10 hours (healthy)
✅ applylens-grafana-prod       Up 10 hours (healthy)
✅ applylens-prometheus-prod    Up 10 hours (healthy)
✅ applylens-kibana-prod        Up 10 hours (healthy)
```

### Public URL Test
```bash
$ Invoke-WebRequest https://applylens.app/welcome

StatusCode : 200
StatusDescription : OK
✅ Site is now accessible!
```

---

## ⚠️ Configuration Mismatch Detected

### Issue: Tunnel Configuration Points to Wrong Services

The Cloudflare Tunnel configuration (managed via Cloudflare dashboard) is routing to:
```json
{
  "ingress": [
    {
      "hostname": "applylens.app",
      "service": "http://applylens.int:80"  ❌ This service doesn't exist
    },
    {
      "hostname": "api.applylens.app",
      "service": "http://applylens-api.int:8003"  ❌ This service doesn't exist
    }
  ]
}
```

**Problem**: Your local Docker Compose uses:
- Network: `applylens_applylens-prod`
- Service names: `nginx` (not `applylens.int`)
- Service names: `api` (not `applylens-api.int`)

### Current Errors in Logs
```bash
2025-10-22T14:13:07Z ERR Request failed error="Unable to reach the origin service.
The service may be down or it may not be responding to traffic from cloudflared:
dial tcp: lookup siteagent-ui.int on 127.0.0.11:53: no such host"
```

These are for other domains (siteagents.app, leoklemet.com) which are NOT running locally.

---

## 🔧 How Cloudflare Tunnel Configuration Works

### Configuration Management

Cloudflare Tunnel configuration is **stored in Cloudflare's cloud**, NOT in your local files. There are 2 ways to manage it:

#### Option 1: Cloudflare Dashboard (Current Setup)
- Configuration is managed via https://dash.cloudflare.com/
- Navigate to: **Zero Trust** → **Networks** → **Tunnels**
- The tunnel token includes the tunnel ID and authentication
- Ingress rules are edited in the dashboard

#### Option 2: Local Config File (Alternative)
```yaml
# ~/.cloudflared/config.yml
tunnel: 08d5feee-f504-47a2-a1f2-b86564900991
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - hostname: applylens.app
    service: http://nginx:80
  - hostname: api.applylens.app
    service: http://api:8003
  - service: http_status:404
```

---

## 🎯 Recommended Fixes

### Fix 1: Update Cloudflare Dashboard Configuration

**Go to**: https://dash.cloudflare.com/ → Zero Trust → Networks → Tunnels → Your Tunnel

**Change ingress rules**:

| Current (❌ Wrong) | Should Be (✅ Correct) |
|-------------------|----------------------|
| `http://applylens.int:80` | `http://nginx:80` |
| `http://applylens-api.int:8003` | `http://api:8003` |

**Why**: The service names must match your Docker Compose service names on the same network.

### Fix 2: Verify Docker Compose Service Names

In `docker-compose.prod.yml`, ensure services are named correctly:
```yaml
services:
  nginx:  # ✅ This is the service name
    container_name: applylens-nginx-prod
    networks:
      - applylens-prod

  api:  # ✅ This is the service name
    container_name: applylens-api-prod
    networks:
      - applylens-prod

  cloudflared:
    networks:
      - applylens-prod  # ✅ Must be on same network
```

### Fix 3: Remove Non-Existent Domain Routes

If you're not hosting these domains locally, remove them from Cloudflare Tunnel config:
- ❌ `siteagents.app` → Not running
- ❌ `www.siteagents.app` → Not running
- ❌ `api.siteagents.app` → Not running
- ❌ `leoklemet.com` → Not running
- ❌ `www.leoklemet.com` → Not running
- ❌ `api.leoklemet.com` → Not running

Or start those services if needed.

---

## 🧪 Testing

### Test Local Access (Bypassing Tunnel)
```bash
# Direct nginx access
$ curl http://localhost/web/inbox
✅ Should return 200 OK

# Direct API access
$ curl http://localhost:8003/status
✅ Should return {"ok": false, "gmail": "degraded", ...}
```

### Test Public Access (Through Tunnel)
```bash
# Public web access
$ curl https://applylens.app/web/inbox
✅ Should return 200 OK

# Public API access
$ curl https://applylens.app/api/status
✅ Should return {"ok": false, "gmail": "degraded", ...}
```

### Check Tunnel Logs for Errors
```bash
$ docker logs -f applylens-cloudflared-prod

# Look for:
✅ "Registered tunnel connection" - Good
❌ "Unable to reach the origin service" - Bad (wrong service name)
❌ "dial tcp: lookup ... no such host" - Bad (DNS failure)
```

---

## 📋 Quick Reference Commands

### Check Tunnel Status
```bash
docker ps --filter "name=cloudflared"
docker logs applylens-cloudflared-prod --tail 50
```

### Restart Tunnel
```bash
docker-compose -f docker-compose.prod.yml restart cloudflared
```

### Stop Tunnel
```bash
docker-compose -f docker-compose.prod.yml stop cloudflared
```

### Start Tunnel
```bash
docker-compose -f docker-compose.prod.yml up -d cloudflared
```

### View Tunnel Configuration
```bash
docker logs applylens-cloudflared-prod | grep "Updated to new configuration"
```

### Test Public URL
```bash
# PowerShell
Invoke-WebRequest -Uri https://applylens.app/welcome -UseBasicParsing

# Or open browser
start https://applylens.app/welcome
```

---

## ✅ Resolution Summary

| Issue | Status | Notes |
|-------|--------|-------|
| HTTP 530 Error | ✅ **FIXED** | Tunnel was not running |
| Cloudflare Tunnel Running | ✅ **YES** | 4 connections active |
| Public Site Accessible | ✅ **YES** | Returns HTTP 200 |
| Service Name Mismatch | ⚠️ **WARNING** | Update Cloudflare dashboard config |
| Non-Existent Domains | ℹ️ **INFO** | Can be removed if not needed |

---

## 🎯 Next Steps

### Immediate (Required)
1. ✅ **DONE**: Start Cloudflare Tunnel container
2. ✅ **DONE**: Verify tunnel connected (4 connections)
3. ✅ **DONE**: Confirm public site accessible (HTTP 200)

### Short-Term (Recommended)
4. ⬜ **TODO**: Update Cloudflare dashboard ingress rules:
   - Change `applylens.int` → `nginx`
   - Change `applylens-api.int` → `api`
5. ⬜ **TODO**: Remove or comment out non-running domains in Cloudflare config
6. ⬜ **TODO**: Test API endpoints via public URL

### Long-Term (Optional)
7. ⬜ Consider: Move tunnel config to local file for version control
8. ⬜ Consider: Add health checks to Cloudflare Tunnel service
9. ⬜ Consider: Set up automatic tunnel restart on failure

---

## 📚 Related Documentation

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Cloudflare Error 530](https://developers.cloudflare.com/support/troubleshooting/cloudflare-errors/troubleshooting-cloudflare-5xx-errors/#error-530)
- `docker-compose.prod.yml` - Production Docker Compose configuration
- `.env` - Environment variables (contains tunnel token)

---

## 🔐 Security Notes

- ✅ Tunnel token is stored in `.env` (gitignored)
- ✅ Tunnel uses HTTPS/TLS for all public traffic
- ✅ No ports exposed publicly (tunnel creates outbound connection)
- ⚠️ Ensure `.env` is never committed to git
- ⚠️ Rotate tunnel token if compromised

---

**Status**: The Cloudflare Tunnel is now operational and the site is accessible via `https://applylens.app`. Configuration optimization recommended but not blocking.
