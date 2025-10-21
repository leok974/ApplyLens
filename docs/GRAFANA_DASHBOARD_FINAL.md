# ✅ Grafana Dashboard - Final Configuration Complete

**Date:** October 20, 2025  
**Dashboard:** ApplyLens Phase 4 Overview  
**Version:** 6  
**Status:** ✅ READY TO USE

---

## 🎯 Dashboard Successfully Configured

**URL:** http://localhost:3000/d/applylens-phase4-overview/applylens-phase-4-overview  
**Login:** admin / admin123

---

## ✅ What Was Fixed

### 1. Correct Field Names Mapped

The dashboard now uses the **actual field names** returned by your API:

| Panel | Endpoint | Fields Used |
|-------|----------|-------------|
| Activity by Day | `/api/metrics/profile/activity_daily` | `day`, `messages_count` |
| Unique Senders | `/api/metrics/profile/activity_daily` | `day`, `unique_senders` |
| Top Senders | `/api/metrics/profile/top_senders_30d` | `from_email`, `messages_30d` |
| Categories | `/api/metrics/profile/categories_30d` | `category`, `messages_30d` |

### 2. Proper JSON Path Selectors

All panels now use: `$.rows[*]` to correctly extract data from the API response structure:

```json
{
  "rows": [
    { "day": "2025-10-17", "messages_count": 14, ... },
    { "day": "2025-10-16", "messages_count": 37, ... }
  ],
  "count": 90,
  "source": "bigquery"
}
```

### 3. Relative URLs with Datasource Base

All panel URLs are relative (e.g., `/api/metrics/profile/activity_daily`)  
Datasource provides the base: `http://applylens-api-prod:8003`  
Final URL: `http://applylens-api-prod:8003/api/metrics/profile/activity_daily`

### 4. Proper Transformations

Each panel has appropriate transformations:

- **Timeseries panels:** `extractFields` to parse JSON into tabular format
- **Table panel:** `extractFields` + `organize` to select/rename columns
- **Barchart panel:** `extractFields` + `organize` for proper field mapping

---

## 📊 Panel Details

### Panel 1: Activity by Day (Messages)
- **Type:** Timeseries (Bar Chart)
- **Data:** 90 days of message activity
- **Fields:** `day` (x-axis), `messages_count` (y-axis)
- **Style:** Bars with 80% fill opacity
- **Current Data:** 14-209 messages per day

### Panel 2: Unique Senders by Day
- **Type:** Timeseries (Line Chart)
- **Data:** Same endpoint, different visualization
- **Fields:** `day` (x-axis), `unique_senders` (y-axis)
- **Style:** Line with 10% fill opacity
- **Note:** Can be updated later to use dedicated endpoint

### Panel 3: Top Senders (30 Days)
- **Type:** Table
- **Data:** 20 senders ranked by message count
- **Columns:** 
  - `from_email` → "Sender"
  - `messages_30d` → "Messages"
- **Hidden:** `first_message_at`, `last_message_at`, `active_days`, `total_size_mb`
- **Top Sender:** Leo Klemet <notifications@github.com> (733 messages)

### Panel 4: Categories (30 Days)
- **Type:** Horizontal Bar Chart
- **Data:** 4 email categories
- **Fields:**
  - `category` → "Category"
  - `messages_30d` → "Messages"
- **Hidden:** `pct_of_total`, `total_size_mb`
- **Categories:** updates (904), forums (142), promotions (62), social (43)

---

## ✅ Verification Results

### Network Connectivity
```bash
docker exec applylens-grafana-prod wget -qO- http://applylens-api-prod:8003/healthz
```
**Result:** ✅ `{"status":"ok"}`

### Data Endpoints
| Endpoint | Rows Returned | Status |
|----------|---------------|--------|
| `/api/metrics/profile/activity_daily` | 90 | ✅ |
| `/api/metrics/profile/top_senders_30d` | 20 | ✅ |
| `/api/metrics/profile/categories_30d` | 4 | ✅ |

### Datasource Configuration
- **Name:** ApplyLens API
- **Type:** marcusolsson-json-datasource
- **URL:** http://applylens-api-prod:8003
- **Access:** Proxy
- **UID:** bf1n52g0leghsb
- **Status:** ✅ Configured and working

### Panel Bindings
- ✅ All 4 panels bound to "ApplyLens API" datasource
- ✅ All using relative URLs (start with `/`)
- ✅ All using correct JSONPath: `$.rows[*]`
- ✅ All have appropriate transformations

---

## 🚀 How to Use the Dashboard

### 1. Open Dashboard
```
http://localhost:3000/d/applylens-phase4-overview
```

### 2. Expected Behavior
- All 4 panels should display data immediately
- No "Bad Gateway" errors
- No "No Data" messages
- Charts refresh every 30 seconds

### 3. Explore Data (Optional)
To test individual queries:
1. Go to: Explore (compass icon in sidebar)
2. Select: "ApplyLens API" datasource
3. Method: GET
4. URL: `/api/metrics/profile/activity_daily`
5. Root selector: `$`
6. Fields: `$.rows[*]`
7. Click: **Run Query**
8. Should see: Table with 90 rows

### 4. Customize Panels (Optional)
To modify a panel:
1. Click panel title → **Edit**
2. **Query tab:** Modify URL, JSONPath, or method
3. **Transform tab:** Add/modify field transformations
4. **Panel options:** Change visualization settings
5. **Save** dashboard when done

---

## 🔧 Technical Details

### API Response Structure
All endpoints return data in this format:
```json
{
  "rows": [ /* array of objects */ ],
  "count": 90,
  "source": "bigquery",
  "dataset": "applylens-gmail-..."
}
```

### JSONPath Selector
`$.rows[*]` extracts all objects from the `rows` array:
```
$ = root object
.rows = get the "rows" property
[*] = all elements in the array
```

### Field Extraction
The `extractFields` transformation converts JSON array into Grafana table format:
```
Input:  [{"day":"2025-10-17", "messages_count":14}, ...]
Output: Table with columns: day, messages_count, unique_senders, etc.
```

### Column Organization
The `organize` transformation:
- **Renames:** `from_email` → "Sender", `messages_30d` → "Messages"
- **Excludes:** Fields you don't want to display
- **Reorders:** Columns by index (0 = first, 1 = second, etc.)

---

## 🐛 Troubleshooting

### If Panels Show "No Data"

**Check datasource:**
```powershell
# Test from Grafana container
docker exec applylens-grafana-prod wget -qO- http://applylens-api-prod:8003/api/metrics/profile/activity_daily
```

**Verify datasource in UI:**
1. Go to: Connections → Data sources → ApplyLens API
2. Click: **Test**
3. Should see: "Data source is working"

### If Panels Show "Bad Gateway"

**Check API container:**
```powershell
docker ps | Select-String api-prod
curl.exe http://localhost:8003/healthz
```

**Check Grafana logs:**
```powershell
docker logs applylens-grafana-prod --tail 50 | Select-String error
```

### If Wrong Data Displayed

**Check field names:**
```powershell
# Test actual API response
curl.exe http://localhost:8003/api/metrics/profile/activity_daily | ConvertFrom-Json | Select-Object -ExpandProperty rows | Select-Object -First 1
```

**Verify panel configuration:**
1. Edit panel
2. Check **Query** tab → JSONPath should be `$.rows[*]`
3. Check **Transform** tab → Field names match API response

---

## 📋 Quick Reference

### Container Info
```
API:     applylens-api-prod (port 8003)
Grafana: applylens-grafana-prod (port 3000)
Network: applylens_applylens-prod
```

### Datasource Config
```
Name:   ApplyLens API
Type:   marcusolsson-json-datasource
URL:    http://applylens-api-prod:8003
Access: proxy
```

### API Endpoints
```
/api/metrics/profile/activity_daily     (90 days)
/api/metrics/profile/top_senders_30d    (20 senders)
/api/metrics/profile/categories_30d     (4 categories)
```

### Dashboard Access
```
URL:      http://localhost:3000/d/applylens-phase4-overview
Login:    admin / admin123
Refresh:  30 seconds
Version:  6
```

---

## 🎉 Success Checklist

- ✅ Dashboard imported (version 6)
- ✅ All panels bound to correct datasource
- ✅ All URLs using relative paths
- ✅ All JSONPath selectors correct (`$.rows[*]`)
- ✅ All field names match API response
- ✅ All transformations configured
- ✅ All endpoints returning data
- ✅ Network connectivity verified
- ✅ No errors in Grafana logs
- ✅ Dashboard accessible at URL

---

## 📁 Files Created

1. **phase3_grafana_dashboard.relative.json** - Final working dashboard
2. **GRAFANA_DASHBOARD_FINAL.md** - This documentation
3. **GRAFANA_VERIFICATION_REPORT.md** - Detailed verification steps
4. **DOCKER_NETWORK_FIX.md** - Docker networking guide
5. **GRAFANA_BAD_GATEWAY_FIX.md** - Troubleshooting guide

---

**Status:** ✅ COMPLETE  
**Dashboard:** http://localhost:3000/d/applylens-phase4-overview  
**All Systems:** OPERATIONAL 🚀
