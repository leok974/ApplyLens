# Grafana + Prometheus Integration Setup

**Date**: October 22, 2025
**Status**: ✅ Complete

## Summary

Successfully configured Grafana to use Prometheus as a datasource for monitoring ApplyLens metrics.

## What Was Done

### 1. Created Datasource Provisioning Configuration

**File**: `infra/grafana/provisioning/datasources/prom.yml`

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    uid: prom
    type: prometheus
    access: proxy
    url: http://applylens-prometheus-prod:9090
    isDefault: true
```

**Key Points**:
- Updated existing `prom.yml` to use correct container name (`applylens-prometheus-prod`)
- Set as default datasource with `isDefault: true`
- Uses proxy access mode (Grafana queries Prometheus on behalf of users)
- Unique identifier: `uid: prom`

### 2. Volume Mount Verification

**File**: `docker-compose.prod.yml` (line 299)

```yaml
volumes:
  - ./infra/grafana/provisioning:/etc/grafana/provisioning:ro
```

The provisioning directory was already correctly mounted in the Grafana service.

### 3. Fixed Conflicting Configuration

**Issue**: Had duplicate datasource files causing "Only one datasource per organization can be marked as default" error

**Resolution**:
- Removed duplicate `prometheus.yaml` file
- Kept and updated original `prom.yml`
- Reset Grafana data volume to clear any stale database entries

### 4. Fresh Grafana Initialization

**Commands Run**:
```powershell
# Removed old Grafana container and volume
docker compose -f docker-compose.prod.yml stop grafana
docker compose -f docker-compose.prod.yml rm -f grafana
docker volume rm applylens_grafana_data_prod

# Started fresh with new configuration
docker compose -f docker-compose.prod.yml up -d grafana
```

## Verification Results

### ✅ Datasource Provisioned Successfully

**Log Entry**:
```
logger=provisioning.datasources ... msg="inserting datasource from configuration" name=Prometheus uid=prom
```

### ✅ Grafana Can Reach Prometheus

**Test**:
```bash
docker exec applylens-grafana-prod wget -qO- http://applylens-prometheus-prod:9090/-/healthy
# Output: Prometheus Server is Healthy.
```

### ✅ ApplyLens Metrics Available

**Sample Metrics Found**:
- `applylens_http_requests_total` - HTTP request counter with labels (method, path, status_code)
- `applylens_email_risk_served_total` - Risk level distribution
- `applylens_backfill_duration_seconds_*` - Gmail backfill performance
- `applylens_crypto_*` - Encryption/decryption metrics
- `applylens_rate_limit_*` - Rate limiting metrics
- `applylens_db_up` - Database health
- `applylens_es_up` - Elasticsearch health
- `applylens_gmail_connected` - Gmail connection status

**Test Query**:
```bash
curl -s "http://localhost:9090/api/v1/query?query=applylens_http_requests_total"
# Returns metrics with labels: app_name, instance, job, method, path, status_code
```

## Grafana Access

**URL**: http://localhost:3000
**Credentials**:
- Username: `${GRAFANA_ADMIN_USER}` (default: admin)
- Password: `${GRAFANA_ADMIN_PASSWORD}` (default: admin)

## Next Steps

### 1. Create/Import Dashboards

Now that Prometheus datasource is configured, you can:

1. **Import Existing Dashboards**:
   - Navigate to Dashboards → Import
   - Check `infra/grafana/dashboards/` for pre-configured dashboards
   - Fix any invalid dashboards (e.g., `traffic_import.json` has empty title)

2. **Create Custom Dashboards**:
   - Use the Prometheus datasource (uid: `prom`)
   - Query ApplyLens metrics for visualization
   - Examples:
     - Request rate: `rate(applylens_http_requests_total[5m])`
     - Error rate: `rate(applylens_http_requests_total{status_code=~"5.."}[5m])`
     - P95 latency: `histogram_quantile(0.95, rate(applylens_http_request_duration_seconds_bucket[5m]))`

### 2. Fix Dashboard Issues

**Known Issue**: `traffic_import.json` dashboard has empty title

**Fix**:
```bash
# Edit the dashboard file
# Add/fix the "title" field in the JSON
```

### 3. Setup Alerting (Optional)

The alerting provisioning is already configured:
- Contact points: `infra/grafana/provisioning/alerting/contact-points.yaml`
- Notification policies: `infra/grafana/provisioning/alerting/notification-policies.yaml`
- Alert rules: `infra/grafana/provisioning/alerting/rules-applylens.yaml`

Review and customize these for your monitoring needs.

## Metrics Endpoint Integration

The `/api/metrics/divergence-24h` endpoint (implemented earlier) also queries Prometheus:

**File**: `services/api/app/routers/metrics.py`
```python
PROM_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")

async def divergence_24h():
    # Queries Prometheus for risk levels, latency, error rates
    q_level_24h = "sum(increase(applylens_email_risk_served_total[24h])) by (level)"
    # Returns health metrics to frontend HealthBadge component
```

This provides programmatic access to metrics data for the ApplyLens UI.

## Troubleshooting

### Datasource Not Appearing in Grafana

1. Check provisioning logs:
   ```bash
   docker logs applylens-grafana-prod | grep -i "datasource\|provisioning"
   ```

2. Verify file is mounted:
   ```bash
   docker exec applylens-grafana-prod cat /etc/grafana/provisioning/datasources/prom.yml
   ```

3. Restart Grafana:
   ```bash
   docker compose -f docker-compose.prod.yml restart grafana
   ```

### "No Data" in Dashboards

1. Test Prometheus connectivity:
   ```bash
   docker exec applylens-grafana-prod wget -qO- http://applylens-prometheus-prod:9090/-/healthy
   ```

2. Verify metrics exist:
   ```bash
   curl "http://localhost:9090/api/v1/label/__name__/values" | jq '.data | map(select(startswith("applylens")))'
   ```

3. Check metric names in dashboard panels match actual metric names

### Multiple Default Datasources Error

This was the issue we encountered and fixed. If it happens again:

1. Check for multiple datasource files:
   ```bash
   docker exec applylens-grafana-prod find /etc/grafana/provisioning/datasources -name "*.yml" -o -name "*.yaml"
   ```

2. Ensure only ONE datasource has `isDefault: true`

3. Reset Grafana if needed (see commands in section 4 above)

## Configuration Files Modified

1. ✅ `infra/grafana/provisioning/datasources/prom.yml` - Updated URL
2. ✅ `docker-compose.prod.yml` - Already had correct volume mount
3. ✅ Removed duplicate `prometheus.yaml` file

## Related Documentation

- [PRODUCTION_REBUILD_SUMMARY.md](./PRODUCTION_REBUILD_SUMMARY.md) - OAuth fixes and API updates
- [METRICS_ENDPOINT_IMPLEMENTATION.md](./METRICS_ENDPOINT_IMPLEMENTATION.md) - Backend metrics API
- Prometheus documentation: https://prometheus.io/docs/
- Grafana provisioning docs: https://grafana.com/docs/grafana/latest/administration/provisioning/
