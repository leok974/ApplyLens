# 🚀 ApplyLens Production Stack - Quick Reference

## One-Command Deployment

```bash
# Linux/Mac
./deploy-prod.sh

# Windows
.\deploy-prod.ps1
```

## Service URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5175 |
| API | http://localhost:8003 |
| API Docs | http://localhost:8003/docs |
| Elasticsearch | http://localhost:9200 |
| Kibana | http://localhost:5601 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

## Essential Commands

```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart service
docker-compose -f docker-compose.prod.yml restart api

# Stop all
docker-compose -f docker-compose.prod.yml down

# Backup database
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres applylens > backup.sql

# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Scale API
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

## Files

- `docker-compose.prod.yml` - Production stack config
- `deploy-prod.sh` / `deploy-prod.ps1` - Deployment scripts
- `PRODUCTION_DEPLOYMENT.md` - Full guide
- `PRODUCTION_QUICK_START.md` - Quick start
- `services/api/Dockerfile.prod` - API production build
- `apps/web/Dockerfile.prod` - Frontend production build

## Documentation

📖 **Full Guide**: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)  
🚀 **Quick Start**: [PRODUCTION_QUICK_START.md](PRODUCTION_QUICK_START.md)  
📝 **Summary**: [docs/PRODUCTION_STACK_COMPLETE.md](docs/PRODUCTION_STACK_COMPLETE.md)

---

**Status**: ✅ Complete and deployed (commit 0beaf38)
