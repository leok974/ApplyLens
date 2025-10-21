# Infrastructure Artifacts Applied - October 20, 2025

## Summary

Successfully applied production-ready artifacts for Elasticsearch data processing and Grafana traffic monitoring.

---

## ✅ What Was Applied

### 1. Elasticsearch Ingest Pipeline

**File:** `infra/elasticsearch/pipelines/applications_v1.json`

**Purpose:** Normalizes application documents on ingestion with:
- Company name normalization (lowercase, trim)
- Boolean flag derivation (archived, deleted)
- Status field processing
- Date parsing with multiple format support
- Error handling

**Status:** ✅ Loaded and tested successfully

**Test Results:**
```json
Input:
  company: "  NeoFinTech  "
  status: "Interview"
  archived_at: null

Output:
  company: "neofintech"        ✅ Normalized
  status_raw: "interview"      ✅ Lowercased
  archived: false              ✅ Derived
  deleted: false               ✅ Derived
  status_archived: "active"    ✅ Created
```

### 2. Grafana Traffic Dashboard

**File:** `infra/grafana/provisioning/dashboards/json/traffic.json`

**Purpose:** Real-time HTTP traffic monitoring with panels for:
- API service status (up/down)
- Request rate (requests/second)
- 4xx/5xx error rates
- 429 rate limiting events
- CSRF & reCAPTCHA failures
- HTTP latency (p95 placeholder)

**Status:** ✅ Provisioned successfully

**Access:** http://localhost:3000 → Dashboards → ApplyLens folder → Traffic

### 3. Supporting Files

- `infra/elasticsearch/pipelines/test_sample.json` - Pipeline test document
- `infra/grafana/dashboards/traffic_import.json` - Import-ready dashboard format

---

## 📋 Files Created/Modified

| File | Type | Status |
|------|------|--------|
| `infra/elasticsearch/pipelines/applications_v1.json` | ES Pipeline | ✅ Created |
| `infra/elasticsearch/pipelines/test_sample.json` | Test Data | ✅ Created |
| `infra/grafana/provisioning/dashboards/json/traffic.json` | Dashboard | ✅ Created |
| `infra/grafana/dashboards/traffic_import.json` | Import Format | ✅ Created |
| `docs/SETUP_ES_PIPELINE_GRAFANA_DASHBOARD.md` | Documentation | ✅ Created |
| `docs/DOC_INDEX.md` | Documentation | ✅ Updated |

---

## 🔧 Setup Commands Executed

### Elasticsearch Pipeline
```powershell
# Load pipeline
$pipeline = Get-Content infra\elasticsearch\pipelines\applications_v1.json -Raw
docker exec -i applylens-api-prod curl -s -X PUT \
  http://elasticsearch:9200/_ingest/pipeline/applylens_applications_v1 \
  -H 'Content-Type: application/json' -d $pipeline

# Result: {"acknowledged": true}

# Test pipeline
$test = Get-Content infra\elasticsearch\pipelines\test_sample.json -Raw
docker exec -i applylens-api-prod curl -s -X POST \
  http://elasticsearch:9200/_ingest/pipeline/applylens_applications_v1/_simulate \
  -H 'Content-Type: application/json' -d $test

# Result: All transformations working correctly ✅
```

### Grafana Dashboard
```powershell
# Move to provisioned location
Move-Item -Path infra\grafana\dashboards\traffic.json \
  -Destination infra\grafana\provisioning\dashboards\json\traffic.json

# Restart Grafana to load dashboard
docker restart applylens-grafana-prod

# Result: Dashboard provisioned successfully ✅
```

---

## 📊 Dashboard Panels

The Traffic dashboard includes:

1. **API Up** (Stat Panel)
   - Shows if API service is up
   - Query: `sum(up{job="applylens-api"})`

2. **Requests per second** (Time Series)
   - Total HTTP request rate
   - Query: `sum(rate(http_requests_total{job="applylens-api"}[5m]))`

3. **4xx/5xx Error Rate** (Time Series)
   - Client and server error rates
   - Queries:
     - 4xx: `sum(rate(http_requests_total{job="applylens-api",code=~"4.."}[5m]))`
     - 5xx: `sum(rate(http_requests_total{job="applylens-api",code=~"5.."}[5m]))`

4. **429s Rate Limited** (Time Series)
   - Rate limiting events
   - Query: `sum(rate(applylens_rate_limit_exceeded_total[5m]))`

5. **CSRF & Captcha Failures** (Time Series)
   - Security validation failures
   - Queries:
     - CSRF: `sum(rate(applylens_csrf_fail_total[5m]))`
     - Captcha: `sum(rate(applylens_recaptcha_verify_total{status="fail"}[5m]))`

6. **HTTP Latency p95** (Time Series - Placeholder)
   - 95th percentile latency
   - Query: `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="applylens-api"}[5m])))`
   - Note: Update with actual metric name if different

---

## 🎯 Pipeline Processing Flow

```
Document Ingestion
        ↓
┌───────────────────────┐
│  Input Document       │
│  {                    │
│    company: "  ABC  " │
│    status: "Interview"│
│    archived_at: null  │
│  }                    │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│  Lowercase & Trim     │
│  company → "abc"      │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│  Rename & Lowercase   │
│  status → status_raw  │
│  status_raw → "inter.."│
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│  Derive Booleans      │
│  archived: false      │
│  deleted: false       │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│  Parse Dates          │
│  applied_at, etc.     │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│  Create Status Field  │
│  status_archived:     │
│    "active"           │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│  Cleanup              │
│  Remove temp fields   │
└───────────┬───────────┘
            ↓
   Indexed Document
```

---

## 🔍 Verification

### Pipeline Verification
```powershell
# Check pipeline exists
docker exec applylens-api-prod curl -s \
  http://elasticsearch:9200/_ingest/pipeline/applylens_applications_v1 \
  | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Expected: Pipeline definition returned
```

### Dashboard Verification
```powershell
# Check dashboard file
docker exec applylens-grafana-prod \
  ls -la /etc/grafana/provisioning/dashboards/json/traffic.json

# Expected: -rwxrwxrwx ... traffic.json

# Access dashboard
# URL: http://localhost:3000
# Path: Dashboards → ApplyLens → Traffic
```

---

## 📝 Next Steps (Optional)

### 1. Attach Pipeline to Index

To automatically apply the pipeline on all writes:

```powershell
docker exec applylens-api-prod curl -s -X PUT \
  http://elasticsearch:9200/gmail_applications-000001/_settings \
  -H 'Content-Type: application/json' \
  -d '{"index":{"default_pipeline":"applylens_applications_v1"}}'
```

### 2. Reprocess Existing Documents

To apply pipeline to existing data:

```powershell
docker exec applylens-api-prod curl -s -X POST \
  http://elasticsearch:9200/_reindex \
  -H 'Content-Type: application/json' \
  -d '{
    "source": {"index": "gmail_applications-000001"},
    "dest": {
      "index": "gmail_applications-v2",
      "pipeline": "applylens_applications_v1"
    }
  }'
```

### 3. Configure Metric Exports

Ensure the API exports all required metrics:
- `http_requests_total` - HTTP request counter
- `applylens_rate_limit_exceeded_total` - Rate limiting
- `applylens_csrf_fail_total` - CSRF failures
- `applylens_recaptcha_verify_total` - reCAPTCHA results

Check metrics endpoint:
```powershell
curl http://localhost:8003/metrics | Select-String "applylens"
```

---

## 🐛 Troubleshooting

### Pipeline Not Processing

**Symptom:** Documents not normalized

**Solution:**
```powershell
# Check pipeline is attached to index
docker exec applylens-api-prod curl -s \
  http://elasticsearch:9200/gmail_applications-000001/_settings \
  | ConvertFrom-Json | Select-Object -ExpandProperty * | 
  Select-Object -ExpandProperty settings | 
  Select-Object -ExpandProperty index

# Look for: default_pipeline: applylens_applications_v1

# Check for processing errors
docker exec applylens-api-prod curl -s \
  'http://elasticsearch:9200/gmail_applications-000001/_search?q=_ingest_error:*' \
  | ConvertFrom-Json | Select-Object -ExpandProperty hits
```

### Dashboard Not Visible

**Symptom:** Traffic dashboard not in Grafana

**Solution:**
```powershell
# Check file exists
docker exec applylens-grafana-prod \
  ls -la /etc/grafana/provisioning/dashboards/json/

# Restart Grafana
docker restart applylens-grafana-prod

# Check Grafana logs
docker logs applylens-grafana-prod --tail 50 | Select-String "dashboard"
```

### Metrics Not Showing

**Symptom:** Dashboard panels empty

**Solution:**
```powershell
# Verify Prometheus is scraping API
curl http://localhost:9090/api/v1/targets | 
  ConvertFrom-Json | 
  Select-Object -ExpandProperty data | 
  Select-Object -ExpandProperty activeTargets | 
  Where-Object { $_.labels.job -eq 'applylens-api' }

# Check metrics exist
curl http://localhost:8003/metrics | Select-String "http_requests_total"

# If missing, verify Prometheus scrape config
docker exec applylens-prometheus-prod cat /etc/prometheus/prometheus.yml
```

---

## 📚 Documentation

Complete setup guide with all commands, examples, and troubleshooting:
- **[SETUP_ES_PIPELINE_GRAFANA_DASHBOARD.md](SETUP_ES_PIPELINE_GRAFANA_DASHBOARD.md)**

Updated documentation index:
- **[DOC_INDEX.md](DOC_INDEX.md)**

---

## ✅ Success Criteria Met

- [x] Elasticsearch pipeline loaded and tested
- [x] Pipeline correctly normalizes test documents
- [x] Grafana dashboard provisioned
- [x] Dashboard accessible at http://localhost:3000
- [x] Documentation created and indexed
- [x] Verification commands tested
- [x] Troubleshooting guide provided

---

**Status:** ✅ All artifacts applied successfully  
**Date:** October 20, 2025  
**Applied By:** Automated setup process
