# ApplyLens Nginx Routing Configuration

## Overview
The ApplyLens web container uses nginx to proxy API requests from the frontend to the FastAPI backend. Due to inconsistent route naming in the backend (some routes under `/api/*`, others under root), nginx applies selective routing rules.

## Container Setup
- **Web Container**: `applylens-web-prod`
- **API Container**: `applylens-api:8000` (internal)
- **Nginx Config**: `/etc/nginx/conf.d/default.conf`
- **Tracked Config**: `infra/nginx/conf.d/applylens.prod.conf`

## Routing Rules

### 1. Auth Compatibility Stubs (Guest Mode)
Frontend requests to auth endpoints return stub responses since full authentication isn't implemented yet.

```nginx
location = /api/auth/csrf {
    return 204;
}

location = /api/auth/me {
    return 200 '{"id":"guest","name":"Guest User","is_authenticated":false,...}';
}
```

### 2. Routes with /api Prefix Stripped
These backend routes exist at the root level (e.g., `/actions/*`, `/metrics/*`, `/gmail/*`) but the frontend requests them with `/api` prefix.

```nginx
# /api/actions/* → /actions/*
location ^~ /api/actions/ {
    proxy_pass http://applylens-api:8000/actions/;
}

# /api/metrics/* → /metrics/*
location ^~ /api/metrics/ {
    proxy_pass http://applylens-api:8000/metrics/;
}

# /api/gmail/* → /gmail/*
location ^~ /api/gmail/ {
    proxy_pass http://applylens-api:8000/gmail/;
}
```

### 3. Routes with /api Prefix Preserved
These backend routes expect the `/api` prefix (e.g., `/api/profile/*`, `/api/extension/*`, `/api/active/*`).

```nginx
# /api/profile/* → /api/profile/*
# /api/extension/* → /api/extension/*
# /api/active/* → /api/active/*
location ^~ /api/ {
    proxy_pass http://applylens-api:8000/api/;
}
```

### 4. Special Chat Routes
Chat routes have specific configurations for SSE streaming and rate limiting.

```nginx
location /api/chat {
    proxy_pass http://applylens-api:8000/chat;
    limit_req zone=api_rl burst=30 nodelay;
}

location /api/chat/stream {
    proxy_pass http://applylens-api:8000/chat/stream;
    proxy_buffering off;  # SSE-friendly
    limit_req zone=api_rl burst=10 nodelay;
}
```

## Backend Route Patterns

### Routes at Root Level (need prefix stripped)
- `/actions/*` - Action management
- `/metrics/*` - Metrics and analytics
- `/gmail/*` - Gmail integration
- `/chat` - Chat endpoints
- `/profile/*` - User profiles (some routes)
- `/search/*` - Search functionality

### Routes under /api/* (keep prefix)
- `/api/profile/me` - Current user profile
- `/api/extension/*` - Browser extension endpoints
- `/api/active/*` - Active learning
- `/api/gmail/backfill/*` - Gmail backfill operations
- `/api/security/*` - Security features
- `/api/ops/*` - Operations endpoints
- `/api/rag/*` - RAG features

## Deployment Notes

### Updating Nginx Config in Production
1. Edit `infra/nginx/conf.d/applylens.prod.conf`
2. Copy to running container:
   ```powershell
   docker cp .\nginx\conf.d\applylens.prod.conf applylens-web-prod:/etc/nginx/conf.d/default.conf
   ```
3. Test configuration:
   ```powershell
   docker exec -u root applylens-web-prod nginx -t
   ```
4. Reload nginx:
   ```powershell
   docker exec -u root applylens-web-prod nginx -s reload
   ```

### Verifying Endpoints
```powershell
# Test all critical endpoints
curl https://applylens.app/api/actions/tray?latest=10
curl https://applylens.app/api/metrics/divergence-bq
curl https://applylens.app/api/profile/me
curl https://applylens.app/api/auth/me
curl https://applylens.app/api/gmail/status
```

## Fixed Issues (Nov 15, 2025)
- ✅ Fixed 502 errors by correcting API container name and port
- ✅ Fixed `/api/actions/*` 404s by stripping `/api` prefix
- ✅ Fixed `/api/metrics/*` 404s by stripping `/api` prefix
- ✅ Fixed `/api/gmail/status` 404 by adding Gmail routing rule
- ✅ Added auth compatibility stubs for guest mode
- ✅ Preserved `/api/profile/me` and other `/api/*` routes

## Cloudflare Tunnel Configuration
The Cloudflare tunnel (version 45) routes traffic as follows:
- `applylens.app` → `http://applylens-web:80` (nginx in web container)
- `api.applylens.app` → `http://applylens-api:8000` (direct to API - optional)

All API requests go through the web container's nginx proxy, which handles the routing complexity.
