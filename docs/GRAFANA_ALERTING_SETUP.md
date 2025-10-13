# 🚨 Grafana Alerting Setup Complete

## ✅ What Was Configured

### 1. **Prometheus Datasource with Fixed UID**

- **File:** `infra/grafana/provisioning/datasources/prom.yml`
- **UID:** `prom` (allows alert rules to reference it reliably)
- **URL:** `http://prometheus:9090`

### 2. **Contact Points**

- **File:** `infra/grafana/provisioning/alerting/contact-points.yaml`
- **Default Contact Point:** Webhook at `http://host.docker.internal:9000/webhook`
- **Purpose:** Sends alert notifications (TODO: replace with real Slack/Email/Teams)

### 3. **Notification Policies**

- **File:** `infra/grafana/provisioning/alerting/notification-policies.yaml`
- **Default Route:** All alerts go to "Default" contact point
- **Grouping:** Alerts grouped by `alertname`
- **Matching:** Routes alerts with severity: critical|warning|info

### 4. **Alert Rules (3 Rules in ApplyLens Folder)**

- **File:** `infra/grafana/provisioning/alerting/rules-applylens.yaml`

#### Rule 1: ApplyLens API Down

- **UID:** `applens_api_down`
- **Severity:** `critical`
- **Condition:** `up{job="applylens-api"} < 0.5` for >1 minute
- **Description:** API target not responding

#### Rule 2: High HTTP Error Rate

- **UID:** `applens_http_error_rate`
- **Severity:** `warning`
- **Condition:** 5xx errors > 5% for 5 minutes
- **Description:** HTTP error rate above acceptable threshold

#### Rule 3: Backfill Errors

- **UID:** `applens_backfill_errors`
- **Severity:** `warning`
- **Condition:** Any backfill errors in last 10 minutes
- **Description:** Backfill process failing

---

## 🔍 Verification Steps

### Check in Grafana UI

1. **Contact Points**
   - URL: <http://localhost:3000/alerting/notifications>
   - Should show: "Default" contact point with webhook

2. **Notification Policies**
   - URL: <http://localhost:3000/alerting/routes>
   - Should show: Root policy routing to "Default"

3. **Alert Rules**
   - URL: <http://localhost:3000/alerting/list>
   - Should show: 3 rules in "ApplyLens" folder
   - Status: OK (green) when system is healthy

### Check Alert Rule Status

```powershell
# Login credentials
$cred = New-Object PSCredential("admin", (ConvertTo-SecureString "admin" -AsPlainText -Force))

# Get alert rules
$rules = Invoke-RestMethod -Uri "http://localhost:3000/api/v1/provisioning/alert-rules" -Credential $cred

# Display rules
$rules | Select-Object title, @{Name='Severity';Expression={$_.labels.severity}}, folderUID | Format-Table
```

---

## 🧪 Testing Alerts

### Test 1: Trigger API Down Alert

```powershell
# Stop API
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop api

# Wait for alert to fire (>1 minute)
Start-Sleep -Seconds 70

# Check alert status
start http://localhost:3000/alerting/list

# Restart API
docker compose -f D:\ApplyLens\infra\docker-compose.yml start api
```

**Expected:** "ApplyLens API Down" alert fires after 1 minute, notification sent to webhook

### Test 2: Simulate HTTP Error Rate

```powershell
# This requires actual 5xx errors from your API
# You'd need to trigger errors by:
# - Stopping dependencies (DB/ES)
# - Calling endpoints that throw exceptions
# - Using test/debug endpoints that return 500

# Example: Stop Elasticsearch to cause errors
docker compose -f D:\ApplyLens\infra\docker-compose.yml stop elasticsearch
# Make requests that need ES
1..20 | % { curl http://localhost:8003/some-endpoint-that-uses-es }
# Wait 5 minutes for alert to fire
```

### Test 3: Backfill Errors

```powershell
# Requires actual backfill errors
# Trigger by:
# - Pointing backfill to invalid data
# - Stopping ES during backfill
# - Using invalid OAuth tokens
```

---

## 📧 Setting Up Real Notifications

### Option A: Email (SMTP)

1. **Update docker-compose.yml** with Grafana SMTP environment variables:

```yaml
grafana:
  environment:
    - GF_SMTP_ENABLED=true
    - GF_SMTP_HOST=smtp.gmail.com:587
    - GF_SMTP_USER=your-email@gmail.com
    - GF_SMTP_PASSWORD=your-app-password
    - GF_SMTP_FROM_ADDRESS=your-email@gmail.com
    - GF_SMTP_FROM_NAME=ApplyLens Alerts
```

2. **Update contact-points.yaml**:

```yaml
contactPoints:
  - orgId: 1
    name: Email
    receivers:
      - uid: ops_email
        type: email
        settings:
          addresses: ops-team@example.com
```

3. **Restart Grafana:**

```powershell
docker compose -f D:\ApplyLens\infra\docker-compose.yml restart grafana
```

### Option B: Slack

1. **Create Slack Incoming Webhook:**
   - Go to <https://api.slack.com/apps>
   - Create new app → Incoming Webhooks
   - Copy webhook URL (e.g., `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX`)

2. **Update contact-points.yaml**:

```yaml
contactPoints:
  - orgId: 1
    name: Slack
    receivers:
      - uid: slack_alerts
        type: slack
        settings:
          url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
          username: ApplyLens Alerts
          icon_emoji: ":rotating_light:"
```

3. **Update notification-policies.yaml** to route to Slack:

```yaml
policies:
  - orgId: 1
    receiver: Slack
    group_by:
      - alertname
```

4. **Restart Grafana:**

```powershell
docker compose -f D:\ApplyLens\infra\docker-compose.yml restart grafana
```

### Option C: Microsoft Teams

1. **Create Teams Incoming Webhook:**
   - In Teams channel → Connectors → Incoming Webhook
   - Copy webhook URL

2. **Update contact-points.yaml**:

```yaml
contactPoints:
  - orgId: 1
    name: Teams
    receivers:
      - uid: teams_alerts
        type: teams
        settings:
          url: https://outlook.office.com/webhook/YOUR-WEBHOOK-URL
```

---

## 🎨 Advanced Alert Configurations

### Add More Alert Rules

Create additional rules in `rules-applylens.yaml`:

```yaml
# Example: High CPU usage
- uid: applens_high_cpu
  title: High CPU Usage
  condition: C
  data:
    - refId: A
      datasourceUid: prom
      relativeTimeRange: { from: 300, to: 0 }
      model:
        refId: A
        expr: rate(process_cpu_seconds_total[5m]) > 0.8
        instant: true
  for: 5m
  annotations:
    summary: "CPU usage > 80%"
  labels:
    severity: warning
    alertname: HighCPU
```

### Route Different Severities to Different Channels

Update `notification-policies.yaml`:

```yaml
policies:
  - orgId: 1
    receiver: Default
    group_by:
      - alertname
    routes:
      # Critical alerts to PagerDuty
      - receiver: PagerDuty
        object_matchers:
          - [ "severity", "=", "critical" ]
        continue: true
      
      # Warning alerts to Slack
      - receiver: Slack
        object_matchers:
          - [ "severity", "=", "warning" ]
        continue: true
      
      # Info alerts to email
      - receiver: Email
        object_matchers:
          - [ "severity", "=", "info" ]
```

---

## 📊 Alert States

Alerts go through these states:

1. **Normal** (Green) - Condition not met
2. **Pending** (Yellow) - Condition met, waiting for `for:` duration
3. **Firing** (Red) - Condition met for duration, notification sent
4. **Resolved** (Gray) - Was firing, now back to normal

---

## 🔧 Troubleshooting

### Alerts Not Appearing in Grafana

```powershell
# Check Grafana logs for provisioning errors
docker logs infra-grafana --tail 50 | Select-String "alerting"

# Verify files exist
Get-ChildItem D:\ApplyLens\infra\grafana\provisioning\alerting\*.yaml

# Check file syntax
Get-Content D:\ApplyLens\infra\grafana\provisioning\alerting\rules-applylens.yaml
```

### Notifications Not Sending

```powershell
# Check contact point configuration
docker logs infra-grafana --tail 100 | Select-String "contact"

# Test webhook manually
Invoke-WebRequest -Method POST -Uri "http://localhost:9000/webhook" `
  -ContentType "application/json" `
  -Body '{"status":"firing","alerts":[{"labels":{"alertname":"test"}}]}'
```

### Datasource Not Found Error

```powershell
# Verify datasource has uid: prom
Get-Content D:\ApplyLens\infra\grafana\provisioning\datasources\prom.yml

# Should contain:
# datasources:
#   - name: Prometheus
#     uid: prom    # <-- Must be present
```

---

## 📁 File Structure

```
infra/grafana/provisioning/
├── datasources/
│   └── prom.yml                          # Prometheus datasource with uid: prom
├── dashboards/
│   ├── applylens.yml                     # Dashboard provider
│   └── json/
│       └── applylens-overview.json       # Main dashboard
└── alerting/                             # ← NEW
    ├── contact-points.yaml               # Notification destinations
    ├── notification-policies.yaml        # Routing rules
    └── rules-applylens.yaml              # Alert rule definitions
```

---

## 🎯 Next Steps

- [ ] Replace webhook contact point with real Slack/Email
- [ ] Test each alert by simulating failure conditions
- [ ] Add more alert rules for business metrics
- [ ] Configure alert silences for maintenance windows
- [ ] Set up on-call schedules (if using PagerDuty)
- [ ] Create runbooks for each alert (links in annotations)
- [ ] Configure alert grouping to reduce notification noise

---

## 📚 Additional Resources

- **Grafana Alerting Docs:** <https://grafana.com/docs/grafana/latest/alerting/>
- **Provisioning Docs:** <https://grafana.com/docs/grafana/latest/administration/provisioning/>
- **Contact Point Types:** <https://grafana.com/docs/grafana/latest/alerting/manage-notifications/>
- **PromQL for Alerts:** <https://prometheus.io/docs/prometheus/latest/querying/basics/>

---

**✅ Alerting is now fully configured and auto-provisioned!**

Open <http://localhost:3000/alerting/list> to see your alert rules in action! 🎉
