# LedgerMind Integration into ApplyLens Production Network

## Overview

This guide integrates LedgerMind (ai-finance-agent-oss-clean) into the ApplyLens production network, allowing both applications to share the same Cloudflare Tunnel while maintaining isolation.

**Status**: 🟡 In Progress
**Last Updated**: 2025-11-22

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Cloudflare Tunnel (08d5feee-f504-47a2-a1f2-b86564900991)│
│ Running in: applylens-cloudflared-prod                  │
└───────────────┬─────────────────────────────────────────┘
                │
    ┌───────────┴───────────┐
    │                       │
    ▼                       ▼
┌─────────────────┐   ┌──────────────────────┐
│ ApplyLens       │   │ LedgerMind           │
│ applylens.app   │   │ app.ledger-mind.org  │
│                 │   │                      │
│ web:80          │   │ nginx:80             │
│ api:8003        │   │ backend:8000         │
└─────────────────┘   └──────────────────────┘
        │                       │
        └───────────┬───────────┘
                    ▼
    ┌──────────────────────────────┐
    │ applylens_applylens-prod     │
    │ Docker Bridge Network        │
    │                              │
    │ Aliases:                     │
    │ - applylens-web-prod         │
    │ - applylens-api-prod         │
    │ - ai-finance.int             │
    │ - ai-finance-api.int         │
    └──────────────────────────────┘
```

---

## Step 1: Update LedgerMind docker-compose.prod.yml

**File**: `ai-finance-agent-oss-clean/docker-compose.prod.yml`

### 1a. Declare External Networks

Add the ApplyLens network to the networks section:

```yaml
networks:
  infra_net:
    external: true
  shared-ollama:
    external: true
  applylens_applylens-prod:
    external: true
```

### 1b. Attach nginx to ApplyLens Network

Update the nginx service:

```yaml
services:
  nginx:
    image: ledgermind-web:main-latest
    container_name: ledgermind-nginx-prod
    # ... existing config (ports, volumes, env)
    networks:
      - infra_net
      - shared-ollama
      - applylens_applylens-prod
    network_aliases:
      - ai-finance.int
    # ... rest of config
```

### 1c. Attach Backend to ApplyLens Network

Update the backend service:

```yaml
services:
  backend:
    image: ledgermind-backend:main-latest
    container_name: ledgermind-backend-prod
    # ... existing config
    networks:
      - infra_net
      - shared-ollama
      - applylens_applylens-prod
    network_aliases:
      - ai-finance-api.int
    # ... rest of config
```

### 1d. Redeploy LedgerMind

```bash
cd /path/to/ai-finance-agent-oss-clean

# Pull latest images (if using registry)
docker compose -f docker-compose.prod.yml pull nginx backend

# Redeploy
docker compose -f docker-compose.prod.yml up -d nginx backend

# Verify containers are running
docker ps --filter "name=ledgermind"
```

### 1e. Verify Network Connectivity

From ApplyLens network, test LedgerMind aliases:

```bash
# Test UI (nginx)
docker exec applylens-cloudflared-prod curl -I http://ai-finance.int/
docker exec applylens-cloudflared-prod curl -I http://ai-finance.int/assets/

# Test API (backend)
docker exec applylens-cloudflared-prod curl -I http://ai-finance-api.int:8000/ready
docker exec applylens-cloudflared-prod curl -I http://ai-finance-api.int:8000/health
```

**Expected**:
- All should return `200 OK`
- No `502 Bad Gateway` errors
- CSS files should have `Content-Type: text/css`

---

## Step 2: Update Cloudflare Tunnel Configuration

**File**: `d:\ApplyLens\infra\cloudflared\config.yml`

### 2a. Updated Configuration

The configuration has been updated to include LedgerMind routes:

```yaml
tunnel: 08d5feee-f504-47a2-a1f2-b86564900991
credentials-file: /etc/cloudflared/08d5feee-f504-47a2-a1f2-b86564900991.json

originRequest:
  connectTimeout: 30s
  tlsTimeout: 10s
  tcpKeepAlive: 30s
  noHappyEyeballs: false
  keepAliveConnections: 100
  keepAliveTimeout: 90s

ingress:
  # LedgerMind UI
  - hostname: app.ledger-mind.org
    service: http://ai-finance.int:80
  - hostname: ledger-mind.org
    service: http://ai-finance.int:80
  - hostname: www.ledger-mind.org
    service: http://ai-finance.int:80

  # LedgerMind API (direct access)
  - hostname: api.ledger-mind.org
    service: http://ai-finance-api.int:8000

  # ApplyLens UI
  - hostname: applylens.app
    service: http://applylens-web-prod:80
  - hostname: www.applylens.app
    service: http://applylens-web-prod:80

  # ApplyLens API
  - hostname: api.applylens.app
    service: http://applylens-api-prod:8003

  # Fallback
  - service: http_status:404
```

### 2b. Restart Cloudflare Tunnel

```bash
docker restart applylens-cloudflared-prod

# Wait a few seconds for tunnel to reconnect
sleep 5

# Verify tunnel is healthy
docker logs applylens-cloudflared-prod --tail 20
```

**Expected logs**:
```
INF Connection <UUID> registered connIndex=0 location=XXX
INF Connection <UUID> registered connIndex=1 location=XXX
INF Updated to new configuration config=...
```

---

## Step 3: DNS Configuration

### Required DNS Records

Configure these in Cloudflare DNS for `ledger-mind.org`:

| Type  | Name | Content | Proxy Status | TTL |
|-------|------|---------|--------------|-----|
| CNAME | @ | 08d5feee-f504-47a2-a1f2-b86564900991.cfargotunnel.com | Proxied | Auto |
| CNAME | www | 08d5feee-f504-47a2-a1f2-b86564900991.cfargotunnel.com | Proxied | Auto |
| CNAME | app | 08d5feee-f504-47a2-a1f2-b86564900991.cfargotunnel.com | Proxied | Auto |
| CNAME | api | 08d5feee-f504-47a2-a1f2-b86564900991.cfargotunnel.com | Proxied | Auto |

### Verification Commands

```bash
# Check DNS resolution
nslookup app.ledger-mind.org
nslookup api.ledger-mind.org

# Check CNAME records
dig app.ledger-mind.org CNAME +short
dig api.ledger-mind.org CNAME +short
```

---

## Step 4: End-to-End Verification

### 4a. UI Tests

```bash
# Test homepage
curl -I https://app.ledger-mind.org/
curl -I https://ledger-mind.org/
curl -I https://www.ledger-mind.org/

# Test assets (CSS, JS)
curl -I https://app.ledger-mind.org/assets/chatSession-DkF0Itkc.css
curl -I https://app.ledger-mind.org/assets/index-BwZ8a4YG.js

# Verify Content-Type headers
curl -I https://app.ledger-mind.org/assets/chatSession-DkF0Itkc.css | grep "Content-Type"
```

**Expected**:
- Status: `200 OK`
- Content-Type: `text/css` for CSS files
- Content-Type: `application/javascript` for JS files
- No `502 Bad Gateway` errors

### 4b. API Tests

```bash
# Test health endpoints
curl https://app.ledger-mind.org/api/ready
curl https://app.ledger-mind.org/api/health

# Test direct API hostname (if configured)
curl https://api.ledger-mind.org/ready
curl https://api.ledger-mind.org/health
```

**Expected**:
- Status: `200 OK`
- Content-Type: `application/json`
- Response body: `{"status":"ok"}` or similar

### 4c. Browser Testing

1. Open https://app.ledger-mind.org/
2. Open browser DevTools (F12) → Network tab
3. Reload page (Ctrl+R)
4. Verify:
   - All assets load with `200 OK`
   - No `502` errors in console
   - CSS and JS files load correctly
   - Application renders properly

---

## Troubleshooting

### Issue: 502 Bad Gateway on Assets

**Symptoms**:
```
curl -I https://app.ledger-mind.org/assets/style.css
HTTP/2 502
```

**Causes**:
1. LedgerMind nginx not on ApplyLens network
2. Incorrect network alias
3. Cloudflare tunnel not restarted

**Fix**:
```bash
# Verify network membership
docker inspect ledgermind-nginx-prod \
  --format '{{range $net, $config := .NetworkSettings.Networks}}{{$net}} {{end}}'

# Should include: applylens_applylens-prod

# Verify alias
docker inspect ledgermind-nginx-prod \
  --format '{{json .NetworkSettings.Networks}}' | jq

# Should show alias: ai-finance.int

# Test from tunnel
docker exec applylens-cloudflared-prod curl -I http://ai-finance.int/assets/style.css
```

### Issue: DNS Not Resolving

**Symptoms**:
```
curl https://app.ledger-mind.org/
curl: (6) Could not resolve host: app.ledger-mind.org
```

**Causes**:
1. DNS records not created
2. Records not proxied
3. DNS propagation delay

**Fix**:
```bash
# Check DNS with Cloudflare nameservers
dig @1.1.1.1 app.ledger-mind.org

# Verify CNAME points to tunnel
dig app.ledger-mind.org CNAME +short
# Should show: 08d5feee-f504-47a2-a1f2-b86564900991.cfargotunnel.com
```

### Issue: Tunnel Not Routing

**Symptoms**:
- DNS resolves
- Cloudflare returns 502/503
- Tunnel logs show errors

**Causes**:
1. config.yml not reloaded
2. Service name typo
3. Network connectivity issue

**Fix**:
```bash
# Check tunnel config loaded
docker exec applylens-cloudflared-prod cat /etc/cloudflared/config.yml

# Check tunnel logs
docker logs applylens-cloudflared-prod -f

# Restart tunnel
docker restart applylens-cloudflared-prod

# Force config reload
docker exec applylens-cloudflared-prod kill -HUP 1
```

---

## Rollback Procedure

If issues arise, revert to ApplyLens-only configuration:

### 1. Restore config.yml

```yaml
ingress:
  - hostname: applylens.app
    service: http://applylens-web-prod:80
  - hostname: www.applylens.app
    service: http://applylens-web-prod:80
  - hostname: api.applylens.app
    service: http://applylens-api-prod:8003
  - service: http_status:404
```

### 2. Restart tunnel

```bash
docker restart applylens-cloudflared-prod
```

### 3. Detach LedgerMind from network

```bash
cd /path/to/ai-finance-agent-oss-clean

# Edit docker-compose.prod.yml - remove applylens_applylens-prod from networks
# Then redeploy
docker compose -f docker-compose.prod.yml up -d nginx backend
```

---

## Monitoring

### Cloudflare Tunnel Metrics

**Check tunnel health**:
```bash
# View active connections
docker logs applylens-cloudflared-prod | grep "Connection.*registered"

# Monitor traffic
docker stats applylens-cloudflared-prod
```

### Application Metrics

**Prometheus Queries**:
```promql
# HTTP requests by hostname
http_requests_total{hostname=~".*ledger-mind.org"}

# Response times
histogram_quantile(0.95, http_request_duration_seconds{hostname=~".*ledger-mind.org"})

# Error rate
rate(http_requests_total{hostname=~".*ledger-mind.org",status=~"5.."}[5m])
```

---

## Security Considerations

### Network Isolation

- ✅ LedgerMind and ApplyLens share network but use different aliases
- ✅ No direct port exposure (all traffic via tunnel)
- ✅ Cloudflare Zero Trust policies can be applied per hostname

### Recommended Cloudflare Policies

1. **Access Control**: Require authentication for sensitive endpoints
2. **Rate Limiting**: Prevent abuse of API endpoints
3. **WAF Rules**: Block malicious traffic patterns
4. **DDoS Protection**: Automatic mitigation enabled

---

## Next Steps

1. ✅ Update LedgerMind docker-compose.prod.yml
2. ✅ Update cloudflared config.yml (DONE)
3. ⏳ Configure DNS records in Cloudflare
4. ⏳ Redeploy LedgerMind stack
5. ⏳ Restart Cloudflare tunnel
6. ⏳ End-to-end testing
7. ⏳ Monitor for 24 hours
8. ⏳ Document any issues/fixes

---

**Last Updated**: 2025-11-22
**Owner**: Infrastructure Team
**Status**: 🟡 Configuration Updated, Awaiting Deployment
