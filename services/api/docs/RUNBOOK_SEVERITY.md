# Severity Tiers & SLAs - Phase 5.4

**Incident severity classification and service level agreements.**

---

## Severity Tiers

### **SEV1: Critical**

**Definition:** Production outage or severe degradation affecting users.

**Examples:**
- Data freshness > 30 minutes (stale data shown to users)
- Quality score < 70% (unreliable predictions)
- Error rate > 10% (frequent failures)
- Planner accuracy < 80% (bad recommendations)
- Security vulnerability detected

**Impact:**
- Multiple users affected
- Core functionality broken
- Data accuracy severely degraded
- Financial loss or reputational damage

**Response:**
- **Acknowledgment:** < 5 minutes
- **Mitigation:** < 30 minutes
- **Resolution:** < 4 hours
- **Page:** Yes (PagerDuty immediate)

**Escalation:**
- Primary on-call → Secondary (15 min) → Manager (30 min)

**Post-mortem:** Required within 48 hours

---

### **SEV2: High**

**Definition:** Significant issue with workaround available.

**Examples:**
- Budget exceeded (latency/cost over threshold)
- Data freshness 5-30 minutes
- Quality score 70-85% (degraded but usable)
- Canary metrics worse than stable (not deployed to prod)
- Non-critical API failure

**Impact:**
- Some users affected
- Degraded performance
- Workaround exists
- Limited feature unavailable

**Response:**
- **Acknowledgment:** < 15 minutes
- **Mitigation:** < 4 hours
- **Resolution:** < 24 hours
- **Page:** Yes (Slack alert with @channel)

**Escalation:**
- Primary on-call → Team channel (1 hour) → Manager (4 hours)

**Post-mortem:** Optional (at team's discretion)

---

### **SEV3: Medium**

**Definition:** Minor issue with minimal user impact.

**Examples:**
- Budget warning (approaching threshold)
- Data freshness < 5 minutes
- Quality score 85-90% (slightly below target)
- P99 latency spike (P95 still OK)
- Monitoring alert firing

**Impact:**
- Few users affected
- Minor degradation
- No workaround needed (self-resolving)
- Internal tooling issue

**Response:**
- **Acknowledgment:** < 1 hour
- **Mitigation:** < 24 hours
- **Resolution:** < 1 week
- **Page:** No (Slack notification only)

**Escalation:**
- Team channel → On-call (24 hours) → Manager (1 week)

**Post-mortem:** Not required

---

### **SEV4: Low**

**Definition:** Cosmetic issue or enhancement request.

**Examples:**
- Cost optimization opportunity
- Non-critical metric slightly off
- Documentation outdated
- Nice-to-have feature request
- Tech debt cleanup

**Impact:**
- No user impact
- Internal inefficiency
- Proactive improvement

**Response:**
- **Acknowledgment:** Best effort
- **Mitigation:** Not applicable
- **Resolution:** Backlog prioritization
- **Page:** No (logged only)

**Escalation:**
- Not applicable

**Post-mortem:** Not applicable

---

## SLA Summary Table

| Severity | Ack | Mitigate | Resolve | Page | Post-Mortem |
|----------|-----|----------|---------|------|-------------|
| **SEV1** | 5 min | 30 min | 4 hours | Yes (PagerDuty) | Required |
| **SEV2** | 15 min | 4 hours | 24 hours | Yes (Slack @channel) | Optional |
| **SEV3** | 1 hour | 24 hours | 1 week | No (Slack notification) | No |
| **SEV4** | Best effort | N/A | Backlog | No | No |

---

## Severity Assignment

### **Automatic Assignment**

Incidents are automatically assigned severity based on:

**Invariant Failures:**
```python
priority = invariant.priority  # "critical", "high", "medium", "low"

if priority == "critical":
    severity = "sev1"
elif priority == "high":
    severity = "sev2"
elif priority == "medium":
    severity = "sev3"
else:
    severity = "sev4"
```

**Budget Violations:**
```python
violation_severity = budget_violation.severity  # "critical", "error", "warning"

if violation_severity == "critical":
    severity = "sev1"
elif violation_severity == "error":
    severity = "sev2"
else:
    severity = "sev3"
```

**Planner Regressions:**
```python
if regression.metric == "accuracy":
    severity = "sev1"  # Accuracy is critical
else:
    severity = "sev2"  # Latency/cost less critical
```

### **Manual Override**

On-call can upgrade/downgrade severity:

```bash
POST /api/incidents/{id}
{
  "severity": "sev1",  # Upgraded from sev2
  "notes": "Customer reports widespread impact, upgrading to SEV1"
}
```

**Guidelines for override:**
- Upgrade if user impact worse than estimated
- Downgrade if workaround effective
- Document reason in notes
- Notify team in Slack

---

## Escalation Matrix

### **SEV1 Escalation**

```
00:00 - Incident created, page primary on-call
00:05 - Primary acknowledges (SLA: 5 min)
00:15 - If not acknowledged, page secondary
00:30 - If not mitigated, escalate to manager
01:00 - If not mitigated, escalate to director
04:00 - Resolution SLA deadline
```

**Escalation triggers:**
- No acknowledgment in 5 minutes
- No mitigation in 30 minutes
- Multiple playbooks failed
- External dependency issue

### **SEV2 Escalation**

```
00:00 - Incident created, Slack alert to #incidents
00:15 - Primary acknowledges (SLA: 15 min)
01:00 - If not acknowledged, @mention in Slack
04:00 - If not mitigated, escalate to manager
24:00 - Resolution SLA deadline
```

**Escalation triggers:**
- No acknowledgment in 1 hour
- No mitigation in 4 hours
- Severity unclear (could be SEV1)

### **SEV3 Escalation**

```
00:00 - Incident created, Slack notification to #incidents
01:00 - Primary acknowledges (SLA: 1 hour)
24:00 - If not acknowledged, assign to on-call rotation
168:00 - Resolution SLA deadline (1 week)
```

**Escalation triggers:**
- No activity in 24 hours
- Recurring issue (3+ times per week)

---

## Severity Examples by Component

### **Inbox Agent**

| Incident | Severity | Reason |
|----------|----------|--------|
| Data freshness > 30 min | SEV1 | Users see stale emails, can't triage properly |
| Data freshness 5-30 min | SEV2 | Degraded but usable |
| Quality score < 70% | SEV1 | Triage predictions unreliable |
| Quality score 70-85% | SEV2 | Acceptable with monitoring |
| Latency P95 > 2 sec | SEV2 | Slow but functional |
| Latency P99 > 5 sec | SEV3 | Affects few users |

### **Knowledge Agent**

| Incident | Severity | Reason |
|----------|----------|--------|
| Index missing | SEV1 | Knowledge base unavailable |
| Synonym file corrupt | SEV2 | Search degraded, workaround exists |
| Cache hit rate < 50% | SEV3 | Performance impact minimal |
| Embedding drift detected | SEV2 | Relevance declining |

### **Planner**

| Incident | Severity | Reason |
|----------|----------|--------|
| Canary accuracy < 80% | SEV1 | Bad recommendations to users |
| Canary latency +100% | SEV2 | Not in prod yet, can rollback |
| Canary cost +50% | SEV3 | Budget concern, not urgent |
| Stable version error rate > 5% | SEV1 | Production issue |

### **Warehouse**

| Incident | Severity | Reason |
|----------|----------|--------|
| DBT run failed | SEV1 | All downstream deps broken |
| Single model failed | SEV2 | Isolated impact |
| Test failure | SEV3 | Data quality warning |
| Documentation stale | SEV4 | Internal only |

---

## Response Time Tracking

### **How SLAs are Measured**

**Acknowledgment time:**
```
incident.acknowledged_at - incident.created_at
```

**Mitigation time:**
```
incident.mitigated_at - incident.created_at
```

**Resolution time:**
```
incident.resolved_at - incident.created_at
```

### **SLA Compliance Reporting**

Weekly report includes:
- % incidents acknowledged within SLA
- % incidents mitigated within SLA
- % incidents resolved within SLA
- Mean time to resolution (MTTR) by severity
- Top contributors to SLA breaches

**Dashboard:** https://monitoring.applylens.com/incidents

---

## On-Call Responsibilities

### **Primary On-Call**

**Duties:**
- Monitor #incidents Slack channel
- Acknowledge SEV1/SEV2 within SLA
- Execute playbooks for mitigation
- Escalate if stuck
- Document actions in incident notes

**Hours:**
- 24/7 coverage (1 week rotation)
- Handoff: Monday 9am PT

**Compensation:**
- On-call stipend: $500/week
- Incident response time: Credited as overtime

### **Secondary On-Call**

**Duties:**
- Backup for primary (15-min delay)
- Review non-urgent incidents (SEV3/SEV4)
- Post-mortem reviews

**Hours:**
- Business hours only (M-F 9am-5pm PT)
- Rotation: 1 week

### **Manager Escalation**

**Duties:**
- Approve high-risk actions (immediate rollbacks)
- Coordinate cross-team efforts
- Communicate with leadership
- Own post-mortem process

**Hours:**
- On-demand (paged as needed)

---

## Post-Mortem Process

### **When Required**

- All SEV1 incidents
- SEV2 incidents with customer impact
- Recurring issues (3+ in a month)
- SLA breaches

### **Template**

```markdown
# Post-Mortem: [Incident Summary]

**Incident ID:** 123
**Severity:** SEV1
**Date:** 2025-10-17
**Duration:** 2 hours 15 minutes
**Author:** engineer@example.com

## Summary

One-paragraph summary of incident, impact, and resolution.

## Timeline

- **10:00 AM**: Incident detected (watcher)
- **10:05 AM**: Acknowledged by on-call
- **10:15 AM**: Dry-run rerun_dbt playbook
- **10:20 AM**: Executed rerun_dbt (full_refresh=true)
- **10:35 AM**: Models rebuilt, quality recovering
- **11:00 AM**: Eval passed, quality at 95%
- **12:15 PM**: Incident resolved

## Root Cause

DBT packages outdated, causing compilation errors in models. Scheduled package refresh job failed silently 3 days ago.

## Impact

- **Users affected**: ~500 (inbox triage users)
- **Data staleness**: 1 hour 45 minutes
- **Quality degradation**: 95% → 68%
- **Financial impact**: $0 (no refunds)

## Resolution

1. Refreshed DBT dependencies (`dbt deps`)
2. Re-ran models with full refresh
3. Verified quality recovered

## Action Items

- [ ] Fix scheduled package refresh job (owner: @data-team, due: 2025-10-20)
- [ ] Add alerting for silent job failures (owner: @infra-team, due: 2025-10-25)
- [ ] Update runbook with dependency refresh steps (owner: @on-call, due: 2025-10-18)

## Lessons Learned

- Silent failures hard to detect (need better monitoring)
- Full refresh took longer than expected (15 min vs 10 min est)
- Dry-run preview was accurate

## Related Incidents

- Incident #118 (2025-10-10): Similar dbt dependency issue
```

### **Post-Mortem Review**

- Share in #incidents channel
- Discuss in weekly team meeting
- Archive in docs/post-mortems/
- Track action items in Jira

---

## SLA Breach Handling

### **When SLA Breached**

1. **Document reason** in incident notes
2. **Escalate immediately** if not already done
3. **Notify manager** via Slack
4. **Include in post-mortem** (required for breaches)

### **Common Breach Reasons**

- Multiple playbooks failed (tried 3+ actions)
- External dependency timeout (vendor API down)
- On-call delayed (personal emergency)
- Severity misclassified (upgraded mid-incident)

### **Acceptable Excuses**

- Vendor outage (AWS/GCP down)
- Major infrastructure failure
- Force majeure (natural disaster)

### **Not Acceptable**

- Forgot to check Slack
- Didn't know how to fix
- Waited for approval too long
- Assumed someone else would handle

---

## Summary

**Key points:**

✅ **SEV1**: Critical, 5/30 min/4 hr SLAs, page on-call  
✅ **SEV2**: High, 15 min/4 hr/24 hr SLAs, Slack alert  
✅ **SEV3**: Medium, 1 hr/24 hr/1 week SLAs, notification only  
✅ **SEV4**: Low, best effort, no SLA  

✅ **Escalate** if not mitigated within SLA  
✅ **Document** all actions in incident notes  
✅ **Post-mortem** required for SEV1 and SLA breaches  
✅ **Track SLA compliance** in weekly reports  

**For incident response procedures, see [INTERVENTIONS_GUIDE.md](./INTERVENTIONS_GUIDE.md)**  
**For remediation steps, see [PLAYBOOKS.md](./PLAYBOOKS.md)**
