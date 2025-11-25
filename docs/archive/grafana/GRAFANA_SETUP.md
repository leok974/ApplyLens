# Grafana Dashboard Setup Guide

This guide explains how to set up and import the ApplyLens Overview dashboard into Grafana.

## Prerequisites

1. **Grafana** running (default: `http://localhost:3000`)
2. **JSON API datasource plugin** installed: `marcusolsson-json-datasource`
3. **API server** running on port 8000
4. **Grafana API key** with Admin or Editor role

## Quick Start

### 1. Verify Your Setup

Run the verification script to check if everything is ready:

```powershell
cd docs
.\verify_grafana_setup.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_TOKEN"
```

This checks:
- ✅ Grafana connectivity
- ✅ API key validity
- ✅ JSON API datasource plugin installation
- ✅ Existing datasources
- ✅ API endpoint availability

### 2. Import the Dashboard

#### Option A: Using the Import Script (Recommended)

```powershell
.\import_grafana_dashboard.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_TOKEN"
```

If your datasource has a different name than "ApplyLens API", use:

```powershell
.\import_grafana_dashboard.ps1 `
  -GrafanaUrl "http://localhost:3000" `
  -ApiKey "YOUR_API_TOKEN" `
  -DatasourceName "Your Datasource Name" `
  -RemapDatasource
```

#### Option B: Manual Import via Grafana UI

1. Open Grafana → Dashboards → Import
2. Click "Upload JSON file"
3. Select `phase3_grafana_dashboard.json`
4. Click "Import"
5. If prompted, select your JSON API datasource

#### Option C: Import via Grafana API (Raw)

```powershell
$env:GRAFANA_URL = "http://localhost:3000"
$env:GRAFANA_API_KEY = "YOUR_API_TOKEN"

$dash = Get-Content phase3_grafana_dashboard.json -Raw
$body = @{
  dashboard = ($dash | ConvertFrom-Json)
  overwrite = $true
  folderId  = 0
} | ConvertTo-Json -Depth 200

Invoke-RestMethod -Uri "$env:GRAFANA_URL/api/dashboards/import" `
  -Headers @{ Authorization = "Bearer $env:GRAFANA_API_KEY" } `
  -ContentType "application/json" -Method Post -Body $body
```

## Dashboard Configuration

### Panels Overview

The dashboard includes 4 main panels:

1. **Warehouse Divergence (24h)** - Stat panel
   - Shows divergence percentage between Elasticsearch and BigQuery
   - Color thresholds:
     - 🟢 Green: < 2%
     - 🟡 Yellow: 2-5%
     - 🔴 Red: > 5%
   - Endpoint: `/api/metrics/divergence-24h`

2. **Activity by Day** - Timeseries chart
   - Daily email message counts (last 30 days)
   - Bar chart visualization
   - Endpoint: `/api/metrics/activity-daily`

3. **Top Senders (30d)** - Table
   - Top 10 email senders by volume
   - Endpoint: `/api/metrics/top-senders-30d`

4. **Categories (30d)** - Bar chart
   - Message distribution by category
   - Horizontal orientation
   - Endpoint: `/api/metrics/categories-30d`

### Dashboard Variables

- **api_base**: Base URL for API endpoints (default: `http://127.0.0.1:8000`)
  - Change this if your API runs on a different host/port
  - Click the variable at the top of the dashboard to edit

### Refresh Rate

- Default: 30 seconds
- Change via dashboard settings (⚙️ icon → General → Auto refresh)

## Troubleshooting

### Dashboard shows "No Data"

1. **Check API server is running:**
   ```powershell
   curl.exe http://127.0.0.1:8000/api/metrics/divergence-24h
   ```

2. **Verify datasource configuration:**
   - Go to Configuration → Data Sources → ApplyLens API
   - Click "Save & Test"

3. **Check panel queries:**
   - Edit a panel → Query tab
   - Verify the URL is correct
   - Check "Query Inspector" for error details

### Plugin Not Found

Install the JSON API datasource plugin:

```bash
grafana-cli plugins install marcusolsson-json-datasource
```

Then restart Grafana:

```powershell
# Windows (if running as service)
Restart-Service grafana

# Or if running manually, stop and restart the Grafana process
```

### API Key Issues

1. **Create a new API key:**
   - Go to Configuration → API Keys
   - Click "New API Key"
   - Name: "Dashboard Import"
   - Role: "Admin" or "Editor"
   - Copy the generated key immediately (you won't see it again)

2. **Test the API key:**
   ```powershell
   $headers = @{ Authorization = "Bearer YOUR_API_TOKEN" }
   Invoke-RestMethod -Uri "http://localhost:3000/api/org" -Headers $headers
   ```

### Datasource UID Mismatch

If panels show "Datasource not found":

1. **Find your datasource UID:**
   ```powershell
   $headers = @{ Authorization = "Bearer YOUR_API_TOKEN" }
   Invoke-RestMethod -Uri "http://localhost:3000/api/datasources" -Headers $headers |
     Where-Object { $_.type -eq "marcusolsson-json-datasource" } |
     Select-Object name, uid
   ```

2. **Re-import with remap:**
   ```powershell
   .\import_grafana_dashboard.ps1 `
     -GrafanaUrl "http://localhost:3000" `
     -ApiKey "YOUR_API_TOKEN" `
     -DatasourceName "Your Datasource Name" `
     -RemapDatasource
   ```

### Wrong API Base URL

1. Edit the dashboard
2. Click "Dashboard settings" (⚙️)
3. Go to "Variables" → "api_base"
4. Update the value to your API URL
5. Click "Save dashboard"

## API Endpoints Reference

The dashboard queries these endpoints:

| Endpoint | Description | Response Fields |
|----------|-------------|-----------------|
| `/api/metrics/divergence-24h` | Divergence percentage | `divergence_pct`, `status`, `message` |
| `/api/metrics/activity-daily` | Daily message counts | Array of `{date, message_count}` |
| `/api/metrics/top-senders-30d` | Top senders | Array of `{sender, messages}` |
| `/api/metrics/categories-30d` | Category distribution | Array of `{category, messages}` |

### Example Response Format

**Divergence:**
```json
{
  "divergence_pct": 0.15,
  "status": "ok",
  "message": "Data is in sync"
}
```

**Activity Daily:**
```json
[
  {"date": "2025-10-01", "message_count": 42},
  {"date": "2025-10-02", "message_count": 38}
]
```

**Top Senders:**
```json
[
  {"sender": "alice@example.com", "messages": 125},
  {"sender": "bob@example.com", "messages": 98}
]
```

**Categories:**
```json
[
  {"category": "Work", "messages": 234},
  {"category": "Personal", "messages": 156}
]
```

## Files in this Directory

- **`phase3_grafana_dashboard.json`** - Main dashboard definition
- **`import_grafana_dashboard.ps1`** - Automated import script
- **`verify_grafana_setup.ps1`** - Setup verification script
- **`GRAFANA_SETUP.md`** - This documentation (you are here)

## Next Steps

After importing the dashboard:

1. ✅ Verify all panels display data
2. ✅ Customize the refresh rate if needed
3. ✅ Add to your favorites or a folder
4. ✅ Share the dashboard URL with your team
5. ✅ Set up alerts (optional)

## Support

If you encounter issues:

1. Check the [Grafana logs](http://localhost:3000/admin/server)
2. Review API server logs for endpoint errors
3. Verify network connectivity between Grafana and API
4. Check browser console for JavaScript errors

## Additional Resources

- [Grafana Documentation](https://grafana.com/docs/)
- [JSON API Datasource Plugin](https://grafana.com/grafana/plugins/marcusolsson-json-datasource/)
- [Grafana HTTP API](https://grafana.com/docs/grafana/latest/developers/http_api/)
