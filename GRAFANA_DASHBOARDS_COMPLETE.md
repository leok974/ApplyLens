# Grafana Dashboard Setup Complete

**Date**: October 22, 2025
**Status**: ✅ All Tasks Complete

## Summary of Actions Taken

### 1. Fixed traffic_import.json Dashboard Error ✅

**Problem**: Dashboard had wrong format (wrapped in `{"dashboard": {...}}`) causing "Dashboard title cannot be empty" error

**Solution**:
- Extracted dashboard object from API wrapper format
- Added unique UID: `applylens-traffic`
- Updated metric names to use `applylens_` prefix
- Fixed label names (`code` → `status_code`)

**Changes**:
- `http_requests_total` → `applylens_http_requests_total`
- `{code=~"4.."}` → `{status_code=~"4.."}`
- `http_request_duration_seconds_bucket` → `applylens_http_request_duration_seconds_bucket`

### 2. Created Comprehensive System Overview Dashboard ✅

**File**: `infra/grafana/dashboards/applylens-overview.json`

**Features** (12 panels):
1. **Database Status** - `applylens_db_up` indicator
2. **Elasticsearch Status** - `applylens_es_up` indicator
3. **Gmail Connected** - `applylens_gmail_connected` indicator
4. **HTTP Request Rate** - Total requests per second
5. **Email Risk Distribution** - Stacked view by risk level
6. **HTTP Error Rate** - 4xx and 5xx errors
7. **HTTP Request Latency** - P50, P95, P99 percentiles
8. **Rate Limiting** - Allowed vs exceeded requests
9. **Gmail Backfill Duration** - Average sync time
10. **Gmail Backfill Rate** - Emails inserted per second
11. **Crypto Operations** - Encryption/decryption rates
12. **Security Events** - CSRF success vs failures

**Configuration**:
- UID: `applylens-overview`
- Refresh: 30 seconds
- Time range: Last 1 hour
- Datasource: `prom` (uid)
- Folder: ApplyLens

### 3. Unified Dashboard Provisioning ✅

**Problem**: Duplicate providers causing conflicts

**Original Configuration**:
- Provider 1: "ApplyLens" → `/etc/grafana/provisioning/dashboards/json`
- Provider 2: "Security" → `/var/lib/grafana/dashboards`
- Resulted in duplicate UIDs and provisioning errors

**Solution**:
- Consolidated to single provider: "ApplyLens"
- All dashboards in: `/var/lib/grafana/dashboards`
- Moved old dashboard files to backup directory

**Updated**: `infra/grafana/provisioning/dashboards/applylens.yml`

### 4. Dashboard Inventory ✅

All dashboards now successfully provisioned:

| Dashboard | UID | Title | Panels | Focus |
|-----------|-----|-------|--------|-------|
| **applylens-overview.json** | `applylens-overview` | ApplyLens - System Overview | 12 | Comprehensive metrics |
| **security.json** | `applylens-security` | ApplyLens Security Monitoring | 8 | CSRF, crypto, reCAPTCHA |
| **api-status-health.json** | `api-status-health` | API Status & Health Monitoring | 6 | Health checks, errors |
| **traffic_import.json** | `applylens-traffic` | ApplyLens — Traffic | 6 | HTTP traffic analysis |
| **dashboard-assistant-window-buckets.json** | `applylens-assistant-windows` | Assistant (Windows & Hit Ratio) | 8 | Chat analytics |

### 5. Verification Results ✅

**Dashboard Provisioning Logs**:
```
logger=provisioning.dashboard ... msg="starting to provision dashboards"
logger=provisioning.dashboard ... msg="finished to provision dashboards"
```

**No Errors**:
- ✅ No "Dashboard title cannot be empty" errors
- ✅ No duplicate UID warnings
- ✅ No restricted database access warnings
- ✅ All 5 dashboards provisioned successfully

**Metrics Available**: 50+ metrics including:
- `applylens_http_requests_total` - HTTP request counter
- `applylens_http_request_duration_seconds_*` - Latency histograms
- `applylens_email_risk_served_total` - Risk level distribution
- `applylens_backfill_*` - Gmail sync metrics
- `applylens_crypto_*` - Encryption operations
- `applylens_rate_limit_*` - Rate limiting
- `applylens_csrf_*` - CSRF protection
- `applylens_db_up`, `applylens_es_up` - Health indicators

## Access Your Dashboards

### Grafana UI
**URL**: http://localhost:3000

**Default Credentials**:
- Username: `admin`
- Password: `admin` (or from `GRAFANA_ADMIN_PASSWORD` env var)

### Dashboard Locations

After logging in, find your dashboards in:
1. **Home** → **Dashboards**
2. **ApplyLens** folder

### Direct URLs (after login)
- System Overview: http://localhost:3000/d/applylens-overview
- Security: http://localhost:3000/d/applylens-security
- Traffic: http://localhost:3000/d/applylens-traffic
- API Health: http://localhost:3000/d/api-status-health
- Assistant: http://localhost:3000/d/applylens-assistant-windows

## Key PromQL Queries Used

### HTTP Traffic
```promql
# Request rate
sum(rate(applylens_http_requests_total[5m]))

# Error rate
sum(rate(applylens_http_requests_total{status_code=~"5.."}[5m]))

# P95 latency
histogram_quantile(0.95, sum by (le) (rate(applylens_http_request_duration_seconds_bucket[5m])))
```

### Business Metrics
```promql
# Email risk distribution
sum by (level) (rate(applylens_email_risk_served_total[5m]))

# Gmail backfill rate
rate(applylens_backfill_inserted_total[5m])

# Backfill duration (average)
rate(applylens_backfill_duration_seconds_sum[5m]) / rate(applylens_backfill_duration_seconds_count[5m])
```

### Security
```promql
# Rate limiting
sum(rate(applylens_rate_limit_exceeded_total[5m]))

# CSRF failures
sum(rate(applylens_csrf_fail_total[5m]))

# Crypto operations
rate(applylens_crypto_encrypt_total[5m])
```

### Health Indicators
```promql
# Database health (1 = up, 0 = down)
applylens_db_up

# Elasticsearch health
applylens_es_up

# Gmail connection
applylens_gmail_connected
```

## Next Steps (Optional)

### 1. Customize Dashboard Variables

Add template variables for filtering:
- User email
- Risk level
- HTTP path
- Time range presets

### 2. Set Up Alerting

Configure alerts for:
- High error rate (>5% 5xx errors)
- High latency (p95 > 1s)
- Service down (db_up == 0)
- Gmail disconnected
- Rate limit exceeded spike

**Files to edit**:
- `infra/grafana/provisioning/alerting/rules-applylens.yaml`
- `infra/grafana/provisioning/alerting/contact-points.yaml`
- `infra/grafana/provisioning/alerting/notification-policies.yaml`

### 3. Add More Panels

Suggestions for additional visualizations:
- **Request breakdown by endpoint** - `sum by (path) (rate(applylens_http_requests_total[5m]))`
- **Top error endpoints** - `topk(5, sum by (path) (rate(applylens_http_requests_total{status_code=~"5.."}[5m])))`
- **Concurrent requests** - `applylens_http_requests_in_progress`
- **Parity check status** - `applylens_parity_mismatch_ratio`

### 4. Dashboard Annotations

Enable annotations for:
- Deployment events
- Configuration changes
- Alert firing/resolution
- Manual interventions

### 5. Share Dashboards

Options:
- Export as JSON for version control ✅ (already done)
- Create dashboard snapshots
- Set up anonymous access (if needed)
- Configure team/user permissions

## Troubleshooting

### Dashboard Shows "No Data"

1. **Check Prometheus connection**:
   ```bash
   docker exec applylens-grafana-prod wget -qO- http://applylens-prometheus-prod:9090/-/healthy
   ```

2. **Verify metrics exist**:
   ```bash
   curl "http://localhost:9090/api/v1/query?query=applylens_http_requests_total"
   ```

3. **Check datasource in Grafana**:
   - Settings → Data Sources → Prometheus
   - Click "Test" button
   - Should show "Data source is working"

### Provisioning Errors

1. **View logs**:
   ```bash
   docker logs applylens-grafana-prod | Select-String "provisioning"
   ```

2. **Check file permissions**:
   ```bash
   docker exec applylens-grafana-prod ls -la /var/lib/grafana/dashboards/
   ```

3. **Validate JSON**:
   ```powershell
   Get-Content "infra/grafana/dashboards/applylens-overview.json" | ConvertFrom-Json
   ```

### Duplicate UID Errors

If you see "the same UID is used more than once":

1. **Check for duplicate files**:
   ```powershell
   Get-ChildItem "infra/grafana" -Recurse -Filter "*.json" |
     ForEach-Object { Get-Content $_.FullName -Raw | ConvertFrom-Json } |
     Group-Object -Property uid | Where-Object Count -gt 1
   ```

2. **Ensure single provider**:
   - Check `infra/grafana/provisioning/dashboards/applylens.yml`
   - Should have only ONE provider

3. **Clear old provisioning directories**:
   - Move or delete old dashboard files
   - Restart Grafana

## Files Modified

1. ✅ `infra/grafana/dashboards/traffic_import.json` - Fixed format, added UID
2. ✅ `infra/grafana/dashboards/applylens-overview.json` - Created new comprehensive dashboard
3. ✅ `infra/grafana/provisioning/dashboards/applylens.yml` - Unified to single provider
4. ✅ `infra/grafana/provisioning/datasources/prom.yml` - Already fixed (from previous task)

## Backup Files

Old dashboard files moved to:
- `infra/grafana/provisioning/dashboards/json/backup/`
  - `applylens-overview.json` (old version)
  - `email_risk_v31.json`
  - `traffic.json`

## Related Documentation

- [GRAFANA_PROMETHEUS_SETUP.md](./GRAFANA_PROMETHEUS_SETUP.md) - Datasource configuration
- [PRODUCTION_REBUILD_SUMMARY.md](./PRODUCTION_REBUILD_SUMMARY.md) - OAuth and API fixes
- [METRICS_ENDPOINT_IMPLEMENTATION.md](./METRICS_ENDPOINT_IMPLEMENTATION.md) - Backend metrics API

## Success Metrics

✅ **Dashboard Provisioning**: 5/5 dashboards loaded without errors
✅ **Prometheus Integration**: Datasource working, metrics flowing
✅ **Metric Coverage**: 50+ ApplyLens metrics available
✅ **Visualization**: 40+ panels across all dashboards
✅ **Documentation**: Complete setup and troubleshooting guides

**All Next Steps from Grafana Setup are now complete!** 🎉
