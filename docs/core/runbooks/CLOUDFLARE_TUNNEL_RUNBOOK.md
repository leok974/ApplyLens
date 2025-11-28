# Cloudflare Tunnel Configuration Runbook

## Brand-Correct Hostname Mapping for applylens.app

This document provides the exact hostnames and routes to configure in the Cloudflare dashboard for the ApplyLens Named Tunnel.

### Tunnel Information

- **Tunnel Name**: `applylens`
- **Tunnel ID**: `08d5feee-f504-47a2-a1f2-b86564900991`
- **Network**: Internal Docker aliases via `applylens.int` and `applylens-api.int`

---

## Hostname Routes (Configure in Cloudflare Dashboard)

Navigate to: **Cloudflare Zero Trust Dashboard** → **Networks** → **Tunnels** → **applylens** → **Public Hostnames**

### 1. Main Domain - applylens.app

- **Hostname**: `applylens.app`
- **Service Type**: `HTTP`
- **URL**: `http://applylens.int:80`
- **Cloudflare Proxy**: ✅ **ON** (Proxied)
- **Description**: Routes main domain traffic through Nginx reverse proxy for path-based routing

### 2. WWW Subdomain - <www.applylens.app>

**Option A - CNAME (Recommended)**:

- **Hostname**: `www.applylens.app`
- **Service Type**: `CNAME`
- **Target**: `applylens.app`
- **Cloudflare Proxy**: ✅ **ON** (Proxied)

**Option B - Direct Tunnel Route**:

- **Hostname**: `www.applylens.app`
- **Service Type**: `HTTP`
- **URL**: `http://applylens.int:80`
- **Cloudflare Proxy**: ✅ **ON** (Proxied)

### 3. API Subdomain - api.applylens.app

- **Hostname**: `api.applylens.app`
- **Service Type**: `HTTP`
- **URL**: `http://applylens-api.int:8000`
- **Cloudflare Proxy**: ✅ **ON** (Proxied)
- **Description**: Direct route to FastAPI backend on port 8000

### 4. Catch-All Rule (Required, Must Be Last)

- **Service Type**: `HTTP Status`
- **Status Code**: `404`
- **Description**: Returns 404 for any unmatched hostnames

---

## Internal Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│ Cloudflare Edge Network                                     │
│  - applylens.app         → Tunnel → applylens.int:80        │
│  - www.applylens.app     → Tunnel → applylens.int:80        │
│  - api.applylens.app     → Tunnel → applylens-api.int:8000  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Docker Internal Network (infra_default)                     │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Nginx           │         │  API (FastAPI)    │         │
│  │  applylens.int   │         │  applylens-api.int│         │
│  │  Port: 80        │         │  Port: 8000       │         │
│  └──────────────────┘         └──────────────────┘         │
│         │                                                    │
│         ├─ /              → API (proxy)                     │
│         ├─ /docs/         → API /docs/ (proxy)              │
│         ├─ /web/          → Web UI (proxy)                  │
│         ├─ /grafana/      → Grafana (proxy)                 │
│         ├─ /kibana/       → Kibana (proxy)                  │
│         └─ /prometheus/   → Prometheus (proxy)              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```text

---

## Configuration Steps

### Step 1: Update config.yml (Already Done)

The tunnel configuration file at `infra/cloudflared/config.yml` has been updated with the correct routes.

### Step 2: Configure Public Hostnames in Dashboard

1. **Login to Cloudflare Zero Trust Dashboard**:
   - Go to: <https://one.dash.cloudflare.com/>

2. **Navigate to Tunnel Configuration**:
   - Select your account
   - Go to **Networks** → **Tunnels**
   - Find tunnel: **applylens** (ID: `08d5feee-f504-47a2-a1f2-b86564900991`)
   - Click **Configure** or **Edit**

3. **Add/Update Public Hostnames** (in this order):

   a. **applylens.app**:
      - Click **Add a public hostname**
      - Subdomain: (leave empty)
      - Domain: `applylens.app`
      - Service: `HTTP` → `applylens.int` → Port `80`
      - Enable **Cloudflare Proxy**
      - Save

   b. **<www.applylens.app>**:
      - Click **Add a public hostname**
      - Subdomain: `www`
      - Domain: `applylens.app`
      - Service: `HTTP` → `applylens.int` → Port `80`
      - Enable **Cloudflare Proxy**
      - Save

   c. **api.applylens.app**:
      - Click **Add a public hostname**
      - Subdomain: `api`
      - Domain: `applylens.app`
      - Service: `HTTP` → `applylens-api.int` → Port `8000`
      - Enable **Cloudflare Proxy**
      - Save

4. **Verify Catch-All Rule Exists**:
   - Should see a catch-all rule with `404` status at the bottom
   - If not present, add it manually

### Step 3: Verify DNS Records

After configuring the tunnel, Cloudflare automatically creates/updates DNS records:

- `applylens.app` → CNAME to `<tunnel-id>.cfargotunnel.com` (Proxied ☁️)
- `www.applylens.app` → CNAME to `<tunnel-id>.cfargotunnel.com` (Proxied ☁️)
- `api.applylens.app` → CNAME to `<tunnel-id>.cfargotunnel.com` (Proxied ☁️)

Check in: **Cloudflare Dashboard** → **DNS** → **Records**

---

## Validation

### 1. Check Tunnel Status

```bash
# Inside the cloudflared container
docker exec infra-cloudflared cloudflared tunnel info applylens
```text

Expected output should show 4 active connections to Cloudflare edge.

### 2. Test Internal Aliases

```bash
# From inside the Docker network
docker exec applylens-nginx ping -c 1 applylens.int
docker exec applylens-nginx ping -c 1 applylens-api.int
```text

### 3. Test External Access

```powershell
# Run the smoke test script
.\scripts\smoke-applylens.ps1
```text

Or manually:

```powershell
# DNS resolution
Resolve-DnsName applylens.app
Resolve-DnsName api.applylens.app

# Health checks
curl https://applylens.app/healthz
curl https://api.applylens.app/ready

# CORS preflight
curl -I https://api.applylens.app/emails `
  -H "Origin: https://applylens.app" `
  -H "Access-Control-Request-Method: POST"
```text

---

## Troubleshooting

### Tunnel Not Connecting

```bash
# Check tunnel logs
docker logs infra-cloudflared

# Restart tunnel
docker compose -f infra/docker-compose.yml restart cloudflared
```text

### 404 Errors

- Verify the hostname is configured in the dashboard
- Check that internal aliases resolve: `docker exec applylens-nginx nslookup applylens.int`
- Verify Nginx is running: `docker ps | grep nginx`

### CORS Errors

- Check `CORS_ALLOW_ORIGINS` environment variable in `.env`
- Should include: `https://applylens.app,https://www.applylens.app`
- Restart API: `docker compose restart api`

### SSL Certificate Issues

- Cloudflare proxy automatically handles SSL
- Ensure **Proxy status** is **ON** (orange cloud) for all DNS records
- Check SSL/TLS mode is **Full** or **Full (strict)** in Cloudflare SSL/TLS settings

---

## Security Notes

1. **Internal Routes Only**: The Docker aliases (`.int` domains) are only accessible within the Docker network
2. **Cloudflare Proxy**: All public traffic goes through Cloudflare's edge network
3. **No Direct Exposure**: The tunnel only exposes the Nginx reverse proxy, not individual services
4. **Rate Limiting**: Consider enabling Cloudflare Rate Limiting rules for production
5. **WAF**: Enable Cloudflare Web Application Firewall for additional protection

---

## Maintenance

### Updating Routes

1. Modify `infra/cloudflared/config.yml`
2. Update hostnames in Cloudflare dashboard
3. Restart tunnel: `docker compose restart cloudflared`
4. Wait 1-2 minutes for changes to propagate

### Monitoring

- Check Cloudflare Analytics for traffic patterns
- Monitor tunnel health in Cloudflare Zero Trust Dashboard
- Check Docker logs: `docker logs -f infra-cloudflared`

---

## Related Documentation

- [Cloudflare Tunnel Quick Start](./CLOUDFLARE_TUNNEL_QUICKSTART.md)
- [Nginx Configuration](./nginx/README.md)
- [Environment Variables](./.env.example)
