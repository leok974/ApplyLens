# 🚀 ApplyLens Quick Deploy Reference

## Current Production
**Version:** v0.4.1
**Git SHA:** 461336d
**Deployed:** 2025-10-23

## One-Liner Commands

### 🔨 Build New Version
```powershell
.\scripts\build-and-tag.ps1 -Version "v0.4.2"
```

### 🚢 Deploy
```powershell
docker-compose -f docker-compose.prod.yml up -d --force-recreate api web
```

### ⏪ Rollback (30 seconds)
```powershell
.\scripts\rollback.ps1 -Version "v0.4.0"
```

### ✅ Verify
```powershell
curl http://localhost:8003/healthz  # API
curl http://localhost:5175/          # Web
```

### 📊 Monitor
```powershell
docker ps --filter "name=applylens-" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
docker logs applylens-api-prod --tail 50
docker logs applylens-web-prod --tail 50
```

## Image Digests (Immutable)
```
API: leoklemet/applylens-api@sha256:99a07206dfb3987c7c8f3775af0f61a405b298d4db54c9877ac567528ab1bc7a
Web: leoklemet/applylens-web@sha256:f069ea49758048488766ee191b423b27bb4d8c02920084d0154aca560772d61e
```

## Emergency Numbers
- Health: `http://localhost:8003/healthz`
- Docs: `http://localhost:8003/docs`
- Grafana: `http://localhost:3000`
- Logs: `docker logs applylens-api-prod -f`

---
📖 Full docs: `docs/DEPLOYMENT.md`
