# Uptime Monitoring Configuration

## Service: Warehouse API Endpoints

### Endpoints to Monitor

#### 1. Activity Daily (Primary Health Check)
```http
GET http://api:8003/api/metrics/profile/activity_daily?days=7
```

**Expected Response:**
```json
[
  {
    "day": "2025-01-15",
    "messages_count": 42,
    "unique_senders": 18,
    "unique_recipients": 5,
    "total_size_mb": 3.45
  },
  ...
]
```

**Health Criteria:**
- ✅ HTTP 200 OK
- ✅ Response time < 5 seconds
- ✅ Valid JSON array
- ✅ At least 1 record returned
- ✅ `messages_count >= 0`

**Failure Conditions:**
- ❌ HTTP 500 (BigQuery connection failure)
- ❌ HTTP 404 (routing issue)
- ❌ Timeout > 10 seconds
- ❌ Invalid JSON
- ❌ Empty array (data pipeline issue)

---

#### 2. Freshness Check (SLO Validation)
```http
GET http://api:8003/api/metrics/profile/freshness
```

**Expected Response:**
```json
{
  "last_bq_sync": "2025-01-15T10:23:00Z",
  "minutes_since_sync": 7,
  "is_fresh": true
}
```

**Health Criteria:**
- ✅ HTTP 200 OK
- ✅ `is_fresh: true`
- ✅ `minutes_since_sync <= 30`
- ✅ Response time < 3 seconds

**Failure Conditions:**
- ❌ `is_fresh: false` (Fivetran sync stale)
- ❌ `minutes_since_sync > 30` (SLO breach)

---

#### 3. Top Senders (Data Quality Check)
```http
GET http://api:8003/api/metrics/profile/top_senders_30d?limit=5
```

**Expected Response:**
```json
[
  {
    "from_email": "notifications@github.com",
    "messages_30d": 734,
    "total_size_mb": 28.19,
    "pct_of_total": 64.64
  },
  ...
]
```

**Health Criteria:**
- ✅ HTTP 200 OK
- ✅ At least 1 sender returned
- ✅ `from_email` not null
- ✅ `messages_30d > 0`

**Failure Conditions:**
- ❌ Empty array (header parsing failure)
- ❌ `from_email: null` (data quality issue)

---

#### 4. Categories (Classification Check)
```http
GET http://api:8003/api/metrics/profile/categories_30d
```

**Expected Response:**
```json
[
  {
    "category": "updates",
    "messages_30d": 897,
    "pct_of_total": 78.89,
    "total_size_mb": 35.67
  },
  ...
]
```

**Health Criteria:**
- ✅ HTTP 200 OK
- ✅ At least 1 category returned
- ✅ Sum of `pct_of_total` ~= 100

---

## Monitoring Tools

### Option 1: Grafana Synthetic Monitoring

**Install Plugin:**
```bash
grafana-cli plugins install grafana-synthetic-monitoring-app
```

**Configure Checks:**
```yaml
checks:
  - name: warehouse-activity-daily
    type: http
    target: http://api:8003/api/metrics/profile/activity_daily?days=7
    frequency: 300000  # 5 minutes
    timeout: 10000
    probes:
      - us-east-1
    settings:
      http:
        method: GET
        validStatusCodes: [200]
        validHTTPVersions: ["HTTP/1.1", "HTTP/2.0"]
    assertions:
      - type: jsonPath
        expression: "$[0].messages_count"
        condition: ">="
        value: 0
      - type: responseTime
        condition: "<"
        value: 5000

  - name: warehouse-freshness
    type: http
    target: http://api:8003/api/metrics/profile/freshness
    frequency: 60000  # 1 minute
    timeout: 5000
    assertions:
      - type: jsonPath
        expression: "$.is_fresh"
        condition: "=="
        value: true
      - type: jsonPath
        expression: "$.minutes_since_sync"
        condition: "<="
        value: 30
```

---

### Option 2: UptimeRobot (Free Tier)

**Configuration:**
1. Go to https://uptimerobot.com
2. Add Monitor → HTTP(s)

**Monitor 1: Activity Daily**
- URL: `http://api:8003/api/metrics/profile/activity_daily?days=7`
- Type: HTTP(s)
- Interval: 5 minutes
- Monitor Timeout: 30 seconds
- Keyword: `messages_count` (check response contains this)
- Alert Contacts: Email/Slack

**Monitor 2: Freshness**
- URL: `http://api:8003/api/metrics/profile/freshness`
- Type: HTTP(s)
- Interval: 5 minutes
- Keyword: `"is_fresh":true`
- Alert if keyword NOT found

**Limitations:**
- Cannot check internal endpoints (need reverse proxy or public URL)
- Basic HTTP checks only (no JSON path validation)

---

### Option 3: Prometheus Blackbox Exporter

**Install:**
```yaml
# docker-compose.prod.yml
services:
  blackbox:
    image: prom/blackbox-exporter:latest
    ports:
      - "9115:9115"
    volumes:
      - ./prometheus/blackbox.yml:/etc/blackbox_exporter/config.yml:ro
    networks:
      - applylens
```

**Configuration (`prometheus/blackbox.yml`):**
```yaml
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      valid_status_codes: [200]
      method: GET
      fail_if_not_matches_regexp:
        - "messages_count"

  http_freshness:
    prober: http
    timeout: 3s
    http:
      valid_status_codes: [200]
      fail_if_not_matches_regexp:
        - '"is_fresh":true'
```

**Prometheus Scrape Config:**
```yaml
scrape_configs:
  - job_name: 'blackbox-warehouse'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - http://api:8003/api/metrics/profile/activity_daily?days=7
          - http://api:8003/api/metrics/profile/top_senders_30d
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox:9115

  - job_name: 'blackbox-freshness'
    metrics_path: /probe
    params:
      module: [http_freshness]
    static_configs:
      - targets:
          - http://api:8003/api/metrics/profile/freshness
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox:9115
```

**Grafana Dashboard:**
- Query: `probe_success{job="blackbox-warehouse"}`
- Uptime %: `avg_over_time(probe_success[24h]) * 100`

---

### Option 4: Simple Bash Cron Script

**Script (`monitoring/check-warehouse-health.sh`):**
```bash
#!/bin/bash
set -e

API_BASE="http://localhost:8003/api/metrics/profile"
LOG_FILE="/var/log/warehouse-health.log"
ALERT_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

check_endpoint() {
    local endpoint=$1
    local check_name=$2
    
    echo "[$(date)] Checking $check_name..."
    
    response=$(curl -s -w "\n%{http_code}" --max-time 10 "$API_BASE/$endpoint")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" != "200" ]; then
        echo "❌ FAIL: $check_name - HTTP $http_code" | tee -a "$LOG_FILE"
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 Warehouse API Alert: $check_name returned HTTP $http_code\"}" \
            "$ALERT_WEBHOOK"
        return 1
    fi
    
    # Check for empty response
    if [ -z "$body" ] || [ "$body" == "[]" ]; then
        echo "❌ FAIL: $check_name - Empty response" | tee -a "$LOG_FILE"
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 Warehouse API Alert: $check_name returned empty data\"}" \
            "$ALERT_WEBHOOK"
        return 1
    fi
    
    echo "✅ PASS: $check_name" | tee -a "$LOG_FILE"
    return 0
}

# Run checks
check_endpoint "activity_daily?days=7" "Activity Daily"
check_endpoint "freshness" "Freshness"
check_endpoint "top_senders_30d?limit=5" "Top Senders"
check_endpoint "categories_30d" "Categories"

# Check freshness specifically
freshness=$(curl -s "$API_BASE/freshness")
is_fresh=$(echo "$freshness" | jq -r '.is_fresh')
minutes=$(echo "$freshness" | jq -r '.minutes_since_sync')

if [ "$is_fresh" != "true" ] || [ "$minutes" -gt 30 ]; then
    echo "❌ FAIL: Data is stale ($minutes minutes old)" | tee -a "$LOG_FILE"
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"🚨 Warehouse Data Stale: $minutes minutes since last sync\"}" \
        "$ALERT_WEBHOOK"
    exit 1
fi

echo "[$(date)] All checks passed ✅" | tee -a "$LOG_FILE"
```

**Crontab:**
```cron
# Run every 5 minutes
*/5 * * * * /path/to/check-warehouse-health.sh

# Or run every hour during business hours
0 9-17 * * 1-5 /path/to/check-warehouse-health.sh
```

---

### Option 5: PowerShell Scheduled Task (Windows)

**Script (`monitoring/Check-WarehouseHealth.ps1`):**
```powershell
$ApiBase = "http://localhost:8003/api/metrics/profile"
$LogFile = "D:\ApplyLens\logs\warehouse-health.log"
$SlackWebhook = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

function Test-Endpoint {
    param(
        [string]$Endpoint,
        [string]$Name
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] Checking $Name..."
    
    try {
        $response = Invoke-RestMethod -Uri "$ApiBase/$Endpoint" -Method Get -TimeoutSec 10
        
        # Check for empty response
        if ($null -eq $response -or ($response -is [array] -and $response.Count -eq 0)) {
            $msg = "❌ FAIL: $Name - Empty response"
            Write-Host $msg
            Add-Content -Path $LogFile -Value "[$timestamp] $msg"
            
            Invoke-RestMethod -Uri $SlackWebhook -Method Post -Body (@{
                text = "🚨 Warehouse API Alert: $Name returned empty data"
            } | ConvertTo-Json) -ContentType 'application/json'
            
            return $false
        }
        
        $msg = "✅ PASS: $Name"
        Write-Host $msg -ForegroundColor Green
        Add-Content -Path $LogFile -Value "[$timestamp] $msg"
        return $true
        
    } catch {
        $msg = "❌ FAIL: $Name - $($_.Exception.Message)"
        Write-Host $msg -ForegroundColor Red
        Add-Content -Path $LogFile -Value "[$timestamp] $msg"
        
        Invoke-RestMethod -Uri $SlackWebhook -Method Post -Body (@{
            text = "🚨 Warehouse API Alert: $Name failed - $($_.Exception.Message)"
        } | ConvertTo-Json) -ContentType 'application/json'
        
        return $false
    }
}

# Run all checks
$checks = @(
    @{ Endpoint = "activity_daily?days=7"; Name = "Activity Daily" },
    @{ Endpoint = "freshness"; Name = "Freshness" },
    @{ Endpoint = "top_senders_30d?limit=5"; Name = "Top Senders" },
    @{ Endpoint = "categories_30d"; Name = "Categories" }
)

$allPassed = $true
foreach ($check in $checks) {
    if (-not (Test-Endpoint -Endpoint $check.Endpoint -Name $check.Name)) {
        $allPassed = $false
    }
}

# Check freshness specifically
try {
    $freshness = Invoke-RestMethod -Uri "$ApiBase/freshness" -Method Get
    if (-not $freshness.is_fresh -or $freshness.minutes_since_sync -gt 30) {
        $msg = "❌ FAIL: Data is stale ($($freshness.minutes_since_sync) minutes old)"
        Write-Host $msg -ForegroundColor Red
        Add-Content -Path $LogFile -Value $msg
        
        Invoke-RestMethod -Uri $SlackWebhook -Method Post -Body (@{
            text = "🚨 Warehouse Data Stale: $($freshness.minutes_since_sync) minutes since last sync"
        } | ConvertTo-Json) -ContentType 'application/json'
        
        exit 1
    }
} catch {
    Write-Host "❌ FAIL: Freshness check error - $($_.Exception.Message)" -ForegroundColor Red
}

if ($allPassed) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] All checks passed ✅" -ForegroundColor Green
    Add-Content -Path $LogFile -Value "[$timestamp] All checks passed ✅"
} else {
    exit 1
}
```

**Create Scheduled Task:**
```powershell
# Run every 5 minutes
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File D:\ApplyLens\monitoring\Check-WarehouseHealth.ps1"

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask -TaskName "Warehouse Health Check" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Monitors ApplyLens warehouse API endpoints"
```

---

## Recommended Setup

**For Production:**
1. **Prometheus Blackbox Exporter** (primary)
   - Integrated with existing Prometheus stack
   - Grafana dashboards for visualization
   - Historical uptime tracking
   
2. **Grafana Alerts** (notifications)
   - Email/Slack notifications
   - PagerDuty integration for on-call

3. **PowerShell Script** (backup, Windows)
   - Scheduled task every 5 minutes
   - Direct Slack webhook alerts
   - Local log file for troubleshooting

**For Development:**
- Manual checks using VERIFICATION-QUERIES.md
- Occasional PowerShell script runs

---

## Test Monitoring Setup

```powershell
# Test all endpoints manually
@('activity_daily?days=7', 'freshness', 'top_senders_30d', 'categories_30d') | ForEach-Object {
    $endpoint = $_
    Write-Host "`nTesting: $endpoint" -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod "http://localhost:8003/api/metrics/profile/$endpoint"
        Write-Host "✅ Status: OK" -ForegroundColor Green
        $response | ConvertTo-Json -Depth 2
    } catch {
        Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}
```

---

## Alert Escalation

**Severity Levels:**

1. **Info** (log only)
   - Response time 3-5 seconds
   - Non-critical endpoint down

2. **Warning** (Slack notification)
   - Response time > 5 seconds
   - Freshness 20-30 minutes
   - 1-2% drift

3. **Critical** (Slack + Email)
   - Any endpoint down > 5 minutes
   - Freshness > 30 minutes (SLO breach)
   - Drift > 2%
   - Empty data returned

4. **Emergency** (PagerDuty)
   - All endpoints down
   - Data corruption detected
   - Security breach
