# Grafana "Bad Gateway" Fix - RESOLVED ✅

## Problem

When trying to access the Grafana dashboard, you saw a "Bad Gateway" error. This was caused by **two issues**:

1. **Wrong API Port**: Dashboard was configured for port 8000, but ApplyLens API runs on port **8003**
2. **Wrong Host**: Dashboard used `127.0.0.1` which doesn't work from inside Docker container
3. **Wrong Endpoint Paths**: Dashboard endpoints didn't match the actual API structure

## Root Cause

```
# What Grafana was trying to access (WRONG):
http://127.0.0.1:8000/api/metrics/divergence-24h  ❌
http://127.0.0.1:8000/api/metrics/activity-daily  ❌

# What actually exists (CORRECT):
http://host.docker.internal:8003/api/metrics/profile/activity_daily  ✅
http://host.docker.internal:8003/api/metrics/profile/top_senders_30d  ✅
http://host.docker.internal:8003/api/metrics/profile/categories_30d  ✅
```

### Why host.docker.internal?

- **Grafana** runs inside a Docker container (`applylens-grafana-prod`)
- **ApplyLens API** runs in another container but exposes port 8003 to the host
- From inside a container, `127.0.0.1` refers to the container itself, not your Windows host
- `host.docker.internal` is Docker's special DNS name that resolves to your host machine

## Solution Applied

### 1. Updated Dashboard Configuration

**File:** `docs/phase4_grafana_dashboard.json` (copied to `phase3_grafana_dashboard.json`)

**Changes:**
- ✅ API Base URL: `http://127.0.0.1:8000` → `http://host.docker.internal:8003`
- ✅ Endpoint paths updated to match actual API:
  - Removed non-existent `divergence-24h` panel
  - Updated to use `/api/metrics/profile/*` endpoints
  - Added proper JSON field mappings

**New Panels:**
1. **Activity by Day (Messages)** - Bar chart showing daily message counts
2. **Unique Senders by Day** - Line chart showing sender diversity
3. **Top Senders (30 Days)** - Table with sender rankings
4. **Categories (30 Days)** - Horizontal bar chart of categories

### 2. Re-imported Dashboard

```powershell
.\import_grafana_dashboard.ps1 `
  -GrafanaUrl "http://localhost:3000" `
  -ApiKey "YOUR_GRAFANA_API_KEY"
```

## Verification

### Test Endpoints from Container

```powershell
# Test if Grafana can reach the API
docker exec applylens-grafana-prod wget -O- http://host.docker.internal:8003/api/metrics/profile/activity_daily
```

**Result:** ✅ Success - Returns 90 days of activity data

### Test from Host

```powershell
# Verify API is accessible from Windows
curl.exe http://localhost:8003/api/metrics/profile/activity_daily
curl.exe http://localhost:8003/api/metrics/profile/top_senders_30d
curl.exe http://localhost:8003/api/metrics/profile/categories_30d
```

**All working!** ✅

## Next Steps

1. **Create the datasource** in Grafana (still required):
   - Go to: http://localhost:3000/connections/datasources/new
   - Search: "JSON API"
   - **Name:** `ApplyLens API` (exact match!)
   - **URL:** (leave empty - panels have their own URLs)
   - Click: **Save & Test**

2. **View the dashboard**:
   - URL: http://localhost:3000/d/applylens-phase4-overview
   - Login: admin / admin123
   - You should now see **4 panels** with **real data**!

## Expected Results

Once you create the datasource, you'll see:

### Panel 1: Activity by Day (Messages)
- 90 days of email activity
- Bar chart showing message volumes
- Recent spike: 209 messages on Oct 1st

### Panel 2: Unique Senders by Day
- Line chart showing sender diversity
- Recent activity: 7-28 unique senders per day

### Panel 3: Top Senders (30 Days)
- Table ranking most active senders
- Shows message counts per sender

### Panel 4: Categories (30 Days)
- Horizontal bar chart
- Distribution of email categories

## API Container Info

```
Container:  applylens-api-prod
Port:       8003 (not 8000!)
Status:     Healthy ✅
Image:      (check with: docker inspect applylens-api-prod)
```

## Troubleshooting

### If you still see "Bad Gateway":

1. **Check API is running:**
   ```powershell
   docker ps | Select-String api-prod
   curl.exe http://localhost:8003/healthz
   ```

2. **Check Grafana can reach API:**
   ```powershell
   docker exec applylens-grafana-prod wget -O- http://host.docker.internal:8003/healthz
   ```

3. **Check datasource configuration:**
   - Go to: http://localhost:3000/connections/datasources
   - Find: "ApplyLens API"
   - Verify: Name is exact match (case-sensitive!)

### If panels show "No Data":

1. **Verify datasource exists:**
   - Must be named exactly: `ApplyLens API`
   - Type: `marcusolsson-json-datasource`

2. **Check dashboard variable:**
   - Click the `api_base` dropdown at top of dashboard
   - Should show: `http://host.docker.internal:8003`
   - Change if needed

3. **Test endpoints manually:**
   ```powershell
   curl.exe http://localhost:8003/api/metrics/profile/activity_daily
   ```

## Files Changed

1. **docs/phase4_grafana_dashboard.json** (NEW)
   - Complete rewrite with correct endpoints
   - Port 8003
   - host.docker.internal
   - Proper JSON field mappings

2. **docs/phase3_grafana_dashboard.json** (UPDATED)
   - Overwritten with phase4 version
   - Used by import script

3. **docs/GRAFANA_BAD_GATEWAY_FIX.md** (THIS FILE)
   - Documentation of the issue and fix

## Summary

✅ **Problem:** Dashboard couldn't reach API  
✅ **Cause:** Wrong port (8000 vs 8003) and wrong host (127.0.0.1 vs host.docker.internal)  
✅ **Solution:** Updated dashboard to use correct API endpoints and Docker networking  
✅ **Status:** Fixed and re-imported  
⏳ **Remaining:** Create "ApplyLens API" datasource in Grafana UI  

**Dashboard URL:** http://localhost:3000/d/applylens-phase4-overview  
**Next Action:** Create the JSON API datasource named "ApplyLens API"

---

**Date Fixed:** October 20, 2025  
**API Port:** 8003  
**Grafana Container:** applylens-grafana-prod
