# Production Deployment Guide

Complete guide for deploying ApplyLens production stack using Docker Compose.

## Prerequisites

- Docker 24.0+ and Docker Compose 2.0+
- At least 4GB RAM available for containers
- 20GB disk space for volumes
- Production secrets configured

## Quick Start

### 1. Configuration

```bash
# Copy environment template
cp infra/.env.example infra/.env

# Edit with production values
nano infra/.env
```

**Required configuration:**
```bash
# Database credentials
POSTGRES_PASSWORD=your_secure_password_here

# OAuth secrets
OAUTH_STATE_SECRET=your_32_character_random_string_here
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback

# Optional: Grafana admin password
GRAFANA_ADMIN_PASSWORD=your_grafana_password
```

### 2. Secrets Setup

```bash
# Create secrets directory
mkdir -p infra/secrets

# Add Google OAuth credentials
# Download from Google Cloud Console and save as:
cp ~/Downloads/client_secret_*.json infra/secrets/google.json
```

### 3. Start the Stack

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d

# Watch logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 4. Run Database Migrations

```bash
# Wait for database to be ready (30 seconds)
sleep 30

# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### 5. Verify Services

```bash
# Check all services are healthy
docker-compose -f docker-compose.prod.yml ps

# Test endpoints
curl http://localhost:8003/healthz          # API health
curl http://localhost:5175/                 # Frontend
curl http://localhost:9200/_cluster/health  # Elasticsearch
curl http://localhost:5601/api/status       # Kibana
curl http://localhost:9090/-/healthy        # Prometheus
curl http://localhost:3000/api/health       # Grafana
```

## Services Overview

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **Frontend** | 5175 | http://localhost:5175 | React/Vite UI |
| **API** | 8003 | http://localhost:8003 | FastAPI backend |
| **PostgreSQL** | 5432 | postgresql://localhost:5432 | Database |
| **Elasticsearch** | 9200 | http://localhost:9200 | Search engine |
| **Kibana** | 5601 | http://localhost:5601 | Analytics UI |
| **Prometheus** | 9090 | http://localhost:9090 | Metrics |
| **Grafana** | 3000 | http://localhost:3000 | Dashboards |
| **Nginx** | 80/443 | http://localhost | Reverse proxy |

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         Internet                              │
└────────────────────────┬─────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │  Nginx  │ (Reverse Proxy)
                    └────┬────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐    ┌─────▼─────┐   ┌─────▼─────┐
   │   Web   │    │    API    │   │  Grafana  │
   │ (React) │    │ (FastAPI) │   │(Monitoring)│
   └─────────┘    └─────┬─────┘   └─────┬─────┘
                        │                │
        ┌───────────────┼────────────────┤
        │               │                │
   ┌────▼────┐   ┌─────▼─────┐   ┌─────▼──────┐
   │   DB    │   │    ES     │   │ Prometheus │
   │(Postgres)│  │(Search)   │   │  (Metrics) │
   └─────────┘   └─────┬─────┘   └────────────┘
                       │
                  ┌────▼────┐
                  │ Kibana  │
                  │(Analytics)│
                  └─────────┘
```

## Management Commands

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f web
```

### Restart Services

```bash
# All services
docker-compose -f docker-compose.prod.yml restart

# Specific service
docker-compose -f docker-compose.prod.yml restart api
```

### Database Operations

```bash
# Backup database
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres applylens > backup.sql

# Restore database
cat backup.sql | docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres applylens

# Access PostgreSQL shell
docker-compose -f docker-compose.prod.yml exec db psql -U postgres applylens

# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Rollback migration
docker-compose -f docker-compose.prod.yml exec api alembic downgrade -1
```

### Scale Services

```bash
# Scale API workers
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

### Update Services

```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Zero-downtime update (requires load balancer)
docker-compose -f docker-compose.prod.yml up -d --no-deps --build api
```

## Monitoring

### Prometheus Metrics

Access metrics at: http://localhost:9090

**Key metrics to monitor:**
- API request rate: `rate(http_requests_total[5m])`
- API error rate: `rate(http_requests_total{status=~"5.."}[5m])`
- Database connections: `pg_stat_database_numbackends`
- Elasticsearch cluster health: `elasticsearch_cluster_health_status`

### Grafana Dashboards

Access dashboards at: http://localhost:3000
- Default credentials: `admin` / `admin` (change on first login)
- Pre-configured dashboards in `infra/grafana/provisioning/dashboards/`

### Application Logs

```bash
# API logs
docker-compose -f docker-compose.prod.yml exec api tail -f /var/log/applylens/access.log
docker-compose -f docker-compose.prod.yml exec api tail -f /var/log/applylens/error.log

# Nginx logs
docker-compose -f docker-compose.prod.yml exec nginx tail -f /var/log/nginx/access.log
docker-compose -f docker-compose.prod.yml exec nginx tail -f /var/log/nginx/error.log
```

## Backup Strategy

### Automated Backups

Create a cron job for daily backups:

```bash
# Add to crontab (crontab -e)
0 2 * * * /path/to/backup-applylens.sh
```

**backup-applylens.sh:**
```bash
#!/bin/bash
BACKUP_DIR="/backups/applylens"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres applylens | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Elasticsearch snapshot
curl -X PUT "localhost:9200/_snapshot/backup/snapshot_$DATE?wait_for_completion=true"

# Keep last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete
```

## Security Hardening

### 1. Use Secrets Management

```bash
# Use Docker secrets instead of environment variables
docker secret create postgres_password /path/to/password
docker secret create google_client_secret /path/to/secret
```

### 2. Enable SSL/TLS

```bash
# Generate self-signed certificate (development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout infra/nginx/ssl/selfsigned.key \
  -out infra/nginx/ssl/selfsigned.crt

# For production, use Let's Encrypt with Certbot
```

### 3. Configure Firewall

```bash
# Allow only necessary ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 4. Enable Authentication

Update `docker-compose.prod.yml`:
```yaml
elasticsearch:
  environment:
    - xpack.security.enabled=true
    - ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs for errors
docker-compose -f docker-compose.prod.yml logs service_name

# Check service health
docker-compose -f docker-compose.prod.yml ps

# Restart service
docker-compose -f docker-compose.prod.yml restart service_name
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Increase Docker memory limit (Docker Desktop)
# Settings > Resources > Memory > Increase to 8GB

# Or limit service memory
docker-compose -f docker-compose.prod.yml up -d --scale api=2
```

### Database Connection Issues

```bash
# Check database is running
docker-compose -f docker-compose.prod.yml ps db

# Test connection
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -c "SELECT 1"

# Check connection from API
docker-compose -f docker-compose.prod.yml exec api python -c "from sqlalchemy import create_engine; import os; engine = create_engine(os.environ['DATABASE_URL']); print(engine.connect())"
```

### Elasticsearch Issues

```bash
# Check cluster health
curl http://localhost:9200/_cluster/health?pretty

# Check node stats
curl http://localhost:9200/_nodes/stats?pretty

# Increase memory if needed (docker-compose.prod.yml)
ES_JAVA_OPTS: "-Xms2g -Xmx2g"
```

## Production Checklist

- [ ] Configure strong passwords for all services
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Enable authentication on Elasticsearch and Kibana
- [ ] Set up automated backups
- [ ] Configure log rotation
- [ ] Set up monitoring alerts
- [ ] Enable Cloudflare Tunnel or alternative CDN
- [ ] Configure DNS records
- [ ] Test disaster recovery procedures
- [ ] Document runbooks for common issues
- [ ] Set up uptime monitoring (e.g., Uptime Robot)

## Support

For issues and questions:
- GitHub Issues: https://github.com/leok974/ApplyLens/issues
- Documentation: See `docs/` directory
- CI Status: Check GitHub Actions

## License

MIT License - See LICENSE file for details
