# ApplyLens Cloudflare Tunnel Runbook

## Overview

This document describes the production Cloudflare Tunnel configuration for ApplyLens.

## Tunnel Configuration

### Tunnel Identity
- **Name**: `applylens`
- **Tunnel ID**: `08d5feee-f504-47a2-a1f2-b86564900991`
- **Management**: Token-based (using `TUNNEL_TOKEN` environment variable)
- **Configuration**: Remote configuration via Cloudflare Zero Trust Dashboard

### High Availability Connectors

The tunnel uses **2 active connectors** for high availability:

| Connector | Container Name | Networks | Status |
|-----------|---------------|----------|--------|
| Connector A | `cfd-a` | `infra_net`, `applylens_applylens-prod` | Active |
| Connector B | `cfd-b` | `infra_net`, `applylens_applylens-prod` | Active |

**Location**: Defined in `d:\ApplyLens\docker-compose.tunnel.yml`

### Network Requirements

⚠️ **CRITICAL**: Both connectors MUST be on both networks:
- `infra_net` - For general infrastructure services
- `applylens_applylens-prod` - To reach ApplyLens production containers

**Why**: The connectors need to resolve and connect to:
- `applylens-web-prod` (on `applylens_applylens-prod` network)
- `applylens-api-prod` (on both networks)

### Public Hostname Routes

| Hostname | Target Service | Purpose |
|----------|---------------|---------|
| `applylens.app` | `http://applylens-web-prod:80` | Main web application |
| `www.applylens.app` | `http://applylens-web-prod:80` | WWW redirect |
| `api.applylens.app` | `http://applylens-api-prod:8000` | API backend |

## Docker Compose Configuration

```yaml
# docker-compose.tunnel.yml
services:
  cfd-a:
    image: cloudflare/cloudflared:latest
    container_name: cfd-a
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARED_TUNNEL_TOKEN}
    networks:
      - infra_net
      - applylens_applylens-prod
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
      - applylens_applylens-prod
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pgrep cloudflared || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3

networks:
  infra_net:
    external: true
  applylens_applylens-prod:
    external: true
```

## Common Operations

### Check Connector Status

```powershell
# List all cloudflared connectors
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | Select-String cloudflared

# Check specific connector logs
docker logs cfd-a --tail 50 --follow
docker logs cfd-b --tail 50 --follow

# Verify network connectivity
docker inspect cfd-a --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'
```

### Restart Connectors

```powershell
# Restart both connectors
cd d:\ApplyLens
docker-compose -f docker-compose.tunnel.yml restart

# Or recreate with latest config
docker-compose -f docker-compose.tunnel.yml up -d --force-recreate
```

### Test Production Access

```powershell
# Quick smoke test
curl -I https://applylens.app/ -H "Cache-Control: no-cache"
curl -I https://applylens.app/api/auth/me -H "Cache-Control: no-cache"

# Use the automated smoke test script
.\scripts\check-applylens-prod.ps1
```

## Troubleshooting

### Issue: 502 Bad Gateway

**Symptoms**: `https://applylens.app/` returns 502

**Common Causes**:
1. Connectors not on `applylens_applylens-prod` network
2. Multiple conflicting connectors running
3. Target containers (`applylens-web-prod`, `applylens-api-prod`) not running

**Diagnosis**:
```powershell
# 1. Check connector logs for DNS resolution errors
docker logs cfd-a --since 5m | Select-String "ERR|error|502"
docker logs cfd-b --since 5m | Select-String "ERR|error|502"

# Look for: "dial tcp: lookup applylens-web-prod ... no such host"
# This means connector can't resolve the target container (wrong network)

# 2. Verify networks
docker inspect cfd-a --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'
# Should show: applylens_applylens-prod infra_net

# 3. Test origin directly (bypass Cloudflare)
curl http://localhost:5175/  # Direct to applylens-web-prod

# 4. Check target containers running
docker ps | Select-String "applylens-web-prod|applylens-api-prod"
```

**Resolution**:
```powershell
# Add missing network to connectors
cd d:\ApplyLens
# Edit docker-compose.tunnel.yml to include both networks
docker-compose -f docker-compose.tunnel.yml up -d --force-recreate

# Wait 15 seconds for connectors to stabilize
Start-Sleep -Seconds 15
curl -I https://applylens.app/
```

### Issue: Unhealthy Connectors

**Symptoms**: `docker ps` shows connectors as "unhealthy"

**Cause**: Health check tries to run `/bin/sh` which doesn't exist in minimal cloudflared image

**Impact**: Cosmetic only - connectors still function normally

**Note**: This is expected behavior. The connectors use a minimal Alpine-based image without shell utilities.

### Issue: Multiple Connectors Conflict

**Symptoms**: Intermittent 502 errors, inconsistent behavior

**Diagnosis**:
```powershell
# Find all cloudflared containers
docker ps -a | Select-String cloudflared

# Check Cloudflare Dashboard
# Zero Trust → Networks → Tunnels → applylens → Connectors
# Should see only 2 active connectors
```

**Resolution**:
```powershell
# Stop duplicate/dev connectors
docker stop infra-cloudflared  # Old redundant connector
docker stop ai-finance-agent-oss-clean-cloudflared-1  # Dev connector

# Keep only cfd-a and cfd-b running
```

## Security & Isolation Rules

### ⚠️ CRITICAL RULE: No Dev Project Reuse

**Rule**: Development projects MUST NOT reuse the production `applylens` tunnel.

**Why**:
- Prevents dev containers from interfering with production routing
- Avoids DNS resolution conflicts
- Maintains clear separation of concerns

**For Dev Projects**:
1. Create a separate named tunnel for development
2. Use different tunnel tokens
3. Configure separate public hostnames (e.g., `dev.applylens.app`)

Example:
```powershell
# Create dev tunnel
cloudflared tunnel create applylens-dev

# Get dev tunnel token
cloudflared tunnel token applylens-dev

# Use in docker-compose.dev.yml with TUNNEL_TOKEN_DEV
```

## Monitoring

### Health Checks

The connectors include a basic health check that verifies the `cloudflared` process is running:

```yaml
healthcheck:
  test: ["CMD-SHELL", "pgrep cloudflared || exit 1"]
  interval: 30s
  timeout: 5s
  retries: 3
```

### Cloudflare Dashboard

**Live Monitoring**: https://one.dash.cloudflare.com/

Navigate to: **Zero Trust → Networks → Tunnels → applylens**

Monitor:
- Connector status (should show 2 healthy connectors)
- Request logs (recent traffic)
- Error rates
- Latency metrics

### Log Analysis

```powershell
# Recent errors
docker logs cfd-a --since 10m | Select-String "ERR|error"
docker logs cfd-b --since 10m | Select-String "ERR|error"

# Request volume (applylens.app traffic)
docker logs cfd-a --since 1h | Select-String "applylens.app" | Measure-Object
docker logs cfd-b --since 1h | Select-String "applylens.app" | Measure-Object

# DNS resolution failures
docker logs cfd-a --since 1h | Select-String "no such host"
```

## Maintenance

### Updating Connectors

```powershell
# Pull latest cloudflared image
docker pull cloudflare/cloudflared:latest

# Recreate connectors with new image
cd d:\ApplyLens
docker-compose -f docker-compose.tunnel.yml pull
docker-compose -f docker-compose.tunnel.yml up -d --force-recreate

# Verify
docker ps | Select-String cloudflared
curl -I https://applylens.app/
```

### Backup Configuration

The tunnel configuration is stored in:
- `docker-compose.tunnel.yml` - Connector definitions
- Environment variable `CLOUDFLARED_TUNNEL_TOKEN` - Authentication token
- Cloudflare Dashboard - Remote configuration (ingress rules)

**Backup steps**:
1. Save `docker-compose.tunnel.yml` to version control ✅
2. Store `CLOUDFLARED_TUNNEL_TOKEN` in secure password manager
3. Document public hostname routes (this file)

## Related Documentation

- [Cloudflare Tunnel Setup Guide](./CLOUDFLARE_TUNNEL_QUICKSTART.md)
- [Production Infrastructure Overview](./PROD_INFRA_OVERVIEW.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)

## Quick Reference

```powershell
# Status check
docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "cfd-"

# Restart connectors
cd d:\ApplyLens && docker-compose -f docker-compose.tunnel.yml restart

# View logs
docker logs cfd-a --tail 50 -f

# Smoke test
.\scripts\check-applylens-prod.ps1

# Emergency: Stop all cloudflared
docker ps | Select-String cloudflared | ForEach-Object { docker stop ($_ -split '\s+')[0] }
```

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-11-18 | Fixed 502 issue by adding `applylens_applylens-prod` network to connectors | System |
| 2025-11-18 | Removed redundant `infra-cloudflared` connector | System |
| 2025-11-18 | Created initial runbook documentation | System |
