# ApplyLens Changes Verification Guide

**Date**: October 22, 2025
**Status**: Changes Deployed ✅

## Quick Verification Steps

### 1. UI Changes - Button Rename "Inbox (Actions)" → "Actions"

The button changes are deployed and running in the container built at **19:07:10**.

**Where to see the changes**:

#### Option A: Visit the Live App
1. Open your browser to: **http://localhost:5175**
2. Look at the **top navigation bar**
3. You should see a button labeled "**Actions**" (not "Inbox (Actions)")
4. Hard refresh if needed: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)

#### Option B: Check the Navigation Menu
1. Go to: **http://localhost:5175**
2. Look for the **hamburger menu** or **navigation menu**
3. The link should say "**Actions**" instead of "**Inbox (Actions)**"

#### Files Modified:
- ✅ `apps/web/src/components/Nav.tsx` - Line 20: `'Actions'`
- ✅ `apps/web/src/components/AppHeader.tsx` - Line 136: `["Actions", "/inbox-actions"]`
- ✅ Container built: `leoklemet/applylens-web:latest` at 2025-10-22 19:07:10

**Tailwind Classes Applied**:
```tsx
className="inline-flex items-center justify-center h-9 px-3 py-0.5 whitespace-nowrap rounded-xl text-sm leading-none border bg-card hover:bg-secondary transition-colors"
aria-label={label}
```

### 2. Grafana Metrics - Dashboards & Visualizations

**Access Grafana**:
- URL: **http://localhost:3000**
- Username: `admin`
- Password: `admin` (or your configured password)

**What to see after login**:

#### A. Dashboards Available (5 total):

1. **ApplyLens - System Overview** 🆕
   - URL: http://localhost:3000/d/applylens-overview
   - 12 panels with comprehensive metrics
   - Shows: DB status, ES status, HTTP traffic, latency, risk distribution, etc.

2. **ApplyLens Security Monitoring**
   - URL: http://localhost:3000/d/applylens-security
   - 8 panels focusing on security metrics
   - Shows: CSRF, crypto operations, reCAPTCHA, rate limiting

3. **ApplyLens — Traffic** ✅ Fixed
   - URL: http://localhost:3000/d/applylens-traffic
   - 6 panels for HTTP traffic analysis
   - Fixed errors, updated to use `applylens_*` metrics

4. **API Status & Health Monitoring**
   - URL: http://localhost:3000/d/api-status-health
   - 6 panels for health checks

5. **Assistant (Windows & Hit Ratio)**
   - URL: http://localhost:3000/d/applylens-assistant-windows
   - 8 panels for chat analytics

#### B. How to Navigate:
1. Click **☰ menu** (top left)
2. Click **Dashboards**
3. Click **ApplyLens** folder
4. Select any dashboard

#### C. Key Metrics You'll See:

**System Health**:
- `applylens_db_up` - Database status (should show 1)
- `applylens_es_up` - Elasticsearch status (should show 1)
- `applylens_gmail_connected` - Gmail connection status

**HTTP Traffic**:
- `applylens_http_requests_total` - Total requests per second
- Error rates by status code (4xx, 5xx)
- Request latency (P50, P95, P99)

**Business Metrics**:
- `applylens_email_risk_served_total` - Email risk distribution
- `applylens_backfill_inserted_total` - Gmail sync rate
- `applylens_backfill_duration_seconds` - Sync performance

**Security**:
- `applylens_csrf_success_total` / `applylens_csrf_fail_total`
- `applylens_crypto_encrypt_total` / `applylens_crypto_decrypt_total`
- `applylens_rate_limit_allowed_total` / `applylens_rate_limit_exceeded_total`

### 3. Verify Metrics are Flowing

**Check Prometheus directly**:
```bash
# Open in browser:
http://localhost:9090

# Or query via curl:
curl "http://localhost:9090/api/v1/query?query=applylens_http_requests_total"
```

**Expected Output**:
```json
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {
          "__name__": "applylens_http_requests_total",
          "app_name": "applylens_api",
          "method": "GET",
          "path": "/ready",
          "status_code": "200"
        },
        "value": [1729645200, "123"]
      }
    ]
  }
}
```

## Troubleshooting: "I don't see the changes"

### UI Changes Not Visible:

**Problem**: Browser cache is showing old version

**Solution**:
```bash
# Hard refresh the browser
# Windows: Ctrl + Shift + R
# Mac: Cmd + Shift + R

# Or clear browser cache:
# 1. Open DevTools (F12)
# 2. Right-click the refresh button
# 3. Select "Empty Cache and Hard Reload"
```

**Problem**: Wrong port

**Solution**:
```bash
# Make sure you're accessing the right port:
http://localhost:5175  ✅ (correct)
# NOT http://localhost:3000 (that's Grafana)
# NOT http://localhost:5173 (old dev port)
```

**Problem**: Container not updated

**Solution**:
```powershell
# Verify container is running the new image
docker ps --filter "name=applylens-web-prod" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

# If needed, restart the container
docker compose -f docker-compose.prod.yml restart web
```

### Grafana Dashboards Not Visible:

**Problem**: Not logged in

**Solution**:
1. Go to http://localhost:3000
2. Login with: admin / admin
3. Navigate to Dashboards

**Problem**: Dashboards not provisioned

**Solution**:
```powershell
# Check provisioning logs
docker logs applylens-grafana-prod | Select-String "provisioning.dashboard"

# Should show:
# logger=provisioning.dashboard ... msg="starting to provision dashboards"
# logger=provisioning.dashboard ... msg="finished to provision dashboards"
# (No error messages)
```

**Problem**: Metrics not showing data

**Solution**:
```powershell
# 1. Check Prometheus is reachable
docker exec applylens-grafana-prod wget -qO- http://applylens-prometheus-prod:9090/-/healthy

# 2. Check metrics exist in Prometheus
curl "http://localhost:9090/api/v1/query?query=applylens_http_requests_total"

# 3. Verify datasource in Grafana
# Go to: Settings → Data Sources → Prometheus
# Click "Test" button - should show "Data source is working"
```

## What Changed - Summary

### UI Changes ✅
- **Nav.tsx**: Button text changed from "Inbox (Actions)" to "Actions"
- **AppHeader.tsx**: Navigation menu item changed to "Actions"
- **Tailwind classes**: Added `whitespace-nowrap`, `inline-flex`, proper spacing
- **Container**: Rebuilt at 2025-10-22 19:07:10
- **Access**: http://localhost:5175

### Grafana Changes ✅
- **Datasource**: Prometheus connected at `http://applylens-prometheus-prod:9090`
- **Dashboards**: 5 dashboards provisioned successfully
- **New dashboard**: `applylens-overview.json` with 12 comprehensive panels
- **Fixed dashboard**: `traffic_import.json` now loads without errors
- **Metrics**: 50+ `applylens_*` metrics available
- **Access**: http://localhost:3000 (login: admin/admin)

## Quick Links

### Frontend (UI Changes)
- **Main App**: http://localhost:5175
- **Actions Page**: http://localhost:5175/inbox-actions

### Monitoring (Grafana)
- **Grafana Login**: http://localhost:3000
- **System Overview**: http://localhost:3000/d/applylens-overview
- **Security Dashboard**: http://localhost:3000/d/applylens-security
- **Traffic Dashboard**: http://localhost:3000/d/applylens-traffic

### Metrics (Prometheus)
- **Prometheus UI**: http://localhost:9090
- **Metrics Endpoint**: http://localhost:9090/api/v1/label/__name__/values

## Next Actions

If you still don't see the changes:

1. **Clear browser cache completely**
2. **Try in incognito/private window**
3. **Access http://localhost:5175 directly** (not through nginx if that's configured)
4. **Check browser console** (F12) for any JavaScript errors
5. **Verify you're on the right port** (5175 for web, 3000 for Grafana)

Let me know which specific change you're trying to see and I can help troubleshoot further!
