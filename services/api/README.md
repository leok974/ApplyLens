# ApplyLens API

FastAPI backend for ApplyLens job inbox application.

## Development

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -U pip
pip install .
uvicorn app.main:app --reload --port 8000
```

## Production Deployment

### Environment Variables

**Required:**
- `DATABASE_URL` - PostgreSQL connection string
- `ES_URL` - Elasticsearch URL (default: `http://es:9200`)
  - **Important:** In production, set to actual container name: `http://applylens-es-prod:9200`
- `REDIS_URL` - Redis connection string (default: `redis://redis:6379/0`)

**Optional:**
- `ES_ENABLED` - Enable/disable Elasticsearch (default: `true`)
- `ELASTICSEARCH_INDEX` - Index name for emails (default: `gmail_emails`)
- `ES_RECREATE_ON_START` - Recreate index on startup (default: `false`)

**Agent v2 (optional):**
- `REDIS_AGENT_URL` - Separate Redis DB for agent cache (default: uses `REDIS_URL`)
- `AGENT_DOMAIN_RISK_TTL_SECONDS` - Domain risk cache TTL (default: `2592000` = 30 days)
- `AGENT_SESSION_TTL_SECONDS` - Session context cache TTL (default: `3600` = 1 hour)

### Docker Deployment

#### Troubleshooting: ES Connection Issues

If the API container fails to start with `ConnectionRefusedError` to Elasticsearch:

**Symptom:**
```
elastic_transport.ConnectionError: Connection error caused by: NewConnectionError
Failed to establish a new connection: [Errno 111] Connection refused
```

**Solution:**
Set `ES_URL` to match your ES container name:
```bash
# In production, if ES container is named "applylens-es-prod"
ES_URL=http://applylens-es-prod:9200

# Or add network alias in docker-compose.yml:
services:
  elasticsearch:
    container_name: applylens-es-prod
    networks:
      applylens-prod:
        aliases:
          - es  # Now ES_URL=http://es:9200 will work
```

**Verify network connectivity:**
```bash
# Check if containers are on same network
docker inspect applylens-api-prod --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'
docker inspect applylens-es-prod --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'

# Test connection from API container
docker exec applylens-api-prod curl -s http://applylens-es-prod:9200
```

### Hot-Deploy Code to Running Container

**⚠️ For testing only - not recommended for production**

To update code in a running container without rebuilding:

```bash
# 1. Create missing directories if needed
docker exec applylens-api-prod mkdir -p /app/app/agent

# 2. Copy updated files
docker cp services/api/app/schemas_agent.py applylens-api-prod:/app/app/schemas_agent.py
docker cp services/api/app/agent/answering.py applylens-api-prod:/app/app/agent/answering.py
docker cp services/api/app/agent/orchestrator.py applylens-api-prod:/app/app/agent/orchestrator.py
docker cp services/api/app/agent/tools.py applylens-api-prod:/app/app/agent/tools.py
docker cp services/api/app/main.py applylens-api-prod:/app/app/main.py
docker cp services/api/app/core/csrf.py applylens-api-prod:/app/app/core/csrf.py

# 3. Restart container
docker restart applylens-api-prod

# 4. Wait for health check
Start-Sleep -Seconds 10
docker exec applylens-api-prod curl -s http://localhost:8000/api/health
```

**Recommended:** Rebuild the Docker image instead:
```bash
docker build -t applylens-api:latest -f Dockerfile.prod .
docker-compose -f docker-compose.prod.yml up -d --no-deps api
```

## Seed Data

```bash
python app/seeds/seed_emails.py
```

## Alembic Migrations

```bash
alembic upgrade head
```
