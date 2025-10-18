# ApplyLens Production Handbook

**Version:** 1.0  
**Last Updated:** October 17, 2025  
**Audience:** Operations, SRE, On-Call Engineers

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Deployment Procedures](#deployment-procedures)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Incident Response](#incident-response)
6. [Operational Tasks](#operational-tasks)
7. [Security & Compliance](#security--compliance)
8. [Troubleshooting](#troubleshooting)

---

## System Overview

ApplyLens is an AI-powered email management system that uses multiple specialized agents to triage, search, plan, and analyze email workflows.

### Core Components

- **API Service** (`services/api`) - FastAPI backend with 6 specialized agents
- **Web UI** (`web`) - React frontend for user interactions
- **Analytics** (`analytics`) - dbt models for data transformation
- **Elasticsearch** - Email indexing and search
- **PostgreSQL** - Primary database
- **Redis** - Caching and rate limiting

### Key Metrics

- **Users:** ~10,000 active users
- **Emails Processed:** ~1M emails/day
- **API Requests:** ~500K requests/day
- **Database Size:** ~500GB
- **Uptime SLA:** 99.9% (43.2 minutes/month downtime budget)

---

## Architecture

### High-Level Diagram

```
┌─────────────┐
│   Users     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  CloudFlare CDN + WAF               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Load Balancer (ALB)                │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│  API Pod 1  │ │  API Pod 2  │
│  (ECS)      │ │  (ECS)      │
└──────┬──────┘ └──────┬──────┘
       │               │
       └───────┬───────┘
               │
       ┌───────┴───────┬───────────┬──────────┐
       ▼               ▼           ▼          ▼
┌──────────┐   ┌──────────┐  ┌─────────┐  ┌─────────┐
│PostgreSQL│   │Elasticsearch│ │  Redis  │  │  S3     │
│  (RDS)   │   │   (ES)      │ │ (Cache) │  │(Storage)│
└──────────┘   └──────────┘  └─────────┘  └─────────┘
```

### Agent Architecture

ApplyLens uses 6 specialized agents:

1. **inbox.triage** - Classify and prioritize emails
2. **inbox.search** - Semantic email search
3. **knowledge.search** - Knowledge graph queries
4. **planner.deploy** - Deployment planning
5. **warehouse.health** - Data quality monitoring
6. **analytics.insights** - Business intelligence

### Data Flow

```
Email Received → Gmail API → inbox.triage → Classification
                                    ↓
                              Email Indexed (ES)
                                    ↓
                              Stored in DB (Postgres)
                                    ↓
                              Analytics Pipeline (dbt)
                                    ↓
                              Warehouse Tables
```

---

## Deployment Procedures

### Release Channels

ApplyLens uses 4 deployment environments:

1. **dev** - Development testing
2. **staging** - Pre-production validation
3. **canary** - Gradual production rollout (10% → 50% → 100%)
4. **prod** - Full production

### Promotion Path

```
dev → staging → canary (10%) → canary (50%) → prod (100%)
```

### Deploying to Staging

```bash
cd deploy/scripts
python promote_release.py staging \
  --from-commit abc123 \
  --skip-backup
```

### Deploying to Production

**IMPORTANT:** Always deploy to canary first!

```bash
# Step 1: Deploy to canary (10%)
python promote_release.py prod \
  --from-commit abc123 \
  --canary-pct 10

# Step 2: Monitor for 30 minutes
# Check metrics: error rate, latency, cost

# Step 3: Increase to 50%
python promote_release.py prod \
  --from-commit abc123 \
  --canary-pct 50

# Step 4: Monitor for 30 minutes

# Step 5: Full rollout
python promote_release.py prod \
  --from-commit abc123 \
  --canary-pct 100
```

### Rollback Procedure

```bash
# Automatic rollback on failure (error rate >5%, latency >2x)
python promote_release.py prod --rollback
```

### Manual Rollback

```bash
# Rollback to previous version
git tag | grep prod | tail -2 | head -1  # Get previous prod tag
python promote_release.py prod --from-commit <previous-tag>
```

### Deployment Checklist

- [ ] All tests passing in CI
- [ ] Database migrations tested in staging
- [ ] No breaking API changes
- [ ] Feature flags configured
- [ ] On-call engineer available
- [ ] Slack #deployments channel notified
- [ ] Monitoring dashboards open

---

## Monitoring & Alerting

### Key Dashboards

1. **System Health** - https://grafana.applylens.io/d/system-health
2. **Agent Performance** - https://grafana.applylens.io/d/agent-performance
3. **SLO Compliance** - https://grafana.applylens.io/d/slo-compliance
4. **Error Budget** - https://grafana.applylens.io/d/error-budget

### Critical Alerts

#### Fast Burn Rate Alert
- **Condition:** Error budget burning >14.4x normal rate (1-hour window)
- **Impact:** Will exhaust monthly budget in <2 hours
- **Action:** Page on-call immediately via PagerDuty
- **Response Time:** <5 minutes

#### Slow Burn Rate Alert
- **Condition:** Error budget burning >6x normal rate (6-hour window)
- **Impact:** Will exhaust monthly budget in <5 days
- **Action:** Notify on-call via Slack
- **Response Time:** <30 minutes

#### Latency Critical
- **Condition:** P95 latency >1.5x SLO target
- **Impact:** Poor user experience
- **Action:** Page on-call immediately
- **Response Time:** <15 minutes

### SLO Targets by Agent

| Agent | Latency P95 | Success Rate | Freshness | Cost/Request |
|-------|-------------|--------------|-----------|--------------|
| inbox.triage | <1.5s | >98% | <30min | <$0.05 |
| inbox.search | <800ms | >99% | - | <$0.02 |
| knowledge.search | <1s | >98% | - | <$0.03 |
| planner.deploy | <5s | >95% | - | <$0.20 |
| warehouse.health | <2s | >98% | <60min | <$0.10 |
| analytics.insights | <3s | >97% | - | <$0.15 |

### Prometheus Metrics

Access metrics at: http://api.applylens.io/metrics

Key metrics:
- `applylens_agent_latency_p95_seconds{agent="..."}`
- `applylens_agent_success_rate{agent="..."}`
- `applylens_agent_error_rate{agent="..."}`
- `applylens_agent_slo_compliant{agent="..."}`

---

## Incident Response

### Severity Levels

- **SEV1** - Complete service outage (page immediately)
- **SEV2** - Significant degradation (page during business hours)
- **SEV3** - Minor issues (Slack notification)
- **SEV4** - Low priority (ticket only)

### On-Call Rotation

Current on-call: Check https://app.applylens.io/oncall

### Incident Commander Responsibilities

1. **Acknowledge** the incident in PagerDuty (2 minutes)
2. **Create** Slack incident channel (auto-created)
3. **Assess** severity and impact
4. **Communicate** status updates every 15 minutes
5. **Coordinate** with subject matter experts
6. **Resolve** incident and verify resolution
7. **Document** timeline in Slack channel
8. **Schedule** postmortem within 48 hours

### Common Incident Scenarios

#### API Outage (SEV1)

**Symptoms:** All API endpoints returning 5xx errors

**Likely Causes:**
- Database connection pool exhausted
- Elasticsearch cluster down
- AWS service outage

**Response:**
1. Check AWS Health Dashboard
2. Verify database connectivity: `psql -h db.applylens.io`
3. Check Elasticsearch: `curl -X GET "es.applylens.io:9200/_cluster/health"`
4. Review recent deployments
5. Consider rollback if recent deploy

**Runbook:** [SEV1 API Outage](#runbook-api-outage)

#### Elasticsearch Degradation (SEV2)

**Symptoms:** Search queries slow or timing out

**Response:**
1. Check ES cluster health
2. Verify JVM heap usage (<75%)
3. Check index sizes and shard allocation
4. Review recent bulk indexing jobs
5. Consider increasing cluster size

**Runbook:** [SEV2 Elasticsearch Issues](#runbook-elasticsearch)

### Postmortem Template

Use template at: `docs/templates/POSTMORTEM.md`

Required sections:
- Timeline of events
- Root cause analysis
- Impact assessment
- Action items (with owners and deadlines)
- Lessons learned

---

## Operational Tasks

### Daily Tasks

- [ ] Check SLO dashboard (all agents compliant)
- [ ] Review overnight alerts
- [ ] Monitor error budget consumption
- [ ] Check data quality reports
- [ ] Review overdue DSR requests

### Weekly Tasks

- [ ] Generate on-call report
- [ ] Review incident metrics (MTTR, count by severity)
- [ ] Analyze cost trends
- [ ] Review data quality metrics
- [ ] Update runbooks based on recent incidents

### Monthly Tasks

- [ ] Review and renew SSL certificates
- [ ] Audit user access and permissions
- [ ] Review retention policies and execute deletions
- [ ] Generate compliance report
- [ ] Capacity planning review

### Database Maintenance

**Backup Verification:**
```bash
# Verify latest backup
aws rds describe-db-snapshots \
  --db-instance-identifier applylens-prod \
  --query 'DBSnapshots[0].[DBSnapshotIdentifier,SnapshotCreateTime]'
```

**Migrations:**
```bash
# Run migrations (staging first!)
cd services/api
alembic upgrade head
```

**Connection Pool Monitoring:**
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Find long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE state = 'active' 
AND now() - pg_stat_activity.query_start > interval '5 minutes';
```

### Elasticsearch Maintenance

**Index Management:**
```bash
# List indices
curl -X GET "es.applylens.io:9200/_cat/indices?v"

# Delete old indices (>90 days)
curl -X DELETE "es.applylens.io:9200/emails-2024-07-*"

# Reindex
curl -X POST "es.applylens.io:9200/_reindex" -H 'Content-Type: application/json' -d'
{
  "source": {"index": "emails-old"},
  "dest": {"index": "emails-new"}
}'
```

**Cluster Health:**
```bash
# Check cluster health
curl -X GET "es.applylens.io:9200/_cluster/health?pretty"

# Check node stats
curl -X GET "es.applylens.io:9200/_nodes/stats?pretty"
```

---

## Security & Compliance

### PII Handling

All logs are automatically scanned and redacted for PII:
- Email addresses
- Phone numbers
- SSN
- Credit card numbers
- IP addresses
- API keys

**PII Access Audit:**
```bash
# Check PII access logs
psql -h db.applylens.io -d applylens -c "
SELECT * FROM pii_audit_log 
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC
LIMIT 100;
"
```

### Data Subject Rights

**Processing DSR Requests:**

1. Access Request (Art. 15):
   - Generate data export
   - Deliver within 30 days

2. Erasure Request (Art. 17):
   - Delete all user data
   - Verify deletion complete
   - Send confirmation

3. Portability Request (Art. 20):
   - Export data in JSON format
   - Upload to secure URL
   - Send download link

**Overdue Requests:**
```bash
# Check overdue DSR requests (>30 days)
curl -X GET "https://api.applylens.io/security/dsr/overdue"
```

### Compliance Audits

**Quarterly Audit Checklist:**
- [ ] Review consent records
- [ ] Verify retention policies enforced
- [ ] Audit PII access logs
- [ ] Review security incidents
- [ ] Update privacy policy if needed
- [ ] Train team on GDPR/CCPA requirements

---

## Troubleshooting

### High Latency

**Diagnosis:**
1. Check APM traces
2. Identify slow database queries
3. Review Elasticsearch query performance
4. Check external API dependencies

**Common Fixes:**
- Add database indexes
- Optimize Elasticsearch queries
- Increase connection pool size
- Scale up infrastructure

### High Error Rate

**Diagnosis:**
1. Check error logs in CloudWatch
2. Review recent deployments
3. Check external service status
4. Verify database connectivity

**Common Fixes:**
- Rollback recent deployment
- Increase timeout values
- Add retry logic
- Scale infrastructure

### Data Quality Issues

**Diagnosis:**
1. Run dbt quality checks
2. Check lineage for upstream issues
3. Review data freshness

**Commands:**
```bash
# Run dbt tests
cd analytics/dbt
dbt test --select source:*

# Check data freshness
dbt source freshness
```

---

## Contacts

### On-Call Schedule
- Primary: Check PagerDuty rotation
- Secondary: Check PagerDuty rotation
- Manager: Check PagerDuty escalation

### Escalation Path

1. **On-Call Engineer** (immediate response)
2. **Engineering Manager** (if no response in 15 min)
3. **VP Engineering** (for SEV1 after 30 min)
4. **CTO** (for extended outages)

### Slack Channels

- `#incidents` - Active incident coordination
- `#deployments` - Deployment notifications
- `#alerts` - Automated alerts
- `#on-call` - On-call discussions
- `#sre` - SRE team channel

### External Dependencies

- **AWS Support:** https://console.aws.amazon.com/support/
- **Gmail API Status:** https://status.google.com/
- **Elasticsearch Cloud:** support@elastic.co
- **PagerDuty Support:** https://support.pagerduty.com/

---

## Appendix

### Useful Commands

```bash
# Check API health
curl https://api.applylens.io/health

# View recent logs
aws logs tail /aws/ecs/applylens-api --follow

# Connect to database
psql -h db.applylens.io -U applylens -d applylens

# Run SQL migration
alembic upgrade head

# Run dbt models
dbt run --select agent_performance_summary

# Check Prometheus metrics
curl http://api.applylens.io/metrics | grep applylens_agent
```

### Related Documentation

- [SLA Overview](./SLA_OVERVIEW.md)
- [Rollback Runbook](./RUNBOOK_ROLLBACK.md)
- [Security Audit Template](./SECURITY_AUDIT.md)
- [On-Call Handbook](./ONCALL_HANDBOOK.md)

---

**Document Ownership:** SRE Team  
**Review Frequency:** Monthly  
**Last Review:** October 17, 2025  
**Next Review:** November 17, 2025
