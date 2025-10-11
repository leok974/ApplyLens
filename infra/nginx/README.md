# Nginx Reverse Proxy Setup

ApplyLens uses Nginx as a single entrypoint for path-based routing to all services.

## Architecture

```
Internet → Cloudflare Tunnel → Nginx (port 80) → Backend Services
                                    ↓
                    ┌───────────────┴────────────────┐
                    │                                │
                 API:8003                        Web:5175
                    │                                │
              Grafana:3000                     Kibana:5601
                    │                                │
              Prometheus:9090                   ES:9200
```

## URL Routes

All services are accessible via **path-based routing** on `applylens.app`:

| Path | Service | Description |
|------|---------|-------------|
| `/` | API (FastAPI) | Main application API |
| `/docs/` | API | FastAPI Swagger UI documentation |
| `/openapi.json` | API | OpenAPI specification |
| `/web/` | Web | Frontend application (Vite/React) |
| `/grafana/` | Grafana | Monitoring dashboards |
| `/kibana/` | Kibana | Log analytics and search |
| `/prometheus/` | Prometheus | Metrics and time-series data |
| `/healthz` | Nginx | Health check endpoint |

## Public URLs (via Cloudflare Tunnel)

- **API**: https://applylens.app/
- **API Docs**: https://applylens.app/docs/
- **Web App**: https://applylens.app/web/
- **Grafana**: https://applylens.app/grafana/
- **Kibana**: https://applylens.app/kibana/
- **Prometheus**: https://applylens.app/prometheus/

## Local Testing

Nginx is exposed on port **8888** for local testing:

```bash
# Health check
curl http://localhost:8888/healthz

# API docs
curl http://localhost:8888/docs/

# OpenAPI spec
curl http://localhost:8888/openapi.json

# Grafana
open http://localhost:8888/grafana/

# Kibana
open http://localhost:8888/kibana/
```

## Configuration Files

### Main Nginx Config
**Location**: `infra/nginx/conf.d/applylens.conf`

Defines all upstream services and routing rules. Uses `map` directive for WebSocket upgrade support.

### Security Headers
**Location**: `infra/nginx/snippets/security-headers.conf`

Applies security headers to all responses:
- `X-Frame-Options: SAMEORIGIN` - Prevent clickjacking
- `X-Content-Type-Options: nosniff` - Prevent MIME sniffing
- `Referrer-Policy: strict-origin-when-cross-origin` - Control referrer info

**Note**: HSTS is commented out until HTTPS is confirmed working via Cloudflare.

### Gzip Compression
**Location**: `infra/nginx/snippets/gzip.conf`

Compresses responses for:
- text/plain, text/css
- application/json, application/javascript
- application/xml, text/javascript

## Service-Specific Configuration

### Grafana Subpath Configuration
**File**: `infra/grafana/grafana.ini`

```ini
[server]
root_url = %(protocol)s://%(domain)s/grafana/
serve_from_sub_path = true
```

This tells Grafana to:
1. Serve all assets with `/grafana/` prefix
2. Rewrite internal links to include the subpath
3. Handle redirects correctly

### Kibana Subpath Configuration
**File**: `infra/kibana/kibana.yml`

```yaml
server.basePath: "/kibana"
server.rewriteBasePath: true
server.publicBaseUrl: "https://applylens.app/kibana"
```

This tells Kibana to:
1. Serve on `/kibana` base path
2. Rewrite all URLs to include the base path
3. Use the public URL for external links

## Cloudflare Tunnel Configuration

**File**: `infra/cloudflared/config.yml`

Routes both `applylens.app` and `www.applylens.app` to Nginx:

```yaml
ingress:
  - hostname: applylens.app
    service: http://nginx:80
  - hostname: www.applylens.app
    service: http://nginx:80
  - service: http_status:404  # Catch-all
```

## Docker Compose

Nginx service definition:

```yaml
nginx:
  image: nginx:1.27-alpine
  container_name: applylens-nginx
  depends_on:
    - api
    - web
    - grafana
    - kibana
    - prometheus
  volumes:
    - ./nginx/conf.d:/etc/nginx/conf.d:ro
    - ./nginx/snippets:/etc/nginx/snippets:ro
  ports:
    - "8888:80"  # Local debug port
  restart: unless-stopped
```

## Benefits

### 1. Single Hostname
All services accessible via `applylens.app` without managing multiple subdomains or DNS records.

### 2. Clean URLs
Path-based routing provides intuitive URLs:
- `applylens.app/docs/` - obvious it's documentation
- `applylens.app/grafana/` - obvious it's monitoring

### 3. Centralized Security
- Security headers applied once at Nginx layer
- Easy to add authentication middleware
- Single SSL/TLS termination point at Cloudflare

### 4. Performance
- Gzip compression reduces bandwidth
- Nginx connection pooling to backends
- Efficient static file serving

### 5. Flexibility
Easy to add new services or change routing without touching DNS.

## Alternative: Subdomain Routing

If you prefer subdomains over paths, uncomment these lines in `cloudflared/config.yml`:

```yaml
ingress:
  # Use subdomains instead of paths
  - hostname: api.applylens.app
    service: http://api:8003
  - hostname: grafana.applylens.app
    service: http://grafana:3000
  - hostname: kibana.applylens.app
    service: http://kibana:5601
```

Then create DNS routes:
```bash
cloudflared tunnel route dns applylens api.applylens.app
cloudflared tunnel route dns applylens grafana.applylens.app
cloudflared tunnel route dns applylens kibana.applylens.app
```

**Note**: With subdomains, you don't need the Grafana/Kibana subpath configuration.

## Troubleshooting

### Nginx Returns 502 Bad Gateway

**Cause**: Backend service is not running or not reachable.

**Fix**:
```bash
# Check which service is down
docker compose ps

# Check Nginx logs
docker compose logs nginx --tail 50

# Restart the specific service
docker compose restart api
```

### Grafana/Kibana Shows Broken Layout

**Cause**: Subpath configuration not loaded.

**Fix**:
```bash
# Verify config files are mounted
docker compose exec grafana cat /etc/grafana/grafana.ini
docker compose exec kibana cat /usr/share/kibana/config/kibana.yml

# Restart services to reload config
docker compose restart grafana kibana
```

### 404 Not Found for All Routes

**Cause**: Nginx config file not loaded or syntax error.

**Fix**:
```bash
# Test Nginx config syntax
docker compose exec nginx nginx -t

# Check if config file is mounted
docker compose exec nginx ls -la /etc/nginx/conf.d/

# View Nginx error log
docker compose logs nginx
```

### Cannot Access via Cloudflare Tunnel

**Cause**: Tunnel not connected or misconfigured.

**Fix**:
```bash
# Check tunnel status
docker compose logs cloudflared --tail 50

# Should see "Registered tunnel connection" messages
# If not, check config file
cat infra/cloudflared/config.yml

# Restart tunnel
docker compose restart cloudflared
```

## Maintenance

### Reload Nginx Config (Without Downtime)

```bash
# After editing nginx config files
docker compose exec nginx nginx -s reload
```

### View Real-Time Access Logs

```bash
docker compose logs -f nginx
```

### Add New Route

1. Edit `infra/nginx/conf.d/applylens.conf`
2. Add new location block:
   ```nginx
   location /newservice/ {
     proxy_pass http://newservice:8080/;
     proxy_set_header Host $host;
   }
   ```
3. Reload: `docker compose exec nginx nginx -s reload`

### Enable HSTS (After HTTPS Confirmed)

1. Edit `infra/nginx/snippets/security-headers.conf`
2. Uncomment HSTS header:
   ```nginx
   add_header Strict-Transport-Security "max-age=86400; includeSubDomains; preload" always;
   ```
3. Reload: `docker compose exec nginx nginx -s reload`

## Performance Tuning

### Increase Worker Processes

For high traffic, increase Nginx workers in `docker-compose.yml`:

```yaml
nginx:
  environment:
    - NGINX_WORKER_PROCESSES=4  # Match CPU cores
```

### Enable HTTP/2

Nginx 1.27 supports HTTP/2 out of the box when behind HTTPS (Cloudflare Tunnel).

### Add Caching

For static assets, add caching headers:

```nginx
location /web/static/ {
  proxy_pass http://web:5175/static/;
  proxy_cache_valid 200 1d;
  add_header Cache-Control "public, max-age=86400";
}
```

## Security Best Practices

### 1. Restrict Access by IP (Optional)

```nginx
location /prometheus/ {
  allow 10.0.0.0/8;    # Internal network
  deny all;
  proxy_pass http://prometheus:9090/;
}
```

### 2. Add Basic Auth (For Services Without Built-in Auth)

```bash
# Create password file
docker compose exec nginx sh -c "echo -n 'admin:' > /etc/nginx/.htpasswd"
docker compose exec nginx sh -c "openssl passwd -apr1 >> /etc/nginx/.htpasswd"
```

Then in nginx config:
```nginx
location /prometheus/ {
  auth_basic "Restricted";
  auth_basic_user_file /etc/nginx/.htpasswd;
  proxy_pass http://prometheus:9090/;
}
```

### 3. Rate Limiting

```nginx
http {
  limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
  
  location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://api:8003/;
  }
}
```

## Monitoring Nginx

### Nginx Access Logs

```bash
# Real-time access log
docker compose logs -f nginx | grep -v healthz

# Count requests by path
docker compose logs nginx | grep -oP '"\w+ \K[^ ]+' | sort | uniq -c | sort -rn
```

### Nginx Metrics (Optional)

Enable stub_status module in `applylens.conf`:

```nginx
location /nginx_status {
  stub_status;
  allow 127.0.0.1;  # Only accessible internally
  deny all;
}
```

Access: `curl http://localhost:8888/nginx_status`

### Add Nginx to Prometheus (Optional)

Install nginx-prometheus-exporter as a sidecar container.

## Summary

Nginx provides a robust, performant, and flexible reverse proxy for ApplyLens:

✅ **Single entrypoint** via applylens.app  
✅ **Clean path-based routing** for all services  
✅ **Centralized security** headers and policies  
✅ **Gzip compression** for reduced bandwidth  
✅ **Easy to extend** with new services  
✅ **Production-ready** with Cloudflare Tunnel integration

For production, consider enabling HSTS, adding rate limiting, and implementing authentication for sensitive endpoints.
