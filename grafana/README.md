# Grafana Dashboard Setup for Backfill Health

Complete Grafana setup guide for monitoring backfill health via Prometheus metrics.

## Components

### 1. Dashboard (`backfill-health-dashboard.json`)

**Panels:**
- **Missing dates[] (bills)** — Stat panel showing count of bills without dates[] field
  - ✅ Green when 0
  - 🔴 Red when > 0
  
- **Bills with dates[]** — Stat panel showing bills with dates[] populated

- **Bills with expires_at** — Stat panel showing bills with expires_at set

- **Missing dates[] over time** — Time series chart tracking missing dates trend
  - Smooth line interpolation
  - 24-hour default range
  - Auto-refresh every 30s

- **Last refresh (unix seconds)** — Stat panel showing last metrics refresh timestamp

**Features:**
- **Instance variable** — Multi-select dropdown to filter by API instance
- **Tags**: applylens, backfill, mailbox
- **Auto-refresh**: Every 30 seconds
- **Time range**: Last 24 hours (adjustable)

### 2. Alert Rule (`alert-backfill-missing.json`)

**Alert:** "Backfill: Missing bill dates > 0"

**Trigger:** When `bills_missing_dates > 0` for 10 minutes

**Evaluation:**
- Query: `bills_missing_dates{instance=~"$instance"}`
- Reduce: Last value
- Threshold: Greater than 1
- Duration: 10 minutes

**Labels:**
- service: applylens-api

**Annotations:**
- Summary: "Bills missing dates[] > 0 for 10m"
- Runbook URL: Configurable

## Prerequisites

### 1. Prometheus Data Source

Ensure Grafana has Prometheus configured:

1. Go to **Grafana → Connections → Data sources**
2. Add **Prometheus** data source
3. Set URL: `http://prometheus:9090` (or your Prometheus host)
4. Set Access: `Server` (default)
5. Click **Save & test**

**Note the UID** (usually `prometheus`). If different, update the JSON files.

### 2. Prometheus Scrape Configuration

Ensure Prometheus is scraping your API's `/metrics` endpoint.

**Add to `prometheus.yml`:**

```yaml
scrape_configs:
  - job_name: 'applylens-api'
    scrape_interval: 30s
    static_configs:
      - targets:
          - 'api:8003'          # Docker service name
          # - 'localhost:8003'  # Local development
    metrics_path: '/metrics'
```

**Reload Prometheus:**
```bash
# Docker
docker-compose restart prometheus

# Or send SIGHUP
docker-compose kill -s SIGHUP prometheus

# Verify targets
curl http://localhost:9090/api/v1/targets
```

### 3. FastAPI Metrics Endpoint

Verify your API is exposing metrics:

```bash
# Test metrics endpoint
curl http://localhost:8003/metrics

# Expected output:
# HELP bills_missing_dates Bills missing dates[] field
# TYPE bills_missing_dates gauge
bills_missing_dates 0.0
# HELP bills_with_dates Bills with dates[] populated
# TYPE bills_with_dates gauge
bills_with_dates 1243.0
# ...
```

## Installation

### Method 1: Grafana UI (Recommended for first-time setup)

**Import Dashboard:**

1. Go to **Grafana → Dashboards → New → Import**
2. Click **Upload JSON file**
3. Select `grafana/backfill-health-dashboard.json`
4. Click **Import**
5. Dashboard appears at `/d/backfill-prom-health`

**Import Alert Rule (Optional):**

1. Go to **Grafana → Alerting → Alert rules**
2. Click **New alert rule**
3. Switch to **JSON** view (toggle in top-right)
4. Paste contents of `grafana/alert-backfill-missing.json`
5. Click **Save rule and exit**

### Method 2: API Import (Automation/CI/CD)

**Import Dashboard:**

```bash
# Set Grafana API token
GRAFANA_TOKEN="your-api-token-here"
GRAFANA_HOST="http://localhost:3000"

# Import dashboard
curl -X POST "${GRAFANA_HOST}/api/dashboards/db" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
  --data-binary @grafana/backfill-health-dashboard.json
```

**PowerShell:**
```powershell
$token = "your-api-token-here"
$host = "http://localhost:3000"

Invoke-RestMethod -Method POST `
  -Uri "${host}/api/dashboards/db" `
  -Headers @{"Authorization"="Bearer ${token}"} `
  -ContentType "application/json" `
  -InFile "grafana\backfill-health-dashboard.json"
```

**Import Alert Rule:**

```bash
curl -X POST "${GRAFANA_HOST}/api/ruler/grafana/api/v1/rules" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
  --data-binary @grafana/alert-backfill-missing.json
```

**PowerShell:**
```powershell
Invoke-RestMethod -Method POST `
  -Uri "${host}/api/ruler/grafana/api/v1/rules" `
  -Headers @{"Authorization"="Bearer ${token}"} `
  -ContentType "application/json" `
  -InFile "grafana\alert-backfill-missing.json"
```

### Method 3: Grafana Provisioning (Persistent/GitOps)

For persistent configuration that survives container restarts:

**1. Create provisioning directory structure:**

```
grafana/
├── provisioning/
│   ├── dashboards/
│   │   ├── dashboards.yml
│   │   └── backfill-health-dashboard.json
│   └── datasources/
│       └── prometheus.yml
```

**2. Create `grafana/provisioning/dashboards/dashboards.yml`:**

```yaml
apiVersion: 1

providers:
  - name: 'ApplyLens Dashboards'
    orgId: 1
    folder: 'ApplyLens'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

**3. Copy dashboard JSON:**
```bash
cp grafana/backfill-health-dashboard.json grafana/provisioning/dashboards/
```

**4. Update docker-compose.yml:**

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    ports:
      - "3000:3000"
```

**5. Restart Grafana:**
```bash
docker-compose restart grafana
```

## Configuration

### Update Prometheus Data Source UID

If your Prometheus datasource UID is not `prometheus`:

1. Find your UID: **Grafana → Connections → Data sources → Prometheus → Settings**
2. Look for `uid` in the URL or API response
3. Update JSON files:

```bash
# Linux/Mac
sed -i 's/"uid": "prometheus"/"uid": "YOUR_UID"/g' grafana/backfill-health-dashboard.json
sed -i 's/"datasourceUid": "prometheus"/"datasourceUid": "YOUR_UID"/g' grafana/alert-backfill-missing.json

# PowerShell
(Get-Content grafana\backfill-health-dashboard.json) -replace '"uid": "prometheus"', '"uid": "YOUR_UID"' | Set-Content grafana\backfill-health-dashboard.json
(Get-Content grafana\alert-backfill-missing.json) -replace '"datasourceUid": "prometheus"', '"datasourceUid": "YOUR_UID"' | Set-Content grafana\alert-backfill-missing.json
```

### Customize Alert Thresholds

Edit `grafana/alert-backfill-missing.json`:

**Change threshold value** (currently > 0):
```json
"params": [
  1,      // Threshold value (change this)
  "gt"    // Comparison: gt (>), lt (<), eq (==)
]
```

**Change alert duration** (currently 10m):
```json
"for": "10m"  // Change to "5m", "30m", etc.
```

**Change evaluation interval** (currently 1m):
```json
"interval": "1m"  // Change to "30s", "5m", etc.
```

## Usage

### View Dashboard

1. Navigate to **Grafana → Dashboards → Backfill Health — Prometheus**
2. URL: `http://localhost:3000/d/backfill-prom-health`

**Dashboard Features:**

- **Instance filter**: Select specific API instances
- **Time range selector**: Adjust time window (top-right)
- **Auto-refresh**: Toggle and configure refresh rate
- **Panel zoom**: Click and drag on time series to zoom
- **Share**: Share dashboard via link or embed

### Monitor Alerts

1. Navigate to **Grafana → Alerting → Alert rules**
2. Find "Backfill: Missing bill dates > 0"
3. View **State**: Normal, Pending, Alerting, NoData, Error

**Alert States:**
- ✅ **Normal**: All bills have dates
- ⏳ **Pending**: Missing dates detected, waiting for 10m threshold
- 🔴 **Alerting**: Bills missing dates for > 10 minutes
- ⚠️ **NoData**: No metrics received
- ❌ **Error**: Query error

### Configure Notifications

**Set up Slack/Email/PagerDuty:**

1. Go to **Grafana → Alerting → Contact points**
2. Click **New contact point**
3. Configure:
   - **Name**: "Backfill Alerts"
   - **Integration**: Slack, Email, PagerDuty, etc.
   - **Settings**: Webhook URL, email addresses, etc.
4. Click **Test** to verify
5. Click **Save contact point**

**Create notification policy:**

1. Go to **Grafana → Alerting → Notification policies**
2. Click **New policy**
3. Add **Label matcher**:
   - Label: `service`
   - Operator: `=`
   - Value: `applylens-api`
4. Select **Contact point**: "Backfill Alerts"
5. Click **Save policy**

Now alerts with `service=applylens-api` label route to your contact point.

## Verification Checklist

- [ ] Prometheus is scraping `/metrics` endpoint
  - Check: `curl http://prometheus:9090/api/v1/targets`
  - Should show `applylens-api` target as **UP**

- [ ] Metrics are visible in Prometheus
  - Check: `curl 'http://prometheus:9090/api/v1/query?query=bills_missing_dates'`
  - Should return current value

- [ ] Dashboard imported successfully
  - Check: `http://localhost:3000/d/backfill-prom-health`
  - Should show 5 panels with data

- [ ] Instance variable populates
  - Dashboard should show dropdown with available instances

- [ ] Auto-refresh works
  - Metrics should update every 30 seconds

- [ ] Alert rule created (if using alerts)
  - Check: Grafana → Alerting → Alert rules
  - Should show "Backfill: Missing bill dates > 0"

- [ ] Alert evaluates correctly
  - Trigger test: Set `bills_missing_dates > 0`
  - Wait 10 minutes
  - Alert should fire

## Troubleshooting

### Dashboard shows "No data"

**Check Prometheus scrape:**
```bash
# Verify target is UP
curl http://prometheus:9090/api/v1/targets | jq '.data.activeTargets[] | select(.job=="applylens-api")'

# Should show state: "up"
```

**Check metrics exist:**
```bash
# Query Prometheus directly
curl 'http://prometheus:9090/api/v1/query?query=bills_missing_dates' | jq .

# Should return value
```

**Check data source:**
- Grafana → Connections → Data sources → Prometheus
- Click **Save & test**
- Should show green checkmark

### Alert doesn't fire

**Check alert rule:**
```bash
# Get alert rule status
curl http://localhost:3000/api/ruler/grafana/api/v1/rules \
  -H "Authorization: Bearer ${GRAFANA_TOKEN}" | jq .
```

**Check evaluation:**
- Grafana → Alerting → Alert rules → "Backfill: Missing bill dates > 0"
- Click **View details**
- See evaluation history and query results

**Trigger manually:**
```bash
# Set high missing count (for testing)
# This would require modifying your ES data or mocking
```

### Panels show wrong values

**Verify metric format:**
```bash
# Check Prometheus metric
curl http://localhost:8003/metrics | grep bills_

# Should show:
# bills_missing_dates 0.0
# bills_with_dates 1243.0
# bills_with_expires_at 1243.0
```

**Check query in panel:**
- Dashboard → Panel → Edit
- See query: `bills_missing_dates{instance=~"$instance"}`
- Run query in Prometheus: `http://prometheus:9090/graph`

### Instance variable is empty

**Check label exists:**
```bash
# Query label values
curl 'http://prometheus:9090/api/v1/label/instance/values' | jq .

# Should return list of instances
```

**Update query:**
- Dashboard → Settings → Variables → instance
- Query: `label_values(bills_missing_dates, instance)`
- Click **Update**

## Advanced Configuration

### Add Coverage Percentage Panel

Add a new panel showing backfill coverage:

```json
{
  "type": "stat",
  "title": "Backfill Coverage %",
  "targets": [
    {
      "expr": "(bills_with_expires_at / bills_with_dates) * 100"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "percent",
      "thresholds": {
        "steps": [
          {"color": "red", "value": null},
          {"color": "yellow", "value": 90},
          {"color": "green", "value": 95}
        ]
      }
    }
  }
}
```

### Add Table Panel for Multi-Instance View

Show all instances in a table:

```json
{
  "type": "table",
  "title": "All Instances Status",
  "targets": [
    {
      "expr": "bills_missing_dates",
      "format": "table",
      "instant": true
    }
  ]
}
```

### Create Unified Dashboard

Combine with other ApplyLens metrics:

1. Export this dashboard: Dashboards → Share → Export
2. Export your main dashboard
3. Merge JSON `panels` arrays
4. Re-import combined dashboard

## Integration with Existing Monitoring

### Add to Agentic Mailbox Dashboard

If you have an existing ApplyLens or Agentic Mailbox dashboard:

1. Open your existing dashboard
2. Click **Add → Visualization**
3. Copy query from `backfill-health-dashboard.json`
4. Paste into new panel
5. Repeat for each panel you want

### Link Dashboards

Add navigation link:

1. Dashboard → Settings → Links
2. Add **Dashboard link**:
   - Title: "Backfill Health"
   - URL: `/d/backfill-prom-health`
3. Save dashboard

## Maintenance

### Update Dashboard

**Method 1: UI**
1. Make changes in Grafana
2. Dashboard → Share → Export
3. Save to `grafana/backfill-health-dashboard.json`
4. Commit to Git

**Method 2: JSON**
1. Edit `grafana/backfill-health-dashboard.json`
2. Re-import via UI or API
3. Grafana will update existing dashboard (same UID)

### Backup Configuration

```bash
# Export all dashboards
curl -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
  http://localhost:3000/api/search?type=dash-db | \
  jq -r '.[] | .uid' | \
  xargs -I {} curl -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
    http://localhost:3000/api/dashboards/uid/{} > backup-{}.json
```

### Version Control

Add to `.gitignore`:
```
# Grafana runtime
grafana/data/
grafana/*.db

# Keep provisioning
!grafana/provisioning/
!grafana/*.json
```

## Resources

- **Grafana Docs**: https://grafana.com/docs/grafana/latest/
- **Prometheus Docs**: https://prometheus.io/docs/
- **ApplyLens Monitoring**: `kibana/README_monitoring.md`
- **API Metrics**: `services/api/app/routers/metrics.py`

## Support

For issues or questions:
- Check logs: `docker-compose logs grafana`
- Verify Prometheus targets: `http://prometheus:9090/targets`
- Test API metrics: `curl http://localhost:8003/metrics`
- Review alert evaluation: Grafana → Alerting → Alert rules
