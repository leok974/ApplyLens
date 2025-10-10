# Backfill Health Monitoring

Comprehensive monitoring solution for backfill operations using Prometheus and Kibana.

## Components

### 1. Prometheus Metrics (`/metrics` endpoint)

FastAPI exposes Prometheus metrics at `/metrics` for real-time scraping.

**Metrics Exposed:**

- `bills_missing_dates` - Number of bills without dates[] field
- `bills_with_dates` - Number of bills with dates[] populated
- `bills_with_expires_at` - Number of bills with expires_at set
- `backfill_health_last_run_timestamp` - Last metrics refresh (Unix timestamp)
- `backfill_health_index_info{index="..."}` - Index name label

**Access:**

```bash
# Local development
curl http://localhost:8003/metrics

# Sample output:
# HELP bills_missing_dates Bills missing dates[] field
# TYPE bills_missing_dates gauge
bills_missing_dates 0.0
# HELP bills_with_dates Bills with dates[] populated
# TYPE bills_with_dates gauge
bills_with_dates 1243.0
# HELP bills_with_expires_at Bills with expires_at field set
# TYPE bills_with_expires_at gauge
bills_with_expires_at 1243.0
```

**Prometheus Scrape Configuration:**

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'applylens-backfill-health'
    scrape_interval: 30s
    static_configs:
      - targets: ['api:8003']
    metrics_path: '/metrics'
```

### 2. Elasticsearch Health Index (Kibana Trending)

Emit health snapshots to Elasticsearch for historical trending in Kibana.

**Prerequisites:**

Create the health index:

```bash
# Dev Tools in Kibana
PUT backfill_health_v1
{
  "mappings": {
    "properties": {
      "index": { "type": "keyword" },
      "missing": { "type": "integer" },
      "with_dates": { "type": "integer" },
      "with_expires_at": { "type": "integer" },
      "ts": { "type": "date" }
    }
  }
}
```

Or via cURL:

```bash
curl -X PUT "http://localhost:9200/backfill_health_v1" \
  -H 'Content-Type: application/json' \
  -d '{
    "mappings": {
      "properties": {
        "index": { "type": "keyword" },
        "missing": { "type": "integer" },
        "with_dates": { "type": "integer" },
        "with_expires_at": { "type": "integer" },
        "ts": { "type": "date" }
      }
    }
  }'
```

**Emit Health Data:**

```bash
# Makefile
make emit-backfill-health

# Direct script
python scripts/emit_backfill_health.py

# PowerShell
$env:ES_URL="http://localhost:9200"
$env:ES_EMAIL_INDEX="gmail_emails_v2"
python scripts/emit_backfill_health.py
```

**Sample Output:**

```
Emitted backfill health: {
  'index': 'gmail_emails_v2',
  'missing': 0,
  'with_dates': 1243,
  'with_expires_at': 1243,
  'ts': '2025-10-10T14:22:31Z'
}
```

### 3. Kibana Dashboard

Import the pre-configured dashboard for visualizing trends.

**Import Dashboard:**

```bash
# PowerShell
Invoke-WebRequest -Method POST `
  -Uri "http://localhost:5601/api/saved_objects/_import?overwrite=true" `
  -Headers @{"kbn-xsrf"="true"} `
  -Form @{file=Get-Item "kibana\backfill-health-missing.ndjson"} `
  | Select-Object -ExpandProperty Content

# Bash/curl
curl -X POST "http://localhost:5601/api/saved_objects/_import?overwrite=true" \
  -H "kbn-xsrf: true" \
  -F "file=@kibana/backfill-health-missing.ndjson"
```

**Dashboard Features:**

- **Index Pattern**: `backfill_health_v1*`
- **Time Field**: `ts`
- **Visualization**: Line chart showing missing dates over time (hourly average)

**Custom Kibana Queries:**

```sql
-- Missing dates trend (hourly)
FROM backfill_health_v1
| STATS missing=AVG(missing) BY DATE_TRUNC(1 hour, ts)
| SORT DATE_TRUNC(1 hour, ts) ASC

-- Bills with dates trend
FROM backfill_health_v1
| STATS with_dates=AVG(with_dates) BY DATE_TRUNC(1 hour, ts)
| SORT DATE_TRUNC(1 hour, ts) ASC

-- Coverage percentage
FROM backfill_health_v1
| STATS 
    total=AVG(with_dates),
    with_exp=AVG(with_expires_at)
  BY DATE_TRUNC(1 hour, ts)
| EVAL coverage_pct = (with_exp / total) * 100
| SORT DATE_TRUNC(1 hour, ts) ASC
```

## Automation

### Scheduled Health Emission

**Cron (Linux/Mac):**

```bash
# Emit health metrics every hour
0 * * * * cd /path/to/applylens && python services/api/scripts/emit_backfill_health.py

# Or use Makefile
0 * * * * cd /path/to/applylens/services/api && make emit-backfill-health
```

**GitHub Actions:**

Add to your backfill workflow (`.github/workflows/backfill-bills.yml`):

```yaml
- name: Emit backfill health
  working-directory: services/api
  env:
    ES_URL: ${{ secrets.ES_URL }}
    ES_API_KEY: ${{ secrets.ES_API_KEY }}
    ES_EMAIL_INDEX: gmail_emails_v2
  run: python scripts/emit_backfill_health.py
```

**Scheduled Task (Windows PowerShell):**

```powershell
# Create scheduled task to run hourly
$action = New-ScheduledTaskAction -Execute "python" `
  -Argument "D:\ApplyLens\services\api\scripts\emit_backfill_health.py" `
  -WorkingDirectory "D:\ApplyLens\services\api"

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)

Register-ScheduledTask -TaskName "ApplyLens-BackfillHealth" `
  -Action $action -Trigger $trigger `
  -Description "Emit backfill health metrics to Elasticsearch"
```

## Testing

### Unit Tests

```bash
# Test health emitter
python -m pytest tests/unit/test_emit_backfill_health.py -v

# Expected: 4 tests pass
```

### E2E Tests

```bash
# Test Prometheus metrics endpoint
python -m pytest tests/e2e/test_metrics_prom.py -v

# Expected: 4 tests pass
```

### Manual Testing

**1. Test Metrics Endpoint:**

```bash
# Start API server
uvicorn app.main:app --reload

# Query metrics
curl http://localhost:8000/metrics
```

**2. Test Health Emission:**

```bash
# Dry run (check output)
python scripts/emit_backfill_health.py

# Verify in ES
curl http://localhost:9200/backfill_health_v1/_search?pretty
```

**3. Test Makefile:**

```bash
cd services/api

# Emit health
make emit-backfill-health

# Check metrics endpoint
curl http://localhost:8000/metrics | grep bills_
```

## Monitoring Checklist

### Before Backfill

- [ ] Check Prometheus is scraping `/metrics`
- [ ] Verify baseline metrics (capture before state)
- [ ] Run `make validate-backfill > before.txt`
- [ ] Emit health snapshot: `make emit-backfill-health`

### During Backfill

- [ ] Monitor Prometheus dashboard for metric changes
- [ ] Watch for alerts on missing_dates gauge

### After Backfill

- [ ] Run `make validate-backfill > after.txt`
- [ ] Compare: `diff before.txt after.txt`
- [ ] Emit health snapshot: `make emit-backfill-health`
- [ ] Verify Kibana dashboard shows improvement

### Ongoing Monitoring

- [ ] Prometheus scraping every 30s
- [ ] Health emission every hour (cron/Actions)
- [ ] Kibana dashboard reviewed weekly
- [ ] Alerts configured for missing_dates > 10

## Alerting (Prometheus)

Example alert rules for `prometheus_rules.yml`:

```yaml
groups:
  - name: backfill_health
    interval: 30s
    rules:
      - alert: BackfillMissingDatesHigh
        expr: bills_missing_dates > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High number of bills missing dates"
          description: "{{ $value }} bills are missing dates[] field"
      
      - alert: BackfillCoverageLow
        expr: (bills_with_expires_at / bills_with_dates) < 0.95
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low backfill coverage"
          description: "Only {{ $value | humanizePercentage }} of bills have expires_at set"
      
      - alert: BackfillMetricsStale
        expr: time() - backfill_health_last_run_timestamp > 300
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Backfill metrics are stale"
          description: "Metrics haven't been refreshed in over 5 minutes"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ES_URL` | `http://localhost:9200` | Elasticsearch server URL |
| `ES_EMAIL_INDEX` | `gmail_emails_v2` | Email index to monitor |
| `ES_HEALTH_INDEX` | `backfill_health_v1` | Health metrics index |
| `ES_API_KEY` | _(none)_ | API key for ES auth |

## Architecture

```
┌─────────────────┐
│   Prometheus    │◄───── Scrape /metrics every 30s
│   (Time Series  │       (Real-time gauges)
│    Database)    │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│   Grafana/      │
│   Alertmanager  │
│   (Dashboards & │
│    Alerts)      │
└─────────────────┘

┌─────────────────┐
│  FastAPI App    │◄───── GET /metrics
│  (/metrics      │       POST /metrics/refresh
│   endpoint)     │
└─────────────────┘
        │
        │ Queries ES
        ▼
┌─────────────────┐
│ Elasticsearch   │◄───── emit_backfill_health.py
│ (Bills Index)   │       (Hourly snapshots)
└─────────────────┘
        │
        │ Health Index
        ▼
┌─────────────────┐
│ backfill_health │
│     _v1         │
│ (Time Series)   │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│    Kibana       │
│   (Dashboards   │
│   & Lens)       │
└─────────────────┘
```

## Troubleshooting

**Metrics endpoint returns 404:**
- Check that router is imported in `app/main.py`
- Verify API is running: `curl http://localhost:8000/healthz`

**Metrics show 0.0 for all values:**
- Check ES connectivity: `curl http://localhost:9200`
- Verify ES_EMAIL_INDEX exists: `curl http://localhost:9200/gmail_emails_v2`
- Check ES_URL environment variable

**Health emission fails:**
- Verify backfill_health_v1 index exists
- Check ES authentication (ES_API_KEY)
- Test with: `python scripts/emit_backfill_health.py`

**Kibana dashboard import fails:**
- Check Kibana version (8.x required for ES|QL)
- Verify index pattern creation
- Try manual import via Kibana UI: Stack Management → Saved Objects

## Next Steps

1. **Set up Prometheus** to scrape `/metrics` endpoint
2. **Create Grafana dashboard** for real-time visualization
3. **Configure alerts** for missing_dates and coverage thresholds
4. **Schedule health emission** (hourly cron or GitHub Actions)
5. **Import Kibana dashboard** for historical trending
6. **Review metrics weekly** to ensure backfill health
