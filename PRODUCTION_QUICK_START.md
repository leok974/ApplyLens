# Production Stack - Quick Start

Complete production-ready deployment of ApplyLens with a single command.

## 📦 What's Included

This production stack includes:

- **Frontend**: React/Vite web application with nginx
- **Backend**: FastAPI with gunicorn workers
- **Database**: PostgreSQL 16 with automatic backups
- **Search**: Elasticsearch 8.13 with Kibana
- **Monitoring**: Prometheus + Grafana dashboards
- **Reverse Proxy**: Nginx with SSL/TLS support
- **Tunnel**: Cloudflare Tunnel (optional)

## 🚀 One-Command Deployment

### Linux/Mac

```bash
# Make script executable
chmod +x deploy-prod.sh

# Run deployment
./deploy-prod.sh
```

### Windows (PowerShell)

```powershell
# Run deployment
.\deploy-prod.ps1
```

The script will:
1. Check prerequisites (Docker, Docker Compose)
2. Validate configuration and secrets
3. Build/pull all service images
4. Start services with health checks
5. Run database migrations (if fresh deployment)
6. Display service URLs and status

## 📋 Manual Deployment

If you prefer manual control:

```bash
# 1. Configure environment
cp infra/.env.example infra/.env
nano infra/.env  # Edit with production values

# 2. Add secrets
mkdir -p infra/secrets
cp ~/Downloads/google-oauth.json infra/secrets/google.json

# 3. Start stack
docker-compose -f docker-compose.prod.yml up -d

# 4. Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# 5. Check status
docker-compose -f docker-compose.prod.yml ps
```

## 🔧 Configuration

### Required Environment Variables

Edit `infra/.env` with:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password

# OAuth
OAUTH_STATE_SECRET=random_32_char_string
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback

# Monitoring (optional)
GRAFANA_ADMIN_PASSWORD=your_grafana_password
```

### Required Secrets

Place in `infra/secrets/`:
- `google.json` - Google OAuth credentials from Google Cloud Console

## 🌐 Service URLs

After deployment, access services at:

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5175 | Main application |
| API | http://localhost:8003 | Backend API |
| API Docs | http://localhost:8003/docs | Interactive API docs |
| Elasticsearch | http://localhost:9200 | Search cluster |
| Kibana | http://localhost:5601 | Analytics |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3000 | Dashboards |
| Nginx | http://localhost:80 | Reverse proxy |

## 📊 Architecture

```
Internet
   │
   ▼
Nginx (80/443)
   │
   ├──▶ Frontend (React/Vite)
   ├──▶ API (FastAPI + Gunicorn)
   ├──▶ Grafana (Monitoring)
   └──▶ Kibana (Analytics)
        │
        ├──▶ PostgreSQL (Database)
        ├──▶ Elasticsearch (Search)
        └──▶ Prometheus (Metrics)
```

## 🛠️ Management Commands

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f api
```

### Restart Services

```bash
# All services
docker-compose -f docker-compose.prod.yml restart

# Specific service
docker-compose -f docker-compose.prod.yml restart api
```

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Or use deployment script
./deploy-prod.sh  # Select option 2
```

### Database Operations

```bash
# Backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres applylens > backup.sql

# Restore
cat backup.sql | docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres applylens

# Migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Scale Services

```bash
# Scale API workers
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

## 🔒 Security Checklist

Before deploying to production:

- [ ] Change all default passwords
- [ ] Configure SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Enable authentication on all services
- [ ] Configure automated backups
- [ ] Set up monitoring alerts
- [ ] Review and harden nginx configuration
- [ ] Enable rate limiting
- [ ] Configure CORS properly
- [ ] Review log retention policies

## 📈 Monitoring

### Prometheus Metrics

Access: http://localhost:9090

Key metrics:
- `rate(http_requests_total[5m])` - Request rate
- `http_request_duration_seconds` - Latency
- `pg_stat_database_numbackends` - DB connections

### Grafana Dashboards

Access: http://localhost:3000
- Default: admin/admin (change on first login)
- Pre-configured dashboards in `infra/grafana/provisioning/`

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs service_name

# Check health
docker-compose -f docker-compose.prod.yml ps

# Restart problematic service
docker-compose -f docker-compose.prod.yml restart service_name
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Increase Docker memory (Settings > Resources)
# Or reduce service replicas
```

### Database Connection Failed

```bash
# Test connection
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -c "SELECT 1"

# Check logs
docker-compose -f docker-compose.prod.yml logs db
```

## 📚 Documentation

- **Full deployment guide**: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- **Judge demo guide**: [README.md](README.md) - Judge Demo section
- **CI status**: [docs/CI_STATUS_SCHEMA_DRIFT.md](docs/CI_STATUS_SCHEMA_DRIFT.md)

## 🆘 Support

- **Issues**: https://github.com/leok974/ApplyLens/issues
- **CI Status**: Check GitHub Actions
- **Logs**: `docker-compose -f docker-compose.prod.yml logs -f`

## 📄 License

MIT License - See LICENSE file
