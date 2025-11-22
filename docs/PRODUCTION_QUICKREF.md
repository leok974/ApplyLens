# ApplyLens Production Quick Reference

> ⚠️ **DEPRECATED – Historical deployment notes**
>
> This document describes an older ApplyLens deployment architecture
> (pre-Cloudflare Tunnel consolidated setup). For current instructions,
> see [`docs/PRODUCTION_DEPLOYMENT.md`](./PRODUCTION_DEPLOYMENT.md).

## 🚀 Current Production Status

**Version:** v0.4.1
**Git SHA:** 461336d
**Deployed:** 2025-10-23

**Image Digests (Immutable):**
```
API: leoklemet/applylens-api@sha256:99a07206dfb3987c7c8f3775af0f61a405b298d4db54c9877ac567528ab1bc7a
Web: leoklemet/applylens-web@sha256:f069ea49758048488766ee191b423b27bb4d8c02920084d0154aca560772d61e
```

## 🚀 Essential Commands

### Build New Version (Development)
```powershell
# Build and tag both services
.\scripts\build-and-tag.ps1 -Version "v0.4.2"

# Build, tag, and push to registry
.\scripts\build-and-tag.ps1 -Version "v0.4.2" -Push
```

### Deploy / Update (Production)
```bash
cd /opt/applylens && git pull && docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --build
```

### Quick Deploy (Force Recreate)
```powershell
docker-compose -f docker-compose.prod.yml up -d --force-recreate api web
```

### Rollback (30 seconds)
```powershell
.\scripts\rollback.ps1 -Version "v0.4.0"
```

### Health Check (One-Liner)
```bash
curl -fsSL https://applylens.app/api/healthz && echo "✓" || echo "✗"
```

### Verify Services
```powershell
curl http://localhost:8003/healthz  # API
curl http://localhost:5175/          # Web
```

### View Logs (Live)
```bash
cd /opt/applylens && docker compose -f docker-compose.prod.yml logs -f
```

### Monitor Containers
```powershell
docker ps --filter "name=applylens-" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
docker logs applylens-api-prod --tail 50
docker logs applylens-web-prod --tail 50
```

### Restart Everything
```bash
cd /opt/applylens && docker compose -f docker-compose.prod.yml restart
```

### Run Migrations
```bash
cd /opt/applylens && docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## 🔧 Common Fixes

### Blank UI
```bash
docker compose -f docker-compose.prod.yml up -d --build web
```

### API Not Responding
```bash
docker compose -f docker-compose.prod.yml restart api
docker compose -f docker-compose.prod.yml logs api --tail=50
```

### Database Issues
```bash
docker compose -f docker-compose.prod.yml restart db
docker compose -f docker-compose.prod.yml logs db --tail=50
```

### Check All Service Status
```bash
docker compose -f docker-compose.prod.yml ps
```

---

## 📊 Monitoring

### Resource Usage
```bash
docker stats --no-stream
```

### Disk Space
```bash
df -h /var/lib/docker
docker system df
```

### Container Logs (Last 100 lines)
```bash
docker compose -f docker-compose.prod.yml logs --tail=100 nginx api web
```

---

## 🔐 Backup

### Database Backup
```bash
docker compose -f docker-compose.prod.yml exec db pg_dump -U applylens applylens > backup_$(date +%Y%m%d).sql
```

### Restore Database
```bash
cat backup_20250114.sql | docker compose -f docker-compose.prod.yml exec -T db psql -U applylens applylens
```

---

## 🚨 Emergency

### Complete Restart
```bash
cd /opt/applylens
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

### Rollback
```bash
cd /opt/applylens
git log --oneline -10
git checkout <previous-commit-hash>
docker compose -f docker-compose.prod.yml up -d --build
```

### Emergency Shutdown
```bash
cd /opt/applylens
docker compose -f docker-compose.prod.yml down
```

---

## 📍 Important Files

- **Environment:** `/opt/applylens/infra/.env.prod`
- **Compose File:** `/opt/applylens/docker-compose.prod.yml`
- **Nginx Config:** `/opt/applylens/infra/nginx/conf.d/applylens.conf`
- **Full Docs:** `/opt/applylens/docs/PRODUCTION_DEPLOY.md`

---

## 🌐 URLs

- **Production:** https://applylens.app
- **API Docs:** https://applylens.app/docs
- **API Health:** https://applylens.app/api/healthz
- **Prometheus:** https://applylens.app/prometheus
- **Grafana:** https://applylens.app/grafana

---

## 🔍 Troubleshooting One-Liners

```bash
# Check if services are responding
curl -I https://applylens.app && echo "✓ Web OK" || echo "✗ Web FAIL"
curl -s https://applylens.app/api/healthz && echo "✓ API OK" || echo "✗ API FAIL"

# Check container health
docker compose -f docker-compose.prod.yml ps | grep -v "Up" && echo "⚠️ Issues found"

# Check disk space
df -h / | awk 'NR==2 {if ($5+0 > 80) print "⚠️ Disk >80%"; else print "✓ Disk OK"}'

# Check memory
free -m | awk 'NR==2 {if ($3/$2*100 > 90) print "⚠️ RAM >90%"; else print "✓ RAM OK"}'

# Quick system health
docker stats --no-stream --format "{{.Name}}: CPU={{.CPUPerc}} MEM={{.MemUsage}}"
```

---

**For detailed documentation, see:** `/opt/applylens/docs/PRODUCTION_DEPLOY.md`
