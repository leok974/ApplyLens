# ES Pipeline & Grafana Dashboard Setup

## Setup Commands

### 1. Load Elasticsearch Ingest Pipeline

```powershell
# Load the pipeline to Elasticsearch
$pipeline = Get-Content infra\elasticsearch\pipelines\applications_v1.json -Raw
docker exec -i applylens-api-prod curl -s -X PUT http://elasticsearch:9200/_ingest/pipeline/applylens_applications_v1 -H 'Content-Type: application/json' -d $pipeline

# Test the pipeline
$test = Get-Content infra\elasticsearch\pipelines\test_sample.json -Raw
docker exec -i applylens-api-prod curl -s -X POST http://elasticsearch:9200/_ingest/pipeline/applylens_applications_v1/_simulate -H 'Content-Type: application/json' -d $test | ConvertFrom-Json | ConvertTo-Json -Depth 20
```

### 2. Attach Pipeline to Index (Optional)

To automatically apply the pipeline on all writes to the `gmail_applications` index:

```powershell
docker exec applylens-api-prod curl -s -X PUT http://elasticsearch:9200/gmail_applications-000001/_settings -H 'Content-Type: application/json' -d '{\"index\":{\"default_pipeline\":\"applylens_applications_v1\"}}'
```

### 3. Import Grafana Dashboard

The Traffic dashboard is automatically loaded via volume mount:
- **Location:** `infra/grafana/dashboards/traffic.json`
- **Mount:** `/var/lib/grafana/dashboards` (read-only)
- **Access:** http://localhost:3000 (admin/admin)

After adding or modifying dashboards, restart Grafana:

```powershell
docker restart applylens-grafana-prod
```

## Files Created

1. **`infra/grafana/dashboards/traffic.json`**
   - Grafana dashboard for HTTP traffic monitoring
   - Tracks: Request rate, error rate, 429s, CSRF/Captcha failures, latency
   - Uses Prometheus datasource variable `${DS_PROM}`

2. **`infra/elasticsearch/pipelines/applications_v1.json`**
   - Ingest pipeline for normalizing application documents
   - Features:
     - Lowercases and trims company name
     - Derives `archived` boolean from `archived_at` timestamp
     - Derives `deleted` boolean from `deleted_at` timestamp
     - Parses dates (applied_at, archived_at, deleted_at)
     - Creates `status_archived` field (active/archived)
     - Error handling with `_ingest_error` field

3. **`infra/elasticsearch/pipelines/test_sample.json`**
   - Test document for pipeline simulation

## Verification

### ES Pipeline Test Result
```json
{
  "docs": [
    {
      "doc": {
        "_source": {
          "archived": false,
          "deleted": false,
          "archived_at": null,
          "status_raw": "interview",
          "company": "neofintech",           // lowercased & trimmed
          "status_archived": "active"        // derived field
        }
      }
    }
  ]
}
```

### Grafana Dashboard
- ✅ Created at: `infra/grafana/dashboards/traffic.json`
- ✅ Mounted to: `/var/lib/grafana/dashboards/traffic.json`
- ✅ Grafana restarted successfully
- 📊 Access: http://localhost:3000/dashboards → "ApplyLens — Traffic"

## ES Pipeline Features

The `applylens_applications_v1` pipeline provides:

1. **Company Normalization**
   - Lowercases company names for consistent searching
   - Trims whitespace

2. **Status Handling**
   - Renames `status` to `status_raw` and lowercases
   - Creates `status_archived` field (active/archived)

3. **Boolean Flags**
   - `archived`: true if `archived_at` is set
   - `deleted`: true if `deleted_at` is set

4. **Date Parsing**
   - Handles ISO8601 and custom formats
   - Gracefully ignores parsing failures

5. **Error Handling**
   - Failed documents get `_ingest_error` field
   - Pipeline continues processing other docs

## Next Steps

### Optional: Apply Pipeline to Existing Documents

If you want to reprocess existing documents with the new pipeline:

```powershell
# Reindex with pipeline
docker exec applylens-api-prod curl -s -X POST http://elasticsearch:9200/_reindex -H 'Content-Type: application/json' -d '{
  "source": {
    "index": "gmail_applications-000001"
  },
  "dest": {
    "index": "gmail_applications-v2",
    "pipeline": "applylens_applications_v1"
  }
}'
```

### Configure Prometheus Metrics (for Dashboard)

The Traffic dashboard expects these metrics:
- `up{job="applylens-api"}` - API service up/down
- `http_requests_total{job="applylens-api",code}` - HTTP request counter
- `applylens_rate_limit_exceeded_total` - Rate limit counter
- `applylens_csrf_fail_total` - CSRF failure counter
- `applylens_recaptcha_verify_total{status}` - Captcha verification counter
- `http_request_duration_seconds_bucket` - Request latency histogram (optional)

Verify metrics are being collected:
```powershell
curl http://localhost:9090/api/v1/label/__name__/values | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-String "applylens"
```

## Troubleshooting

### Pipeline Not Working
```powershell
# Check if pipeline exists
docker exec applylens-api-prod curl -s http://elasticsearch:9200/_ingest/pipeline/applylens_applications_v1

# View pipeline errors
docker exec applylens-api-prod curl -s http://elasticsearch:9200/gmail_applications-000001/_search?q=_ingest_error:*
```

### Dashboard Not Showing
```powershell
# Check Grafana logs
docker logs applylens-grafana-prod --tail 50

# Verify file is mounted
docker exec applylens-grafana-prod ls -la /var/lib/grafana/dashboards/

# Restart Grafana
docker restart applylens-grafana-prod
```

### Metrics Missing
```powershell
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | ConvertFrom-Json | Select-Object -ExpandProperty data

# Check if metrics exist
curl http://localhost:8003/metrics | Select-String "applylens"
```
