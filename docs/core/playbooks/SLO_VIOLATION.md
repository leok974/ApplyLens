# Incident Playbook: SLO Violation (SEV2/SEV3)

**Version:** 1.0  
**Last Updated:** October 17, 2025  
**Severity:** SEV2 (if fast burn) or SEV3 (if slow burn)

## Quick Reference

- **Fast Burn Duration:** 15-45 minutes (SEV2)
- **Slow Burn Duration:** Hours to days (SEV3)
- **Response Time:** <15 minutes (fast burn), <2 hours (slow burn)
- **MTTR Goal:** <4 hours (fast burn), <24 hours (slow burn)

---

## Symptoms

### Fast Burn Alert (SEV2)

**Trigger Conditions:**
- Error budget burning >14.4x normal rate
- 1-hour window measurement
- Will exhaust monthly budget in <2 hours

**User Impact:**
- Elevated error rates (2-5%)
- Increased latency (1.5-2x normal)
- Some requests timing out

**Example Alert:**

```
🔥 FAST BURN ALERT: inbox.triage
Error budget burning at 18.5x rate
Time to exhaustion: 87 minutes
Current error rate: 4.2%
Threshold: 2%
```

### Slow Burn Alert (SEV3)

**Trigger Conditions:**
- Error budget burning >6x normal rate
- 6-hour window measurement
- Will exhaust monthly budget in <5 days

**User Impact:**
- Slightly elevated error rates (2-3%)
- Minor latency increase
- Intermittent failures

**Example Alert:**

```
⚠️ SLOW BURN ALERT: analytics.insights
Error budget burning at 7.2x rate
Time to exhaustion: 4.1 days
Current error rate: 3.8%
Threshold: 3%
```

---

## Immediate Actions

### For Fast Burn (SEV2)

```bash
# 1. Acknowledge alert (within 5 minutes)
# PagerDuty notification sent

# 2. Create Slack incident channel
# Auto-created: #incident-{timestamp}

# 3. Post initial status
🔥 **SEV2: Fast Burn Alert - inbox.triage**
**Started:** 15:20 UTC
**Status:** Investigating
**IC:** @your-name
**Impact:** 4.2% error rate (2% threshold)
**Budget Status:** 87 minutes to exhaustion

Updates every 10 minutes.

# 4. Check dashboard
open https://grafana.applylens.io/d/slo-compliance?var-agent=inbox.triage
```

### For Slow Burn (SEV3)

```bash
# 1. Acknowledge alert (within 1 hour)
# Slack notification sent to #alerts

# 2. Create tracking ticket
# Use Jira or GitHub issue

# 3. Post in #sre channel
⚠️ **Slow burn alert: analytics.insights**
Investigating elevated error rate (3.8% vs 3% threshold)
Tracking in JIRA-1234

# 4. Begin investigation (not urgent)
```

---

## Investigation

### Step 1: Identify Affected Agent

```bash
# Check all agents' error budgets
curl -s http://api.applylens.io/metrics | grep applylens_agent_error_budget_remaining

# Example output:
applylens_agent_error_budget_remaining{agent="inbox.triage"} 0.42
applylens_agent_error_budget_remaining{agent="inbox.search"} 0.89
applylens_agent_error_budget_remaining{agent="analytics.insights"} 0.35

# Identify agent(s) with low budget (<0.5)
```

### Step 2: Analyze Error Patterns

```bash
# Get recent errors for affected agent
aws logs filter-pattern /aws/ecs/applylens-api \
  --filter-pattern '{$.level = "ERROR" && $.agent = "inbox.triage"}' \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --region us-east-1 \
  | jq -r '.events[].message' \
  | head -50

# Look for common patterns:
# - Specific error messages repeating
# - Timeouts to external services
# - Database query errors
# - Rate limiting errors
```

### Step 3: Check Recent Changes

```bash
# Check recent deployments
cd /opt/applylens/deploy
git log --since="24 hours ago" --oneline

# Check if deployment correlates with burn rate increase
# Use Grafana annotation or git timestamp

# If deployment is cause:
# 🔴 LIKELY CAUSE: Recent code change
# 👉 ACTION: Consider rollback or hotfix
```

### Step 4: Examine External Dependencies

```bash
# Check third-party API status
# Gmail API
curl -s https://www.google.com/appsstatus/dashboard/incidents.json | jq .

# Elasticsearch
curl -X GET "es.applylens.io:9200/_cluster/health?pretty"

# Database
psql -h db.applylens.io -U applylens -d applylens -c "
SELECT * FROM pg_stat_activity WHERE state = 'active' AND wait_event_type IS NOT NULL;
"

# If external service degraded:
# 🔴 LIKELY CAUSE: Dependency issue
# 👉 ACTION: Implement circuit breaker or rate limiting
```

### Step 5: Analyze Latency Distribution

```bash
# Get latency percentiles for affected agent
curl -s http://api.applylens.io/metrics | grep 'applylens_agent_latency.*inbox.triage'

# Example output:
applylens_agent_latency_p50{agent="inbox.triage"} 0.8
applylens_agent_latency_p95{agent="inbox.triage"} 2.3
applylens_agent_latency_p99{agent="inbox.triage"} 4.8

# Compare to baseline (from dashboard)
# Baseline P95: 1.5s
# Current P95: 2.3s
# Increase: 53%

# If latency spike:
# 🔴 LIKELY CAUSE: Performance regression
# 👉 ACTION: Profile slow requests
```

---

## Resolution Procedures

### Scenario A: Recent Deployment Regression

**Symptoms:** Burn rate increased after deployment

**Option 1: Rollback (Fast)**

```bash
# If impact is severe (>5% error rate)
python promote_release.py prod \
  --from-commit <previous-version> \
  --emergency

# Monitor burn rate recovery (10-15 minutes)
watch -n 30 'curl -s http://api.applylens.io/metrics | grep applylens_agent_error_rate'
```

**Option 2: Hotfix (If rollback too disruptive)**

```bash
# 1. Identify and fix bug locally
# 2. Run tests
pytest tests/test_inbox_triage.py -v

# 3. Deploy hotfix
git add -A
git commit -m "Hotfix: Fix inbox.triage error handling"
git push origin main

# 4. Wait for CI/CD pipeline
# 5. Deploy to canary first
python promote_release.py prod --canary-pct 10

# 6. Monitor for 15 minutes
# If burn rate decreases, continue rollout
```

---

### Scenario B: External Service Degradation

**Symptoms:** Errors from Gmail API, Elasticsearch timeouts

**Resolution: Circuit Breaker + Fallback**

```bash
# 1. Check which service is degraded
# Gmail API
curl -X GET "https://gmail.googleapis.com/gmail/v1/users/me/messages" \
  -H "Authorization: Bearer $TOKEN"

# 2. Enable circuit breaker (if available)
# Via feature flag or config update

# 3. Reduce request rate to degraded service
# Update rate limiter settings:
psql -h db.applylens.io -U applylens -d applylens -c "
UPDATE rate_limit_config 
SET requests_per_minute = 10 
WHERE service = 'gmail_api';
"

# 4. Monitor for service recovery
# Check status page or health endpoint every 5 minutes

# 5. Once recovered, restore normal rate
psql -h db.applylens.io -U applylens -d applylens -c "
UPDATE rate_limit_config 
SET requests_per_minute = 100 
WHERE service = 'gmail_api';
"
```

---

### Scenario C: Database Performance

**Symptoms:** Slow queries, connection timeouts

**Resolution: Query Optimization or Scaling**

```bash
# 1. Identify slow queries
psql -h db.applylens.io -U applylens -d applylens -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# 2. Check for missing indexes
psql -h db.applylens.io -U applylens -d applylens -c "
SELECT schemaname, tablename, attname
FROM pg_stats
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
AND n_distinct > 100
AND correlation < 0.5;
"

# 3. Add index if needed (test in staging first!)
psql -h db.applylens.io -U applylens -d applylens -c "
CREATE INDEX CONCURRENTLY idx_emails_user_id_created 
ON emails(user_id, created_at);
"

# 4. If urgent, scale up database
aws rds modify-db-instance \
  --db-instance-identifier applylens-prod \
  --db-instance-class db.r5.2xlarge \
  --apply-immediately \
  --region us-east-1

# 5. Monitor query performance
# Should see improvement within 5-10 minutes
```

---

### Scenario D: Increased Load

**Symptoms:** Error rate increases during peak hours

**Resolution: Scale Infrastructure**

```bash
# 1. Check current capacity
aws ecs describe-services \
  --cluster applylens-prod \
  --services applylens-api-prod \
  --region us-east-1 \
  --query 'services[0].desiredCount'

# 2. Scale up ECS tasks
aws ecs update-service \
  --cluster applylens-prod \
  --service applylens-api-prod \
  --desired-count 10 \
  --region us-east-1

# 3. Wait for tasks to become healthy (3-5 minutes)
aws ecs wait services-stable \
  --cluster applylens-prod \
  --services applylens-api-prod \
  --region us-east-1

# 4. Verify load distribution
curl https://api.applylens.io/metrics | grep applylens_request_count

# 5. Monitor burn rate (should decrease)
```

---

### Scenario E: Cost Budget Exceeded

**Symptoms:** Cost per request exceeds target ($0.05 → $0.15)

**Resolution: Optimize Model Usage**

```bash
# 1. Identify expensive operations
# Check CloudWatch costs by service
aws ce get-cost-and-usage \
  --time-period Start=2025-10-17,End=2025-10-18 \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# 2. Review model selection
# Switch to smaller models for non-critical tasks
psql -h db.applylens.io -U applylens -d applylens -c "
UPDATE agent_config 
SET model = 'gpt-3.5-turbo' 
WHERE agent = 'inbox.triage' AND priority = 'low';
"

# 3. Implement caching
# Add Redis cache for frequent queries

# 4. Reduce token usage
# Trim prompts, reduce context size

# 5. Monitor cost decrease
# Check metrics dashboard
```

---

## Recovery Verification

### Check Burn Rate

```bash
# Current burn rate
curl -s http://api.applylens.io/metrics | grep applylens_agent_burn_rate

# Should be <1.0 (normal) after resolution

# Error budget remaining
curl -s http://api.applylens.io/metrics | grep applylens_agent_error_budget_remaining

# Should be stabilizing or increasing
```

### Monitor for 30 Minutes

```bash
# Set up watch command
watch -n 60 '
echo "=== Burn Rate ===" && 
curl -s http://api.applylens.io/metrics | grep applylens_agent_burn_rate{agent="inbox.triage"} &&
echo "\n=== Error Rate ===" &&
curl -s http://api.applylens.io/metrics | grep applylens_agent_error_rate{agent="inbox.triage"} &&
echo "\n=== Latency P95 ===" &&
curl -s http://api.applylens.io/metrics | grep applylens_agent_latency_p95{agent="inbox.triage"}
'

# If metrics stabilize within 30 minutes:
# ✅ Resolution successful
```

---

## Communication

### Fast Burn Update Template

```
🔥 **UPDATE [15:35 UTC]**
**Status:** Root cause identified - slow database queries
**Action:** Added index, monitoring performance
**Burn Rate:** 18.5x → 8.2x (improving)
**Error Rate:** 4.2% → 2.8% (improving)
**Budget Remaining:** 42%
```

### Resolution Announcement

```
✅ **SLO BURN RESOLVED [16:10 UTC]**
**Agent:** inbox.triage
**Duration:** 50 minutes
**Cause:** Missing database index on emails table
**Resolution:** Added index on (user_id, created_at)
**Current Status:**
  - Burn rate: 0.8x (normal)
  - Error rate: 1.2% (below 2% threshold)
  - Error budget: 45% remaining

No user-facing impact. Monitoring continues.
```

---

## Post-Incident Actions

### Immediate (Within 1 Hour)

- [ ] Document root cause in incident channel
- [ ] Create action items for prevention
- [ ] Update monitoring if gaps identified
- [ ] Update runbook with learnings

### Follow-Up (Within 1 Week)

- [ ] Conduct incident review (if fast burn)
- [ ] Implement preventive measures
- [ ] Adjust SLO targets if consistently missed
- [ ] Share lessons learned with team

---

## Prevention Strategies

### Proactive Monitoring

```bash
# Set up predictive alerts
# Alert if error rate trending upward (even below threshold)

# Example Prometheus rule:
- alert: ErrorRateTrendingUp
  expr: |
    (rate(applylens_agent_errors_total[1h]) - rate(applylens_agent_errors_total[1h] offset 1h))
    / rate(applylens_agent_errors_total[1h] offset 1h) > 0.5
  for: 15m
  annotations:
    summary: "Error rate increasing by >50%"
```

### Load Testing

```bash
# Run weekly load tests
cd services/api
locust -f tests/load/locustfile.py \
  --host https://staging.applylens.io \
  --users 1000 \
  --spawn-rate 50 \
  --run-time 30m

# Identify performance bottlenecks before production
```

### Chaos Engineering

```bash
# Inject failures to test resilience
# Run monthly chaos tests

# Example: Increase ES latency
cd services/api/tests/chaos
python inject_latency.py --service elasticsearch --latency 500ms --duration 10m

# Verify SLO compliance maintained
```

---

## Related Documentation

- [SLA_OVERVIEW.md](../SLA_OVERVIEW.md) - SLO targets and error budgets
- [PRODUCTION_HANDBOOK.md](../PRODUCTION_HANDBOOK.md) - Monitoring dashboards
- [PLAYBOOK_API_OUTAGE.md](./PLAYBOOK_API_OUTAGE.md) - If escalates to SEV1

---

**Document Ownership:** SRE Team  
**Review Frequency:** Quarterly  
**Last Review:** October 17, 2025  
**Recent Incidents:** 3 fast burns in Q3 2025 (database, external API, code regression)
