# ApplyLens – Production Deploy (Cloudflare Tunnel host)

All production deploys for ApplyLens happen **on the production host itself**, not from a dev machine.

## Prerequisites (already configured on host)

- Repo is checked out at `/home/leo/ApplyLens`
- Docker + docker compose installed
- Cloudflare Tunnel containers already running (unchanged by normal deploys)

## Standard deploy steps

```bash
cd /home/leo/ApplyLens

# 1. Pull latest code
git pull

# 2. Pull latest images for web + api
docker compose -f docker-compose.prod.yml pull web api

# 3. Restart web + api with new images
docker compose -f docker-compose.prod.yml up -d web api
```

That's it. Tunnel + DB + ES + Redis keep running; this only updates the web and API containers.

## Post-deploy verification

```bash
# Check container status
docker ps --filter "name=applylens-*-prod"

# Verify API version
curl https://api.applylens.app/api/version

# Check logs if needed
docker logs applylens-api-prod --tail 50
docker logs applylens-web-prod --tail 50
```

## Deployment context

- **Infrastructure**: Cloudflare Named Tunnel (08d5feee-f504-47a2-a1f2-b86564900991)
- **Network**: applylens_applylens-prod (Docker internal)
- **Containers**:
  - `applylens-web-prod` (port 80, nginx serving React app)
  - `applylens-api-prod` (port 8003, FastAPI)
- **Routes**:
  - applylens.app → web:80
  - api.applylens.app → api:8003
- **Access**: No direct SSH from dev machine, deployment runs ON production host

## Current version

Version 0.5.23 includes:
- Agent V2 Learning Loop with real feedback aggregation
- Polished MailChat UI with hero header, tool strip, and avatars
- Redesigned AgentCardList with per-intent styling and feedback controls
