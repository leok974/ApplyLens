# Interventions Guide - Phase 5.4

**Operational guide for the ApplyLens interventions system.**

---

## Overview

The **interventions system** automatically detects, tracks, and remediates failures across the ApplyLens platform. It connects evaluation results, budget monitoring, and planner canaries to create actionable incidents with automated remediation.

### **What is an Incident?**

An incident is a tracked failure that requires human or automated intervention:

- **Invariant Failures**: Evaluation guardrails violated (data freshness, quality thresholds)
- **Budget Overruns**: Cost, latency, or quality budgets exceeded
- **Planner Regressions**: Canary deployments showing performance degradation

### **Incident Lifecycle**

```
┌──────┐     ┌────────────┐     ┌──────────┐     ┌──────────┐     ┌────────┐
│ Open │ --> │ Acknowledged │ --> │ Mitigated │ --> │ Resolved │ --> │ Closed │
└──────┘     └─────────────┘     └──────────┘     └──────────┘     └────────┘
   │                │                   │                │
   │ Watcher        │ On-call           │ Playbook       │ Verification
   │ detected       │ accepts           │ executed       │ confirms fix
```

---

## How It Works

### **1. Detection (Watcher)**

Background job runs every 15 minutes:

```python
# app/intervene/watcher.py
watcher = InvariantWatcher(db)

# Check recent eval results
incidents = watcher.check_invariants(lookback_minutes=60)

# Check budget status
incidents += watcher.check_budgets()

# Check planner canaries
incidents += watcher.check_planner_regressions()
```

**Triggers:**
- Eval runs fail invariants
- Budget thresholds exceeded
- Planner canary metrics degrade
- Gate evaluations fail (via bridge)

### **2. Incident Creation**

When failure detected:

1. **Deduplication**: Check if incident already open for same key
2. **Rate Limiting**: Max 3 incidents per key per hour
3. **Severity Assignment**: Map failure priority to SEV tier
4. **Playbook Suggestion**: Recommend remediation actions
5. **External Issue**: Auto-create GitHub/GitLab/Jira ticket
6. **SSE Notification**: Real-time alert to web UI

```python
# Example incident
{
  "id": 123,
  "kind": "invariant",
  "key": "INV_data_freshness_inbox",
  "severity": "sev1",
  "status": "open",
  "summary": "Data freshness violation for inbox.triage",
  "playbooks": ["rerun_eval", "rerun_dbt"],
  "issue_url": "https://github.com/org/repo/issues/456"
}
```

### **3. Notification**

Multiple notification channels:

- **Web UI**: Real-time SSE updates with browser notifications
- **External Issue**: GitHub/GitLab/Jira ticket with full context
- **Logs**: Structured logging for monitoring tools

### **4. Acknowledgment**

On-call engineer acknowledges incident:

```bash
# Via API
POST /api/incidents/123/acknowledge
{
  "acknowledged_by": "engineer@example.com",
  "notes": "Investigating root cause"
}
```

**Effect:**
- Status changes: `open` → `acknowledged`
- SSE event published: `incident_updated`
- SLA timer paused (implementation pending)

### **5. Remediation**

Execute playbook actions:

**Dry-Run First:**
```bash
POST /api/playbooks/incidents/123/actions/dry-run
{
  "action_type": "rerun_dbt",
  "params": {
    "models": ["inbox_emails", "triage_results"],
    "full_refresh": false
  }
}

# Response shows estimated impact
{
  "status": "dry_run_success",
  "estimated_duration": "10 minutes",
  "estimated_cost": "$0.10",
  "changes": [
    "Will re-run 2 dbt models",
    "Estimated 10 minutes execution time"
  ]
}
```

**Execute with Approval:**
```bash
POST /api/playbooks/incidents/123/actions/execute
{
  "action_type": "rerun_dbt",
  "params": {...},
  "approved_by": "engineer@example.com"  # Required if action needs approval
}
```

### **6. Verification**

After remediation:

1. **Monitor**: Watch for improvement in metrics
2. **Mitigate**: Mark incident as mitigated if issue contained
3. **Resolve**: Mark as resolved once fully fixed
4. **Close**: Archive after verification period

---

## Who Gets Paged?

### **Severity-Based Escalation**

| Severity | Response Time | Escalation | Page? |
|----------|--------------|------------|-------|
| **SEV1** | Immediate | On-call → Manager → Director | Yes (PagerDuty) |
| **SEV2** | 4 hours | On-call → Team channel | Yes (Slack alert) |
| **SEV3** | 24 hours | Team channel only | No (Slack notification) |
| **SEV4** | Best effort | Logged only | No |

### **On-Call Rotation**

**Current rotation** (configured in PagerDuty):
- Primary: Rotates weekly (Mon-Mon)
- Secondary: Backup escalation after 15 minutes
- Manager: Final escalation after 30 minutes

**Escalation flow:**
```
Incident created (SEV1/SEV2)
    │
    ├─> PagerDuty alert sent to Primary
    │   └─> If no ack in 15 min → Secondary
    │       └─> If no ack in 15 min → Manager
    │
    └─> Slack notification to #incidents
```

### **Incident Ownership**

**Who owns what:**
- **Inbox/Knowledge agents**: Data platform team
- **Insights agents**: Analytics team
- **Warehouse health**: Data infrastructure team
- **Planner canaries**: ML platform team
- **Budget violations**: Cost optimization team (SEV3/4 only)

---

## Incident Response Procedure

### **Step 1: Acknowledge (< 5 minutes)**

```bash
# 1. Check incident in web UI or Slack notification
# 2. Acknowledge via API or web UI
POST /api/incidents/{id}/acknowledge
{
  "acknowledged_by": "you@example.com",
  "notes": "Investigating"
}

# 3. Confirm external issue created
# Visit incident.issue_url for full context
```

### **Step 2: Assess (< 15 minutes)**

**Review incident details:**
- Check `details` field for root cause hints
- Review recent deployments/changes
- Check related metrics in monitoring dashboards
- Look for correlation with other incidents

**Determine severity:**
- Is this a true SEV1? (customer-impacting, urgent)
- Can we mitigate quickly? (yes → proceed, no → escalate)
- Is rollback safe? (check deployment history)

### **Step 3: Mitigate (< 30 minutes for SEV1)**

**Execute suggested playbook:**

1. **Dry-run first** (always):
   ```bash
   POST /api/playbooks/incidents/{id}/actions/dry-run
   ```

2. **Review changes**:
   - Check estimated duration/cost
   - Verify action scope (which models/indices/versions)
   - Confirm no unintended side effects

3. **Execute with approval**:
   ```bash
   POST /api/playbooks/incidents/{id}/actions/execute
   {
     "action_type": "...",
     "params": {...},
     "approved_by": "you@example.com"
   }
   ```

4. **Mark as mitigated**:
   ```bash
   POST /api/incidents/{id}/mitigate
   {
     "notes": "Executed rerun_dbt playbook, models rebuilt successfully"
   }
   ```

### **Step 4: Monitor (< 2 hours)**

**Watch for recovery:**
- Monitor eval results (next run should pass)
- Check metrics dashboards (latency/quality improving?)
- Verify external issue updated (comment added automatically)

**If not improving:**
- Consider escalating severity
- Try alternative playbook
- Engage subject matter expert (SME)

### **Step 5: Resolve (< 4 hours for SEV1)**

**Once verified fixed:**
```bash
POST /api/incidents/{id}/resolve
{
  "notes": "Root cause: stale dbt dependencies. Fix: refreshed packages. Verified: eval passed, quality back to 95+"
}
```

**Update external issue:**
- Comment with resolution summary
- Close GitHub/GitLab/Jira ticket

### **Step 6: Post-Mortem (SEV1 only)**

**Within 48 hours:**
- Write post-mortem document
- Identify root cause
- Document remediation steps
- Propose preventive measures
- Update runbooks if needed

---

## Common Scenarios

### **Scenario 1: Invariant Failure - Data Freshness**

**Incident:**
```
kind: invariant
key: INV_data_freshness_inbox
severity: sev1
summary: Data freshness violation for inbox.triage
details.invariant.threshold: 300 seconds
details.invariant.actual: 1800 seconds
```

**Response:**
1. Acknowledge immediately (customer-impacting)
2. Check dbt run logs (failure? timeout?)
3. Dry-run: `rerun_dbt` playbook
4. Execute: Re-run failed models
5. Monitor: Next eval should pass within 15 minutes

**Root causes:**
- DBT run failed (compilation error, dependency issue)
- Upstream data delayed (Fivetran sync stuck)
- Database connection timeout

### **Scenario 2: Budget Violation - Latency Spike**

**Incident:**
```
kind: budget
key: BUDGET_inbox.triage_latency_p95
severity: sev2
summary: P95 latency 1850ms exceeds budget 1000ms
details.violation.budget_type: latency_p95
details.current_metrics.p95_latency_ms: 1850
```

**Response:**
1. Acknowledge within 15 minutes
2. Check recent deployments (new code deployed?)
3. Dry-run: `clear_cache` playbook
4. Execute: Clear Elasticsearch query cache
5. Monitor: P95 should drop within 5 minutes

**Root causes:**
- Elasticsearch cache bloat
- Inefficient query added
- Database index missing
- Increased load (spike in traffic)

### **Scenario 3: Planner Regression - Accuracy Drop**

**Incident:**
```
kind: planner
key: PLANNER_REG_v1.2.3-canary
severity: sev1
summary: Planner regression: v1.2.3-canary accuracy
details.regression.metric: accuracy
details.regression.drop: 0.13
```

**Response:**
1. Acknowledge immediately (critical)
2. Review canary metrics dashboard
3. **DO NOT** execute rerun (won't help)
4. Dry-run: `rollback_planner` playbook
5. Execute: Rollback to stable version
6. Post-deployment: Investigate canary failure root cause

**Root causes:**
- Model training data issue
- Feature engineering bug
- Hyperparameter regression
- Dataset drift

---

## Escalation Paths

### **When to Escalate**

**Escalate to manager if:**
- Incident not mitigated within SLA (30 min for SEV1, 4h for SEV2)
- Playbooks ineffective (tried all suggestions, still failing)
- Severity unclear (could be SEV1 but seems contained)
- Multiple related incidents (systemic issue)
- External dependency failure (vendor API down)

**Escalate to director if:**
- Manager unavailable
- Incident impact > 50% of users
- Data loss risk identified
- Security concern suspected

### **How to Escalate**

**Via Slack:**
```
@manager Escalating incident #123 (SEV1)
Reason: Playbooks ineffective, quality still dropping
Actions tried: rerun_dbt, clear_cache, refresh_synonyms
Current status: Quality at 65% (threshold 85%)
Need: SME consult or rollback approval
```

**Via PagerDuty:**
- Re-assign incident to next escalation level
- Add notes with context
- Include tried remediation actions

---

## Runbook Links

For detailed remediation procedures, see:

- **[PLAYBOOKS.md](./PLAYBOOKS.md)**: Step-by-step action execution
- **[RUNBOOK_SEVERITY.md](./RUNBOOK_SEVERITY.md)**: Severity tiers and SLAs
- **[API_REFERENCE.md](./API_REFERENCE.md)**: REST API documentation

---

## Configuration

### **Enable Interventions**

```yaml
# config/settings.yaml
interventions:
  enabled: true
  watcher:
    interval_minutes: 15
    rate_limit_hours: 1
    max_incidents_per_window: 3
  issue_provider:
    provider: github  # or gitlab, jira
    config:
      token: ${GITHUB_TOKEN}
      owner: leok974
      repo: ApplyLens
```

### **Customize Budgets**

```python
# app/eval/budgets.py
DEFAULT_BUDGETS = {
    "inbox.triage": Budget(
        min_quality_score=85.0,
        max_avg_latency_ms=500.0,
        max_p95_latency_ms=1000.0,
        # Adjust thresholds as needed
    ),
}
```

### **Add Custom Playbooks**

```python
# app/intervene/actions/custom.py
@register_action
class CustomAction(AbstractAction):
    def execute(self):
        # Custom remediation logic
        pass
```

---

## Monitoring

### **Key Metrics**

Track in dashboards:
- **Incident rate**: Incidents created per hour
- **MTTR**: Mean time to resolution
- **SLA compliance**: % incidents resolved within SLA
- **Playbook success rate**: % actions that resolved incidents
- **False positive rate**: % incidents closed as not-a-bug

### **Alerts**

Set up alerts for:
- Incident rate spike (> 5 per hour)
- SLA breach (SEV1 open > 30 min)
- Watcher failure (no incidents checked in > 1 hour)
- Playbook failure rate (> 20%)

---

## Troubleshooting

### **Watcher Not Running**

```bash
# Check scheduler
ps aux | grep watcher

# Check logs
tail -f logs/watcher.log

# Restart manually
python -m app.intervene.watcher
```

### **Incident Not Created**

1. Check deduplication (incident already open?)
2. Check rate limit (3 per hour exceeded?)
3. Check watcher logs (error creating incident?)
4. Verify budget enabled (`enabled: true`)

### **External Issue Not Created**

1. Check adapter configured (`issue_provider` in config)
2. Verify credentials valid (API token works?)
3. Check adapter logs (HTTP error?)
4. Test adapter manually (`python -m app.intervene.adapters.github`)

### **SSE Not Working**

1. Check SSE router registered (`app.include_router(sse_router)`)
2. Verify EventSource connection (browser console)
3. Check firewall (SSE port open?)
4. Restart backend (in-memory publisher reset)

---

## Summary

**Interventions system provides:**

✅ **Automatic detection** of failures across platform  
✅ **Intelligent deduplication** and rate limiting  
✅ **Actionable incidents** with context and playbooks  
✅ **External issue tracking** for visibility  
✅ **Real-time notifications** via SSE and browser alerts  
✅ **Guided remediation** with dry-run and approval  
✅ **Clear escalation paths** for complex incidents  

**For operators**: Follow response procedures, execute playbooks, escalate when needed  
**For developers**: Add custom actions, tune budgets, improve playbooks  
**For managers**: Monitor SLAs, review post-mortems, allocate on-call resources
