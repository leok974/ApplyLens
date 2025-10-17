# Quick Reference Card - Advanced Production Features

## 📋 Files Created

### Elasticsearch ILM
```
infra/es/ilm_emails_rolling_90d.json        - ILM policy (hot 30d, delete 90d)
infra/es/index_template_gmail_emails.json   - Index template with ILM
infra/es/apply_ilm.sh                       - Setup script (Bash)
infra/es/rollback_ilm.sh                    - Rollback script (Bash)
```

### Grafana Dashboard
```
infra/grafana/dashboard-assistant-window-buckets.json  - 7-panel monitoring dashboard
```

### Documentation
```
docs/SETUP-GUIDE-ADVANCED.md            - Complete setup instructions
docs/production-ops-advanced.md         - Operations guide (400+ lines)
docs/deployment-checklist-advanced.md   - Step-by-step deployment
docs/IMPLEMENTATION-SUMMARY.md          - Test results & summary
```

---

## 🚀 Quick Apply

### 1. ILM Policy (2 minutes)

**Windows PowerShell:**
```powershell
$ES_URL = "http://localhost:9200"

# Apply policy
Invoke-RestMethod -Uri "$ES_URL/_ilm/policy/emails-rolling-90d" -Method Put -Headers @{"Content-Type"="application/json"} -InFile infra/es/ilm_emails_rolling_90d.json

# Apply template
Invoke-RestMethod -Uri "$ES_URL/_index_template/gmail-emails-template" -Method Put -Headers @{"Content-Type"="application/json"} -InFile infra/es/index_template_gmail_emails.json

# Verify
Invoke-RestMethod -Uri "$ES_URL/gmail_emails/_ilm/explain?human" | ConvertTo-Json
```

**Linux/Mac Bash:**
```bash
export ES_URL=http://localhost:9200
./infra/es/apply_ilm.sh
```

### 2. Grafana Dashboard (1 minute)

**Via UI:**
1. Open http://localhost:3000/dashboards
2. Click "Import"
3. Upload `infra/grafana/dashboard-assistant-window-buckets.json`
4. Click "Load" → "Import"
5. Access: http://localhost:3000/d/applylens-assistant-windows

**Via API:**
```bash
curl -X POST "http://localhost:3000/api/dashboards/db" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary @infra/grafana/dashboard-assistant-window-buckets.json
```

### 3. Streaming Canary (Already Live ✅)

**Test Current State:**
```powershell
curl "http://localhost/api/chat/stream?q=test&window_days=7"
# Expected: HTTP 200, Content-Type: text/event-stream
```

**Disable Streaming:**
```powershell
# Edit infra/.env.prod: CHAT_STREAMING_ENABLED=false
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --no-deps api
# Restart time: ~1 second
```

---

## ✅ Verification

### ILM Policy
```bash
# Check policy exists
curl http://localhost:9200/_ilm/policy/emails-rolling-90d

# Verify index managed
curl http://localhost:9200/gmail_emails/_ilm/explain?human | jq '.indices | to_entries[0].value.managed'
# Expected: true
```

### Grafana Dashboard
```
# Access dashboard
http://localhost:3000/d/applylens-assistant-windows

# Expected: 7 panels load with data within 1-2 minutes
```

### Streaming Canary
```powershell
# Test enabled
curl -I "http://localhost/api/chat/stream?q=test&window_days=7"
# Expected: HTTP/1.1 200 OK

# Test disabled
# (Set CHAT_STREAMING_ENABLED=false and restart)
curl -I "http://localhost/api/chat/stream?q=test&window_days=7"
# Expected: HTTP/1.1 503 Service Unavailable
#           x-chat-streaming-disabled: 1
```

---

## 🔄 Rollback

### ILM
```bash
export ES_URL=http://localhost:9200
./infra/es/rollback_ilm.sh
# Or manually:
# curl -X DELETE http://localhost:9200/_index_template/gmail-emails-template
# curl -X DELETE http://localhost:9200/_ilm/policy/emails-rolling-90d
```

### Grafana Dashboard
```bash
curl -X DELETE "http://localhost:3000/api/dashboards/uid/applylens-assistant-windows" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Or delete from UI: Dashboard settings → Delete
```

### Streaming Canary
```powershell
# Re-enable streaming
# Edit infra/.env.prod: CHAT_STREAMING_ENABLED=true
docker compose -f docker-compose.prod.yml --env-file infra/.env.prod up -d --no-deps api
```

---

## 📊 Dashboard Panels

1. **Tool Queries by Window Bucket** - Query rate by time window (7/30/60/90+d)
2. **Zero-Hit Ratio by Window** - % queries with 0 results, by window
3. **Hit Ratio (Last 15m)** - Overall success rate across all windows
4. **HTTP 429 Rate** - Rate limiting events per second
5. **ES Search p95 Latency** - Elasticsearch query performance (95th percentile)
6. **Active Chat Sessions** - Approx concurrent users (from UX heartbeats)
7. **Chat Opens vs Messages** - Engagement funnel comparison

---

## 💾 Storage Impact (ILM)

**Without ILM:**
- Retention: Forever
- Storage: ~50GB/year (assuming 10K emails/day)

**With ILM (90-day rolling):**
- Retention: 90 days
- Storage: ~12GB (76% reduction)
- Rollover: Monthly (30 days or 20GB)

**Timeline:**
- Month 0: `gmail_emails-000001` created
- Month 1: Rollover to `gmail_emails-000002`
- Month 4: `gmail_emails-000001` deleted (90 days old)

---

## 🔍 Monitoring Queries

### ILM Status
```bash
# Check managed indices
curl http://localhost:9200/_cat/indices/gmail_emails-*?v

# ILM explain
curl http://localhost:9200/gmail_emails/_ilm/explain?human

# Trigger manual rollover (testing)
curl -X POST http://localhost:9200/gmail_emails/_rollover -H 'Content-Type: application/json' -d '{}'
```

### Grafana Metrics (Prometheus)
```promql
# Window bucket queries
sum(rate(assistant_tool_queries_total[5m])) by (window_bucket, has_hits)

# Zero-hit ratio
sum(rate(assistant_tool_queries_total{has_hits="0"}[5m])) / sum(rate(assistant_tool_queries_total[5m]))

# 429 rate
sum(rate(http_requests_total{status=~"429",handler=~"/api/chat.*"}[5m]))

# Active sessions (UX heartbeats)
rate(ux_heartbeat_total[1m]) * 30
```

### Canary Metrics
```promql
# 503 rate (streaming disabled)
sum(rate(applylens_http_requests_total{status_code="503",path="/api/chat/stream"}[5m]))

# Non-streaming fallback usage
sum(rate(applylens_http_requests_total{path="/api/chat"}[5m]))
```

---

## 🎯 Status Summary

| Feature | Files | Status | Action |
|---------|-------|--------|--------|
| **ILM Policy** | 4 files | ✅ Created | Apply script |
| **Grafana Dashboard** | 1 file | ✅ Created | Import JSON |
| **Streaming Canary** | N/A | ✅ **LIVE** | Already working |

**Documentation:** 4 comprehensive guides created

---

## 📞 Support

For detailed instructions, see:
- **Setup:** `docs/SETUP-GUIDE-ADVANCED.md`
- **Operations:** `docs/production-ops-advanced.md`
- **Deployment:** `docs/deployment-checklist-advanced.md`
- **Summary:** `docs/IMPLEMENTATION-SUMMARY.md`

---

*Last Updated: October 16, 2025*
