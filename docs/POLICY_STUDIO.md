# Policy Studio - User Guide

**ApplyLens Policy UI Editor & Rule Testing Sandbox**

The Policy Studio provides a complete environment for creating, testing, and deploying policy rules that govern agentic actions across your inbox, knowledge base, and deployment pipelines.

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Creating Rules](#creating-rules)
4. [Linting & Validation](#linting--validation)
5. [Simulation & Testing](#simulation--testing)
6. [Version Management](#version-management)
7. [Activation & Deployment](#activation--deployment)
8. [Rollback Procedures](#rollback-procedures)

---

## Overview

### What is a Policy Bundle?

A **Policy Bundle** is a versioned collection of rules that control:
- Which agent actions require approval
- Which actions should be automatically denied
- Budget thresholds for expensive operations
- Risk-based gating (e.g., quarantine high-risk emails)

Each bundle uses **semantic versioning** (MAJOR.MINOR.PATCH) and progresses through states:
- **Draft**: Under development, can be edited
- **Active (Canary)**: Deployed to 10% of traffic for monitoring
- **Active (Full)**: Promoted to 100% after passing quality gates

### Key Features

- **Visual Rule Builder**: Create rules without writing JSON
- **Real-time Linting**: Catch errors before deployment (duplicates, conflicts, unreachable rules)
- **What-If Simulator**: Test rules against real and synthetic data
- **Diff Viewer**: Compare versions side-by-side
- **Canary Deployment**: Gradual rollout with auto-rollback on quality gate failures
- **Approval Integration**: Requires Phase 5.4 approval before activation

---

## Getting Started

### Accessing Policy Studio

Navigate to `/policy-studio` in the ApplyLens web app. You'll see:

```
┌─────────────────────────────────────────────┐
│ Policy Studio                               │
├─────────────────────────────────────────────┤
│ Active Version: 2.1.0 (100%)                │
│                                             │
│ [Create New Bundle]  [Import Bundle]       │
│                                             │
│ Recent Bundles:                             │
│ • 2.1.0 (Active - 100%)                     │
│ • 2.0.5 (Draft)                             │
│ • 2.0.4 (Archived)                          │
└─────────────────────────────────────────────┘
```

### Creating Your First Bundle

1. Click **"Create New Bundle"**
2. Enter version (e.g., `2.2.0`)
3. Add optional notes describing changes
4. Click **"Create"** to start with an empty rule set

---

## Creating Rules

### Rule Structure

Each rule has:

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
  "reason": "Quarantine high-risk phishing emails automatically",
  "priority": 100,
  "enabled": true,
  "budget": {
    "cost": 0.05,
    "compute": 2,
    "risk": "low"
  }
}
```

### Using the Rule Builder

**Agent**: Select from dropdown:
- `inbox.triage`: Email classification and routing
- `knowledge.search`: Knowledge base updates
- `planner.deploy`: Deployment automation

**Action**: The operation being controlled:
- `quarantine`, `escalate`: Inbox actions
- `apply`, `update`, `delete`, `reindex`: Knowledge actions
- `deploy`, `rollback`: Planner actions

**Effect**: What happens when the rule matches:
- `allow`: Proceed without approval
- `deny`: Block the action entirely
- `needs_approval`: Require human approval (Phase 5.4)

**Conditions**: Filter when this rule applies:
- `risk_score>=`: 85 (numeric comparison)
- `category`: "phishing" (exact match)
- `domain_seen_days<`: 30 (less than 30 days old)

**Priority**: Higher numbers take precedence (range: 1-1000)

**Budget**: Resource limits for this action:
- `cost`: Dollar cost estimate
- `compute`: CPU/memory units
- `risk`: low/medium/high

### Advanced: Condition Operators

Conditions support rich comparisons:

| Operator | Example | Meaning |
|----------|---------|---------|
| `>=` | `risk_score>=: 85` | Greater than or equal |
| `<=` | `age<=: 30` | Less than or equal |
| `>` | `confidence>: 0.9` | Greater than |
| `<` | `compute<: 100` | Less than |
| `==` | `severity==: "high"` | Exact match |
| `!=` | `status!=: "archived"` | Not equal |

---

## Linting & Validation

### Lint Panel

The **Lint Panel** shows real-time validation as you edit:

```
┌─────────────────────────────────────────────┐
│ Lint Results                                │
├─────────────────────────────────────────────┤
│ ❌ 2 Errors                                  │
│ ⚠️  3 Warnings                               │
│ ℹ️  1 Info                                   │
│                                             │
│ Errors:                                     │
│ • Line 12: Duplicate rule ID                │
│   "inbox-quarantine-high-risk"              │
│   → Rename to unique ID                     │
│                                             │
│ • Line 45: Conflicting rules                │
│   "inbox-allow-all" allows what             │
│   "inbox-deny-phishing" denies              │
│   → Review agent/action overlap             │
│                                             │
│ Warnings:                                   │
│ • Line 8: Rule may be unreachable           │
│   Higher-priority catch-all shadows this    │
│   → Increase priority or remove             │
└─────────────────────────────────────────────┘
```

### Common Lint Errors

**Duplicate IDs**: Each rule must have a unique ID
```json
// ❌ Bad
{"id": "inbox-rule", ...}
{"id": "inbox-rule", ...}  // Duplicate!

// ✅ Good
{"id": "inbox-high-risk", ...}
{"id": "inbox-low-risk", ...}
```

**Conflicting Rules**: Allow/deny conflict for same agent+action
```json
// ❌ Bad
{"agent": "inbox.triage", "action": "quarantine", "effect": "allow"}
{"agent": "inbox.triage", "action": "quarantine", "effect": "deny"}

// ✅ Good: Use conditions to differentiate
{"agent": "inbox.triage", "action": "quarantine", "effect": "allow", "conditions": {"risk_score>=": 85}}
{"agent": "inbox.triage", "action": "quarantine", "effect": "deny", "conditions": {"risk_score<": 50}}
```

**Missing Reasons**: All rules need explanations
```json
// ❌ Bad
{"id": "rule-1", "reason": ""}

// ✅ Good
{"id": "rule-1", "reason": "Quarantine high-risk emails to prevent phishing attacks"}
```

---

## Simulation & Testing

### What-If Simulator

Test your rules before deploying. The simulator runs your policy against:
1. **Fixtures**: Curated edge cases (9 scenarios)
2. **Synthetic**: AI-generated test cases (100-1000)
3. **Custom**: Your own test data

### Running a Simulation

1. Click **"Simulate"** in the rule editor
2. Select dataset:
   - **Fixtures**: High-risk inbox, full reindex, canary deploy, etc.
   - **Synthetic (100)**: Quick validation
   - **Synthetic (1000)**: Comprehensive testing
3. Review results:

```
┌─────────────────────────────────────────────┐
│ Simulation Results                          │
├─────────────────────────────────────────────┤
│ Total Cases: 100                            │
│ • Allow: 45 (45%)                           │
│ • Deny: 20 (20%)                            │
│ • Needs Approval: 30 (30%)                  │
│ • No Match: 5 (5%)                          │
│                                             │
│ Estimated Budget:                           │
│ • Cost: $45.50                              │
│ • Compute: 1,200 units                      │
│                                             │
│ ⚠️ Budget Breach Detected:                   │
│ • Case #23: Cost $25 exceeds threshold      │
│   → Review rule "knowledge-full-reindex"    │
└─────────────────────────────────────────────┘
```

### Comparing Versions

Use **Compare Mode** to see how changes affect decisions:

1. Select baseline version (e.g., `2.1.0`)
2. Select proposed version (e.g., `2.2.0`)
3. View delta report:

```
┌─────────────────────────────────────────────┐
│ Version Comparison: 2.1.0 → 2.2.0           │
├─────────────────────────────────────────────┤
│ Changes (15 total):                         │
│                                             │
│ • Case #7: allow → deny                     │
│   inbox_high_risk_new_domain                │
│   More conservative quarantine              │
│                                             │
│ • Case #12: needs_approval → allow          │
│   knowledge_small_reindex                   │
│   Increased auto-approval threshold         │
│                                             │
│ Delta Summary:                              │
│ • Allow rate: 45% → 50% (+5%)               │
│ • Deny rate: 20% → 18% (-2%)                │
│ • Approval rate: 30% → 27% (-3%)            │
│ • Avg cost: $0.45 → $0.52 (+15%)            │
└─────────────────────────────────────────────┘
```

---

## Version Management

### Semantic Versioning

Follow semantic versioning conventions:

- **MAJOR (X.0.0)**: Breaking changes (complete policy rewrite)
- **MINOR (1.X.0)**: New rules or features (additive changes)
- **PATCH (1.1.X)**: Bug fixes or minor adjustments

Examples:
- `2.1.0` → `2.2.0`: Added new inbox rules (minor bump)
- `2.2.0` → `2.2.1`: Fixed typo in reason text (patch bump)
- `2.2.1` → `3.0.0`: Complete rewrite of approval logic (major bump)

### Diff Viewer

Compare any two versions side-by-side:

```
┌───────────────────┬───────────────────┐
│ v2.1.0            │ v2.2.0            │
├───────────────────┼───────────────────┤
│ Rule: inbox-hr-1  │ Rule: inbox-hr-1  │
│ priority: 100     │ priority: 150 ✏️   │
│                   │                   │
│                   │ ➕ Rule: inbox-hr-2 │
│                   │   (new rule)      │
│                   │                   │
│ Rule: kb-reindex  │ ❌ (removed)       │
└───────────────────┴───────────────────┘

Summary:
• 1 rule modified
• 1 rule added
• 1 rule removed
• 10 rules unchanged
```

### Import/Export

**Export** a signed bundle:
1. Click **"Export"** on any bundle
2. Downloads `policy-bundle-2.2.0.json`
3. Signature valid for 24 hours (configurable)

**Import** from another environment:
1. Click **"Import Bundle"**
2. Upload signed JSON file
3. System verifies signature and expiry
4. Creates as draft (requires activation)

---

## Activation & Deployment

### Approval Gate

Activating a policy bundle requires **approval** from Phase 5.4:

1. Click **"Activate"** on a draft bundle
2. Request approval with:
   - Justification (why these changes?)
   - Risk assessment (low/medium/high)
   - Rollback plan (how to revert if needed?)
3. Wait for approval (requires 2 approvers for high-risk changes)
4. Once approved, bundle enters **canary phase**

### Canary Deployment

New bundles start at **10% traffic** for safety:

```
Day 1 (0h):   Activate at 10%
             ↓ Monitor quality gates for 24h
Day 2 (24h):  ✅ Gates pass → Promote to 50%
             ↓ Monitor for another 24h
Day 3 (48h):  ✅ Gates pass → Promote to 100%
```

**Quality Gates** (must all pass):
- Error rate < 5%
- Deny rate < 30%
- Cost increase < 20%
- Minimum 100 decisions

### Monitoring Canary

Check canary status in the dashboard:

```
┌─────────────────────────────────────────────┐
│ Canary Status: v2.2.0                       │
├─────────────────────────────────────────────┤
│ Traffic: 10% (canary)                       │
│ Time Active: 18 hours                       │
│ Decisions: 1,245                            │
│                                             │
│ Quality Gates:                              │
│ • Error rate: 2.1% ✅ (< 5%)                 │
│ • Deny rate: 18.5% ✅ (< 30%)                │
│ • Cost increase: +8.2% ✅ (< 20%)            │
│ • Sample size: 1,245 ✅ (>= 100)             │
│                                             │
│ Promotion Eligible: 6 hours                 │
│                                             │
│ [Promote to 50%]  [Rollback]                │
└─────────────────────────────────────────────┘
```

### Auto-Promotion

If gates pass after 24h, the system can auto-promote:
1. 10% → 50% (automatic)
2. Monitor for another 24h
3. 50% → 100% (automatic)

Manual promotion available anytime after 24h.

---

## Rollback Procedures

### When to Rollback

Trigger rollback if:
- **Quality gates fail**: High error/deny rates
- **Budget breach**: Costs exceed thresholds
- **Unexpected behavior**: Policies not acting as expected
- **Incident escalation**: Phase 5.4 incident severity HIGH

### Manual Rollback

1. Navigate to active bundle (e.g., `2.2.0`)
2. Click **"Rollback"**
3. Enter reason (required, minimum 10 characters)
4. Confirm rollback
5. System will:
   - Deactivate current bundle (`2.2.0` → inactive)
   - Reactivate previous version (`2.1.0` → 100%)
   - Create high-severity incident
   - Record rollback metadata

```
┌─────────────────────────────────────────────┐
│ Rollback Confirmation                       │
├─────────────────────────────────────────────┤
│ Current:  v2.2.0 (10% canary)               │
│ Previous: v2.1.0 (last stable)              │
│                                             │
│ Reason: [Error rate exceeded 10% during     │
│          canary phase, multiple user        │
│          complaints about false denies]     │
│                                             │
│ ⚠️ This will:                                │
│ • Deactivate v2.2.0 immediately             │
│ • Reactivate v2.1.0 at 100% traffic         │
│ • Create incident INC-2024-0123             │
│ • Notify policy team via Slack              │
│                                             │
│ [Cancel]  [Confirm Rollback]                │
└─────────────────────────────────────────────┘
```

### Auto-Rollback

The system will automatically rollback if:
- Error rate exceeds 10% (2x threshold)
- Deny rate exceeds 50% (major disruption)
- Cost increase exceeds 50% (budget explosion)

Auto-rollback creates a **HIGH severity incident** with:
- Metric that triggered rollback
- Before/after comparison
- Affected decision IDs
- Recommended actions

### Post-Rollback Steps

After rolling back:

1. **Review Incident**: Check INC-XXXX for root cause
2. **Analyze Logs**: Use Phase 5 telemetry to find bad decisions
3. **Fix in Draft**: Edit the rolled-back bundle (now draft)
4. **Re-simulate**: Test fixes with simulation
5. **Re-submit**: Request approval and try again

---

## Best Practices

### Rule Hygiene

- **Use descriptive IDs**: `inbox-quarantine-high-risk` not `rule-1`
- **Write clear reasons**: Explain *why* the rule exists
- **Set appropriate priorities**: Leave gaps (10, 20, 30) for easy insertion
- **Enable by default**: Only disable during debugging
- **Tag rules**: Use `tags: ["security", "phishing"]` for organization

### Testing Strategy

1. **Lint first**: Fix all errors before simulating
2. **Test with fixtures**: Ensure edge cases work
3. **Run synthetic (100)**: Quick validation
4. **Compare versions**: Check delta before deploying
5. **Test rollback**: Simulate rollback procedure in staging

### Deployment Cadence

- **Patches (X.X.1)**: Deploy anytime (low risk)
- **Minors (X.1.0)**: Weekly cycle (moderate risk)
- **Majors (2.0.0)**: Monthly + change freeze (high risk)

### Canary Monitoring

- **Watch first 6h**: Most issues appear early
- **Check dashboards**: Grafana policy metrics
- **Review incidents**: Phase 5.4 incident queue
- **Slack alerts**: Enable for gate failures

---

## Troubleshooting

### "Approval Required"

**Symptom**: Cannot activate bundle
**Solution**: Submit approval request in Phase 5.4 approvals tray

### "Insufficient Samples"

**Symptom**: Canary won't promote after 24h
**Solution**: Increase traffic or wait for more decisions (need 100+ samples)

### "Conflicting Rules"

**Symptom**: Linter shows conflict error
**Solution**: Add conditions to differentiate rules or change priorities

### "Budget Breach in Simulation"

**Symptom**: Simulation shows cost overruns
**Solution**: Add budget limits to rules or adjust approval thresholds

---

## API Reference

### Programmatic Access

All Policy Studio features available via REST API:

```bash
# List bundles
GET /policy/bundles

# Create bundle
POST /policy/bundles
{
  "version": "2.2.0",
  "rules": [...],
  "notes": "Added phishing rules"
}

# Lint rules
POST /policy/lint
{"rules": [...]}

# Simulate
POST /policy/simulate
{
  "rules": [...],
  "dataset": "fixtures"
}

# Activate with approval
POST /policy/bundles/{id}/activate
{
  "approval_id": 123,
  "activated_by": "alice",
  "canary_pct": 10
}

# Check quality gates
POST /policy/bundles/{id}/check-gates
{"metrics": {...}}

# Promote canary
POST /policy/bundles/{id}/promote
{"target_pct": 50}

# Rollback
POST /policy/bundles/{id}/rollback
{
  "reason": "High error rate",
  "rolled_back_by": "bob"
}
```

---

## Support

- **Documentation**: `/docs/policy-studio`
- **Slack**: `#policy-help`
- **Runbook**: `RUNBOOK_POLICY.md`
- **Recipes**: `POLICY_RECIPES.md` for common patterns
