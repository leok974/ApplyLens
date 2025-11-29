# Production Health Checks

Quick smoke tests to verify core endpoints are responding correctly in production.

## Resume + Opportunities Health

These endpoints are critical for the Opportunities page functionality:

```bash
# Resume endpoint - should return null or resume data (200)
curl -s https://applylens.app/api/resume/current

# Opportunities endpoint - should return [] or opportunity list (200)
curl -s https://applylens.app/api/opportunities
```

Both should return 200 status. The resume endpoint may return `null` if no active resume is uploaded. The opportunities endpoint may return `[]` if no opportunities exist.

If either returns `{"detail":"Not Found"}` with 404, it indicates a routing issue (check nginx/Cloudflare tunnel configuration).

## Version Endpoint

```bash
# Version info - should return build metadata (200)
curl -s https://applylens.app/version
```

## Common Issues

### 404 "Not Found" on /api/* routes

**Symptoms**: Browser console shows 404 errors for `/api/resume/current` or `/api/opportunities`

**Likely causes**:
1. Cloudflare Tunnel routing to wrong container (should be `applylens-nginx-prod:80`)
2. Nginx config has incorrect proxy_pass (check `infra/nginx/conf.d/applylens.prod.conf`)
3. Old nginx container interfering (check `docker ps` for duplicate nginx containers)

**Verification steps**:
```bash
# Test API directly (bypassing nginx)
curl http://localhost:8003/api/resume/current

# Test nginx with correct Host header
curl -H "Host: applylens.app" http://localhost:80/api/resume/current

# Test through Cloudflare
curl https://applylens.app/api/resume/current
```

If direct API works but Cloudflare doesn't, it's a routing/tunnel issue, not application code.
