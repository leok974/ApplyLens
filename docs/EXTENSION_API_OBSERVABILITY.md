# Extension API Observability

## Prometheus Metrics

All extension endpoints now expose Prometheus counters for monitoring activity:

### Metrics Available

1. **`applylens_extension_applications_total`**
   - Tracks job applications logged via browser extension
   - Label: `source` (e.g., "linkedin", "greenhouse", "browser_extension")
   - Endpoint: `POST /api/extension/applications`

2. **`applylens_extension_outreach_total`**
   - Tracks recruiter outreach messages logged
   - Label: `source` (e.g., "linkedin", "email", "browser_extension")
   - Endpoint: `POST /api/extension/outreach`

3. **`applylens_extension_form_generations_total`**
   - Tracks AI-generated form answers
   - No labels (simple counter)
   - Endpoint: `POST /api/extension/generate-form-answers`

4. **`applylens_extension_dm_generations_total`**
   - Tracks AI-generated recruiter DMs
   - No labels (simple counter)
   - Endpoint: `POST /api/extension/generate-recruiter-dm`

### Accessing Metrics

Metrics are exposed at the `/metrics` endpoint:
```bash
curl http://localhost:8003/metrics | grep applylens_extension
```

Example output:
```
# HELP applylens_extension_applications_total Extension job application logs
# TYPE applylens_extension_applications_total counter
applylens_extension_applications_total{source="linkedin"} 42.0
applylens_extension_applications_total{source="greenhouse"} 18.0

# HELP applylens_extension_outreach_total Extension recruiter outreach logs
# TYPE applylens_extension_outreach_total counter
applylens_extension_outreach_total{source="linkedin"} 15.0
applylens_extension_outreach_total{source="email"} 8.0

# HELP applylens_extension_form_generations_total Extension form answer generations
# TYPE applylens_extension_form_generations_total counter
applylens_extension_form_generations_total 127.0

# HELP applylens_extension_dm_generations_total Extension recruiter DM generations
# TYPE applylens_extension_dm_generations_total counter
applylens_extension_dm_generations_total 89.0
```

---

## Grafana Dashboard

### Import Dashboard

1. **Navigate to Grafana**:
   ```
   http://localhost:3000  # or your Grafana instance
   ```

2. **Import Dashboard**:
   - Click **Dashboards** → **Import**
   - Upload `infra/grafana/dashboards/extension-activity.json`
   - Or paste JSON content directly

3. **Dashboard UID**: `extension-activity`

### Dashboard Panels

**1. Extension Applications (24h increase by source)** - Time series
- Query: `sum(increase(applylens_extension_applications_total[24h])) by (source)`
- Shows job application trends broken down by source (LinkedIn, Greenhouse, etc.)

**2. Extension Outreach (24h increase by source)** - Time series
- Query: `sum(increase(applylens_extension_outreach_total[24h])) by (source)`
- Shows recruiter outreach activity by platform

**3. Form Generations (24h)** - Stat panel
- Query: `sum(increase(applylens_extension_form_generations_total[24h]))`
- Single number showing total AI form fills in last 24 hours

**4. DM Generations (24h)** - Stat panel
- Query: `sum(increase(applylens_extension_dm_generations_total[24h]))`
- Single number showing total AI DM generations

**5. Extension Activity Summary (1h)** - Bar gauge
- Shows all 4 metrics side-by-side for the last hour
- Quick overview of extension usage

### Refresh Rate
- Default: 30 seconds
- Time range: Last 24 hours

---

## PromQL Queries

### Useful Queries for Alerts/Analysis

```promql
# Applications per hour
rate(applylens_extension_applications_total[1h])

# Total applications by source (all time)
sum by (source) (applylens_extension_applications_total)

# Ratio of applications to outreach
sum(applylens_extension_applications_total) / sum(applylens_extension_outreach_total)

# Form generation rate (per minute)
rate(applylens_extension_form_generations_total[5m]) * 60

# Alert: High form generation rate (>10/min)
rate(applylens_extension_form_generations_total[5m]) * 60 > 10
```

### Example Alert (Prometheus)

Add to `infra/prometheus/alerts.yml`:

```yaml
groups:
  - name: extension_activity
    interval: 30s
    rules:
      - alert: ExtensionApplicationSpike
        expr: rate(applylens_extension_applications_total[5m]) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High extension application rate"
          description: "{{ $value }} applications per second (>2/sec threshold)"

      - alert: ExtensionFormGenerationSpike
        expr: rate(applylens_extension_form_generations_total[5m]) * 60 > 20
        for: 5m
        labels:
          severity: info
        annotations:
          summary: "High form generation activity"
          description: "{{ $value }} form generations per minute"
```

---

## Testing Metrics

### 1. Start Dev Server
```powershell
# Using VS Code task
# Press Ctrl+Shift+P → "Run Task" → "API: Dev Server (Extension Mode)"

# Or manually:
cd services/api
$env:APPLYLENS_DEV='1'
$env:DATABASE_URL='sqlite:///./dev_extension.db'
$env:ES_ENABLED='0'
python -m uvicorn app.main:app --reload --port 8003
```

### 2. Generate Test Data
```powershell
# Log an application
Invoke-RestMethod -Uri "http://localhost:8003/api/extension/applications" `
    -Method POST `
    -ContentType "application/json" `
    -Body (@{
        company = "Google"
        role = "Senior Backend Engineer"
        job_url = "https://careers.google.com/jobs/123"
        source = "linkedin"
    } | ConvertTo-Json)

# Log outreach
Invoke-RestMethod -Uri "http://localhost:8003/api/extension/outreach" `
    -Method POST `
    -ContentType "application/json" `
    -Body (@{
        company = "Meta"
        role = "Full Stack Engineer"
        recruiter_name = "Jane Smith"
        source = "linkedin"
    } | ConvertTo-Json)

# Generate form answers
Invoke-RestMethod -Uri "http://localhost:8003/api/extension/generate-form-answers" `
    -Method POST `
    -ContentType "application/json" `
    -Body (@{
        job = @{ title = "Backend Engineer"; company = "Stripe" }
        fields = @(
            @{ field_id = "q1"; label = "Why Stripe?" }
        )
    } | ConvertTo-Json -Depth 5)
```

### 3. Check Metrics
```powershell
# Fetch all extension metrics
curl.exe http://localhost:8003/metrics | Select-String "applylens_extension"
```

### 4. Verify in Grafana
- Open dashboard: `http://localhost:3000/d/extension-activity`
- Wait 30 seconds for refresh
- Check that counters have incremented

---

## Prometheus Configuration

Ensure Prometheus is scraping the API metrics endpoint:

**`infra/prometheus/prometheus.yml`**:
```yaml
scrape_configs:
  - job_name: 'applylens-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['api:8003']  # or 'localhost:8003' for dev
    metrics_path: '/metrics'
```

Restart Prometheus to apply changes:
```bash
docker compose -f infra/docker-compose.yml restart prometheus
```

---

## Production Notes

1. **Metric Cardinality**:
   - `source` label has low cardinality (typically 3-5 values)
   - Safe for production Prometheus

2. **Retention**:
   - Prometheus default: 15 days
   - Increase in `prometheus.yml` with `--storage.tsdb.retention.time=90d`

3. **Aggregation**:
   - Use recording rules for frequently queried data
   - Example: Pre-compute 24h increases every 5 minutes

4. **Grafana Variables**:
   - Add `$source` template variable for filtering by source
   - Query: `label_values(applylens_extension_applications_total, source)`

---

## Related Documentation
- [Extension API Rate Limiting](./EXTENSION_API_RATE_LIMITING.md)
- [Prometheus Setup](../infra/prometheus/README.md)
- [Grafana Dashboards](../infra/grafana/README.md)
