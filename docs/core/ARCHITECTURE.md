# ApplyLens Architecture

## Service Overview

ApplyLens runs as a set of Docker containers orchestrated with Docker Compose, exposed to the internet via Cloudflare Tunnel.

### Core Services

```
┌─────────────────────────────────────────────────────────────────┐
│                        Cloudflare Edge                          │
│                  (applylens.app, api.applylens.app)            │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Cloudflare Tunnel  │
                    │ (infra-cloudflared)│
                    └─────────┬──────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌──────▼──────┐
│ applylens-web  │   │ applylens-api   │   │   nginx     │
│   (React/Vite) │   │    (FastAPI)    │   │  (reverse   │
│   Port: 80     │   │   Port: 8000    │   │   proxy)    │
│   Maps: 5175   │   │   Maps: 8003    │   │  Port: 80   │
└───────┬────────┘   └────────┬────────┘   └──────┬──────┘
        │                     │                    │
        │            ┌────────┴────────┐           │
        │            │                 │           │
   ┌────▼────┐  ┌────▼────┐      ┌────▼────┐ ┌────▼────┐
   │   ES    │  │   DB    │      │  Redis  │ │  Other  │
   │ (9200)  │  │ (5432)  │      │ (6379)  │ │ Services│
   └─────────┘  └─────────┘      └─────────┘ └─────────┘
```

### Service Details

#### applylens-web-prod
- **Image**: `leoklemet/applylens-web:latest`
- **Port Mapping**: `5175:80`
- **Role**: Serves React SPA + proxies `/api/*` to backend
- **nginx Config**: `/etc/nginx/conf.d/default.conf`
- **Key Routes**:
  - `/` → SPA (index.html)
  - `/extension` → Extension pages
  - `/profile` → User profile
  - `/api/*` → Proxy to `applylens-api-prod:8000`

#### applylens-api-prod
- **Image**: `leoklemet/applylens-api:0.6.0-phase6`
- **Port Mapping**: `8003:8000`
- **Role**: FastAPI backend (auth, search, extensions, AI)
- **Dependencies**: Elasticsearch, PostgreSQL, Redis
- **Key Endpoints**:
  - `/api/auth/*` → OAuth, session management
  - `/api/search` → Email search
  - `/api/extension/*` → Extension endpoints
  - `/api/chat` → AI chat interface
  - `/docs` → OpenAPI documentation

#### es (Elasticsearch)
- **Image**: `elasticsearch:8.16.1`
- **Port**: `9200`
- **Role**: Email indexing and full-text search
- **Indexes**: `gmail_emails`, `applications`

#### db (PostgreSQL)
- **Image**: `postgres:17-alpine`
- **Port**: `5432`
- **Role**: Relational data (users, sessions, applications)

#### redis
- **Image**: `redis:7-alpine`
- **Port**: `6379`
- **Role**: Session storage, rate limiting

#### infra-cloudflared (Cloudflare Tunnel)
- **Image**: `cloudflare/cloudflared:latest`
- **Tunnel ID**: `08d5feee-f504-47a2-a1f2-b86564900991`
- **Role**: Zero-trust tunnel to expose services
- **Networks**: `infra_net`, `applylens_applylens-prod`

## Domain Mapping

### Production Hostnames

| Domain | Tunnel Route | Container | Port | Purpose |
|--------|-------------|-----------|------|---------|
| `applylens.app` | `http://applylens-web-prod:80` | applylens-web-prod | 80 | Main web app |
| `www.applylens.app` | `http://applylens-web-prod:80` | applylens-web-prod | 80 | WWW redirect |
| `api.applylens.app` | `http://applylens-api-prod:8000` | applylens-api-prod | 8000 | Direct API access |

**Note**: Cloudflare tunnel configuration is managed via the Cloudflare Zero Trust Dashboard, not local config files.

### Routing Architecture

#### Option 1: Main Domain (`applylens.app`)
```
Browser → Cloudflare Edge → Cloudflare Tunnel → applylens-web-prod:80
                                                          ↓
                                                  nginx proxies /api/*
                                                          ↓
                                              applylens-api-prod:8000
```

#### Option 2: API Subdomain (`api.applylens.app`)
```
Browser → Cloudflare Edge → Cloudflare Tunnel → applylens-api-prod:8000
```

**Why both?**
- Main domain provides SPA routing and API proxy in one container
- API subdomain allows direct backend access (no nginx hop)
- Extensions use `api.applylens.app` for cleaner architecture

## Docker Networks

### applylens_applylens-prod
- **Services**: web, api, db, es, redis
- **Purpose**: Production service mesh

### infra_default (also infra_net)
- **Services**: nginx, cloudflared, other infrastructure
- **Purpose**: Reverse proxy and tunnel services

### Network Connections
- `cloudflared` connects to **both** networks:
  - `infra_net` for nginx access
  - `applylens_applylens-prod` for direct container access

## Authentication Flow

### Google OAuth (Primary)

```
1. User clicks "Sign In with Google"
   ↓
2. Frontend redirects to /api/auth/google/login
   ↓
3. Backend redirects to accounts.google.com/o/oauth2/v2/auth
   ↓
4. User authorizes, Google redirects to /api/auth/google/callback
   ↓
5. Backend validates, creates session, redirects to /
   ↓
6. Frontend loads, calls /api/auth/me
   ↓
7. Backend returns user { id, email } with session cookie
```

### Session Management

- **Session Cookie**: `session=<jwt-signed-payload>`
- **CSRF Protection**: `/api/auth/csrf` returns CSRF token
- **Validation**: Every API call checks session cookie
- **Storage**: Redis (server-side sessions)

### Key Auth Endpoints

| Endpoint | Method | Purpose | Returns |
|----------|--------|---------|---------|
| `/api/auth/google/login` | GET | Start OAuth flow | 307 redirect to Google |
| `/api/auth/google/callback` | GET | OAuth callback | 307 redirect to app |
| `/api/auth/me` | GET | Get current user | `{ id, email }` or 401 |
| `/api/auth/csrf` | GET | Get CSRF token | `{ csrfToken }` |
| `/api/auth/logout` | POST | End session | 200 OK |

### Auth in Different Contexts

#### Web App (`applylens.app`)
- Uses `/api/auth/*` (proxied through nginx)
- Session cookie domain: `.applylens.app`
- LoginGuard component checks `/api/auth/me` on mount

#### Extension (`chrome-extension://`)
- Uses `api.applylens.app/auth/*` (direct)
- CORS enabled for extension origin
- No session cookies (uses API keys in future)

#### Dev Mode (localhost)
- Auth bypass available via `VITE_BYPASS_AUTH=true`
- Mock user: `{ id: "dev-user-local", email: "dev@localhost" }`
- Only works in Vite dev server

## nginx Configuration

### Web Container (`applylens-web-prod`)

Located at: `/etc/nginx/conf.d/default.conf`

Key location blocks:

```nginx
# SPA routing for extension pages
location = /extension {
    try_files /index.html =404;
}

location /extension/ {
    try_files $uri $uri/ /index.html;
}

# API proxy (NO auth stubs!)
location ^~ /api/ {
    proxy_pass http://applylens-api-prod:8000/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Static assets with caching
location ~* ^/assets/.*\.(js|css|woff|woff2|ttf|eot|otf)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# SPA fallback
location / {
    try_files $uri $uri/ /index.html;
}
```

**Important**: No `location = /api/auth/me` stub! All `/api/*` requests proxy to backend.

### Infrastructure nginx (`applylens-nginx`)

Located at: `infra/nginx/dev.conf`

**Note**: This nginx is NOT in the ApplyLens request path anymore. It serves other services:
- SiteAgent
- LedgerMind
- Portfolio site

ApplyLens traffic goes **directly** from Cloudflare Tunnel to containers.

## Environment Variables

### Backend (`applylens-api-prod`)

Key environment variables:

```bash
# Base URL for OAuth redirects
APPLYLENS_BASE_URL=https://applylens.app

# OAuth configuration
OAUTH_REDIRECT_URI=https://applylens.app/api/auth/google/callback
GOOGLE_OAUTH_SCOPES=openid email profile https://www.googleapis.com/auth/gmail.readonly

# CORS origins
CORS_ALLOW_ORIGINS=https://applylens.app,https://www.applylens.app

# Database
DATABASE_URL=postgresql://postgres:***@db:5432/applylens

# Feature flags
COMPANION_BANDIT_ENABLED=true
APPLYLENS_DEV=false
```

### Frontend (`applylens-web-prod`)

Build-time environment variables (embedded in JS bundle):

```bash
# Development mode
VITE_DEV=false

# Auth bypass (dev only)
VITE_BYPASS_AUTH=false

# Feature flags
VITE_FEATURE_COMPANION=true
```

## Health Checks & Monitoring

### Service Health Endpoints

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| API | `/ready` | `{"status":"ready","db":"ok","es":"ok"}` |
| Web | `/` | 200 OK (HTML) |
| Elasticsearch | `/_cluster/health` | `{"status":"green"}` |

### Prometheus Metrics

- **API metrics**: `http://localhost:8003/metrics`
- **Prometheus UI**: `http://applylens.app:9090`
- **Grafana**: `http://applylens.app:3001`

### Key Metrics to Monitor

- `autofill_policy_total` - Bandit policy decisions
- `http_requests_total` - API request count
- `http_request_duration_seconds` - API latency
- `elasticsearch_query_duration_seconds` - Search performance

## Deployment Workflow

### 1. Build Web Image

```bash
cd apps/web
docker build -f Dockerfile.prod -t leoklemet/applylens-web:0.5.1 .
docker push leoklemet/applylens-web:0.5.1
docker tag leoklemet/applylens-web:0.5.1 leoklemet/applylens-web:latest
docker push leoklemet/applylens-web:latest
```

### 2. Build API Image

```bash
cd services/api
docker build -t leoklemet/applylens-api:0.6.0-phase6 .
docker push leoklemet/applylens-api:0.6.0-phase6
```

### 3. Deploy to Production

```bash
cd infra
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### 4. Verify Deployment

```bash
# Check services
docker ps --filter "name=applylens"

# Test endpoints
curl https://applylens.app/
curl https://api.applylens.app/ready

# Check logs
docker logs applylens-web-prod --tail 50
docker logs applylens-api-prod --tail 50
```

## Common Troubleshooting

### 502 Bad Gateway

**Symptom**: Browser shows "Service Temporarily Unavailable"

**Possible causes**:
1. Backend container not running
2. nginx misconfigured (check for auth stubs)
3. Cloudflare tunnel disconnected

**Debug steps**:
```bash
# Check container health
docker ps --filter "name=applylens-api-prod"

# Test direct container access
curl http://localhost:8003/ready

# Check nginx logs
docker logs applylens-web-prod --tail 50

# Test API endpoint with cache bypass
curl -H "Cache-Control: no-cache" https://applylens.app/api/ready
```

### OAuth Redirect Loops

**Symptom**: Keeps redirecting between login and app

**Cause**: `APPLYLENS_BASE_URL` mismatch or session cookie domain issue

**Fix**: Ensure environment variables match:
```bash
APPLYLENS_BASE_URL=https://applylens.app
OAUTH_REDIRECT_URI=https://applylens.app/api/auth/google/callback
```

### Extension Can't Connect

**Symptom**: Extension shows "Offline" or API errors

**Cause**: CORS not enabled or wrong API base URL

**Fix**: Check CORS origins in backend:
```bash
CORS_ALLOW_ORIGINS=https://applylens.app,https://www.applylens.app
```

## Routing & Domain Health Checks

ApplyLens shares infrastructure with LedgerMind (AI finance agent) but **must maintain strict domain separation** to prevent cross-contamination.

### Critical Routing Rules

⚠️ **Do NOT point `app.ledger-mind.org` at `applylens-nginx`**

LedgerMind domains must **always** route to LedgerMind's nginx:
- **Container**: `ai-finance.int:80` (Docker network alias)
- **Local**: `localhost:8083` (host port binding)
- **Cloudflare Tunnel**: Configured in `infra/cloudflared/config.yml`

### Canonical Health Check Endpoints

| Domain | Service | Endpoint | Expected Response |
|--------|---------|----------|-------------------|
| `applylens.app` | ApplyLens Web | `/health` | `"healthy"` |
| `api.applylens.app` | ApplyLens API | `/healthz` | `{"status":"ok"}` |
| `app.ledger-mind.org` | LedgerMind (via CF) | `/api/ready` | `{"ok":true,"db":{...}}` |
| `localhost:8083` | LedgerMind (local) | `/api/ready` | `{"ok":true,"db":{...}}` |

### Automated Routing Verification

Use the routing health check script to verify all endpoints at once:

```powershell
pwsh infra/scripts/check-routing.ps1
```

**What it checks:**
- All 4 endpoints return 2xx status codes
- LedgerMind responses don't contain "ApplyLens" (no contamination)
- Colorized output: Green = OK, Red = Failed/Misconfigured
- Exit code 1 if any check fails

**Example output:**
```
===============================================
  ApplyLens & LedgerMind Routing Health Check
===============================================

[APPLYLENS_WEB] Testing: https://applylens.app/health
  Status: 200
  Body: healthy
  ✓ OK

[LEDGERMIND_CF] Testing: https://app.ledger-mind.org/api/ready
  Status: 200
  Body: {"ok":true,"db":{"ok":true...
  ✓ OK

✓ SUCCESS: All 4 endpoints healthy and routing correctly
```

### Manual Verification

If the script fails, manually test each endpoint:

```bash
# ApplyLens Web
curl -s https://applylens.app/health
# Expected: "healthy"

# ApplyLens API
curl -s https://api.applylens.app/healthz
# Expected: {"status":"ok"}

# LedgerMind via Cloudflare Tunnel
curl -s https://app.ledger-mind.org/api/ready
# Expected: {"ok":true,"db":{...},"migrations":{...}}

# LedgerMind local (on host)
curl -s http://localhost:8083/api/ready
# Expected: {"ok":true,"db":{...},"migrations":{...}}
```

**Warning Signs:**
- ❌ `app.ledger-mind.org` returns `"healthy"` → Routing to wrong nginx!
- ❌ `applylens.app` returns database status → Routing to wrong nginx!
- ❌ Any endpoint returns 404/502 → Service down or misconfigured

### Related Documentation

- **nginx Configuration**: See [`docs/infra/LEDGERMIND_ROUTING.md`](infra/LEDGERMIND_ROUTING.md) for detailed routing architecture
- **nginx Validation**: Use [`scripts/nginx-validate.ps1`](../scripts/nginx-validate.ps1) to test nginx config
- **Cloudflare Config**: See `infra/cloudflared/config.yml` for tunnel ingress rules

### Future Work

The routing check script can be integrated into CI/CD for:
- Periodic health monitoring in production
- Pre-deployment verification in staging
- Automated alerting on routing misconfiguration

## Security Considerations

### Network Isolation
- Database and Elasticsearch not exposed to internet
- Only web (80) and API (8000) accessible via tunnel
- Redis used for session storage (not exposed)

### Authentication
- OAuth 2.0 with Google (OIDC)
- Server-side sessions in Redis
- CSRF protection on state-changing endpoints
- Extension uses CSRF-exempt paths

### Secrets Management
- Google OAuth secrets in `/secrets/google.json`
- Database password in environment variables
- Session signing key in `OAUTH_STATE_SECRET`

### Rate Limiting
- nginx rate limiting on `/api/chat` endpoints
- Cloudflare bot protection at edge
- API-level rate limiting per user
