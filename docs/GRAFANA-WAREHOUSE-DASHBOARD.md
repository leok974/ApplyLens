# Grafana Dashboard Configuration for Warehouse Metrics

## Dashboard: Email Analytics Warehouse

### Panel 1: Email Activity (Daily)
**Type:** Time Series Graph  
**Data Source:** BigQuery or API Proxy  
**Query:**
```sql
SELECT 
  UNIX_SECONDS(TIMESTAMP(day)) * 1000 as time,
  messages_count as value,
  'messages' as metric
FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_marts.mart_email_activity_daily`
WHERE day >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
ORDER BY day

UNION ALL

SELECT 
  UNIX_SECONDS(TIMESTAMP(day)) * 1000 as time,
  unique_senders as value,
  'senders' as metric
FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_marts.mart_email_activity_daily`
WHERE day >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
ORDER BY day
```

**Alternative (API):**
- Endpoint: `http://api:8003/api/metrics/profile/activity_daily?days=90`
- Transform: JSON to Time Series
- Refresh: 5 minutes

**Visualization:**
- Lines + Points
- Y-Axis: Messages Count
- Y-Axis (right): Unique Senders
- Legend: Bottom
- Time Range: Last 90 days

---

### Panel 2: Top Senders (30 Days)
**Type:** Bar Chart (Horizontal)  
**Data Source:** API  
**Query:**
- Endpoint: `http://api:8003/api/metrics/profile/top_senders_30d?limit=10`
- Field: `from_email` (X-axis), `messages_30d` (Y-axis)

**Visualization:**
- Orientation: Horizontal
- Show values: Yes
- Color: Gradient by value

---

### Panel 3: Category Distribution
**Type:** Pie Chart  
**Data Source:** API  
**Query:**
- Endpoint: `http://api:8003/api/metrics/profile/categories_30d`
- Fields: `category`, `pct_of_total`

**Visualization:**
- Display labels: Name + Percent
- Legend: Right
- Colors: 
  - updates: Blue
  - forums: Green
  - promotions: Yellow
  - primary: Red

---

### Panel 4: Data Freshness SLO
**Type:** Stat Panel  
**Data Source:** API  
**Query:**
- Endpoint: `http://api:8003/api/metrics/profile/freshness`
- Field: `minutes_since_sync`
- Refresh: 1 minute

**Thresholds:**
- Green: 0-15 minutes (Fresh)
- Yellow: 15-30 minutes (Warning)
- Red: 30+ minutes (Stale - SLO breach)

**Display:**
- Value: Minutes since sync
- Sparkline: Enabled
- Color mode: Background

---

### Panel 5: ES ↔ BQ Drift %
**Type:** Stat Panel with Sparkline  
**Data Source:** Prometheus  
**Query:**
```promql
applylens_gmail_7d_delta_pct
```

**Thresholds:**
- Green: 0-1% (Normal)
- Yellow: 1-2% (Warning)
- Red: 2%+ (Critical - Data inconsistency)

**Alerts:**
- Warning: `applylens_gmail_7d_delta_pct > 1 for 6h`
- Critical: `applylens_gmail_7d_delta_pct > 2 for 24h`

---

### Panel 6: Daily Volume Trend
**Type:** Single Stat  
**Data Source:** BigQuery  
**Query:**
```sql
SELECT 
  messages_count as value
FROM `applylens-gmail-1759983601.gmail_raw_stg_gmail_marts.mart_email_activity_daily`
WHERE day = CURRENT_DATE() - 1
```

**Comparison:** Week-over-week change
```sql
SELECT 
  ROUND((curr.messages_count - prev.messages_count) * 100.0 / prev.messages_count, 1) as wow_change_pct
FROM 
  (SELECT messages_count FROM `...mart_email_activity_daily` WHERE day = CURRENT_DATE() - 1) curr,
  (SELECT messages_count FROM `...mart_email_activity_daily` WHERE day = CURRENT_DATE() - 8) prev
```

**Alert:** `wow_change_pct > 50` (spike detection)

---

## Alert Rules

### Critical Alerts

**1. Data Freshness Breach**
```yaml
alert: DataFreshnessCritical
expr: applylens_warehouse_freshness_minutes > 30
for: 5m
labels:
  severity: critical
annotations:
  summary: "Warehouse data is stale ({{ $value }}min old)"
  description: "Fivetran sync has not run in over 30 minutes. SLO breached."
```

**2. High Drift (ES vs BQ)**
```yaml
alert: DataDriftHigh
expr: applylens_gmail_7d_delta_pct > 2
for: 24h
labels:
  severity: critical
annotations:
  summary: "ES↔BQ drift is {{ $value }}%"
  description: "Data inconsistency detected. ES and BQ counts differ by >2%."
```

### Warning Alerts

**3. Freshness Warning**
```yaml
alert: DataFreshnessWarning
expr: applylens_warehouse_freshness_minutes > 20
for: 10m
labels:
  severity: warning
annotations:
  summary: "Warehouse data aging ({{ $value }}min old)"
```

**4. Moderate Drift**
```yaml
alert: DataDriftModerate
expr: applylens_gmail_7d_delta_pct > 1
for: 6h
labels:
  severity: warning
annotations:
  summary: "ES↔BQ drift is {{ $value }}%"
```

**5. Volume Spike**
```yaml
alert: EmailVolumeSpike
expr: (
  sum(rate(applylens_emails_indexed_total[1h])) 
  / 
  sum(rate(applylens_emails_indexed_total[1h] offset 1w))
) > 1.5
for: 2h
labels:
  severity: warning
annotations:
  summary: "Email volume 50%+ above normal"
```

---

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────┐
│  Email Analytics Warehouse                              │
├──────────────────┬──────────────────┬───────────────────┤
│  Daily Activity  │  Top Senders     │  Category Mix     │
│  (90 days line)  │  (bar chart)     │  (pie chart)      │
│                  │                  │                   │
├──────────────────┴──────────────────┴───────────────────┤
│  Volume Today    │  Freshness       │  ES↔BQ Drift %    │
│  (vs 1w ago)     │  (minutes)       │  (7d window)      │
├──────────────────┴──────────────────┴───────────────────┤
│  Recent Alerts                                          │
│  [List of active alerts]                                │
└─────────────────────────────────────────────────────────┘
```

---

## Setup Instructions

### 1. Import Dashboard

```bash
# Export existing dashboard
curl -H "Authorization: Bearer <api-key>" \
  http://localhost:3000/api/dashboards/uid/warehouse-metrics \
  > warehouse-dashboard.json

# Or create new from template
grafana-cli dashboards install <dashboard-id>
```

### 2. Configure Data Sources

**BigQuery:**
- Plugin: `grafana-bigquery-datasource`
- Project: `applylens-gmail-1759983601`
- Service Account: Upload `applylens-warehouse-key.json`
- Location: `US`

**API (JSON):**
- Plugin: `marcusolsson-json-datasource`
- URL: `http://api:8003`
- Method: GET
- Headers: None (internal network)

**Prometheus:**
- URL: `http://prometheus:9090`
- Access: Server (default)

### 3. Set Up Notifications

**Slack:**
```yaml
notifiers:
  - name: slack-warehouse-alerts
    type: slack
    settings:
      url: <webhook-url>
      channel: #warehouse-alerts
      username: Grafana
      icon_emoji: ":chart_with_upwards_trend:"
```

**Email:**
```yaml
notifiers:
  - name: email-oncall
    type: email
    settings:
      addresses: oncall@company.com
      singleEmail: true
```

---

## Quick Test

```powershell
# Test all panels manually
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/activity_daily?days=7'
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/top_senders_30d?limit=10'
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/categories_30d'
Invoke-RestMethod 'http://localhost:8003/api/metrics/profile/freshness'

# Check Prometheus metrics
Invoke-RestMethod 'http://localhost:9090/api/v1/query?query=applylens_gmail_7d_delta_pct'
```

---

## Export/Import

### Export current dashboard
```bash
curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
  http://localhost:3000/api/dashboards/uid/warehouse-metrics \
  | jq . > dashboards/warehouse-metrics.json
```

### Import dashboard
```bash
curl -X POST -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -H "Content-Type: application/json" \
  -d @dashboards/warehouse-metrics.json \
  http://localhost:3000/api/dashboards/db
```
