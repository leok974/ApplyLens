# Policy Operations Runbook

**Emergency procedures and operational guidelines for ApplyLens Policy System**

This runbook provides step-by-step procedures for common operational tasks and emergency scenarios.

---

## Table of Contents

1. [Emergency Procedures](#emergency-procedures)
2. [Rollback Procedures](#rollback-procedures)
3. [Incident Response](#incident-response)
4. [Version Management](#version-management)
5. [Monitoring & Alerts](#monitoring--alerts)
6. [Troubleshooting](#troubleshooting)
7. [Post-Mortem Process](#post-mortem-process)

---

## Emergency Procedures

### EMERGENCY: Policy Causing Production Impact

**Severity**: P0 (Critical)  
**MTTR Target**: < 5 minutes

#### Symptoms
- High error rates (>10%)
- Mass denials of legitimate actions
- Budget explosion
- User complaints flooding support

#### Immediate Actions

**Step 1: Confirm Policy is the Root Cause** (30 seconds)
```bash
# Check recent policy activations
curl -H "Authorization: Bearer $TOKEN" \
  https://api.applylens.com/policy/bundles?active_only=true

# Check error rate spike correlation
curl https://api.applylens.com/metrics/errors?window=5m
```

**Step 2: Initiate Emergency Rollback** (60 seconds)
```bash
# Get active bundle ID
ACTIVE_BUNDLE_ID=$(curl -s ... | jq '.bundles[0].id')

# Rollback immediately
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Emergency rollback: high error rate affecting production",
    "rolled_back_by": "oncall-engineer",
    "create_incident": true
  }' \
  https://api.applylens.com/policy/bundles/$ACTIVE_BUNDLE_ID/rollback
```

**Step 3: Verify Rollback Success** (30 seconds)
```bash
# Confirm previous version is active at 100%
curl https://api.applylens.com/policy/bundles?active_only=true

# Check error rate recovery
curl https://api.applylens.com/metrics/errors?window=5m
```

**Step 4: Communicate Status** (60 seconds)
```bash
# Post to #incidents Slack channel
/incident update "Policy rolled back to v2.1.0. Monitoring recovery."

# Update status page if customer-facing
curl -X POST https://status.applylens.com/api/incidents/...
```

**Total Time**: ~3 minutes

---

### EMERGENCY: Rollback Not Working

**Severity**: P0 (Critical)  
**Escalation Required**

#### When to Use
- Rollback API returns error
- Previous version also has issues
- No previous version exists

#### Immediate Actions

**Step 1: Bypass Policy System** (90 seconds)
```bash
# Disable policy evaluation entirely (emergency override)
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Emergency-Override: true" \
  -d '{"enabled": false, "reason": "Emergency bypass"}' \
  https://api.applylens.com/policy/system/disable
```

**Step 2: Page SRE Lead** (immediate)
```bash
# Trigger PagerDuty escalation
pd trigger --service=policy-system --severity=critical \
  --description="Policy rollback failed, system disabled"
```

**Step 3: Manual Failover** (5 minutes)
```sql
-- Direct database update (use with extreme caution)
BEGIN;

-- Deactivate all bundles
UPDATE policy_bundles SET active = false, canary_pct = 0;

-- Reactivate last known good version (replace ID)
UPDATE policy_bundles 
SET active = true, canary_pct = 100 
WHERE version = '2.0.0';

COMMIT;
```

**Step 4: Incident Bridge** (immediate)
- Start Zoom bridge: `zoom-bridge-policy-emergency`
- Invite: SRE lead, policy team lead, eng manager
- Update: Every 5 minutes until resolved

---

## Rollback Procedures

### Standard Rollback (Non-Emergency)

**Use When**: Canary quality gates fail, but not user-facing yet

#### Prerequisites
- Current bundle in canary phase (10% or 50%)
- Monitoring shows degradation
- Previous version exists and was stable

#### Procedure

**Step 1: Assess Impact** (5 minutes)
```bash
# Check canary metrics
curl https://api.applylens.com/policy/bundles/{id}/canary-status

# Review affected decisions
curl https://api.applylens.com/policy/decisions?bundle_id={id}&status=error
```

**Step 2: Create Rollback Ticket** (2 minutes)
- **Title**: `Policy Rollback: v{new} → v{old}`
- **Reason**: Detailed explanation with metrics
- **Impact**: Number of affected decisions
- **Approvers**: Policy team lead + on-call SRE

**Step 3: Execute Rollback** (2 minutes)
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "reason": "Error rate 7.2% exceeds 5% threshold during canary. See ticket POL-2024-123.",
    "rolled_back_by": "alice",
    "create_incident": true
  }' \
  https://api.applylens.com/policy/bundles/{id}/rollback
```

**Step 4: Verify and Monitor** (10 minutes)
```bash
# Confirm rollback
curl https://api.applylens.com/policy/bundles?active_only=true

# Monitor for 10 minutes
watch -n 30 'curl https://api.applylens.com/metrics/errors?window=5m'
```

**Step 5: Post-Mortem** (within 24h)
- Create post-mortem doc
- Analyze root cause
- Document learnings
- Update policy testing procedures

---

### Auto-Rollback Scenarios

The system automatically rolls back when:

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Error rate spike | >10% (2x normal) | Immediate rollback |
| Deny rate spike | >50% | Immediate rollback |
| Cost explosion | +50% vs baseline | Rollback + budget alert |
| Zero matches | >20% no-match rate | Rollback + alert |

**Auto-Rollback Creates**:
- HIGH severity incident (INC-YYYY-XXXX)
- Slack notification to #policy-alerts
- PagerDuty event (non-urgent)
- Rollback metadata in database

**Your Responsibilities After Auto-Rollback**:
1. Acknowledge incident within 15 minutes
2. Investigate root cause within 1 hour
3. Fix in draft bundle
4. Re-simulate with enhanced test cases
5. Re-deploy with extra monitoring

---

## Incident Response

### Policy-Related Incident Mapping

**How incidents trigger policy actions:**

```
Phase 5.4 Incident → Policy Rollback
├─ Severity: HIGH or CRITICAL
├─ Source: policy.activate
├─ Action: rollback
└─ Auto-creates: Rollback with incident ID
```

#### Incident-Triggered Rollback Flow

```mermaid
Incident Created (HIGH)
    ↓
Policy System Checks Active Bundle
    ↓
Is bundle <24h old? → YES → Auto-Rollback
                   → NO → Page On-Call (manual decision)
    ↓
Rollback Executed
    ↓
Incident Updated with Rollback Details
    ↓
Monitor Recovery (15 min)
```

#### Response Checklist

- [ ] Incident severity = HIGH or CRITICAL?
- [ ] Related to policy decisions? (check `agent` field)
- [ ] Active bundle age < 24 hours?
- [ ] Error rate > 5%?
- [ ] **Decision**: Rollback or investigate first?

**Rollback Decision Matrix**:

| Age | Error Rate | Decision |
|-----|------------|----------|
| <2h | >5% | ROLLBACK immediately |
| 2-12h | >10% | ROLLBACK immediately |
| 12-24h | >15% | ROLLBACK immediately |
| >24h | >20% | Investigate first (may be unrelated) |

---

## Version Management

### Semantic Versioning Guidelines

**MAJOR (X.0.0)**: Breaking changes
- Complete rewrite of policy logic
- Incompatible rule format changes
- Agent/action schema changes

**MINOR (1.X.0)**: Additive changes
- New rules added
- New agents or actions supported
- Feature additions (e.g., new conditions)

**PATCH (1.1.X)**: Fixes
- Bug fixes in existing rules
- Typo corrections
- Priority adjustments
- Threshold tuning

#### Examples

```
2.1.3 → 2.1.4: Fixed typo in inbox rule reason
2.1.4 → 2.2.0: Added new knowledge.search rules
2.2.0 → 3.0.0: Migrated to new rule schema format
```

### Version Lifecycle

```
Draft → (Approval) → Canary 10% → (24h) → Canary 50% → (24h) → Active 100%
                         ↓                      ↓                    ↓
                    [Rollback]            [Rollback]            [Rollback]
```

**Draft**: 
- Can edit freely
- Cannot be activated without approval
- No traffic

**Canary 10%**:
- Immutable (cannot edit)
- Receives 10% of decisions
- Quality gates monitored
- 24h minimum before promotion

**Canary 50%**:
- Receives 50% of decisions
- Quality gates must still pass
- 24h minimum before full promotion

**Active 100%**:
- All traffic
- Immutable
- Can only be rolled back (deactivated)

**Archived**:
- Rolled back or superseded
- Read-only
- Retained for audit trail

### Version Hygiene

**DO**:
✅ Always increment version on changes  
✅ Use descriptive notes explaining changes  
✅ Tag versions with release info  
✅ Keep at least 3 historical versions  

**DON'T**:
❌ Reuse version numbers  
❌ Skip versions (e.g., 2.1.0 → 2.3.0)  
❌ Edit active bundles directly  
❌ Delete versions (archive instead)  

---

## Monitoring & Alerts

### Key Metrics Dashboard

**Grafana Dashboard**: `Policy System Health`

**Panels**:
1. **Active Bundle**: Version, canary %, time active
2. **Decision Rate**: Decisions/min over time
3. **Error Rate**: % of decisions resulting in errors
4. **Effect Distribution**: Allow/Deny/Approval breakdown
5. **Budget**: Cost/compute spend vs limits
6. **Quality Gates**: All 4 gates with pass/fail status

### Alert Rules

**Critical Alerts** (PagerDuty):
```yaml
- alert: PolicyErrorRateHigh
  expr: policy_error_rate_5m > 0.10
  for: 2m
  annotations:
    summary: "Policy error rate >10% for 2+ minutes"
    runbook: "Execute emergency rollback procedure"

- alert: PolicyRollbackFailed
  expr: policy_rollback_failures > 0
  for: 0m
  annotations:
    summary: "Policy rollback failed - immediate escalation required"
    runbook: "Bypass policy system, page SRE lead"
```

**Warning Alerts** (Slack #policy-alerts):
```yaml
- alert: PolicyCanaryGateFailing
  expr: policy_canary_gate_passed == 0
  for: 5m
  annotations:
    summary: "Canary quality gate failing"
    runbook: "Review metrics, consider rollback"

- alert: PolicyBudgetHigh
  expr: policy_cost_24h > policy_cost_budget * 0.8
  for: 0m
  annotations:
    summary: "Policy cost at 80% of daily budget"
    runbook: "Review expensive operations, adjust rules"
```

### Slack Notifications

**Channels**:
- `#policy-alerts`: All alerts (warning+)
- `#policy-changes`: Activations, promotions, rollbacks
- `#incidents`: Critical issues only

**Notification Format**:
```
🚨 [POLICY ALERT] Error Rate High
Bundle: v2.2.0 (Canary 10%)
Error Rate: 12.3% (threshold: 10%)
Duration: 3 minutes
Action: Auto-rollback initiated
Runbook: https://docs.applylens.com/runbooks/policy#emergency-rollback
```

---

## Troubleshooting

### Issue: Canary Won't Promote

**Symptoms**: Canary at 10% for >24h, promotion button disabled

**Diagnosis**:
```bash
# Check quality gates
curl https://api.applylens.com/policy/bundles/{id}/check-gates \
  -d '{"metrics": {...}}'

# Review gate status
curl https://api.applylens.com/policy/bundles/{id}/canary-status
```

**Common Causes**:
1. **Insufficient samples**: Need 100+ decisions
   - **Fix**: Wait for more traffic or lower `min_sample_size`
   
2. **Error rate too high**: >5%
   - **Fix**: Investigate errors, fix in new version
   
3. **Deny rate too high**: >30%
   - **Fix**: Review overly restrictive rules
   
4. **Cost increase**: >20%
   - **Fix**: Optimize budget or adjust threshold

---

### Issue: Policy Not Taking Effect

**Symptoms**: Rules don't seem to apply to decisions

**Diagnosis**:
```bash
# Check active bundle
curl https://api.applylens.com/policy/bundles?active_only=true

# Test specific decision
curl -X POST https://api.applylens.com/policy/evaluate \
  -d '{
    "agent": "inbox.triage",
    "action": "quarantine",
    "context": {"risk_score": 90}
  }'
```

**Common Causes**:
1. **Bundle not activated**: Still in draft
   - **Fix**: Activate with approval
   
2. **Canary percentage too low**: Only 10% of traffic
   - **Fix**: Promote to 50% or 100%
   
3. **Rule priority issues**: Lower-priority rule shadowed
   - **Fix**: Review lint warnings for unreachable rules
   
4. **Condition mismatch**: Conditions don't match context
   - **Fix**: Test with simulation, adjust conditions

---

### Issue: Import Failed

**Symptoms**: Bundle import returns 400 error

**Diagnosis**:
```bash
# Check signature validity
curl -X POST https://api.applylens.com/policy/bundles/verify \
  -d @exported-bundle.json

# Check version conflict
curl https://api.applylens.com/policy/bundles?version={version}
```

**Common Causes**:
1. **Signature expired**: >24h since export
   - **Fix**: Re-export with fresh signature
   
2. **Invalid signature**: Tampered or wrong secret
   - **Fix**: Verify HMAC_SECRET matches across environments
   
3. **Version exists**: Duplicate version number
   - **Fix**: Use `import_as_version` parameter to rename

---

## Post-Mortem Process

### When to Write Post-Mortem

**Required**:
- Emergency rollback
- User-facing impact
- Budget overrun >$1000
- P0/P1 incidents

**Optional**:
- Canary rollback (non-emergency)
- Interesting edge cases
- Process improvements

### Post-Mortem Template

```markdown
# Policy Post-Mortem: [Title]

**Date**: 2024-01-15
**Author**: alice@company.com
**Reviewers**: bob@company.com, charlie@company.com

## Summary
[2-3 sentence summary of what happened]

## Timeline (UTC)
- 14:23: Bundle v2.2.0 activated at 10% canary
- 14:35: Error rate spike to 8.2% detected
- 14:37: On-call engineer paged
- 14:40: Manual rollback initiated to v2.1.0
- 14:42: Error rate returned to baseline (1.5%)
- 14:45: Incident closed

## Impact
- **Duration**: 19 minutes (14:23 - 14:42)
- **Canary Traffic**: 10% of production
- **Failed Decisions**: ~450 errors
- **User Impact**: None (canary contained)
- **Cost**: $12 wasted on failed operations

## Root Cause
[Detailed explanation of what went wrong]

## What Went Well
- [Positive aspects of response]

## What Went Wrong
- [Problems during incident]

## Action Items
- [ ] [Owner] [Action] [Due Date]
- [ ] alice: Add test case for edge condition - Jan 20
- [ ] bob: Update linter to catch this pattern - Jan 25
- [ ] charlie: Add monitoring for this metric - Jan 30

## Lessons Learned
[Key takeaways for future reference]

## Related Incidents
- INC-2024-0042: Similar error pattern
- INC-2023-0901: Previous rollback
```

### Post-Mortem Review Meeting

**Attendees**:
- Incident owner
- On-call engineer
- Policy team lead
- Affected team representatives

**Agenda** (30 minutes):
1. Timeline review (5 min)
2. Root cause discussion (10 min)
3. What went well/wrong (5 min)
4. Action items assignment (5 min)
5. Q&A (5 min)

**Outcomes**:
- Published post-mortem doc
- Action items in Jira
- Updated runbook if needed
- Knowledge shared in eng all-hands

---

## Contacts

### Escalation Path

1. **On-Call Engineer** (first responder)
   - PagerDuty: `policy-system-oncall`
   - Slack: `@oncall-policy`

2. **Policy Team Lead** (subject matter expert)
   - Slack: `@policy-lead`
   - Email: policy-team@company.com

3. **SRE Lead** (infrastructure escalation)
   - PagerDuty: `sre-lead`
   - Slack: `@sre-lead`

4. **VP Engineering** (executive escalation)
   - Phone: [redacted]
   - Only for P0 lasting >1 hour

### Team Channels

- **#policy-help**: General questions
- **#policy-alerts**: Automated alerts
- **#policy-changes**: Deployment notifications
- **#incidents**: Active incident coordination

---

## Appendix: Quick Reference

### Emergency Commands

```bash
# Rollback current bundle
curl -X POST /policy/bundles/{id}/rollback \
  -d '{"reason": "Emergency", "rolled_back_by": "oncall"}'

# Disable policy system
curl -X POST /policy/system/disable \
  -H "X-Emergency-Override: true"

# Check active bundle
curl /policy/bundles?active_only=true

# Get canary status
curl /policy/bundles/{id}/canary-status
```

### Decision Matrix

| Scenario | Action | MTTR Target |
|----------|--------|-------------|
| Error rate >10% | Emergency rollback | 5 min |
| Canary gate fail | Standard rollback | 15 min |
| Budget alert | Review + adjust rules | 1 hour |
| Lint errors | Fix in draft | N/A |
| Import fail | Check signature | 10 min |

### Links

- **Grafana**: https://grafana.applylens.com/d/policy
- **PagerDuty**: https://company.pagerduty.com/services/policy
- **Docs**: https://docs.applylens.com/policy-studio
- **Status Page**: https://status.applylens.com
