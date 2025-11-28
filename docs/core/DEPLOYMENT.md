# ApplyLens – Production Deploy (LOCAL docker-compose host)

## IMPORTANT CONTEXT FOR TOOLS / ASSISTANTS

- Deployments are always run **directly on this host**.
- There is **no separate remote machine** that needs SSH.
- This repo (`/home/leo/ApplyLens`) lives on the same server that runs Docker.
- Cloudflare Tunnel is already running and is NOT part of normal deploy steps.

## Standard deploy commands

```bash
cd /home/leo/ApplyLens

# Pull latest code
git pull

# Pull latest images
docker compose -f docker-compose.prod.yml pull web api

# Restart services with the new images
docker compose -f docker-compose.prod.yml up -d web api
```

## Post-deploy verification

```bash
# Check container status
docker ps --filter "name=applylens-*-prod"

# Verify API is responding
curl http://localhost:8003/api/healthz

# Check logs if needed
docker logs applylens-api-prod --tail 50
docker logs applylens-web-prod --tail 50
```

## Infrastructure context

- **Network**: applylens_applylens-prod (Docker internal)
- **Containers**:
  - `applylens-web-prod` (port 5175 → 80, nginx serving React app)
  - `applylens-api-prod` (port 8003, FastAPI)
- **Public Routes** (via Cloudflare Tunnel):
  - applylens.app → web:80
  - api.applylens.app → api:8003
- **Entry**: Cloudflare Named Tunnel handles all external traffic
