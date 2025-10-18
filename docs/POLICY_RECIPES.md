# Policy Recipes - Common Patterns

**Pre-built policy patterns for ApplyLens agentic system**

This guide provides tested policy patterns for common use cases. Copy and adapt these recipes for your needs.

---

## Table of Contents

1. [Inbox Triage](#inbox-triage)
2. [Knowledge Management](#knowledge-management)
3. [Deployment Safety](#deployment-safety)
4. [Budget Controls](#budget-controls)
5. [Business Hours Gating](#business-hours-gating)
6. [Risk-Based Approval](#risk-based-approval)
7. [Category Exceptions](#category-exceptions)

---

## Inbox Triage

### Recipe 1: Quarantine High-Risk Emails

**Use Case**: Automatically quarantine emails with high phishing risk

```json
{
  "id": "inbox-quarantine-high-risk",
  "agent": "inbox.triage",
  "action": "quarantine",
  "effect": "allow",
  "conditions": {
    "risk_score>=": 85,
    "category": "phishing"
  },
  "reason": "Automatically quarantine high-risk phishing emails to protect users",
  "priority": 100,
  "enabled": true,
  "budget": {
    "cost": 0.05,
    "compute": 2,
    "risk": "low"
  },
  "tags": ["security", "phishing", "auto"]
}
```

**When to use**:
- Production environments with active phishing threats
- After training AI on phishing corpus
- When risk scores are calibrated (>80% precision)

**Variations**:
- Lower threshold to 75 for stricter protection
- Add `domain_seen_days<: 30` for new domains
- Add `has_attachments==: true` for suspicious files

---

### Recipe 2: Escalate Suspicious with Manual Review

**Use Case**: Flag medium-risk emails for human review

```json
{
  "id": "inbox-escalate-medium-risk",
  "agent": "inbox.triage",
  "action": "escalate",
  "effect": "needs_approval",
  "conditions": {
    "risk_score>=": 60,
    "risk_score<": 85,
    "sender_reputation<": 0.5
  },
  "reason": "Escalate medium-risk emails with low sender reputation for manual review",
  "priority": 90,
  "enabled": true,
  "budget": {
    "cost": 0.10,
    "compute": 5,
    "risk": "medium"
  },
  "tags": ["security", "manual-review"]
}
```

**When to use**:
- When you want human-in-the-loop for uncertain cases
- Testing new risk models before auto-quarantine
- High-value accounts requiring extra caution

---

### Recipe 3: Allow Trusted Senders

**Use Case**: Whitelist known-good senders

```json
{
  "id": "inbox-allow-trusted",
  "agent": "inbox.triage",
  "action": "allow",
  "effect": "allow",
  "conditions": {
    "sender_domain": "@company.com",
    "dkim_valid==": true
  },
  "reason": "Allow all emails from verified company domain",
  "priority": 200,
  "enabled": true,
  "budget": {
    "cost": 0.01,
    "compute": 1,
    "risk": "low"
  },
  "tags": ["whitelist", "trusted"]
}
```

**When to use**:
- Internal company communications
- Trusted partner domains
- Bypass risk scoring for known-good sources

**Variations**:
- Add multiple trusted domains: `"sender_domain": "@partner1.com|@partner2.com"`
- Require SPF+DKIM: `"spf_pass==": true, "dkim_valid==": true`
- Time-limited: Add `"received_hour>=": 8, "received_hour<": 18` for business hours only

---

## Knowledge Management

### Recipe 4: Auto-Approve Small Reindex

**Use Case**: Allow small reindex operations without approval

```json
{
  "id": "knowledge-small-reindex-auto",
  "agent": "knowledge.search",
  "action": "reindex",
  "effect": "allow",
  "conditions": {
    "size_gb<": 10,
    "doc_count<": 100000,
    "estimated_cost<": 5.0
  },
  "reason": "Automatically approve small reindex operations under $5 to reduce approval burden",
  "priority": 100,
  "enabled": true,
  "budget": {
    "cost": 5.0,
    "compute": 50,
    "risk": "low"
  },
  "tags": ["knowledge", "auto-approve", "efficiency"]
}
```

**When to use**:
- Frequent small updates to knowledge base
- Development/staging environments
- Trusted teams with good hygiene

**Variations**:
- Tighten limits: `size_gb<: 5, estimated_cost<: 2.0`
- Business hours only: Add `"current_hour>=": 8, "current_hour<": 18`
- Require dry-run first: Add `"dry_run_completed==": true`

---

### Recipe 5: Require Approval for Large Operations

**Use Case**: Mandate manual review for expensive reindex

```json
{
  "id": "knowledge-large-reindex-approval",
  "agent": "knowledge.search",
  "action": "reindex",
  "effect": "needs_approval",
  "conditions": {
    "size_gb>=": 50,
    "estimated_cost>=": 25.0
  },
  "reason": "Large reindex operations (>50GB, >$25) require approval to prevent budget overruns",
  "priority": 90,
  "enabled": true,
  "budget": {
    "cost": 100.0,
    "compute": 500,
    "risk": "high"
  },
  "tags": ["knowledge", "approval-required", "budget"]
}
```

**When to use**:
- Production environments with budget constraints
- After incidents involving runaway costs
- When multiple teams share infrastructure

---

### Recipe 6: Block Deletions in Production

**Use Case**: Prevent accidental data loss

```json
{
  "id": "knowledge-block-delete-prod",
  "agent": "knowledge.search",
  "action": "delete",
  "effect": "deny",
  "conditions": {
    "environment": "production",
    "soft_delete==": false
  },
  "reason": "Block hard deletes in production to prevent data loss; use soft delete instead",
  "priority": 200,
  "enabled": true,
  "budget": {
    "cost": 0,
    "compute": 0,
    "risk": "high"
  },
  "tags": ["knowledge", "safety", "data-protection"]
}
```

**When to use**:
- Production databases with critical data
- Compliance requirements (retain data for N years)
- After data loss incidents

**Variations**:
- Allow with approval: Change `"effect": "deny"` to `"effect": "needs_approval"`
- Require reason: Add `"deletion_reason!=": ""`
- Audit log: Tag with `"audit==": true`

---

## Deployment Safety

### Recipe 7: Canary Deploys Only

**Use Case**: Require canary rollout for all deployments

```json
{
  "id": "planner-canary-required",
  "agent": "planner.deploy",
  "action": "deploy",
  "effect": "needs_approval",
  "conditions": {
    "canary_enabled==": false,
    "environment": "production"
  },
  "reason": "All production deploys must use canary rollout to minimize blast radius",
  "priority": 200,
  "enabled": true,
  "budget": {
    "cost": 10.0,
    "compute": 100,
    "risk": "high"
  },
  "tags": ["deployment", "safety", "canary"]
}
```

**When to use**:
- Production services with user traffic
- After deployment incidents
- When adopting progressive delivery

---

### Recipe 8: Allow Emergency Rollbacks

**Use Case**: Fast-path rollbacks without approval

```json
{
  "id": "planner-emergency-rollback",
  "agent": "planner.deploy",
  "action": "rollback",
  "effect": "allow",
  "conditions": {
    "severity": "critical",
    "incident_active==": true
  },
  "reason": "Allow immediate rollback during active critical incidents",
  "priority": 300,
  "enabled": true,
  "budget": {
    "cost": 5.0,
    "compute": 50,
    "risk": "medium"
  },
  "tags": ["deployment", "emergency", "rollback"]
}
```

**When to use**:
- Active incident response
- Mean time to recovery (MTTR) optimization
- On-call runbooks

**Variations**:
- Require incident: `"incident_id!=": ""`
- Time limit: Add `"incident_age_minutes<": 30`
- Notify Slack: Add `"notify_slack==": true`

---

### Recipe 9: Block Off-Hours Deploys

**Use Case**: Restrict deploys to business hours

```json
{
  "id": "planner-business-hours-only",
  "agent": "planner.deploy",
  "action": "deploy",
  "effect": "deny",
  "conditions": {
    "current_hour<": 8,
    "current_hour>=": 18,
    "environment": "production",
    "override_approved==": false
  },
  "reason": "Block production deploys outside business hours (8am-6pm) unless pre-approved",
  "priority": 150,
  "enabled": true,
  "budget": {
    "cost": 0,
    "compute": 0,
    "risk": "low"
  },
  "tags": ["deployment", "business-hours", "safety"]
}
```

**When to use**:
- Teams without 24/7 on-call coverage
- Reducing weekend incidents
- Coordinating with support availability

**Variations**:
- Weekend block: Add `"day_of_week": "Saturday|Sunday"`
- Holiday block: Add `"is_holiday==": true`
- Exception for hotfixes: Add `"is_hotfix==": true` to conditions with `!=` operator

---

## Budget Controls

### Recipe 10: Cost Thresholds

**Use Case**: Approve anything over $100

```json
{
  "id": "budget-high-cost-approval",
  "agent": "*",
  "action": "*",
  "effect": "needs_approval",
  "conditions": {
    "estimated_cost>=": 100.0
  },
  "reason": "Require approval for any action estimated to cost over $100",
  "priority": 50,
  "enabled": true,
  "budget": {
    "cost": 100.0,
    "compute": 1000,
    "risk": "high"
  },
  "tags": ["budget", "cost-control", "approval"]
}
```

**When to use**:
- Strict budget controls
- Preventing cost surprises
- Multi-tenant environments

**Variations**:
- Tiered thresholds: Create multiple rules at $50, $100, $500
- Per-agent limits: Replace `"agent": "*"` with specific agent
- Daily budget: Add `"daily_spend>=": 1000.0`

---

### Recipe 11: Compute Limits

**Use Case**: Block compute-intensive operations

```json
{
  "id": "budget-compute-limit",
  "agent": "knowledge.search",
  "action": "reindex",
  "effect": "deny",
  "conditions": {
    "compute>=": 1000,
    "current_load>=": 0.8
  },
  "reason": "Block high-compute reindex operations when system load is high (>80%)",
  "priority": 100,
  "enabled": true,
  "budget": {
    "cost": 0,
    "compute": 0,
    "risk": "medium"
  },
  "tags": ["budget", "compute", "performance"]
}
```

**When to use**:
- Shared infrastructure with resource contention
- Preventing performance degradation
- Load-aware scheduling

---

## Business Hours Gating

### Recipe 12: Weekday Only Actions

**Use Case**: Defer non-urgent actions to weekdays

```json
{
  "id": "schedule-weekday-only",
  "agent": "knowledge.search",
  "action": "update",
  "effect": "deny",
  "conditions": {
    "day_of_week": "Saturday|Sunday",
    "priority": "low",
    "urgent==": false
  },
  "reason": "Defer low-priority knowledge updates to weekdays to preserve weekend capacity",
  "priority": 80,
  "enabled": true,
  "budget": {
    "cost": 0,
    "compute": 0,
    "risk": "low"
  },
  "tags": ["schedule", "weekend", "efficiency"]
}
```

**When to use**:
- Cost optimization (weekend spot pricing)
- Team capacity planning
- SLA-based prioritization

---

## Risk-Based Approval

### Recipe 13: High-Risk Requires Two Approvers

**Use Case**: Require multiple approvals for dangerous operations

```json
{
  "id": "risk-high-two-approvers",
  "agent": "*",
  "action": "*",
  "effect": "needs_approval",
  "conditions": {
    "risk": "high",
    "approvers_count<": 2
  },
  "reason": "High-risk actions require approval from two people to prevent single-person mistakes",
  "priority": 250,
  "enabled": true,
  "budget": {
    "cost": 0,
    "compute": 0,
    "risk": "high"
  },
  "metadata": {
    "min_approvers": 2
  },
  "tags": ["risk", "approval", "safety"]
}
```

**When to use**:
- Production deployments
- Database schema changes
- Security policy modifications

---

## Category Exceptions

### Recipe 14: Newsletter Auto-Archive

**Use Case**: Automatically archive newsletters

```json
{
  "id": "inbox-archive-newsletters",
  "agent": "inbox.triage",
  "action": "archive",
  "effect": "allow",
  "conditions": {
    "category": "newsletter",
    "unsubscribe_link_present==": true,
    "spam_score<": 50
  },
  "reason": "Auto-archive newsletters (with unsubscribe links) to keep inbox clean",
  "priority": 70,
  "enabled": true,
  "budget": {
    "cost": 0.02,
    "compute": 1,
    "risk": "low"
  },
  "tags": ["inbox", "productivity", "auto"]
}
```

**When to use**:
- Inbox zero workflows
- After user enables "auto-archive newsletters" setting
- Reducing notification fatigue

---

### Recipe 15: VIP Bypass

**Use Case**: Never quarantine emails from VIPs

```json
{
  "id": "inbox-vip-bypass",
  "agent": "inbox.triage",
  "action": "quarantine",
  "effect": "deny",
  "conditions": {
    "sender_vip==": true
  },
  "reason": "Never quarantine emails from VIP senders to avoid blocking important communications",
  "priority": 500,
  "enabled": true,
  "budget": {
    "cost": 0,
    "compute": 0,
    "risk": "low"
  },
  "tags": ["inbox", "vip", "whitelist"]
}
```

**When to use**:
- C-suite communications
- Customer success contacts
- Partner communications

**Variations**:
- VIP list: Maintain `vip_senders` table
- Domain-based: `"sender_domain": "@vip-partner.com"`
- Conditional: Still apply risk scoring, just don't auto-quarantine

---

## Advanced Patterns

### Recipe 16: Progressive Rollout

**Use Case**: Gradually increase action limits over time

```json
[
  {
    "id": "rollout-phase-1",
    "agent": "inbox.triage",
    "action": "quarantine",
    "effect": "allow",
    "conditions": {
      "risk_score>=": 90,
      "rollout_day<": 7
    },
    "reason": "Phase 1: Only quarantine extremely high risk (>90) for first week",
    "priority": 100,
    "enabled": true
  },
  {
    "id": "rollout-phase-2",
    "agent": "inbox.triage",
    "action": "quarantine",
    "effect": "allow",
    "conditions": {
      "risk_score>=": 85,
      "rollout_day>=": 7,
      "rollout_day<": 14
    },
    "reason": "Phase 2: Lower threshold to 85 after one week of monitoring",
    "priority": 90,
    "enabled": true
  },
  {
    "id": "rollout-phase-3",
    "agent": "inbox.triage",
    "action": "quarantine",
    "effect": "allow",
    "conditions": {
      "risk_score>=": 80,
      "rollout_day>=": 14
    },
    "reason": "Phase 3: Final threshold at 80 after two weeks",
    "priority": 80,
    "enabled": true
  }
]
```

**When to use**:
- Rolling out new AI models
- A/B testing policy changes
- Building user confidence gradually

---

### Recipe 17: Circuit Breaker

**Use Case**: Auto-disable policy on high error rate

```json
{
  "id": "circuit-breaker",
  "agent": "inbox.triage",
  "action": "*",
  "effect": "deny",
  "conditions": {
    "error_rate_5min>=": 0.10,
    "circuit_open==": true
  },
  "reason": "Circuit breaker: Block all inbox actions if error rate exceeds 10% in last 5 minutes",
  "priority": 1000,
  "enabled": true,
  "budget": {
    "cost": 0,
    "compute": 0,
    "risk": "critical"
  },
  "metadata": {
    "circuit_open_threshold": 0.10,
    "circuit_reset_minutes": 15
  },
  "tags": ["reliability", "circuit-breaker", "emergency"]
}
```

**When to use**:
- Protecting against cascading failures
- AI model degradation scenarios
- API rate limit protection

---

## Testing Recipes

Before deploying any recipe:

1. **Lint**: Ensure no conflicts with existing rules
2. **Simulate**: Test with fixtures and synthetic data
3. **Compare**: Diff against current active policy
4. **Canary**: Deploy at 10% first
5. **Monitor**: Watch quality gates for 24h
6. **Iterate**: Adjust thresholds based on real data

## Recipe Naming Convention

Follow this pattern for consistency:

```
{agent}-{action}-{descriptor}

Examples:
✅ inbox-quarantine-high-risk
✅ knowledge-reindex-small-auto
✅ planner-deploy-canary-only

❌ rule-1
❌ my-policy
❌ temp-test
```

## Contributing

To add a new recipe:

1. Test in staging for 1 week minimum
2. Document use case and variations
3. Include before/after metrics
4. Submit PR with simulation results
5. Tag with relevant categories

---

## Support

- **Questions**: `#policy-help` on Slack
- **Bug reports**: GitHub Issues
- **Custom recipes**: Email `policy-team@company.com`
