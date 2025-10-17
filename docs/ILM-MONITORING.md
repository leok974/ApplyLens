# Elasticsearch ILM Monitoring Guide

## Overview

This guide covers monitoring queries and dashboard additions for Elasticsearch Index Lifecycle Management (ILM).

---

## Prometheus Metrics (if using Elasticsearch Exporter)

### ILM Phase Distribution

**Metric**: Count of indices by ILM phase (hot/warm/cold/delete)

```promql
# Count by phase
count by (phase) (ilm_executing_actions_total)

# Or using Elasticsearch metrics
elasticsearch_ilm_indices_total{phase=~"hot|warm|cold|delete"}
```

**Grafana Panel Configuration:**
```json
{
  "type": "stat",
  "title": "ILM Phases - Index Count",
  "targets": [
    { "expr": "count(elasticsearch_ilm_indices_total) by (phase)" }
  ],
  "fieldConfig": {
    "defaults": { "unit": "short" }
  }
}
```

---

## Elasticsearch Direct Queries

### 1. Current Phase Per Index

**Query**:
```bash
# Via curl
curl -s "http://elasticsearch:9200/_cat/ilm?v"

# PowerShell (from container)
docker exec applylens-api-prod curl -s "http://elasticsearch:9200/_cat/ilm?v"

# Python
import requests
r = requests.get('http://elasticsearch:9200/_cat/ilm?v')
print(r.text)
```

**Expected Output**:
```
index                 policy            phase  action       step              
gmail_emails-000001   emails-rolling-90d hot    rollover     check-rollover-ready
```

**Grafana Table Panel**:
```json
{
  "type": "table",
  "title": "ILM Index Status",
  "targets": [
    {
      "expr": "elasticsearch_ilm_indices_info",
      "format": "table"
    }
  ],
  "transformations": [
    {
      "id": "organize",
      "options": {
        "excludeByName": {},
        "indexByName": {},
        "renameByName": {
          "index": "Index",
          "phase": "Phase",
          "action": "Action",
          "step": "Step"
        }
      }
    }
  ]
}
```

---

### 2. Storage Trend by Index

**Query**:
```bash
# Current storage per index
curl -s "http://elasticsearch:9200/_cat/indices/gmail_emails-*?v&h=index,docs.count,store.size,pri.store.size"

# Detailed stats
curl -s "http://elasticsearch:9200/_stats/store" | jq '.indices | to_entries[] | {index: .key, size_bytes: .value.total.store.size_in_bytes, size_mb: (.value.total.store.size_in_bytes / 1024 / 1024 | round)}'
```

**Prometheus Query** (if using Elasticsearch exporter):
```promql
# Total storage by index
sum(elasticsearch_indices_store_size_bytes) by (index)

# Only gmail_emails indices
sum(elasticsearch_indices_store_size_bytes{index=~"gmail_emails-.*"}) by (index)

# Storage growth rate (5m)
rate(elasticsearch_indices_store_size_bytes{index=~"gmail_emails-.*"}[5m])
```

**Grafana Time Series Panel**:
```json
{
  "type": "timeseries",
  "title": "Email Index Storage Trend",
  "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
  "targets": [
    {
      "expr": "sum(elasticsearch_indices_store_size_bytes{index=~\"gmail_emails-.*\"}) by (index) / 1024 / 1024 / 1024",
      "legendFormat": "{{index}}",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "decgbytes",
      "custom": { "lineWidth": 2, "fillOpacity": 10 }
    }
  }
}
```

---

### 3. ILM Execution Stats

**Query**:
```bash
# ILM explain for specific index
curl -s "http://elasticsearch:9200/gmail_emails-000001/_ilm/explain?human" | jq

# All ILM-managed indices
curl -s "http://elasticsearch:9200/gmail_emails-*/_ilm/explain?human" | jq '.indices | to_entries[] | {index: .key, managed: .value.managed, phase: .value.phase, action: .value.action, step: .value.step}'
```

**PowerShell Monitoring Script**:
```powershell
# Check ILM status for all gmail indices
$ilmStatus = docker exec applylens-api-prod python -c @"
import requests, json
r = requests.get('http://elasticsearch:9200/gmail_emails-*/_ilm/explain?human')
data = r.json()
for idx, info in data['indices'].items():
    print(f'{idx:30} | Phase: {info.get(\"phase\",\"N/A\"):10} | Managed: {info.get(\"managed\",False)} | Age: {info.get(\"age\",\"N/A\")}')
"@
Write-Host $ilmStatus
```

---

### 4. Rollover Readiness Check

**Query**:
```bash
# Check if index is ready to rollover
curl -s "http://elasticsearch:9200/gmail_emails-000001/_ilm/explain?human" | jq '.indices | .[] | {
  phase: .phase,
  action: .action,
  step: .step,
  age: .age,
  size: .lifecycle_date_millis,
  step_info: .step_info
}'
```

**Conditions to Watch**:
- `age`: Should be approaching "30d"
- `step`: "check-rollover-ready" indicates evaluation in progress
- `step_info.message`: Details if rollover is blocked

---

### 5. Document Count Trend

**Query**:
```bash
# Document count per index
curl -s "http://elasticsearch:9200/_cat/indices/gmail_emails-*?v&h=index,docs.count,docs.deleted"

# Total docs across all gmail indices
curl -s "http://elasticsearch:9200/_cat/indices/gmail_emails-*?h=docs.count" | awk '{s+=$1} END {print s}'
```

**Prometheus Query**:
```promql
# Document count by index
elasticsearch_indices_docs{index=~"gmail_emails-.*"}

# Total documents
sum(elasticsearch_indices_docs{index=~"gmail_emails-.*"})

# Document ingestion rate (5m)
rate(elasticsearch_indices_docs{index=~"gmail_emails-.*"}[5m])
```

---

## Grafana Dashboard Panel - Complete Example

### Panel: ILM Storage & Rollover Overview

```json
{
  "dashboard": {
    "title": "Elasticsearch ILM Monitoring",
    "panels": [
      {
        "type": "stat",
        "title": "Active ILM Indices",
        "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4},
        "targets": [
          { "expr": "count(elasticsearch_indices_store_size_bytes{index=~\"gmail_emails-.*\"})" }
        ],
        "fieldConfig": { "defaults": { "unit": "short" } }
      },
      {
        "type": "stat",
        "title": "Total Storage (All Indices)",
        "gridPos": {"x": 6, "y": 0, "w": 6, "h": 4},
        "targets": [
          { "expr": "sum(elasticsearch_indices_store_size_bytes{index=~\"gmail_emails-.*\"}) / 1024 / 1024 / 1024" }
        ],
        "fieldConfig": { "defaults": { "unit": "decgbytes", "decimals": 2 } }
      },
      {
        "type": "timeseries",
        "title": "Storage by Index (Over Time)",
        "gridPos": {"x": 0, "y": 4, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "elasticsearch_indices_store_size_bytes{index=~\"gmail_emails-.*\"} / 1024 / 1024",
            "legendFormat": "{{index}}"
          }
        ],
        "fieldConfig": { "defaults": { "unit": "decmbytes" } }
      },
      {
        "type": "timeseries",
        "title": "Document Count by Index",
        "gridPos": {"x": 0, "y": 12, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "elasticsearch_indices_docs{index=~\"gmail_emails-.*\"}",
            "legendFormat": "{{index}}"
          }
        ],
        "fieldConfig": { "defaults": { "unit": "short" } }
      },
      {
        "type": "table",
        "title": "ILM Phase Status",
        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 12},
        "targets": [
          {
            "expr": "elasticsearch_ilm_indices_info{index=~\"gmail_emails-.*\"}",
            "format": "table"
          }
        ]
      }
    ]
  }
}
```

---

## Alerting Rules

### 1. Index Approaching Rollover

**Prometheus Alert**:
```yaml
- alert: ILM_IndexNearRollover
  expr: |
    (elasticsearch_indices_store_size_bytes{index=~"gmail_emails-.*"} / 1024 / 1024 / 1024) > 18
  for: 5m
  labels:
    severity: info
  annotations:
    summary: "Index {{ $labels.index }} approaching 20GB rollover threshold"
    description: "Current size: {{ $value | humanize }}GB (threshold: 20GB)"
```

### 2. ILM Policy Not Executing

**Prometheus Alert**:
```yaml
- alert: ILM_PolicyStalled
  expr: |
    increase(elasticsearch_ilm_policy_execution_errors_total[10m]) > 0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "ILM policy execution errors detected"
    description: "Policy {{ $labels.policy }} has errors"
```

### 3. Storage Growth Anomaly

**Prometheus Alert**:
```yaml
- alert: ILM_StorageGrowthAnomaly
  expr: |
    rate(elasticsearch_indices_store_size_bytes{index=~"gmail_emails-.*"}[1h]) > 100000000
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Unusual storage growth in {{ $labels.index }}"
    description: "Growth rate: {{ $value | humanize }}B/s (normal: <10MB/s)"
```

---

## Monitoring Script (PowerShell)

Save as `infra/es/monitor_ilm.ps1`:

```powershell
# ILM Monitoring Script
param(
    [string]$ES_URL = "http://localhost:9200",
    [switch]$Watch
)

function Get-ILMStatus {
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  Elasticsearch ILM Status                                      ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    
    # Get index stats
    Write-Host "Index Overview:" -ForegroundColor Yellow
    docker exec applylens-api-prod curl -s "$ES_URL/_cat/indices/gmail_emails-*?v&h=index,docs.count,store.size,health,status"
    
    Write-Host ""
    Write-Host "ILM Phase Status:" -ForegroundColor Yellow
    docker exec applylens-api-prod curl -s "$ES_URL/_cat/ilm/gmail_emails-*?v"
    
    Write-Host ""
    Write-Host "Storage Breakdown:" -ForegroundColor Yellow
    $stats = docker exec applylens-api-prod python -c @"
import requests, json
r = requests.get('$ES_URL/_stats/store')
data = r.json()
total_bytes = 0
for idx, info in data['indices'].items():
    if 'gmail_emails' in idx:
        size_mb = info['total']['store']['size_in_bytes'] / 1024 / 1024
        print(f'  {idx:30} | {size_mb:8.2f} MB')
        total_bytes += info['total']['store']['size_in_bytes']
print(f'  {\"TOTAL\":30} | {total_bytes/1024/1024:8.2f} MB')
"@
    Write-Host $stats
    
    Write-Host ""
}

if ($Watch) {
    while ($true) {
        Clear-Host
        Get-ILMStatus
        Write-Host ""
        Write-Host "Refreshing in 30 seconds... (Ctrl+C to stop)" -ForegroundColor Gray
        Start-Sleep -Seconds 30
    }
} else {
    Get-ILMStatus
}
```

**Usage**:
```powershell
# One-time check
.\infra\es\monitor_ilm.ps1

# Continuous monitoring (refreshes every 30s)
.\infra\es\monitor_ilm.ps1 -Watch
```

---

## Summary - Monitoring Metrics

| Metric | Query | Use Case |
|--------|-------|----------|
| **ILM Phase Count** | `count by (phase) (ilm_executing_actions_total)` | Track phase distribution |
| **Current Phase Per Index** | `_cat/ilm?v` | See which phase each index is in |
| **Storage Trend** | `sum(elasticsearch_indices_store_size_bytes) by (index)` | Monitor storage growth |
| **Document Count** | `elasticsearch_indices_docs{index=~"gmail_emails-.*"}` | Track ingestion rate |
| **Rollover Readiness** | `/_ilm/explain?human` | Check if rollover imminent |
| **ILM Errors** | `elasticsearch_ilm_policy_execution_errors_total` | Detect policy failures |

---

## Next Steps

1. **Add to Grafana**: Import the monitoring panels above
2. **Set Up Alerts**: Configure Prometheus alerting rules
3. **Monitor First Rollover**: Watch for first automatic rollover at 30 days
4. **Validate Deletions**: Confirm old indices delete after 90 days

For setup instructions, see: `docs/SETUP-GUIDE-ADVANCED.md`
