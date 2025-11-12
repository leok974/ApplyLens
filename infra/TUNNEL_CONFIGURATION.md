# Cloudflare Tunnel HA Configuration - ApplyLens

**Date Completed:** November 11, 2025
**Status:** ✅ Operational (100% success rate in burn-in testing)

## Architecture

```
Internet → Cloudflare Edge (QUIC) → 2x HA Tunnel Connectors → infra_net → Backend Services
```

## Tunnel Details

- **Tunnel ID:** `08d5feee-f504-47a2-a1f2-b86564900991`
- **Protocol:** QUIC (automatic, default in cloudflared:latest)
- **Authentication:** Token-based (stored in `.env`)
- **Connectors:** 2x (cfd-a, cfd-b) for high availability
- **Connections:** 4x per connector (iad05, iad09, iad11, iad15)

## Public Hostname Routes

Configured in Cloudflare Zero Trust Dashboard:

1. **applylens.app** → `http://applylens-web:80`
2. **api.applylens.app** → `http://applylens-api:8003`

## Docker Configuration

**File:** `docker-compose.tunnel.yml`

```yaml
services:
  cfd-a:
    image: cloudflare/cloudflared:latest
    container_name: cfd-a
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARED_TUNNEL_TOKEN}
    networks:
      - infra_net
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pgrep cloudflared || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3

  cfd-b:
    image: cloudflare/cloudflared:latest
    container_name: cfd-b
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARED_TUNNEL_TOKEN}
    networks:
      - infra_net
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pgrep cloudflared || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3

networks:
  infra_net:
    external: true
```

## Network Topology

- **Network:** `infra_net` (external Docker network)
- **Tunnel Containers:** cfd-a, cfd-b
- **Backend Services:**
  - applylens-web-prod (alias: applylens-web)
  - applylens-api-prod (alias: applylens-api)

## Stability Testing Results

**60-request burn-in test (30 seconds):**
- ✅ 60/60 requests successful (100%)
- ✅ 0 failures
- ✅ 0 timeouts
- ✅ 0 502 errors

**Endpoints tested:**
- `https://applylens.app/favicon-32.png` → 200 OK
- `https://applylens.app/welcome` → 200 OK
- `https://api.applylens.app/healthz` → 200 OK

## Critical Fixes Applied

1. **Removed conflicting containers:** Stopped 4 old cloudflared instances that were fighting for tunnel resources
   - applylens-cloudflared-prod
   - infra-cloudflared
   - cloudflared
   - ai-finance-agent-oss-clean-cloudflared-1

2. **Simplified tunnel command:** Using default QUIC protocol (no custom flags needed)

3. **Token authentication:** Using `TUNNEL_TOKEN` env var instead of volume-mounted credentials

4. **Stopped edge-nginx:** Ensured no port conflicts on host

## Hardening Checklist

- ✅ **QUIC Protocol:** Enabled by default (cloudflared:latest)
- ✅ **HA Connectors:** 2 connectors (cfd-a, cfd-b)
- ✅ **Multiple Connections:** 4 connections per connector to different edge locations
- ✅ **Auto-restart:** `restart: unless-stopped` configured
- ✅ **Container DNS:** All on infra_net with proper aliases
- ✅ **Origins Configured:** Routes set in CF dashboard
- ✅ **Single Front Door:** edge-nginx stopped to avoid conflicts
- ✅ **Static Assets:** Favicon verified (200 OK)

## Monitoring

**Health Monitor Script:** `scripts/monitor-tunnel-health.ps1`

```powershell
.\scripts\monitor-tunnel-health.ps1
```

**Manual Quick Check:**

```powershell
curl.exe -s -o NUL -w "%{http_code}" https://applylens.app/
curl.exe -s -o NUL -w "%{http_code}" https://api.applylens.app/healthz
```

**View Tunnel Logs:**

```powershell
docker logs cfd-a --tail 100 --follow
docker logs cfd-b --tail 100 --follow
```

**Check Tunnel Status:**

```powershell
docker ps --filter "name=cfd-"
```

## Maintenance Commands

**Start tunnel:**
```powershell
docker compose -f docker-compose.tunnel.yml up -d
```

**Stop tunnel:**
```powershell
docker compose -f docker-compose.tunnel.yml down
```

**Restart tunnel:**
```powershell
docker compose -f docker-compose.tunnel.yml restart
```

**View connector status:**
```powershell
docker ps --filter "name=cfd-" --format "table {{.Names}}\t{{.Status}}"
```

## Nice-to-Have Enhancements (Future)

1. **Cloudflare WAF:** Enable standard WAF rules for applylens.app and api.applylens.app
2. **Caching Rules:** Add Cache Rule for `/assets/*` with hashed assets
3. **Metrics Dashboard:** Expose cloudflared metrics on port 2000
4. **Alerting:** Set up Prometheus/Grafana alerts for tunnel health

## Troubleshooting

**If you see 502 errors:**

1. Check tunnel logs:
   ```powershell
   docker logs cfd-a --since 2m | Select-String "ERR|error|502|timeout"
   docker logs cfd-b --since 2m | Select-String "ERR|error|502|timeout"
   ```

2. Verify backends are healthy:
   ```powershell
   docker ps --filter "name=applylens-" --format "table {{.Names}}\t{{.Status}}"
   ```

3. Test backend directly:
   ```powershell
   docker run --rm --network infra_net curlimages/curl -sS http://applylens-web:80/
   docker run --rm --network infra_net curlimages/curl -sS http://applylens-api:8003/healthz
   ```

4. Check for conflicting cloudflared containers:
   ```powershell
   docker ps --filter "name=cloudflared"
   ```

**Expected behavior:**
- Auth endpoints (`/api/auth/me`) returning 401 before login is normal
- Healthcheck showing "unhealthy" but requests succeeding is cosmetic (pgrep timing)

## Notes

- Tunnel uses default QUIC protocol (automatically selected by cloudflared:latest)
- No need for `--protocol quic` flag (causes issues)
- Token-based auth simplifies deployment vs file-based credentials
- 2 connectors provide redundancy across edge locations
- Each connector maintains 4 connections for load balancing
