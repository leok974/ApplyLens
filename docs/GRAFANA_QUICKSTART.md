# Grafana Dashboard - Quick Reference

## ✅ Dashboard Successfully Created

**File:** `docs/phase3_grafana_dashboard.json`

**Dashboard Details:**
- **UID:** `applylens-overview`
- **Title:** ApplyLens Overview
- **Panels:** 4
- **Variables:** 1 (api_base)
- **Refresh:** 30 seconds
- **Time Range:** Last 30 days

## 📊 Dashboard Panels

### 1. Warehouse Divergence (24h) - Stat Panel
- **Type:** stat
- **Endpoint:** `${api_base}/api/metrics/divergence-24h`
- **Position:** Top-left (8w × 4h)
- **Thresholds:**
  - 🟢 Green: < 2% divergence
  - 🟡 Yellow: 2-5% divergence
  - 🔴 Red: > 5% divergence
- **Unit:** Percent
- **Cache:** 15 seconds

### 2. Activity by Day - Timeseries
- **Type:** timeseries
- **Endpoint:** `${api_base}/api/metrics/activity-daily`
- **Position:** Full width (24w × 8h)
- **Visualization:** Bar chart
- **Shows:** Daily message counts over 30 days
- **Cache:** 30 seconds

### 3. Top Senders (30d) - Table
- **Type:** table
- **Endpoint:** `${api_base}/api/metrics/top-senders-30d`
- **Position:** Bottom-left (12w × 8h)
- **Columns:** sender, messages
- **Cache:** 30 seconds

### 4. Categories (30d) - Bar Chart
- **Type:** barchart
- **Endpoint:** `${api_base}/api/metrics/categories-30d`
- **Position:** Bottom-right (12w × 8h)
- **Orientation:** Horizontal
- **Cache:** 30 seconds

## 🚀 Import Instructions

### Method 1: Automated Script (Recommended)

```powershell
cd D:\ApplyLens\docs
.\import_grafana_dashboard.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_TOKEN"
```

### Method 2: Manual Import

1. Open Grafana: `http://localhost:3000`
2. Go to: Dashboards → Import
3. Upload: `docs/phase3_grafana_dashboard.json`
4. Click: Import

### Method 3: Verify First, Then Import

```powershell
# Step 1: Verify setup
.\verify_grafana_setup.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_TOKEN"

# Step 2: Import dashboard
.\import_grafana_dashboard.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_TOKEN"
```

## 🔧 Configuration

### Required: JSON API Datasource Plugin

Install if not already present:

```bash
grafana-cli plugins install marcusolsson-json-datasource
```

Then restart Grafana.

### Required: Datasource Setup

1. Go to: Configuration → Data Sources → Add data source
2. Search: "JSON API"
3. Name: "ApplyLens API" (or any name - can remap during import)
4. No URL needed (each panel has its own URL)
5. Click: Save & Test

### Optional: Customize API Base URL

After import, edit the `api_base` variable:
- Default: `http://127.0.0.1:8000`
- Click variable dropdown at top of dashboard to change

## ✅ Pre-flight Checklist

Before importing, ensure:

- [ ] Grafana is running (`http://localhost:3000`)
- [ ] API server is running on port 8000
- [ ] JSON API datasource plugin is installed
- [ ] At least one JSON API datasource exists in Grafana
- [ ] You have a Grafana API key (Admin or Editor role)
- [ ] API endpoints return data:
  - [ ] `/api/metrics/divergence-24h`
  - [ ] `/api/metrics/activity-daily`
  - [ ] `/api/metrics/top-senders-30d`
  - [ ] `/api/metrics/categories-30d`

## 🧪 Quick Test

```powershell
# Test API endpoints
$base = "http://127.0.0.1:8000"
curl.exe "$base/api/metrics/divergence-24h"
curl.exe "$base/api/metrics/activity-daily"
curl.exe "$base/api/metrics/top-senders-30d"
curl.exe "$base/api/metrics/categories-30d"

# Test Grafana
curl.exe http://localhost:3000/api/health
```

## 📁 Files Created

| File | Purpose |
|------|---------|
| `phase3_grafana_dashboard.json` | Dashboard definition (ready to import) |
| `import_grafana_dashboard.ps1` | Automated import script |
| `verify_grafana_setup.ps1` | Pre-import verification |
| `GRAFANA_SETUP.md` | Detailed setup guide |
| `GRAFANA_QUICKSTART.md` | This quick reference |

## 🐛 Common Issues

### "No Data" in Panels

**Cause:** API server not running or wrong URL

**Fix:**
```powershell
# Check API server
curl.exe http://127.0.0.1:8000/api/metrics/divergence-24h

# Update api_base variable in dashboard if needed
```

### "Datasource not found"

**Cause:** Dashboard expects datasource UID "ApplyLens API" but yours is different

**Fix:**
```powershell
.\import_grafana_dashboard.ps1 `
  -GrafanaUrl "http://localhost:3000" `
  -ApiKey "YOUR_TOKEN" `
  -DatasourceName "Your Datasource Name" `
  -RemapDatasource
```

### Plugin Not Found

**Cause:** JSON API datasource plugin not installed

**Fix:**
```bash
grafana-cli plugins install marcusolsson-json-datasource
# Then restart Grafana
```

## 🎯 Next Steps

After successful import:

1. ✅ Open dashboard in Grafana
2. ✅ Verify all 4 panels show data
3. ✅ Bookmark or add to a folder
4. ✅ Customize refresh rate if needed
5. ✅ Share URL with team members
6. ✅ Set up alerts (optional)

## 🔗 URLs

- **Grafana:** http://localhost:3000
- **API:** http://127.0.0.1:8000
- **Dashboard (after import):** http://localhost:3000/d/applylens-overview/applylens-overview

## 📚 Documentation

For detailed instructions, see: [`GRAFANA_SETUP.md`](./GRAFANA_SETUP.md)

---

**Status:** ✅ Dashboard JSON validated and ready to import!
