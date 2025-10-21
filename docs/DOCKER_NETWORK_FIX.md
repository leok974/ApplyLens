# Docker Network Hostname Fix ✅

## The Issue

You tried `http://applylens-api:8003` but got a "Bad Gateway" error.

## The Solution

Use the **full container name**: `http://applylens-api-prod:8003`

## Why?

### Container Names in Docker Networks

When containers are on the same Docker network, they can reach each other using their **container names** as hostnames.

```
Your containers on network: applylens_applylens-prod
├── applylens-api-prod       ← Full name needed!
├── applylens-grafana-prod
├── applylens-db-prod
├── applylens-redis-prod
└── ... (other containers)
```

### What You Tried vs What Works

| What You Tried | Why It Failed | What Works |
|----------------|---------------|------------|
| `applylens-api:8003` | Container doesn't exist with that name | `applylens-api-prod:8003` ✅ |
| `localhost:8003` | Refers to inside the Grafana container | `applylens-api-prod:8003` ✅ |
| `127.0.0.1:8003` | Refers to inside the Grafana container | `applylens-api-prod:8003` ✅ |

### Alternative Options

You could also use:
- `http://host.docker.internal:8003` - Points to your Windows host (works but slower)
- `http://172.25.0.9:8003` - Direct IP address (works but brittle if container restarts)
- `http://applylens-api-prod:8003` - **Best option!** (uses Docker DNS, fast and reliable)

## Dashboard Updated ✅

**File:** `docs/phase3_grafana_dashboard.json`

**Changed from:**
```json
"query": "http://host.docker.internal:8003"
```

**Changed to:**
```json
"query": "http://applylens-api-prod:8003"
```

## How to Verify

### 1. From Grafana Container (Should Work)
```powershell
docker exec applylens-grafana-prod wget -O- http://applylens-api-prod:8003/healthz
```
**Expected:** `{"status":"ok"}`

### 2. Test the Metrics Endpoint
```powershell
docker exec applylens-grafana-prod wget -O- http://applylens-api-prod:8003/api/metrics/profile/activity_daily 2>&1 | Select-String "rows"
```
**Expected:** JSON with 90 days of data

### 3. View Dashboard
```
URL: http://localhost:3000/d/applylens-phase4-overview
Login: admin / admin123
```

After creating the "ApplyLens API" datasource, all 4 panels should display data!

## Docker Networking Cheat Sheet

### List Networks
```powershell
docker network ls
```

### See Which Network a Container Uses
```powershell
docker inspect <container-name> -f "{{.HostConfig.NetworkMode}}"
```

### List All Containers on a Network
```powershell
docker network inspect <network-name> -f "{{range .Containers}}{{.Name}} {{end}}"
```

### Test Connectivity Between Containers
```powershell
docker exec <container-1> wget -O- http://<container-2>:<port>/healthz
```

## Summary

✅ **Problem:** Used wrong hostname `applylens-api`  
✅ **Solution:** Use full container name `applylens-api-prod`  
✅ **Dashboard:** Updated and re-imported  
✅ **Next Step:** Create "ApplyLens API" datasource in Grafana UI  

**Dashboard URL:** http://localhost:3000/d/applylens-phase4-overview

---

**Both containers are on:** `applylens_applylens-prod` network  
**API Container Name:** `applylens-api-prod`  
**Grafana Container Name:** `applylens-grafana-prod`  
**API Port:** 8003
