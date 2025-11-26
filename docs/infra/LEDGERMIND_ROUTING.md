# LedgerMind Routing Notes

**CRITICAL**: LedgerMind is **NOT** served by ApplyLens nginx containers.

## Overview

This document explains the routing separation between ApplyLens and LedgerMind to prevent cross-contamination where LedgerMind accidentally calls ApplyLens APIs or vice versa.

## ApplyLens Domains

ApplyLens nginx handles **ONLY** the following domains:

- `applylens.app`, `www.applylens.app` → `applylens-nginx:80` → `applylens-web-prod:80` (web container)
- `api.applylens.app` → `applylens-nginx:80` → `applylens-api-prod:8003` (API container)

### ApplyLens nginx Configuration

ApplyLens nginx server blocks are **strictly limited** to:

```nginx
server_name applylens.app www.applylens.app;
server_name api.applylens.app;
```

**No other domains** (especially not `*.ledger-mind.org`) should be handled by ApplyLens nginx.

### Configuration Files

- **Dev environment**: `infra/nginx/dev.conf`
- **Production environment**: `infra/nginx/conf.d/applylens.prod.conf`
- **Edge (HTTPS)**: `infra/nginx/edge/conf.d/10-https.conf`

All these configs use **host-specific `server_name`** directives and do **NOT** use:
- `server_name _;` (catch-all)
- `default_server` flag (unless explicitly for ApplyLens domains only)

## LedgerMind Domains

LedgerMind runs its **own nginx** container on the same host, listening on:

- **Host network**: `http://localhost:8083`
- **Docker network**: `http://ledgermind-web.int:80` (internal)

### Cloudflare Tunnel Configuration

Cloudflare Tunnel routes LedgerMind domains to the LedgerMind nginx:

- `app.ledger-mind.org` → `http://localhost:8083` (or `http://ledgermind-web.int:80`)
- `assistant.ledger-mind.org` → `http://localhost:8083`

This tunnel configuration is **managed outside** the ApplyLens repository:
- **Location**: On the infrastructure host's `cloudflared` configuration
- **Dashboard**: Cloudflare Zero Trust → Tunnels → `applylens` tunnel
- **Config file**: `/etc/cloudflared/config.yml` (or Cloudflare Dashboard ingress rules)

### ⚠️ CRITICAL WARNING

**Do NOT route `*.ledger-mind.org` to `applylens-nginx:80`** or the LedgerMind frontend will accidentally call ApplyLens APIs, causing:
- Authentication failures (different user databases)
- Data corruption (LedgerMind financial data mixed with ApplyLens job data)
- Feature breakage (different API contracts)

## Shared Cloudflare Tunnel

The `infra-cloudflared` container in `infra/docker-compose.yml` serves **multiple projects**:
- `applylens.app` (this repo)
- `siteagents.app` (separate project)
- `leoklemet.com` (portfolio)
- `ledger-mind.org`, `app.ledger-mind.org` (LedgerMind project)

The tunnel connector (cloudflared) is configured with ingress rules in the **Cloudflare Dashboard**, not in local YAML files.

### Network Requirements

The `infra-cloudflared` container **MUST** be on these networks:

```yaml
networks:
  - infra_net              # For ledgermind-web.int, siteagent-ui.int, etc.
  - applylens_applylens-prod  # For applylens-nginx:80, applylens-api-prod:8000
  - default                # For applylens-nginx in infra stack
```

## Debugging Checklist

### 1. Verify LedgerMind is Responding

```bash
# Test LedgerMind nginx directly on host
curl -s http://localhost:8083/api/ready
```

**Expected response**: LedgerMind JSON (finance agent metadata)

```json
{
  "status": "ready",
  "service": "ledgermind-api",
  "agent": "finance"
}
```

### 2. Verify ApplyLens is NOT Responding on LedgerMind Port

```bash
# This should NOT return ApplyLens data
curl -s http://localhost:8083/api/healthz
```

**Expected**: 404 or connection refused (if LedgerMind doesn't have `/api/healthz`)

### 3. Test Cloudflare Tunnel Routing

```bash
# Test public LedgerMind domain
curl -s https://app.ledger-mind.org/api/ready
```

**Expected**: Same JSON as localhost:8083 test above

**If you see ApplyLens responses**, Cloudflare is routing to the wrong nginx:
- Check Cloudflare Zero Trust → Tunnels → `applylens` → Public Hostnames
- Verify `app.ledger-mind.org` points to `http://localhost:8083` (or `http://ledgermind-web.int:80`)
- **NOT** to `http://applylens-nginx:80` or `http://applylens-web-prod:80`

### 4. Test ApplyLens Domains

```bash
# Test ApplyLens web
curl -s https://applylens.app/health
# Expected: "healthy" (or HTML from SPA)

# Test ApplyLens API
curl -s https://api.applylens.app/healthz
# Expected: {"status": "ok"} or ApplyLens API response
```

### 5. Test nginx Config Isolation

```bash
# Check ApplyLens nginx doesn't respond to LedgerMind domains
docker exec applylens-nginx nginx -T | grep server_name
```

**Expected output** (should ONLY contain):
```
server_name www.applylens.app;
server_name applylens.app;
server_name api.applylens.app;
```

**Should NOT contain**:
- `server_name _;` (catch-all)
- `server_name *.ledger-mind.org;`
- `server_name app.ledger-mind.org;`

## Common Issues

### Issue: app.ledger-mind.org returns ApplyLens UI

**Cause**: Cloudflare tunnel is routing to `applylens-nginx:80` instead of `localhost:8083`

**Fix**:
1. Go to Cloudflare Zero Trust → Tunnels → `applylens` tunnel
2. Find the public hostname for `app.ledger-mind.org`
3. Change the service URL from `http://applylens-nginx:80` to `http://localhost:8083`
4. Save and wait 30 seconds for propagation

### Issue: app.ledger-mind.org returns 502 Bad Gateway

**Cause**: LedgerMind nginx is not running or Cloudflare can't reach it

**Fix**:
```bash
# Check if LedgerMind containers are running
docker ps | grep ledger

# If not running, start them (in LedgerMind repo)
cd /path/to/ledgermind
docker-compose up -d

# Test locally
curl http://localhost:8083/api/ready
```

### Issue: ApplyLens nginx is responding to all hostnames

**Cause**: nginx config has `server_name _;` or `default_server` without specific hostname

**Fix**:
1. Edit `infra/nginx/dev.conf` or `infra/nginx/conf.d/applylens.prod.conf`
2. Remove any `server_name _;` or `default_server` directives
3. Ensure all server blocks have explicit `server_name applylens.app;` (or similar)
4. Reload nginx: `docker exec applylens-nginx nginx -s reload`
5. Or use the validation script: `./scripts/nginx-validate.ps1`

## Validation Script

Use the nginx validation script to safely test and reload configuration:

```powershell
# Test nginx config without reloading
.\scripts\nginx-validate.ps1

# Test and reload if valid
.\scripts\nginx-validate.ps1 -Reload
```

## Architecture Diagram

```
Internet
    │
    └─── Cloudflare Edge
            │
            ├─── applylens.app ──────────┐
            │                            │
            ├─── api.applylens.app ──────┤
            │                            ▼
            │                    applylens-nginx:80
            │                            │
            │                            ├─── applylens-web-prod:80
            │                            └─── applylens-api-prod:8003
            │
            └─── app.ledger-mind.org ────┐
                                         │
                                         ▼
                                localhost:8083 (LedgerMind nginx)
                                         │
                                         ├─── ledgermind-web.int:80
                                         └─── ledgermind-api.int:8000
```

## Related Documentation

- [ApplyLens Architecture](../APPLYLENS_ARCHITECTURE.md)
- [Deployment Guide](../DEPLOYMENT.md)
- [nginx Configuration Guide](../../infra/nginx/README.md)

## Summary

- **ApplyLens nginx**: Handles `applylens.app` and `api.applylens.app` ONLY
- **LedgerMind nginx**: Handles `*.ledger-mind.org` via `localhost:8083`
- **Cloudflare Tunnel**: Routes domains to the correct nginx based on hostname
- **No catch-all**: ApplyLens nginx must not use `server_name _;` or respond to non-ApplyLens domains
- **Validation**: Always test nginx config with the validation script before reloading in production
