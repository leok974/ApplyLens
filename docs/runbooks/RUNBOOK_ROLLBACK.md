# Rollback Runbook

**Version:** 1.0  
**Last Updated:** October 17, 2025  
**Audience:** On-Call Engineers, SRE Team

## Purpose

This runbook provides step-by-step procedures for rolling back deployments in ApplyLens production environment.

---

## When to Rollback

### Automatic Rollback Triggers

The deployment system automatically triggers rollback when:

1. **Error Rate Spike**
   - Error rate >5% for 5 consecutive minutes
   - Comparison window: Previous 1 hour average

2. **Latency Degradation**
   - P95 latency >2x baseline for 10 minutes
   - Baseline: Previous 24-hour average

3. **Critical Alert**
   - Fast burn rate alert triggered (>14.4x)
   - Database connection failures >10% for 3 minutes

### Manual Rollback Criteria

Consider manual rollback when:

- [ ] User reports of widespread issues
- [ ] SLO violation across multiple agents
- [ ] Database migration failure
- [ ] Third-party integration failure
- [ ] Security vulnerability introduced
- [ ] Feature flag not preventing issue

**Decision Rule:** If unsure, rollback. We can always re-deploy after fixing.

---

## Pre-Rollback Checklist

Before initiating rollback:

1. [ ] **Verify Issue:** Confirm problem exists (not false alarm)
2. [ ] **Check Status:** Review monitoring dashboards
3. [ ] **Communicate:** Post in `#incidents` Slack channel
4. [ ] **Create Incident:** Open PagerDuty incident
5. [ ] **Identify Version:** Note current and target rollback versions
6. [ ] **Backup Plan:** Ensure database backup is recent

---

## Rollback Procedures

### Method 1: Automatic Rollback (Preferred)

**When to Use:** Deployment in progress, automatic checks triggered

**Steps:**

```bash
# The GitHub Actions workflow automatically rolls back
# You just need to monitor the process

# 1. Check workflow status
open https://github.com/leok974/ApplyLens/actions

# 2. Monitor Slack #deployments channel for updates
# Automated message will appear: "🔴 Rollback initiated for prod"

# 3. Verify rollback completion (5-10 minutes)
curl https://api.applylens.io/version
# Should show previous version

# 4. Check health
curl https://api.applylens.io/health
# Should return: {"status": "healthy"}
```

**Timeline:**
- Detection: <2 minutes
- Rollback trigger: <1 minute
- Traffic shift: 2-3 minutes
- Full rollback: 5-10 minutes

---

### Method 2: Manual Rollback via Script (Recommended)

**When to Use:** Automatic rollback failed or after detecting issue post-deployment

**Prerequisites:**
- SSH access to deployment server
- AWS credentials configured
- Git repository access

**Steps:**

```bash
# 1. Connect to deployment server
ssh deploy@applylens-deploy.internal

# 2. Navigate to deployment directory
cd /opt/applylens/deploy/scripts

# 3. Check current production version
git tag | grep prod | tail -1
# Example output: prod-v1.2.3-20251017-abc123

# 4. Identify previous stable version
git tag | grep prod | tail -2 | head -1
# Example output: prod-v1.2.2-20251016-def456

# 5. Run rollback script
python promote_release.py prod \
  --from-commit def456 \
  --skip-validation \
  --emergency

# 6. Monitor progress (script provides real-time updates)
# Expected output:
# ✅ Validating rollback target...
# ✅ Creating rollback deployment...
# ✅ Shifting traffic (100% -> 0%)...
# ✅ Updating load balancer...
# ✅ Verifying health checks...
# ✅ Rollback complete!

# 7. Verify new version
curl https://api.applylens.io/version
```

**Flags Explained:**
- `--skip-validation`: Skip pre-deployment tests (faster)
- `--emergency`: Immediate 100% traffic shift (no canary)

**Timeline:**
- Script execution: 3-5 minutes
- Traffic shift: 1-2 minutes
- Health check verification: 2-3 minutes
- **Total:** 6-10 minutes

---

### Method 3: Direct ECS Task Rollback

**When to Use:** Script rollback failed, need immediate action

**Steps:**

```bash
# 1. List current ECS services
aws ecs list-services \
  --cluster applylens-prod \
  --region us-east-1

# 2. Get current task definition
aws ecs describe-services \
  --cluster applylens-prod \
  --services applylens-api-prod \
  --region us-east-1 \
  --query 'services[0].taskDefinition'

# 3. List previous task definitions
aws ecs list-task-definitions \
  --family-prefix applylens-api-prod \
  --sort DESC \
  --max-items 5 \
  --region us-east-1

# 4. Identify previous stable version
# Example: applylens-api-prod:123 (current)
#          applylens-api-prod:122 (previous, stable)

# 5. Update service to use previous task definition
aws ecs update-service \
  --cluster applylens-prod \
  --service applylens-api-prod \
  --task-definition applylens-api-prod:122 \
  --region us-east-1

# 6. Wait for deployment to stabilize (5-10 minutes)
aws ecs wait services-stable \
  --cluster applylens-prod \
  --services applylens-api-prod \
  --region us-east-1

# 7. Verify health
curl https://api.applylens.io/health
```

**Timeline:**
- Task definition update: <1 minute
- ECS rolling deployment: 8-12 minutes
- Health check stabilization: 2-3 minutes
- **Total:** 10-15 minutes

---

### Method 4: Canary Rollback

**When to Use:** Issue only affects canary traffic, production unaffected

**Steps:**

```bash
# 1. Check canary status
aws elbv2 describe-target-groups \
  --names applylens-api-canary-prod \
  --region us-east-1

# 2. Reduce canary traffic to 0%
python promote_release.py prod \
  --canary-pct 0 \
  --no-deploy

# 3. Verify 100% traffic on stable version
curl https://api.applylens.io/version
# Should show stable version

# 4. Stop canary tasks
aws ecs update-service \
  --cluster applylens-prod \
  --service applylens-api-canary-prod \
  --desired-count 0 \
  --region us-east-1
```

**Timeline:**
- Traffic reduction: <1 minute
- Task termination: 2-3 minutes
- **Total:** 3-5 minutes

---

## Database Rollback

### When Database Migrations Are Involved

**CRITICAL:** Database rollbacks are more complex and risky.

#### Step 1: Assess Migration Impact

```bash
# 1. Check recent migrations
cd services/api
alembic history | head -10

# 2. Review migration file
cat alembic/versions/0018_consent_log.py

# 3. Determine if migration is reversible
# Look for complete downgrade() function
```

#### Step 2: Test Downgrade (Staging First!)

```bash
# ALWAYS test in staging first!
export DATABASE_URL="postgresql://staging-db"

# 1. Check current version
alembic current

# 2. Downgrade one version
alembic downgrade -1

# 3. Verify application still works
pytest tests/

# 4. If successful, proceed to production
```

#### Step 3: Production Database Rollback

```bash
# 1. Create database backup
aws rds create-db-snapshot \
  --db-instance-identifier applylens-prod \
  --db-snapshot-identifier rollback-backup-$(date +%Y%m%d-%H%M%S)

# 2. Wait for backup completion (5-10 minutes)
aws rds wait db-snapshot-completed \
  --db-snapshot-identifier rollback-backup-20251017-143000

# 3. Connect to production database
export DATABASE_URL="postgresql://prod-db"

# 4. Downgrade migration
alembic downgrade -1

# 5. Verify downgrade
alembic current
```

#### Step 4: Application Rollback

```bash
# After database rollback, roll back application code
python promote_release.py prod \
  --from-commit <previous-version> \
  --emergency
```

**Timeline:**
- Database backup: 10-15 minutes
- Migration downgrade: 2-5 minutes
- Application rollback: 6-10 minutes
- **Total:** 18-30 minutes

---

## Post-Rollback Verification

After rollback completes, verify system health:

### 1. Version Check

```bash
# Verify correct version deployed
curl https://api.applylens.io/version

# Expected format:
# {"version": "1.2.2", "commit": "def456", "deployed_at": "2025-10-16T10:30:00Z"}
```

### 2. Health Checks

```bash
# API health
curl https://api.applylens.io/health
# Expected: {"status": "healthy", "database": "ok", "elasticsearch": "ok"}

# Database connectivity
psql -h db.applylens.io -U applylens -d applylens -c "SELECT 1;"

# Elasticsearch
curl -X GET "es.applylens.io:9200/_cluster/health"
```

### 3. Smoke Tests

```bash
# Run critical path tests
cd services/api

# Test email triage
curl -X POST https://api.applylens.io/agents/inbox.triage/predict \
  -H "Content-Type: application/json" \
  -d '{"email_id": "test-123"}'

# Test email search
curl -X GET https://api.applylens.io/agents/inbox.search/search?q=meeting

# Test authentication
curl -X POST https://api.applylens.io/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test"}'
```

### 4. Monitor Metrics

Check dashboards for 15-30 minutes:

- [ ] Error rate returning to baseline (<2%)
- [ ] Latency returning to normal (P95 <1.5s)
- [ ] Success rate >98%
- [ ] No new alerts triggered
- [ ] User traffic stable

**Dashboard:** https://grafana.applylens.io/d/system-health

---

## Communication

### During Rollback

**Slack Template:**

```
🔴 **ROLLBACK IN PROGRESS**

**Incident:** [Brief description]
**Severity:** SEV1/SEV2
**Action:** Rolling back from v1.2.3 to v1.2.2
**ETA:** 10 minutes
**Impact:** [User-facing impact]

Updates every 5 minutes in this channel.
```

### After Rollback

**Slack Template:**

```
✅ **ROLLBACK COMPLETE**

**Resolution:** Rolled back to v1.2.2
**Status:** System stable
**Verification:** All health checks passing
**Next Steps:** 
  - Root cause analysis
  - Fix and re-deploy
  - Postmortem scheduled

Incident closed. Monitoring for 1 hour.
```

### Customer Communication

If customer-impacting, post to status page:

```
**Title:** Service Degradation Resolved

**Message:**
We experienced elevated error rates between 14:00-14:15 UTC.
The issue has been resolved by rolling back a recent deployment.
All systems are now operating normally.

We apologize for any inconvenience.
```

---

## Troubleshooting Failed Rollbacks

### Rollback Script Fails

**Symptoms:** `promote_release.py` exits with error

**Common Causes:**
1. AWS credentials expired
2. Git tag not found
3. ECS service limit reached

**Solution:**

```bash
# Refresh AWS credentials
aws sso login

# Verify git tag exists
git tag | grep <target-version>

# Check ECS service capacity
aws ecs describe-clusters --cluster applylens-prod
```

### Health Checks Fail After Rollback

**Symptoms:** ECS tasks fail health checks, keep restarting

**Investigation:**

```bash
# Check task logs
aws logs tail /aws/ecs/applylens-api --follow

# Common issues:
# - Database migration mismatch
# - Environment variable missing
# - Dependency version conflict
```

**Solution:**

```bash
# If database issue, may need to rollback database too
alembic downgrade -1

# If environment issue, check parameter store
aws ssm get-parameters-by-path --path /applylens/prod/
```

### Rollback Partially Complete

**Symptoms:** Some tasks rolled back, others still on bad version

**Solution:**

```bash
# Force redeploy all tasks
aws ecs update-service \
  --cluster applylens-prod \
  --service applylens-api-prod \
  --force-new-deployment \
  --region us-east-1
```

---

## Prevention

To reduce rollback frequency:

1. **Staging Testing:** Deploy to staging 24 hours before prod
2. **Canary Deployment:** Always use gradual rollout (10% → 50% → 100%)
3. **Feature Flags:** Use flags to toggle new features
4. **Database Migrations:** Make migrations backwards-compatible
5. **Automated Tests:** Comprehensive test coverage
6. **Monitoring:** Proactive alerting before customer impact

---

## Escalation

If rollback unsuccessful after 30 minutes:

1. **Page Engineering Manager**
2. **Consider full outage response**
3. **Evaluate database restore from backup**
4. **Prepare customer communication**

Emergency Contact: +1-555-0123 (24/7 on-call line)

---

**Document Ownership:** SRE Team  
**Review Frequency:** After each rollback incident  
**Last Review:** October 17, 2025  
**Next Review:** November 17, 2025
