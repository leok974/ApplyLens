# Grafana Dashboard Setup - Complete Guide

## 📋 Overview

This directory contains everything you need to set up Grafana and import the ApplyLens Overview dashboard.

## 🗂️ Files in This Directory

| File | Purpose |
|------|---------|
| **Setup & Installation** |
| `INSTALL_GRAFANA.md` | Complete guide to install Grafana on Windows |
| `INSTALL_GRAFANA_PLUGIN.md` | Guide to install JSON API datasource plugin |
| `install_grafana_plugin.ps1` | Automated plugin installation script |
| **Dashboard** |
| `phase3_grafana_dashboard.json` | Dashboard definition (ready to import) |
| `import_grafana_dashboard.ps1` | Automated dashboard import script |
| **Verification & Testing** |
| `verify_grafana_setup.ps1` | Pre-import setup verification |
| `test_dashboard_endpoints.ps1` | Test all API endpoints |
| **Documentation** |
| `GRAFANA_SETUP.md` | Detailed setup and troubleshooting guide |
| `GRAFANA_QUICKSTART.md` | Quick reference guide |
| `README_GRAFANA.md` | This file |

## 🚀 Quick Start

### Prerequisites

- ✅ API server running on port 8000
- ⚠️ Grafana installed (if not, see Step 1)
- ⚠️ JSON API datasource plugin installed (see Step 2)

### Step 1: Install Grafana (if not installed)

**Option A: Using Chocolatey (easiest)**
```powershell
# Run as Administrator
choco install grafana
Start-Service grafana
```

**Option B: MSI Installer**
1. Download from: https://grafana.com/grafana/download?platform=windows
2. Install MSI file
3. Service starts automatically

**Option C: Docker**
```powershell
docker run -d --name=grafana -p 3000:3000 `
  -e "GF_INSTALL_PLUGINS=marcusolsson-json-datasource" `
  grafana/grafana:latest
```

**Full guide:** See [`INSTALL_GRAFANA.md`](./INSTALL_GRAFANA.md)

### Step 2: Install JSON API Plugin

**After Grafana is running:**

```powershell
cd D:\ApplyLens\docs
.\install_grafana_plugin.ps1
```

**If Grafana not found**, manually specify path:
```powershell
.\install_grafana_plugin.ps1 -GrafanaPath "C:\Program Files\GrafanaLabs\grafana"
```

**Docker users:** Plugin is auto-installed if you used the docker command above.

**Full guide:** See [`INSTALL_GRAFANA_PLUGIN.md`](./INSTALL_GRAFANA_PLUGIN.md)

### Step 3: Create Datasource

1. Open Grafana: http://localhost:3000
2. Login: `admin` / `admin` (change password on first login)
3. Go to: **Configuration (⚙️) → Data Sources → Add data source**
4. Search: **"JSON API"**
5. Configure:
   - **Name:** `ApplyLens API`
   - **URL:** (leave empty - panels use their own URLs)
6. Click: **Save & Test**

### Step 4: Get API Key

1. Go to: **Configuration (⚙️) → API Keys**
2. Click: **New API Key**
3. Configure:
   - **Key name:** `Dashboard Import`
   - **Role:** `Admin` or `Editor`
4. Click: **Add**
5. **Copy the key** (you won't see it again!)

### Step 5: Verify Setup

```powershell
cd D:\ApplyLens\docs

# Test API endpoints
.\test_dashboard_endpoints.ps1

# Verify Grafana setup
.\verify_grafana_setup.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_KEY"
```

### Step 6: Import Dashboard

```powershell
.\import_grafana_dashboard.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_KEY"
```

**If datasource has different name:**
```powershell
.\import_grafana_dashboard.ps1 `
  -GrafanaUrl "http://localhost:3000" `
  -ApiKey "YOUR_API_KEY" `
  -DatasourceName "Your Datasource Name" `
  -RemapDatasource
```

### Step 7: View Dashboard

Open: http://localhost:3000/d/applylens-overview/applylens-overview

## 📊 Dashboard Details

**Title:** ApplyLens Overview  
**UID:** applylens-overview  
**Panels:** 4  
**Refresh:** 30 seconds  

### Panels

1. **Warehouse Divergence (24h)** - Stat
   - Shows: Divergence percentage
   - Thresholds: 🟢 <2%, 🟡 2-5%, 🔴 >5%
   - Endpoint: `/api/metrics/divergence-24h`

2. **Activity by Day** - Timeseries
   - Shows: Daily message counts (30 days)
   - Endpoint: `/api/metrics/activity-daily`

3. **Top Senders (30d)** - Table
   - Shows: Top 10 senders
   - Endpoint: `/api/metrics/top-senders-30d`

4. **Categories (30d)** - Bar Chart
   - Shows: Message distribution
   - Endpoint: `/api/metrics/categories-30d`

## 🧪 Testing

### Test API Endpoints

```powershell
.\test_dashboard_endpoints.ps1
```

**Expected output:**
```
✅ All endpoints ready for Grafana!
Total Tests:  4
Passed:       4
Failed:       0
Success Rate: 100%
```

### Test Grafana Setup

```powershell
.\verify_grafana_setup.ps1 -ApiKey "YOUR_API_KEY"
```

**Checks:**
- ✅ Grafana connectivity
- ✅ API key validity
- ✅ Plugin installation
- ✅ Datasource configuration
- ✅ API endpoint availability

## 🔧 Troubleshooting

### Grafana Not Found

**Problem:** `install_grafana_plugin.ps1` says "Grafana installation not found"

**Solution:**
1. Install Grafana first: See [`INSTALL_GRAFANA.md`](./INSTALL_GRAFANA.md)
2. Or specify path: `.\install_grafana_plugin.ps1 -GrafanaPath "C:\path\to\grafana"`

### Plugin Installation Failed

**Problem:** Permission errors during plugin installation

**Solution:**
1. Run PowerShell as Administrator
2. Or manually download plugin: https://grafana.com/grafana/plugins/marcusolsson-json-datasource/
3. Extract to: `C:\Program Files\GrafanaLabs\grafana\data\plugins\`

### Dashboard Shows "No Data"

**Problem:** Panels show "No Data" after import

**Solutions:**
1. **Check API server:**
   ```powershell
   curl.exe http://127.0.0.1:8000/api/metrics/divergence-24h
   ```

2. **Check datasource:**
   - Go to datasource settings
   - Click "Save & Test"

3. **Check api_base variable:**
   - Click variable dropdown at top of dashboard
   - Verify it points to: `http://127.0.0.1:8000`

4. **Test endpoints:**
   ```powershell
   .\test_dashboard_endpoints.ps1
   ```

### Datasource Not Found

**Problem:** After import, panels show "Datasource not found"

**Solution:**
```powershell
# Remap datasource during import
.\import_grafana_dashboard.ps1 `
  -ApiKey "YOUR_KEY" `
  -DatasourceName "Your Actual Datasource Name" `
  -RemapDatasource
```

### Port 3000 Conflict

**Problem:** Another service using port 3000

**Solution:**
```powershell
# Find and kill process
netstat -ano | findstr :3000
Stop-Process -Id <PID> -Force

# Or configure Grafana to use different port
# Edit: C:\Program Files\GrafanaLabs\grafana\conf\defaults.ini
# Change: http_port = 3001
```

## 📚 Documentation

| Document | What It Covers |
|----------|----------------|
| **INSTALL_GRAFANA.md** | Grafana installation methods (Chocolatey, MSI, Docker) |
| **INSTALL_GRAFANA_PLUGIN.md** | Plugin installation methods and troubleshooting |
| **GRAFANA_SETUP.md** | Complete setup guide, configuration, troubleshooting |
| **GRAFANA_QUICKSTART.md** | Quick reference, checklists, common commands |

## 🎯 Common Workflows

### Fresh Installation

```powershell
# 1. Install Grafana (run as Admin)
choco install grafana
Start-Service grafana

# 2. Install plugin
cd D:\ApplyLens\docs
.\install_grafana_plugin.ps1

# 3. Open Grafana, create datasource, get API key

# 4. Import dashboard
.\import_grafana_dashboard.ps1 -ApiKey "YOUR_KEY"
```

### Update Dashboard

```powershell
# Just re-run import (overwrite=true)
.\import_grafana_dashboard.ps1 -ApiKey "YOUR_KEY"
```

### Verify Everything

```powershell
# Test API
.\test_dashboard_endpoints.ps1

# Verify Grafana
.\verify_grafana_setup.ps1 -ApiKey "YOUR_KEY"

# Import dashboard
.\import_grafana_dashboard.ps1 -ApiKey "YOUR_KEY"
```

## 🐳 Docker Alternative

If you prefer containerized setup:

```powershell
# Single command setup
docker run -d `
  --name=grafana `
  -p 3000:3000 `
  -e "GF_INSTALL_PLUGINS=marcusolsson-json-datasource" `
  -e "GF_AUTH_ANONYMOUS_ENABLED=true" `
  -e "GF_AUTH_ANONYMOUS_ORG_ROLE=Admin" `
  grafana/grafana:latest

# Wait for startup
Start-Sleep -Seconds 10

# Import dashboard
.\import_grafana_dashboard.ps1 -ApiKey "YOUR_KEY"
```

## 📞 Support

If you encounter issues:

1. Check troubleshooting sections in guides
2. Review Grafana logs: `C:\Program Files\GrafanaLabs\grafana\data\log\grafana.log`
3. Test API endpoints: `.\test_dashboard_endpoints.ps1`
4. Verify setup: `.\verify_grafana_setup.ps1`

## 🔗 Quick Links

- **Grafana UI:** http://localhost:3000
- **API Base:** http://127.0.0.1:8000
- **Dashboard URL:** http://localhost:3000/d/applylens-overview
- **Grafana Downloads:** https://grafana.com/grafana/download
- **Plugin Page:** https://grafana.com/grafana/plugins/marcusolsson-json-datasource/

---

**Summary:** Install Grafana → Install plugin → Create datasource → Import dashboard → Done! 🎉
