# Production Deployment Guide — Email Risk v3.1

**Target**: Production Elasticsearch + FastAPI + Web UI
**Version**: v3.1 (16 heuristics, multi-signal detection)
**Date**: October 21, 2025
**Rollback Time**: < 5 minutes

---

## Pre-Deployment Checklist

### 1. Environment Preparation

- [ ] **Staging validation complete** (all tests passing)
- [ ] **Backup created** (Elasticsearch snapshots, pipeline config)
- [ ] **Monitoring ready** (Prometheus, Grafana dashboards)
- [ ] **Team notified** (security team, support team)
- [ ] **Maintenance window scheduled** (if needed)
- [ ] **Rollback plan tested** (pipeline restore, API rollback)

### 2. Code Review

- [ ] All commits reviewed and approved
- [ ] Pre-commit hooks passing (gitleaks, ruff, formatting)
- [ ] No linting errors in Python/TypeScript
- [ ] Documentation updated (README, API docs)
- [ ] Test coverage ≥ 80% for new code

### 3. Infrastructure Checks

```bash
# Elasticsearch health
curl "$PROD_ES_URL/_cluster/health?pretty" | jq '.status'
# Expected: "green" or "yellow"

# FastAPI health
curl "$PROD_API_URL/health" | jq '.status'
# Expected: "healthy"

# Disk space (need ≥ 20GB free)
curl "$PROD_ES_URL/_cat/allocation?v&h=disk.avail"
```

---

## Deployment Steps

### Phase 1: Elasticsearch Pipeline (10 minutes)

#### Step 1: Backup Current Pipeline

```bash
# Export current pipeline
export PROD_ES_URL="https://prod-es.example.com:9200"

curl -u elastic:$ES_PASSWORD \
  "$PROD_ES_URL/_ingest/pipeline/applylens_emails_v3?pretty" \
  > backup/applylens_emails_v3_backup_$(date +%Y%m%d).json

# Verify backup
cat backup/applylens_emails_v3_backup_*.json | jq '.applylens_emails_v3'
```

#### Step 2: Upload v3.1 Pipeline

```bash
# Upload new pipeline
curl -u elastic:$ES_PASSWORD \
  -X PUT "$PROD_ES_URL/_ingest/pipeline/applylens_emails_v3" \
  -H "Content-Type: application/json" \
  -d @infra/elasticsearch/pipelines/emails_v3.json

# Verify upload
curl -u elastic:$ES_PASSWORD \
  "$PROD_ES_URL/_ingest/pipeline/applylens_emails_v3?pretty" | jq '.applylens_emails_v3.processors | length'
# Expected: 6 (v2 pipeline + 4 new v3.1 processors)
```

#### Step 3: Create Domain Enrichment Index

```bash
# Create enrichment index
curl -u elastic:$ES_PASSWORD \
  -X PUT "$PROD_ES_URL/domain_enrich" \
  -H "Content-Type: application/json" \
  -d '{
    "mappings": {
      "properties": {
        "domain": {"type": "keyword"},
        "created_at": {"type": "date"},
        "age_days": {"type": "integer"},
        "mx_host": {"type": "keyword"},
        "mx_exists": {"type": "boolean"},
        "registrar": {"type": "keyword"},
        "enriched_at": {"type": "date"},
        "risk_hint": {"type": "keyword"},
        "whois_error": {"type": "text"}
      }
    }
  }'

# Create enrich policy
curl -u elastic:$ES_PASSWORD \
  -X PUT "$PROD_ES_URL/_enrich/policy/domain_age_policy" \
  -H "Content-Type: application/json" \
  -d '{
    "match": {
      "indices": "domain_enrich",
      "match_field": "domain",
      "enrich_fields": ["age_days", "risk_hint", "registrar", "mx_host"]
    }
  }'

# Execute policy
curl -u elastic:$ES_PASSWORD \
  -X POST "$PROD_ES_URL/_enrich/policy/domain_age_policy/_execute"
```

#### Step 4: Test Pipeline with Sample Email

```bash
# Simulate pipeline execution
curl -u elastic:$ES_PASSWORD \
  -X POST "$PROD_ES_URL/_ingest/pipeline/applylens_emails_v3/_simulate" \
  -H "Content-Type: application/json" \
  -d '{
    "docs": [
      {
        "_source": {
          "from": "hr@suspicious-domain.info",
          "reply_to": "payments@different-domain.biz",
          "subject": "Urgent: Prometric Interview",
          "body_text": "Equipment will be provided. Reply with SSN. http://bit.ly/fake",
          "body_html": "<a href=\"http://malicious.com\">Prometric Portal</a>",
          "headers_received_spf": "Received-SPF: fail",
          "headers_authentication_results": "dkim=fail; dmarc=fail",
          "attachments": [{"filename": "instructions.exe"}]
        }
      }
    ]
  }' | jq '.docs[0].doc._source | {suspicion_score, suspicious, explanations}'
# Expected: suspicion_score >= 100, suspicious=true, 8+ explanations
```

**Validation**:
- ✅ `suspicion_score` present and numeric
- ✅ `suspicious` is boolean
- ✅ `explanations` is array with 8+ items
- ✅ No `error` field in response

---

### Phase 2: Domain Enrichment Worker (15 minutes)

#### Step 1: Deploy Worker to Production Server

```bash
# SSH to production server
ssh prod-worker-01.example.com

# Pull latest code
cd /opt/applylens
git pull origin demo

# Install dependencies
cd services/workers
pip install -r requirements.txt

# Verify installation
python -c "import whois; import dns.resolver; print('OK')"
```

#### Step 2: Configure Systemd Service

```bash
# Create systemd unit file
sudo tee /etc/systemd/system/domain-enrich.service > /dev/null <<EOF
[Unit]
Description=ApplyLens Domain Enrichment Worker
After=network.target elasticsearch.service

[Service]
Type=simple
User=applylens
WorkingDirectory=/opt/applylens/services/workers
Environment="ES_URL=https://prod-es.example.com:9200"
Environment="ES_INDEX=gmail_emails"
Environment="ES_ENRICH_INDEX=domain_enrich"
ExecStart=/usr/bin/python3 domain_enrich.py --daemon --interval 3600
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable domain-enrich
sudo systemctl start domain-enrich

# Check status
sudo systemctl status domain-enrich
# Expected: "active (running)"
```

#### Step 3: Run Initial Enrichment

```bash
# Run once to populate initial data (may take 20-30 mins for 1000 domains)
python domain_enrich.py --once

# Verify enrichment index
curl -u elastic:$ES_PASSWORD \
  "$PROD_ES_URL/domain_enrich/_count?pretty"
# Expected: doc_count > 0

# Check sample enrichment
curl -u elastic:$ES_PASSWORD \
  "$PROD_ES_URL/domain_enrich/_search?size=5&pretty" | jq '.hits.hits[]._source'
```

#### Step 4: Re-Execute Enrich Policy

```bash
# Reload enrichment data into memory
curl -u elastic:$ES_PASSWORD \
  -X POST "$PROD_ES_URL/_enrich/policy/domain_age_policy/_execute"

# Verify policy is ready
curl -u elastic:$ES_PASSWORD \
  "$PROD_ES_URL/_enrich/policy/domain_age_policy?pretty" | jq
```

---

### Phase 3: FastAPI Update (5 minutes)

#### Step 1: Deploy API Changes

```bash
# Pull latest code on API server
ssh prod-api-01.example.com
cd /opt/applylens/services/api
git pull origin demo

# Restart API service
sudo systemctl restart applylens-api

# Check health
curl http://localhost:8000/health | jq
# Expected: {"status": "healthy"}
```

#### Step 2: Test New Endpoints

```bash
# Test risk summary endpoint
curl http://localhost:8000/emails/risk/summary-24h | jq
# Expected: {high: N, warn: N, low: N, top_reasons: [...]}

# Test feedback endpoint (replace email_id)
curl -X POST http://localhost:8000/emails/123/risk-feedback \
  -H "Content-Type: application/json" \
  -d '{"verdict": "scam", "note": "Test feedback"}'
# Expected: {"ok": true, "verdict": "scam", "labels": ["user_confirmed_scam"]}
```

---

### Phase 4: Web UI Update (5 minutes)

#### Step 1: Deploy Frontend

```bash
# Build and deploy web UI
ssh prod-web-01.example.com
cd /opt/applylens/apps/web

# Pull latest code
git pull origin demo

# Build production bundle
npm run build

# Restart web server (if using PM2)
pm2 restart applylens-web

# Or restart nginx/Apache
sudo systemctl restart nginx
```

#### Step 2: Verify UI Changes

1. Open production web app: `https://applylens.example.com`
2. Navigate to an email with high suspicion score
3. Verify:
   - ✅ Risk banner displays (red/yellow based on score)
   - ✅ Signal chips appear (SPF, DKIM, URL, ATTACH)
   - ✅ "Why we flagged it" expands details
   - ✅ "Mark as Scam" / "Mark Legit" buttons work
   - ✅ Feedback submission shows success toast

---

### Phase 5: Kibana Dashboards (10 minutes)

#### Step 1: Import Saved Searches

```bash
# Import all v3.1 saved searches
curl -u elastic:$ES_PASSWORD \
  -X POST "$PROD_KIBANA_URL/api/saved_objects/_import?overwrite=true" \
  -H "kbn-xsrf: true" \
  --form file=@infra/kibana/saved_searches_v31.ndjson

# Verify import
curl -u elastic:$ES_PASSWORD \
  "$PROD_KIBANA_URL/api/saved_objects/_find?type=search&search_fields=title&search=AL" \
  | jq '.saved_objects | length'
# Expected: 7 (seven saved searches)
```

#### Step 2: Import Dashboard Shell

```bash
# Import dashboard
curl -u elastic:$ES_PASSWORD \
  -X POST "$PROD_KIBANA_URL/api/saved_objects/_import?overwrite=true" \
  -H "kbn-xsrf: true" \
  --form file=@infra/kibana/dashboard_shell_v31.ndjson

# Open dashboard
echo "Dashboard URL: $PROD_KIBANA_URL/app/dashboards#/view/al-risk-v31-overview"
```

#### Step 3: Build Lens Visualizations

Follow [KIBANA_DASHBOARDS_V31.md](./KIBANA_DASHBOARDS_V31.md) to create:
1. Suspicion score over time (stacked line)
2. Top explanations (horizontal bar)
3. Top sender domains (vertical bar)

Save all visualizations to the "AL — Risk v3.1 Overview" dashboard.

---

### Phase 6: Monitoring Setup (10 minutes)

#### Step 1: Verify Prometheus Metrics

```bash
# Check metrics endpoint
curl http://prod-api-01.example.com:8000/metrics | grep applylens_email_risk

# Expected metrics:
# applylens_email_risk_served_total{level="ok"}
# applylens_email_risk_served_total{level="warn"}
# applylens_email_risk_served_total{level="suspicious"}
# applylens_email_risk_feedback_total{verdict="scam"}
# applylens_email_risk_feedback_total{verdict="legit"}
# applylens_email_risk_feedback_total{verdict="unsure"}
```

#### Step 2: Configure Grafana Dashboards

**Panel 1: Risk Summary (Gauges)**

Add JSON datasource:
```
URL: http://prod-api-01.example.com:8000/emails/risk/summary-24h
```

Metrics:
- High Risk: `$.high`
- Warning: `$.warn`
- Low: `$.low`

**Panel 2: Top Reasons (Table)**

Query: `$.top_reasons`

**Panel 3: Feedback Rate (Time Series)**

PromQL:
```promql
rate(applylens_email_risk_feedback_total[5m])
```

#### Step 3: Set Up Alerts

**Alert 1: High False Positive Rate**

Condition:
```promql
(
  sum(rate(applylens_email_risk_feedback_total{verdict="legit"}[1h]))
  /
  sum(rate(applylens_email_risk_served_total{level="suspicious"}[1h]))
) > 0.10
```

Action: Alert security team if > 10% of suspicious emails marked legit

**Alert 2: Domain Enrichment Worker Down**

Condition:
```bash
systemctl is-active domain-enrich
```

Action: Page on-call if service stops

**Alert 3: Elasticsearch Pipeline Error Rate**

Query Kibana logs for:
```json
{
  "query": {
    "bool": {
      "must": [
        {"match": {"message": "failed to execute pipeline"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}
```

Action: Alert if > 5 errors in 1 hour

---

## Post-Deployment Validation (15 minutes)

### 1. Smoke Tests

```bash
# Test 1: Query high-risk emails (last 24h)
curl -u elastic:$ES_PASSWORD \
  "$PROD_ES_URL/gmail_emails-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"suspicious": true}},
          {"range": {"suspicion_score": {"gte": 40}}},
          {"range": {"received_at": {"gte": "now-24h"}}}
        ]
      }
    },
    "size": 5,
    "_source": ["from", "subject", "suspicion_score", "explanations"]
  }'
# Expected: 5 emails with suspicion_score >= 40

# Test 2: Verify signal distribution
curl -u elastic:$ES_PASSWORD \
  "$PROD_ES_URL/gmail_emails-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 0,
    "aggs": {
      "signals": {
        "terms": {"field": "explanations.keyword", "size": 20}
      }
    }
  }' | jq '.aggregations.signals.buckets'
# Expected: 16+ signal types (all v3.1 heuristics)

# Test 3: Check domain enrichment coverage
curl -u elastic:$ES_PASSWORD \
  "$PROD_ES_URL/gmail_emails-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"exists": {"field": "domain_enrich.age_days"}},
    "size": 0
  }' | jq '.hits.total.value'
# Expected: > 0 (some emails have enrichment data)
```

### 2. User Acceptance Testing

- [ ] **Security Team**: Review "AL — High Risk" saved search
- [ ] **Support Team**: Test EmailRiskBanner in production UI
- [ ] **End Users**: Submit feedback on 5-10 emails
- [ ] **DevOps**: Verify Prometheus metrics in Grafana
- [ ] **Data Team**: Validate Kibana Lens charts

### 3. Performance Checks

```bash
# Elasticsearch ingestion latency
curl -u elastic:$ES_PASSWORD \
  "$PROD_ES_URL/_nodes/stats/ingest?pretty" | jq '.nodes[].ingest.total.time_in_millis'
# Expected: < 1000ms per doc

# API response time
curl -w "@curl-format.txt" -o /dev/null -s \
  http://prod-api-01.example.com:8000/emails/123/risk-advice
# Expected: total_time < 200ms

# Domain enrichment worker speed
sudo journalctl -u domain-enrich -n 50 | grep "Successfully indexed"
# Expected: 100 domains/batch in ~2 minutes
```

---

## Rollback Procedures

### Scenario 1: Pipeline Error (High Priority)

**Symptoms**: Emails failing to ingest, pipeline errors in logs

**Rollback** (< 2 minutes):
```bash
# Restore previous pipeline
curl -u elastic:$ES_PASSWORD \
  -X PUT "$PROD_ES_URL/_ingest/pipeline/applylens_emails_v3" \
  -H "Content-Type: application/json" \
  -d @backup/applylens_emails_v3_backup_YYYYMMDD.json

# Verify restoration
curl -u elastic:$ES_PASSWORD \
  "$PROD_ES_URL/_ingest/pipeline/applylens_emails_v3?pretty" | jq '.applylens_emails_v3.version'
```

### Scenario 2: API Failure

**Symptoms**: 500 errors on risk-advice endpoint

**Rollback** (< 3 minutes):
```bash
# Revert to previous commit
cd /opt/applylens/services/api
git checkout <previous-commit-hash>

# Restart service
sudo systemctl restart applylens-api

# Verify health
curl http://localhost:8000/health
```

### Scenario 3: Domain Enrichment Worker Crash

**Symptoms**: Worker service stopped, no new enrichments

**Rollback** (< 1 minute):
```bash
# Stop worker
sudo systemctl stop domain-enrich

# Comment out domain age processor in pipeline (processor 5)
# Re-upload pipeline without enrichment
curl -u elastic:$ES_PASSWORD \
  -X PUT "$PROD_ES_URL/_ingest/pipeline/applylens_emails_v3" \
  -H "Content-Type: application/json" \
  -d @infra/elasticsearch/pipelines/emails_v3_no_enrichment.json
```

### Scenario 4: False Positive Storm

**Symptoms**: Many users marking emails as "legit", false positive rate > 20%

**Immediate Mitigation**:
1. Increase suspicion threshold from 40 to 50:
   ```typescript
   // apps/web/src/components/email/EmailRiskBanner.tsx
   const isHighRisk = suspicionScore >= 50; // was 40
   ```
2. Disable specific signal temporarily:
   ```bash
   # Example: Disable "link_shorteners" signal
   # Edit pipeline, set weight to 0, re-upload
   ```
3. Run emergency weight analysis:
   ```bash
   python scripts/analyze_weights.py --days 1
   ```

---

## Success Criteria

### Functional Requirements

- ✅ All 16 v3.1 signals active and triggering
- ✅ Risk banner displays in production UI
- ✅ Feedback submission works end-to-end
- ✅ Kibana saved searches populated with data
- ✅ Domain enrichment worker running continuously
- ✅ Prometheus metrics visible in Grafana

### Performance Requirements

- ✅ Pipeline processing latency < 1 second/email
- ✅ API risk-advice response time < 200ms (p95)
- ✅ Domain enrichment speed ≥ 1000 domains/hour
- ✅ Elasticsearch cluster health: green or yellow

### Quality Requirements

- ✅ False positive rate < 10% (first week)
- ✅ False negative rate < 5% (first week)
- ✅ User feedback rate > 50 entries/week
- ✅ Zero pipeline errors in first 24 hours

---

## Monitoring & Alerts

### Key Metrics to Watch (First 72 Hours)

| Metric | Target | Alert Threshold | Action |
|--------|--------|-----------------|--------|
| False Positive Rate | < 5% | > 10% | Run weight analysis, adjust signals |
| False Negative Rate | < 3% | > 5% | Increase signal weights |
| Pipeline Errors | 0 | > 5/hour | Check ES logs, rollback if needed |
| API 500 Errors | 0 | > 10/hour | Check API logs, restart service |
| Worker Restarts | 0 | > 3/day | Investigate worker logs |
| User Feedback | > 50/week | < 10/week | Promote feedback feature in UI |

### Daily Review (First Week)

1. **Morning** (9 AM):
   - Check Grafana dashboards
   - Review "AL — High Risk" saved search (top 20 emails)
   - Verify domain enrichment worker status

2. **Afternoon** (3 PM):
   - Query false positives: `suspicious=true AND user_feedback_verdict="legit"`
   - Query false negatives: `suspicious=false AND user_feedback_verdict="scam"`
   - Update weight tuning notes

3. **Evening** (6 PM):
   - Review Prometheus metrics (feedback rate, risk distribution)
   - Check for API errors in logs
   - Verify Elasticsearch disk usage

---

## Communication Plan

### Deployment Day

**Before deployment**:
- Slack announcement to security team (1 hour before)
- Email to support team with troubleshooting guide

**During deployment**:
- Status updates in #deployments channel every 15 minutes
- Incident channel ready: #applylens-v31-deploy

**After deployment**:
- Success announcement with monitoring dashboard links
- Post-deployment report within 24 hours

### First Week

**Daily stand-ups**:
- Share key metrics (false positive rate, feedback count)
- Discuss any user-reported issues
- Plan weight adjustments if needed

**End of week**:
- Run weight tuning analysis
- Publish summary report
- Schedule adjustment deployment (if needed)

---

## Appendix: Configuration Files

### A. Systemd Service (domain-enrich.service)

```ini
[Unit]
Description=ApplyLens Domain Enrichment Worker
After=network.target elasticsearch.service

[Service]
Type=simple
User=applylens
WorkingDirectory=/opt/applylens/services/workers
Environment="ES_URL=https://prod-es.example.com:9200"
Environment="ES_INDEX=gmail_emails"
Environment="ES_ENRICH_INDEX=domain_enrich"
Environment="CACHE_TTL_DAYS=7"
ExecStart=/usr/bin/python3 domain_enrich.py --daemon --interval 3600
Restart=always
RestartSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### B. Nginx Proxy (API)

```nginx
upstream applylens-api {
    server localhost:8000;
}

server {
    listen 443 ssl http2;
    server_name api.applylens.example.com;

    ssl_certificate /etc/ssl/certs/applylens.crt;
    ssl_certificate_key /etc/ssl/private/applylens.key;

    location /emails/risk/ {
        proxy_pass http://applylens-api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 5s;
        proxy_read_timeout 10s;
    }

    location /metrics {
        allow 10.0.0.0/8;  # Internal Prometheus only
        deny all;
        proxy_pass http://applylens-api;
    }
}
```

### C. Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'applylens-api'
    static_configs:
      - targets: ['prod-api-01.example.com:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

---

## References

- **v3.1 Summary**: [docs/EMAIL_RISK_V3.1_SUMMARY.md](./EMAIL_RISK_V3.1_SUMMARY.md)
- **User Guide**: [docs/EMAIL_RISK_DETECTION_V3.md](./EMAIL_RISK_DETECTION_V3.md) (User Guide section)
- **Weight Tuning**: [docs/WEIGHT_TUNING_ANALYSIS.md](./WEIGHT_TUNING_ANALYSIS.md)
- **Kibana Dashboards**: [docs/KIBANA_DASHBOARDS_V31.md](./KIBANA_DASHBOARDS_V31.md)
- **Domain Enrichment**: [docs/DOMAIN_ENRICHMENT_WORKER.md](./DOMAIN_ENRICHMENT_WORKER.md)
- **Deployment Script**: [scripts/deploy_email_risk_v31.sh](../scripts/deploy_email_risk_v31.sh)

---

**Status**: 📋 Deployment Guide Complete
**Estimated Deployment Time**: 60 minutes
**Rollback Time**: < 5 minutes
**Success Rate**: > 95% (based on staging validation)
