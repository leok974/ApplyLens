# Deploy: Brand-Correct Cloudflare Tunnel Routes, Aliases, Environment & Smoke Tests

## Summary

This PR implements brand-correct configuration for the `applylens.app` domain, including:
- Docker network aliases for internal service routing
- Updated Cloudflare Tunnel configuration with proper hostnames
- Production environment variable templates
- Comprehensive smoke test script
- Detailed runbook for Cloudflare tunnel configuration

## Changes

### 1. Docker Network Aliases
**File**: `infra/docker-compose.yml`

Added internal DNS aliases for services to enable proper routing within the Docker network:
- `nginx` → `applylens.int` (main UI/reverse proxy)
- `api` → `applylens-api.int` (FastAPI backend)

These aliases allow the Cloudflare Tunnel to reference services by internal hostnames rather than service names.

### 2. Cloudflare Tunnel Configuration
**File**: `infra/cloudflared/config.yml`

Updated with brand-correct hostname mapping:
```yaml
ingress:
  - hostname: applylens.app
    service: http://applylens.int:80
  
  - hostname: www.applylens.app
    service: http://applylens.int:80
  
  - hostname: api.applylens.app
    service: http://applylens-api.int:8003
  
  - service: http_status:404
```

### 3. Production Environment Template
**File**: `infra/.env.prod.example` *(new)*

Added comprehensive production environment configuration:
```bash
# Brand-correct URLs
SITE_BASE_URL=https://applylens.app
PUBLIC_API_ORIGIN=https://api.applylens.app

# CORS Configuration
CORS_ALLOW_ORIGINS=https://applylens.app,https://www.applylens.app

# Cookie Settings
COOKIE_DOMAIN=.applylens.app
COOKIE_SECURE=1
COOKIE_SAMESITE=lax
```

### 4. Cloudflare Tunnel Runbook
**File**: `infra/docs/CLOUDFLARE_TUNNEL_RUNBOOK.md` *(new)*

Comprehensive guide including:
- Step-by-step hostname configuration
- Internal architecture diagrams
- Validation procedures
- Troubleshooting guide
- Security best practices

### 5. Smoke Test Script
**File**: `scripts/smoke-applylens.ps1` *(new)*

PowerShell smoke test script with 10 comprehensive tests:
- DNS resolution for all subdomains
- API health check (`/ready` endpoint)
- CORS preflight validation
- Main domain and WWW subdomain checks
- Static assets (`robots.txt`, `sitemap.xml`)
- API documentation endpoint
- Security headers verification
- SSL/TLS certificate validation

## Deployment Checklist

### Pre-Deployment
- [ ] Verify local environment with `docker compose up -d`
- [ ] Ensure service account credentials are in `infra/secrets/`
- [ ] Copy `.env.example` to `.env` and configure for local testing

### Cloudflare Dashboard Configuration
The tunnel configuration file is updated, but hostnames **must be configured manually in the Cloudflare Dashboard**:

1. **Login to Cloudflare Zero Trust**
   - Navigate to: https://one.dash.cloudflare.com/

2. **Configure Public Hostnames**
   - Go to: **Networks** → **Tunnels** → **applylens** (ID: `08d5feee-f504-47a2-a1f2-b86564900991`)
   - Click **Configure** or **Edit** → **Public Hostnames** tab

3. **Add/Update the following hostnames** (in order):
   
   #### a. Main Domain
   - Subdomain: *(empty)*
   - Domain: `applylens.app`
   - Service: **HTTP** → `applylens.int` → Port `80`
   - Cloudflare Proxy: ✅ **ON**
   
   #### b. WWW Subdomain
   - Subdomain: `www`
   - Domain: `applylens.app`
   - Service: **HTTP** → `applylens.int` → Port `80`
   - Cloudflare Proxy: ✅ **ON**
   
   #### c. API Subdomain
   - Subdomain: `api`
   - Domain: `applylens.app`
   - Service: **HTTP** → `applylens-api.int` → Port `8003`
   - Cloudflare Proxy: ✅ **ON**

4. **Verify Catch-All Rule**
   - Ensure there's a catch-all rule at the bottom with status `404`

### Post-Deployment Validation

1. **Check Tunnel Status**
   ```bash
   docker logs infra-cloudflared
   ```
   Expected: 4 active connections to Cloudflare edge

2. **Run Smoke Tests**
   ```powershell
   .\scripts\smoke-applylens.ps1
   ```
   Expected: All tests pass

3. **Manual Checks**
   - [ ] https://applylens.app/ loads correctly
   - [ ] https://www.applylens.app/ redirects or loads
   - [ ] https://api.applylens.app/ready returns 200
   - [ ] https://api.applylens.app/docs loads API documentation
   - [ ] CORS works from frontend to API

4. **Verify DNS Records in Cloudflare Dashboard**
   - Go to: **DNS** → **Records**
   - Confirm CNAME records for: `applylens.app`, `www`, `api`
   - All should point to: `<tunnel-id>.cfargotunnel.com` with **Proxied** status (🟠)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Cloudflare Edge Network                                     │
│  - applylens.app         → Tunnel → applylens.int:80        │
│  - www.applylens.app     → Tunnel → applylens.int:80        │
│  - api.applylens.app     → Tunnel → applylens-api.int:8003  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Docker Internal Network (infra_default)                     │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Nginx           │         │  API (FastAPI)    │         │
│  │  applylens.int   │         │  applylens-api.int│         │
│  │  Port: 80        │         │  Port: 8003       │         │
│  └──────────────────┘         └──────────────────┘         │
│         │                                                    │
│         ├─ /              → API (proxy)                     │
│         ├─ /docs/         → API /docs/ (proxy)              │
│         ├─ /web/          → Web UI (proxy)                  │
│         ├─ /grafana/      → Grafana (proxy)                 │
│         └─ /kibana/       → Kibana (proxy)                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Security Considerations

1. **Internal Aliases**: The `.int` domains are only accessible within Docker network
2. **Cloudflare Proxy**: All traffic goes through Cloudflare's edge (DDoS protection, WAF)
3. **Cookie Security**: Secure flag enabled, domain scoped to `.applylens.app`
4. **CORS**: Restrictive allowlist (only `applylens.app` and `www.applylens.app`)
5. **No Direct Exposure**: Tunnel only exposes Nginx reverse proxy, not individual services

## Testing Instructions

### Local Testing (Before Merge)
```bash
# 1. Pull the branch
git checkout deploy/applylens-brand-correct

# 2. Start services
cd infra
docker compose down
docker compose up -d

# 3. Check internal aliases
docker exec applylens-nginx ping -c 1 applylens.int
docker exec applylens-nginx ping -c 1 applylens-api.int

# 4. Verify tunnel logs
docker logs -f infra-cloudflared
```

### Production Testing (After Merge & Deploy)
```powershell
# Run comprehensive smoke tests
.\scripts\smoke-applylens.ps1

# Expected output: All tests pass
```

## Breaking Changes

None. This is a configuration enhancement that maintains backward compatibility.

## Documentation

- **Runbook**: `infra/docs/CLOUDFLARE_TUNNEL_RUNBOOK.md` - Complete guide for tunnel configuration
- **Environment**: `infra/.env.prod.example` - Production environment template
- **Smoke Tests**: `scripts/smoke-applylens.ps1` - Automated validation script

## Related Issues

- Implements brand-correct domain mapping for applylens.app
- Establishes internal service aliases for cleaner architecture
- Provides deployment validation toolkit

## Rollback Plan

If issues occur after deployment:

1. **Revert Cloudflare Dashboard Changes**:
   - Go to Cloudflare Zero Trust → Tunnels → applylens
   - Remove the hostname routes or revert to previous configuration

2. **Revert Code Changes**:
   ```bash
   git revert HEAD
   git push origin main
   ```

3. **Restart Services**:
   ```bash
   cd infra
   docker compose restart cloudflared nginx api
   ```

## Reviewers

Please verify:
- [ ] Docker network aliases are correctly configured
- [ ] Cloudflare tunnel config uses proper internal hostnames
- [ ] Environment variables follow security best practices
- [ ] Smoke test script covers all critical endpoints
- [ ] Runbook is comprehensive and actionable

---

**After merging, operator must manually configure hostnames in Cloudflare Dashboard as per the checklist above.**
