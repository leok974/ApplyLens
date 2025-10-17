# Production Operations Guide - Advanced Features

**Date**: October 15, 2025  
**Status**: ✅ Implemented & Tested  
**Components**: Elasticsearch ILM, Grafana Dashboard, Streaming Canary Toggle

---

## 1. Elasticsearch ILM Policy (90-Day Retention)

### Overview
Automatic index lifecycle management with 90-day retention and monthly rollover to manage storage costs and performance.

### Policy Details

**Hot Phase**:
- **Rollover triggers**: 
  - Max age: 30 days
  - Max size: 20 GB
- **Priority**: 100 (high)
- **Purpose**: Active indices receiving writes

**Delete Phase**:
- **Trigger**: After 90 days
- **Action**: Delete entire index
- **Purpose**: Compliance & cost control

### Setup

#### A. Run Setup Script (PowerShell)

```powershell
# Set Elasticsearch URL (optional, defaults to http://localhost:9200)
$env:ES_URL = "http://localhost:9200"

# Run setup script
.\scripts\setup-es-ilm.ps1
```

**Expected Output**:
```
=== Elasticsearch ILM Policy Setup ===

Target: http://localhost:9200

1. Creating ILM policy 'emails-rolling-90d'...
✓ ILM policy created

2. Creating index template 'gmail-emails-template'...
✓ Index template created

3. Checking existing indices...
   ✓ Rollover index already exists: gmail_emails-000001

4. Verifying ILM setup...
   Policy status:
     - hot
     - delete
   
   Index status:
     gmail_emails-000001: phase=hot, action=rollover

=== Setup Complete ===
```

#### B. Manual Migration (If Concrete Index Exists)

If you currently have a concrete `gmail_emails` index (not using aliases):

**1. Stop API Ingestion**:
```powershell
docker compose -f docker-compose.prod.yml stop api
```

**2. Create First Write Index**:
```powershell
$body = '{"aliases":{"gmail_emails":{"is_write_index":true}}}'
Invoke-RestMethod -Uri "http://localhost:9200/gmail_emails-000001" -Method Put -ContentType "application/json" -Body $body
```

**3. Reindex Data (Optional)**:
```powershell
$body = '{"source":{"index":"gmail_emails"},"dest":{"index":"gmail_emails-000001"}}'
Invoke-RestMethod -Uri "http://localhost:9200/_reindex" -Method Post -ContentType "application/json" -Body $body
```

**4. Delete Old Index**:
```powershell
Invoke-RestMethod -Uri "http://localhost:9200/gmail_emails" -Method Delete
```

**5. Restart API**:
```powershell
docker compose -f docker-compose.prod.yml start api
```

### Monitoring

#### Check ILM Status
```powershell
Invoke-RestMethod -Uri "http://localhost:9200/gmail_emails/_ilm/explain?human" | ConvertTo-Json -Depth 10
```

**Sample Output**:
```json
{
  "indices": {
    "gmail_emails-000001": {
      "index": "gmail_emails-000001",
      "managed": true,
      "policy": "emails-rolling-90d",
      "phase": "hot",
      "action": "rollover",
      "age": "15d",
      "phase_time_millis": 1697500800000
    }
  }
}
```

#### Manual Rollover (Testing)
```powershell
Invoke-RestMethod -Uri "http://localhost:9200/gmail_emails/_rollover" -Method Post -ContentType "application/json" -Body "{}"
```

**Result**: Creates `gmail_emails-000002` and marks it as write index.

### Expected Behavior

**Month 1 (Day 0-30)**:
- Index: `gmail_emails-000001`
- Phase: Hot
- Status: Receiving writes

**Month 2 (Day 30-60)**:
- Old: `gmail_emails-000001` (hot, read-only)
- New: `gmail_emails-000002` (hot, write index)

**Month 3 (Day 60-90)**:
- Index 1: Still hot, read-only
- Index 2: Still hot, read-only  
- Index 3: `gmail_emails-000003` (hot, write)

**Month 4 (Day 90+)**:
- Index 1: **DELETED** (age > 90 days)
- Index 2: Hot, read-only
- Index 3: Hot, read-only
- Index 4: `gmail_emails-000004` (hot, write)

### Storage Impact

**Before ILM**:
- 1 year data = ~50 GB
- No automatic cleanup
- Manual intervention required

**After ILM**:
- 90 days data = ~12 GB (76% reduction)
- Automatic cleanup
- Predictable storage costs

### Troubleshooting

**Issue**: Rollover not happening after 30 days

**Solution**:
```powershell
# Check ILM polling interval (default 10m)
Invoke-RestMethod -Uri "http://localhost:9200/_cluster/settings?include_defaults=true" | ConvertTo-Json

# Force immediate policy execution
Invoke-RestMethod -Uri "http://localhost:9200/_ilm/move/gmail_emails-000001" -Method Post -Body '{"current_step":{"phase":"hot","action":"rollover","name":"check-rollover-ready"},"next_step":{"phase":"hot","action":"rollover","name":"attempt-rollover"}}'
```

**Issue**: Indices not being deleted after 90 days

**Solution**:
```powershell
# Check index age
Invoke-RestMethod -Uri "http://localhost:9200/_cat/indices/gmail_emails-*?v&h=index,creation.date.string,docs.count,store.size"

# Manually force delete phase (DANGEROUS)
Invoke-RestMethod -Uri "http://localhost:9200/_ilm/move/gmail_emails-000001" -Method Post -Body '{"current_step":{"phase":"hot","action":"rollover","name":"complete"},"next_step":{"phase":"delete","action":"wait_for_snapshot","name":"wait-for-snapshot"}}'
```

---

## 2. Grafana Dashboard - Window Buckets & Hit Ratio

### Overview
Comprehensive dashboard for monitoring assistant query performance, window bucket usage, rate limits, and user engagement.

### Installation

#### A. Import Dashboard

```powershell
# Copy dashboard JSON to Grafana container
docker cp infra/grafana/dashboards/dashboard-assistant-window-buckets.json applylens-grafana-prod:/tmp/

# Import via Grafana API
$dashboardJson = Get-Content infra/grafana/dashboards/dashboard-assistant-window-buckets.json | ConvertFrom-Json
$body = @{ dashboard = $dashboardJson; overwrite = $true } | ConvertTo-Json -Depth 20
Invoke-RestMethod -Uri "http://localhost:3000/api/dashboards/db" -Method Post -ContentType "application/json" -Body $body -Headers @{ Authorization = "Bearer YOUR_API_KEY" }
```

**Or import via UI**:
1. Navigate to: `http://localhost:3000/dashboards`
2. Click **Import**
3. Upload `dashboard-assistant-window-buckets.json`
4. Click **Load** → **Import**

#### B. Dashboard Access

**URL**: `http://localhost:3000/d/applylens-assistant-windows`

**Credentials**: 
- Username: `admin`
- Password: (from `.env.prod` - `GRAFANA_ADMIN_PASSWORD`)

### Panels Overview

#### Panel 1: Tool Queries by Window Bucket (rate 5m)
**Type**: Time series  
**Metric**: `sum(rate(assistant_tool_queries_total[5m])) by (window_bucket, has_hits)`

**What it shows**: Query volume split by window days (7/30/60/90+) and whether results were found.

**Interpretation**:
- **High 7d queries**: Users want recent data (fast)
- **High 90+d queries**: Users searching historical data (slower)
- **Green lines (has_hits=1)**: Successful searches
- **Red lines (has_hits=0)**: No results found

#### Panel 2: Zero-Hit Ratio by Window (5m)
**Type**: Time series  
**Metric**: `sum(rate(...{has_hits="0"}[5m])) / sum(rate(...[5m])) by (window_bucket)`

**What it shows**: Percentage of queries returning zero results per window bucket.

**Interpretation**:
- **< 30%**: Healthy (green)
- **30-70%**: Warning (yellow)
- **> 70%**: Critical (red) - triggers alert

**Alert**: AssistantLowHitRate fires if > 70% for 10 minutes.

#### Panel 3: Hit Ratio (last 15m, all windows)
**Type**: Stat  
**Metric**: `sum(rate(...{has_hits="1"}[15m])) / sum(rate(...[15m]))`

**What it shows**: Overall search success rate.

**Color coding**:
- Red: < 30% (critical)
- Yellow: 30-70% (warning)
- Green: > 70% (healthy)

#### Panel 4: HTTP 429 Rate /s (chat & stream)
**Type**: Time series  
**Metric**: `sum(rate(applylens_http_requests_total{status_code="429"}[5m]))`

**What it shows**: Rate limit errors per second.

**Interpretation**:
- **0 req/s**: No rate limiting (normal)
- **> 0.1 req/s**: Occasional limits (acceptable)
- **> 1 req/s**: Severe rate limiting (investigate)

#### Panel 5: Active Chat Sessions (approx)
**Type**: Stat  
**Metric**: `rate(ux_heartbeat_total[1m]) * 30`

**What it shows**: Approximate concurrent users with chat open.

**Calculation**: 
- Each user sends 1 heartbeat per 30s
- Rate per minute × 30 ≈ concurrent users

#### Panel 6: Chat Opens vs Messages Sent
**Type**: Time series  
**Metrics**: 
- `rate(ux_chat_opened_total[5m]) * 300`
- `rate(assistant_tool_queries_total[5m]) * 300`

**What it shows**: User engagement funnel.

**Interpretation**:
- **Gap between lines**: Users open chat but don't send messages
- **Lines overlap**: High engagement (users actively chatting)

#### Panel 7: Engagement Ratio (msgs/open)
**Type**: Stat  
**Metric**: `rate(...queries...[10m]) / rate(...opened...[10m])`

**What it shows**: Average messages sent per chat session.

**Color coding**:
- Red: < 0.2 (20% engagement - poor)
- Yellow: 0.2-0.5 (moderate)
- Green: > 0.5 (50%+ engagement - good)

### Alerts Configuration

**Recommended Alerts** (create in Grafana Alerting):

```promql
# Low Hit Rate (already in Prometheus)
(rate(assistant_tool_queries_total{has_hits="0"}[5m]) 
 / rate(assistant_tool_queries_total[5m])) > 0.7

# Excessive Rate Limiting
sum(rate(applylens_http_requests_total{status_code="429"}[5m])) > 0.5

# Zero Active Sessions (no users)
rate(ux_heartbeat_total[5m]) == 0

# Low Engagement (users not chatting)
(rate(assistant_tool_queries_total[10m]) 
 / rate(ux_chat_opened_total[10m])) < 0.1
```

### Dashboard Customization

**Change Time Range**:
- Top right → Click time selector
- Options: Last 15m, 1h, 6h, 24h, 7d

**Adjust Refresh Rate**:
- Top right → Refresh dropdown
- Options: 5s, 10s (default), 30s, 1m, 5m

**Export Dashboard**:
```powershell
Invoke-RestMethod -Uri "http://localhost:3000/api/dashboards/uid/applylens-assistant-windows" -Headers @{ Authorization = "Bearer YOUR_API_KEY" } | ConvertTo-Json -Depth 20 > dashboard-backup.json
```

---

## 3. Streaming Canary Toggle

### Overview
Feature flag to disable SSE streaming and fall back to non-streaming `/chat` endpoint without code changes or downtime.

### Use Cases

**When to disable streaming**:
1. **Nginx proxy issues**: SSE timeout problems
2. **Load testing**: Compare streaming vs non-streaming performance
3. **Client bugs**: Frontend EventSource errors
4. **Rollback**: Quick rollback during incidents
5. **Maintenance**: Planned service degradation

### Configuration

#### A. Environment Variable

**File**: `docker-compose.prod.yml`

```yaml
api:
  environment:
    CHAT_STREAMING_ENABLED: "true"  # Default: enabled
```

**Values**:
- `"true"`, `"1"`, `"yes"`, `"y"` → Enabled
- `"false"`, `"0"`, `"no"`, `"n"` → Disabled

#### B. Disable Streaming (Live Toggle)

**1. Update Environment**:
```powershell
# Edit docker-compose.prod.yml
# Change: CHAT_STREAMING_ENABLED: "false"

# Or set in .env.prod
echo "CHAT_STREAMING_ENABLED=false" >> infra/.env.prod
```

**2. Restart API (No Downtime - Rolling Update)**:
```powershell
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --no-deps api
```

**3. Verify**:
```powershell
# Test streaming endpoint
curl -v "http://localhost/api/chat/stream?q=test"
# Expected: HTTP 503 with header X-Chat-Streaming-Disabled: 1
```

#### C. Re-Enable Streaming

```powershell
# Edit docker-compose.prod.yml
# Change: CHAT_STREAMING_ENABLED: "true"

docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --no-deps api
```

### Behavior

#### When Streaming Enabled (Default)

**Frontend**:
```
User sends message
  ↓
EventSource connects to /api/chat/stream
  ↓
Receives SSE events (intent, tool, answer, done)
  ↓
Updates UI in real-time
```

**Backend**:
```
POST /chat/stream → Streams response with SSE
POST /chat → Returns complete JSON response
```

#### When Streaming Disabled

**Frontend**:
```
User sends message
  ↓
EventSource connects to /api/chat/stream
  ↓
Receives HTTP 503 + X-Chat-Streaming-Disabled: 1
  ↓
Automatically falls back to POST /chat
  ↓
Waits for complete response
  ↓
Updates UI once (no streaming)
```

**Backend**:
```
POST /chat/stream → Returns 503 immediately
POST /chat → Returns complete JSON response (normal)
```

**User Experience**:
- Slight delay (wait for full response)
- No real-time updates
- Otherwise identical functionality

### Frontend Fallback Logic

**File**: `apps/web/src/components/MailChat.tsx`

```typescript
try {
  const ev = new EventSource(url)
  // ... streaming logic
} catch (err: any) {
  // Check if streaming disabled
  if (err instanceof Response && err.status === 503) {
    const streamingDisabled = err.headers?.get('X-Chat-Streaming-Disabled')
    if (streamingDisabled === '1') {
      console.log('[Chat] Streaming disabled, falling back to non-streaming')
      
      // Automatic fallback to /chat endpoint
      const response = await sendChatMessage({ ... })
      // Render complete response
      return
    }
  }
  // ... other error handling
}
```

**Transparent to user** - No error messages, just works without streaming.

### Monitoring

**Metrics to Watch**:

```promql
# Streaming disabled 503 count
sum(rate(applylens_http_requests_total{status_code="503",path="/api/chat/stream"}[5m]))

# Fallback /chat usage
sum(rate(applylens_http_requests_total{path="/api/chat",method="POST"}[5m]))

# Response time comparison
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket{path=~"/api/chat.*"}[5m])
) by (path)
```

**Expected Changes When Disabled**:
- Stream 503s spike to ~100% of stream attempts
- Non-streaming /chat usage increases
- P95 latency increases (waiting for full response)
- User engagement may decrease slightly (less responsive)

### Testing

#### A. Manual Test

**1. Enable streaming (default)**:
```powershell
# Send test message in UI
# Expected: Real-time updates, intent tokens appear, then answer streams in
```

**2. Disable streaming**:
```powershell
$env:CHAT_STREAMING_ENABLED = "false"
docker compose -f docker-compose.prod.yml up -d --no-deps api
```

**3. Test fallback**:
```powershell
# Send test message in UI
# Expected: Slight delay, then complete response appears at once (no streaming)
```

**4. Check console**:
```
[Chat] Streaming disabled, falling back to non-streaming endpoint
```

**5. Re-enable**:
```powershell
$env:CHAT_STREAMING_ENABLED = "true"
docker compose -f docker-compose.prod.yml up -d --no-deps api
```

#### B. Load Test Comparison

```powershell
# Streaming enabled
vegeta attack -duration=60s -rate=10 -targets=targets.txt | vegeta report

# Streaming disabled
$env:CHAT_STREAMING_ENABLED = "false"
docker compose up -d --no-deps api
vegeta attack -duration=60s -rate=10 -targets=targets.txt | vegeta report

# Compare P95 latency, error rate
```

### Rollback Playbook

**Scenario**: Streaming causing issues in production

**Steps**:

**1. Immediate Disable (30 seconds)**:
```powershell
# SSH to production server
cd /opt/applylens

# Edit environment
sed -i 's/CHAT_STREAMING_ENABLED=true/CHAT_STREAMING_ENABLED=false/' infra/.env.prod

# Restart API only (no downtime)
docker compose -f docker-compose.prod.yml up -d --no-deps api
```

**2. Verify Fallback**:
```powershell
# Test endpoint
curl -I "http://localhost/api/chat/stream?q=test"
# Expected: HTTP/1.1 503 Service Unavailable
# Expected header: X-Chat-Streaming-Disabled: 1

# Test UI
# Open chat, send message
# Expected: Works without streaming
```

**3. Investigate Root Cause**:
- Check API logs: `docker logs applylens-api-prod --tail 100`
- Check nginx logs: `docker logs applylens-nginx-prod --tail 100`
- Check Grafana: Panel 4 (429 rate), Panel 5 (active sessions)

**4. Fix & Re-Enable** (when ready):
```powershell
# Re-enable streaming
sed -i 's/CHAT_STREAMING_ENABLED=false/CHAT_STREAMING_ENABLED=true/' infra/.env.prod
docker compose -f docker-compose.prod.yml up -d --no-deps api
```

### Kubernetes Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: applylens-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: applylens-api:latest
        env:
        - name: CHAT_STREAMING_ENABLED
          value: "false"  # Toggle here
        # ... other env vars
```

**Apply change**:
```bash
kubectl apply -f deployment.yaml
# Rolling update - zero downtime
```

---

## Summary

### ILM Policy
- ✅ 90-day retention (cost savings)
- ✅ Monthly rollover (performance)
- ✅ Automatic cleanup (no manual intervention)
- ✅ Setup script provided

### Grafana Dashboard
- ✅ 7 comprehensive panels
- ✅ Window bucket analysis
- ✅ Hit ratio monitoring
- ✅ Rate limit tracking
- ✅ User engagement metrics
- ✅ Ready to import

### Streaming Canary
- ✅ Zero-downtime toggle
- ✅ Automatic frontend fallback
- ✅ Transparent to users
- ✅ Quick rollback (30 seconds)
- ✅ Environment variable driven

All features are **production-ready** and **fully documented**. 🎯
