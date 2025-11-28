# Incident Playbook: API Outage (SEV1)

**Version:** 1.0  
**Last Updated:** October 17, 2025  
**Severity:** SEV1 (Critical)

## Quick Reference

- **Typical Duration:** 15-60 minutes
- **Response Time:** <5 minutes
- **MTTR Goal:** <2 hours
- **On-Call Action:** Page immediately via PagerDuty

---

## Symptoms

User-facing symptoms that indicate API outage:

- [ ] All API endpoints returning 5xx errors
- [ ] API health endpoint unreachable
- [ ] Load balancer showing 0 healthy targets
- [ ] Complete loss of service functionality
- [ ] User reports: "Can't access ApplyLens"

**Detection Sources:**
- Monitoring alerts (Prometheus/Grafana)
- Health check failures
- User reports to support
- Status page monitoring

---

## Immediate Actions (First 5 Minutes)

### 1. Acknowledge Incident

```bash
# PagerDuty will create incident automatically
# Acknowledge within 2 minutes to stop escalation

# Via PagerDuty app or:
curl -X PUT https://api.pagerduty.com/incidents/{incident_id} \
  -H "Authorization: Token token={YOUR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"incident": {"type": "incident_reference", "status": "acknowledged"}}'
```

### 2. Create Incident Channel

```bash
# Slack incident channel auto-created
# Channel name: #incident-{timestamp}
# Post initial status

# Template:
🚨 **SEV1: API Outage**
**Started:** 14:35 UTC
**Status:** Investigating
**IC:** @your-name
**Impact:** Complete service unavailable

Updates every 5 minutes.
```

### 3. Quick Health Check

```bash
# Check if API is truly down
curl -I https://api.applylens.io/health
# Expected during outage: timeout or 5xx

# Check load balancer
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/applylens-api/abc123 \
  --region us-east-1

# Look for: "State": "unhealthy" on all targets
```

---

## Investigation (Next 10 Minutes)

### Check 1: Recent Deployments

**Most common cause of outages.**

```bash
# Check recent deployments
cd /opt/applylens/deploy
git log -5 --oneline

# Check when last deployment occurred
git show --stat

# If deployed in last 2 hours:
# 🔴 LIKELY CAUSE: Recent deployment
# 👉 ACTION: Proceed to Rollback section
```

### Check 2: AWS Service Health

```bash
# Check AWS Health Dashboard
open https://health.aws.amazon.com/health/status

# Or via CLI
aws health describe-events \
  --filter eventTypeCategories=issue \
  --region us-east-1

# If AWS issue found:
# 🔴 CAUSE: AWS infrastructure
# 👉 ACTION: Wait for AWS resolution, monitor status page
```

### Check 3: Database Connectivity

```bash
# Test database connection
psql -h db.applylens.io -U applylens -d applylens -c "SELECT 1;"

# If connection fails:
# 🔴 LIKELY CAUSE: Database unavailable
# 👉 ACTION: Proceed to Database Issues section

# Check connection pool
psql -h db.applylens.io -U applylens -d applylens -c "
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';
"

# If >80% of max connections (typically 100):
# 🔴 LIKELY CAUSE: Connection pool exhausted
# 👉 ACTION: Restart API pods
```

### Check 4: ECS Task Health

```bash
# Check running tasks
aws ecs list-tasks \
  --cluster applylens-prod \
  --service-name applylens-api-prod \
  --region us-east-1

# If no tasks running:
# 🔴 CAUSE: All tasks crashed
# 👉 ACTION: Check task logs

# Get task logs
aws logs tail /aws/ecs/applylens-api --since 10m

# Look for common errors:
# - "Cannot connect to database"
# - "Out of memory"
# - "Port already in use"
```

### Check 5: Elasticsearch Health

```bash
# Check ES cluster health
curl -X GET "es.applylens.io:9200/_cluster/health?pretty"

# Expected during outage:
# "status": "red" or connection timeout

# If ES is down:
# 🔴 CAUSE: Elasticsearch unavailable
# 👉 ACTION: Proceed to Elasticsearch section
```

---

## Resolution Procedures

### Scenario A: Recent Deployment (70% of outages)

**Symptoms:** Deployment in last 2 hours, previous version was stable

**Resolution:** Rollback deployment

```bash
# 1. Identify previous stable version
cd /opt/applylens/deploy
git tag | grep prod | tail -2

# 2. Initiate rollback
python promote_release.py prod \
  --from-commit <previous-version> \
  --emergency

# 3. Monitor rollback progress (6-10 minutes)
watch -n 5 'curl -s https://api.applylens.io/health | jq .'

# 4. Verify resolution
curl https://api.applylens.io/version
# Should show previous version

# 5. Update incident channel
✅ **Rollback complete**
Service restored to v1.2.2
Monitoring for stability
```

**See:** [RUNBOOK_ROLLBACK.md](./RUNBOOK_ROLLBACK.md) for detailed steps

---

### Scenario B: Database Connection Pool Exhausted

**Symptoms:** Database reachable, but API can't connect

**Resolution:** Restart API pods and investigate connection leaks

```bash
# 1. Force restart all API pods
aws ecs update-service \
  --cluster applylens-prod \
  --service applylens-api-prod \
  --force-new-deployment \
  --region us-east-1

# 2. Monitor task startup (3-5 minutes)
aws ecs describe-services \
  --cluster applylens-prod \
  --services applylens-api-prod \
  --region us-east-1

# 3. Verify health restored
curl https://api.applylens.io/health

# 4. Investigate connection leaks (post-incident)
psql -h db.applylens.io -U applylens -d applylens -c "
SELECT pid, usename, application_name, state, query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
AND now() - query_start > interval '5 minutes';
"

# 5. Kill long-running idle connections
psql -h db.applylens.io -U applylens -d applylens -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
AND now() - query_start > interval '10 minutes';
"
```

---

### Scenario C: Database Completely Down

**Symptoms:** Cannot connect to database at all

**Resolution:** Check RDS status and failover if needed

```bash
# 1. Check RDS instance status
aws rds describe-db-instances \
  --db-instance-identifier applylens-prod \
  --region us-east-1 \
  --query 'DBInstances[0].DBInstanceStatus'

# Possible statuses:
# - "available" (good)
# - "storage-full" (need to increase)
# - "failed" (need to restore from backup)
# - "rebooting" (wait for completion)

# 2. If storage-full, increase storage
aws rds modify-db-instance \
  --db-instance-identifier applylens-prod \
  --allocated-storage 600 \
  --apply-immediately \
  --region us-east-1

# 3. If failed, check for multi-AZ failover
aws rds describe-db-instances \
  --db-instance-identifier applylens-prod \
  --query 'DBInstances[0].MultiAZ'

# 4. If multi-AZ enabled, force failover
aws rds reboot-db-instance \
  --db-instance-identifier applylens-prod \
  --force-failover \
  --region us-east-1

# 5. If not multi-AZ, restore from snapshot (30-60 min)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier applylens-prod-restored \
  --db-snapshot-identifier <latest-snapshot> \
  --region us-east-1
```

---

### Scenario D: Elasticsearch Down

**Symptoms:** ES cluster unreachable or all nodes red

**Resolution:** Restart ES cluster or scale up

```bash
# 1. Check Elasticsearch cluster status
curl -X GET "es.applylens.io:9200/_cluster/health?pretty"

# 2. Check node stats
curl -X GET "es.applylens.io:9200/_cat/nodes?v"

# 3. If all nodes down, restart cluster (ES Cloud)
# Log into Elastic Cloud console
open https://cloud.elastic.co/deployments

# 4. If self-managed, restart ES service
ssh es-node-1.applylens.io
sudo systemctl restart elasticsearch

# 5. Wait for cluster to recover (5-15 minutes)
watch -n 10 'curl -s -X GET "es.applylens.io:9200/_cluster/health?pretty"'

# 6. Once green, verify API health
curl https://api.applylens.io/health
```

---

### Scenario E: AWS Service Outage

**Symptoms:** AWS Health Dashboard shows incidents in your region

**Resolution:** Wait for AWS resolution or failover to backup region

```bash
# 1. Check AWS status
open https://health.aws.amazon.com/health/status

# 2. If regional outage, consider DR failover
# (Only if RTO/RPO requirements not met by AWS recovery)

# 3. Monitor AWS status page every 5 minutes

# 4. Post updates to status page
curl -X POST https://api.statuspage.io/v1/pages/{page_id}/incidents \
  -H "Authorization: OAuth {token}" \
  -d "incident[name]=AWS Service Outage" \
  -d "incident[status]=investigating" \
  -d "incident[body]=We are experiencing issues due to AWS service disruption in us-east-1. AWS is actively working on resolution."

# 5. Once AWS resolves, verify service health
```

---

### Scenario F: Unknown Cause

**If root cause unclear after 15 minutes:**

```bash
# 1. Collect comprehensive diagnostics
./scripts/diagnostic-dump.sh > /tmp/diagnostic-$(date +%s).log

# 2. Attempt service restart
aws ecs update-service \
  --cluster applylens-prod \
  --service applylens-api-prod \
  --force-new-deployment \
  --region us-east-1

# 3. If restart doesn't help, try rollback
python promote_release.py prod \
  --from-commit <previous-known-good> \
  --emergency

# 4. Escalate to engineering manager
# Page: engineering-manager oncall

# 5. Consider enabling maintenance mode
# Redirect to static "Under Maintenance" page
```

---

## Recovery Verification

After service restored, verify:

### 1. Health Checks Pass

```bash
# API health
curl https://api.applylens.io/health | jq .
# Expected: {"status": "healthy", "database": "ok", "elasticsearch": "ok", "redis": "ok"}

# All agents responsive
for agent in inbox.triage inbox.search knowledge.search planner.deploy warehouse.health analytics.insights; do
  echo "Testing $agent..."
  curl -X POST https://api.applylens.io/agents/$agent/predict \
    -H "Content-Type: application/json" \
    -d '{"test": true}'
done
```

### 2. Monitor Key Metrics

```bash
# Check error rate (should be <2%)
curl -s http://api.applylens.io/metrics | grep applylens_agent_error_rate

# Check latency (P95 should be <2s)
curl -s http://api.applylens.io/metrics | grep applylens_agent_latency_p95

# Check success rate (should be >98%)
curl -s http://api.applylens.io/metrics | grep applylens_agent_success_rate
```

### 3. User Validation

```bash
# Run smoke tests
cd services/api
pytest tests/smoke/ -v

# Test critical user flows
# - Login
# - View inbox
# - Search emails
# - Classify email
# - Generate insights
```

---

## Communication

### During Incident (Every 5 Minutes)

**Slack Update Template:**

```
🔴 **UPDATE [14:40 UTC]**
**Status:** Investigating database connection issues
**Action:** Restarting API pods
**ETA:** 5 minutes
**Impact:** All users unable to access service
```

### Resolution Announcement

**Slack:**

```
✅ **INCIDENT RESOLVED [14:52 UTC]**
**Duration:** 17 minutes
**Cause:** Database connection pool exhausted
**Resolution:** Restarted API pods, killed idle connections
**Status:** Service fully operational

Monitoring for 30 minutes. Postmortem scheduled for tomorrow 10am.
```

**Status Page:**

```
**Incident Resolved**

The API outage has been resolved. All systems are operating normally.

**Cause:** Database connection pool exhaustion
**Resolution:** Service restarted and connections cleared
**Duration:** 14:35-14:52 UTC (17 minutes)

We apologize for the disruption.
```

### Customer Email (if >30 min outage)

```
Subject: ApplyLens Service Disruption - October 17, 2025

Dear ApplyLens Users,

We experienced a service disruption today between 14:35-14:52 UTC (17 minutes).

What happened:
Our database connection pool became exhausted, preventing API requests from completing.

What we did:
We restarted our API services and cleared stale database connections.

What we're doing to prevent this:
- Implementing connection pool monitoring
- Adding automatic connection cleanup
- Increasing connection pool limits

We deeply apologize for this disruption. If you have any questions, please contact support@applylens.io.

Thank you for your patience,
ApplyLens SRE Team
```

---

## Post-Incident Actions

Within 2 hours:

- [ ] Schedule postmortem meeting (within 48 hours)
- [ ] Create postmortem document from template
- [ ] Extract logs and metrics for analysis
- [ ] Create action items for prevention
- [ ] Update runbook with lessons learned

Within 48 hours:

- [ ] Conduct postmortem meeting (blameless)
- [ ] Assign owners to action items
- [ ] Update monitoring/alerting as needed
- [ ] Communicate findings to leadership

---

## Prevention

To reduce API outage frequency:

1. **Monitoring:**
   - Database connection pool usage alerts
   - ECS task health monitoring
   - Proactive capacity alerts

2. **Testing:**
   - Load testing before deployments
   - Chaos engineering tests
   - Staging environment validation

3. **Architecture:**
   - Implement circuit breakers
   - Add connection pool auto-scaling
   - Multi-region failover capability

4. **Processes:**
   - Mandatory canary deployments
   - Automated rollback triggers
   - Pre-deployment checklist

---

## Related Documentation

- [RUNBOOK_ROLLBACK.md](./RUNBOOK_ROLLBACK.md) - Rollback procedures
- [PLAYBOOK_DATABASE_ISSUES.md](./PLAYBOOK_DATABASE_ISSUES.md) - Database troubleshooting
- [PRODUCTION_HANDBOOK.md](../PRODUCTION_HANDBOOK.md) - General operations

---

**Document Ownership:** SRE Team  
**Review Frequency:** After each SEV1 incident  
**Last Review:** October 17, 2025  
**Last Incident:** September 15, 2025 (database connection pool)
