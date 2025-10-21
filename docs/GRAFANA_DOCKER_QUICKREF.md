# Grafana Docker Setup - Quick Reference

## ✅ Current Status

**Grafana Container:** `applylens-grafana-prod`  
**Status:** ✅ Running  
**Version:** 11.1.0  
**URL:** http://localhost:3000  
**Credentials:** admin / admin  

**Plugin Installed:** ✅ marcusolsson-json-datasource @ 1.3.24

## 📋 Quick Setup Steps

### 1. Access Grafana
```
http://localhost:3000
Username: admin
Password: admin
```

### 2. Create JSON API Datasource

1. Go to: **Configuration (⚙️) → Data Sources → Add data source**
2. Search: **"JSON API"**
3. Configure:
   - **Name:** `ApplyLens API`
   - **URL:** (leave empty - panels use their own URLs)
4. Click: **Save & Test**

### 3. Get API Key

1. Go to: **Configuration (⚙️) → API Keys**
2. Click: **New API Key**
3. Configure:
   - **Name:** `Dashboard Import`
   - **Role:** `Admin`
4. Click: **Add**
5. **Copy the key immediately!** (You won't see it again)

### 4. Import Dashboard

```powershell
cd D:\ApplyLens\docs
.\import_grafana_dashboard.ps1 -ApiKey "YOUR_API_KEY_HERE"
```

## 🐳 Docker Commands

### View Grafana logs
```powershell
docker logs -f applylens-grafana-prod
```

### Restart Grafana
```powershell
docker restart applylens-grafana-prod
```

### Stop Grafana
```powershell
cd D:\ApplyLens
docker-compose -f docker-compose.prod.yml stop grafana
```

### Start Grafana
```powershell
cd D:\ApplyLens
docker-compose -f docker-compose.prod.yml up -d grafana
```

### Rebuild Grafana (if needed)
```powershell
cd D:\ApplyLens
docker-compose -f docker-compose.prod.yml up -d --force-recreate grafana
```

### Check installed plugins
```powershell
docker exec applylens-grafana-prod grafana-cli plugins ls
```

## 📊 Dashboard Details

**Title:** ApplyLens Overview  
**UID:** `applylens-overview`  
**URL:** http://localhost:3000/d/applylens-overview  
**Panels:** 4  
**Refresh:** 30 seconds  

### Panels

1. **Warehouse Divergence (24h)** - Stat
   - Endpoint: `/api/metrics/divergence-24h`
   - Thresholds: 🟢 <2%, 🟡 2-5%, 🔴 >5%

2. **Activity by Day** - Timeseries
   - Endpoint: `/api/metrics/activity-daily`
   - Shows: 30 days of daily message counts

3. **Top Senders (30d)** - Table
   - Endpoint: `/api/metrics/top-senders-30d`
   - Shows: Top 10 email senders

4. **Categories (30d)** - Bar Chart
   - Endpoint: `/api/metrics/categories-30d`
   - Shows: Message distribution by category

## 🧪 Testing

### Test API endpoints
```powershell
cd D:\ApplyLens\docs
.\test_dashboard_endpoints.ps1
```

### Verify Grafana setup
```powershell
.\verify_grafana_setup.ps1 -ApiKey "YOUR_API_KEY"
```

### Test single endpoint
```powershell
curl.exe http://localhost:8000/api/metrics/divergence-24h
```

## 🔧 Troubleshooting

### Dashboard shows "No Data"

**Check API server:**
```powershell
curl.exe http://localhost:8000/api/metrics/divergence-24h
```

**Check datasource configuration:**
- Go to datasource settings
- Click "Save & Test"
- Ensure no errors

**Check api_base variable:**
- Default should be: `http://127.0.0.1:8000`
- Or: `http://host.docker.internal:8000` (if API is on host)

### Plugin not found

**Reinstall plugin:**
```powershell
# Add plugin to docker-compose.prod.yml if not already there
# - GF_INSTALL_PLUGINS=grafana-piechart-panel,marcusolsson-json-datasource

# Rebuild container
cd D:\ApplyLens
docker-compose -f docker-compose.prod.yml up -d --force-recreate grafana

# Verify
docker exec applylens-grafana-prod grafana-cli plugins ls
```

### Grafana not accessible

**Check container status:**
```powershell
docker ps | Select-String grafana
```

**Check logs:**
```powershell
docker logs applylens-grafana-prod --tail 50
```

**Restart container:**
```powershell
docker restart applylens-grafana-prod
```

## 📁 Configuration Files

**Production compose:** `docker-compose.prod.yml`  
**Dev/Infra compose:** `infra/docker-compose.yml`  
**Dashboard JSON:** `docs/phase3_grafana_dashboard.json`  
**Grafana config:** `infra/grafana/grafana.ini`  
**Provisioning:** `infra/grafana/provisioning/`  

## 🔗 Quick Links

- **Grafana:** http://localhost:3000
- **API:** http://localhost:8000
- **Dashboard:** http://localhost:3000/d/applylens-overview
- **Prometheus:** http://localhost:9090

## 📚 Documentation

- `README_GRAFANA.md` - Complete setup guide
- `INSTALL_GRAFANA.md` - Installation methods
- `GRAFANA_SETUP.md` - Detailed configuration
- `GRAFANA_QUICKSTART.md` - Quick reference

## 🎯 Common Workflows

### First-time setup
1. Open Grafana → Create datasource → Get API key → Import dashboard

### Update dashboard
```powershell
cd D:\ApplyLens\docs
.\import_grafana_dashboard.ps1 -ApiKey "YOUR_KEY"
```

### Restart after config change
```powershell
docker restart applylens-grafana-prod
```

### Rebuild with new plugins
```powershell
cd D:\ApplyLens
docker-compose -f docker-compose.prod.yml up -d --force-recreate grafana
```

---

**Status:** ✅ Ready to import dashboard!  
**Last Updated:** October 20, 2025
