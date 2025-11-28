# Policy Management Runbook

**Phase 4 - Agent Governance**

This runbook covers creating, managing, and troubleshooting policy rules for autonomous agents.

## Table of Contents

- [Overview](#overview)
- [Policy Rule Structure](#policy-rule-structure)
- [Creating Policies](#creating-policies)
- [Priority and Precedence](#priority-and-precedence)
- [Conditions](#conditions)
- [Testing Policies](#testing-policies)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Overview

The Policy Engine evaluates authorization decisions for agent actions using priority-based rules. It supports:

- **Allow/Deny effects** with precedence rules
- **Priority-based evaluation** (highest priority first)
- **Conditional matching** (numeric and exact match)
- **Approval workflows** for soft denies
- **Wildcard matching** for agents and actions

## Policy Rule Structure

```python
from app.policy import PolicyRule

PolicyRule(
    id="unique-rule-id",           # Unique identifier
    agent="agent_name",             # Agent name or "*" for all
    action="action_name",           # Action name or "*" for all
    conditions={"key": value},      # Optional conditions
    effect="allow",                 # "allow" or "deny"
    reason="Human-readable reason", # Explanation
    priority=100                    # Higher = evaluated first (0-1000)
)
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique rule identifier (use kebab-case) |
| `agent` | string | No | Agent name or `*` (default: `*`) |
| `action` | string | No | Action name or `*` (default: `*`) |
| `conditions` | dict | No | Matching conditions (default: `{}`) |
| `effect` | string | Yes | `"allow"` or `"deny"` |
| `reason` | string | No | Human-readable explanation |
| `priority` | int | No | Evaluation priority (default: 0, range: 0-1000) |

## Creating Policies

### 1. Get Current Policy

```bash
GET /api/v1/policy

# Response
{
    "rules": [...],
    "budgets": {...}
}
```

### 2. Add New Rule

```bash
PUT /api/v1/policy

# Request body
{
    "rules": [
        {
            "id": "deny-large-diffs",
            "agent": "knowledge_update",
            "action": "apply",
            "conditions": {"changes_count": 1000},
            "effect": "deny",
            "reason": "Large diffs require manual review",
            "priority": 100
        }
    ],
    "budgets": {
        "knowledge_update": {
            "ms": 30000,
            "ops": 100,
            "cost_cents": 50
        }
    }
}
```

### 3. Using Python API

```python
from app.policy import PolicyEngine, PolicyRule

# Create rule
rule = PolicyRule(
    id="allow-low-risk-quarantine",
    agent="inbox_triage",
    action="quarantine",
    conditions={"risk_score": 70},  # risk_score < 70
    effect="allow",
    priority=50
)

# Add to engine
engine = PolicyEngine([rule])
decision = engine.decide(
    agent="inbox_triage",
    action="quarantine",
    context={"risk_score": 65}
)

print(decision.effect)  # "allow"
print(decision.reason)  # "allow by policy rule allow-low-risk-quarantine"
```

## Priority and Precedence

### Evaluation Order

1. **Sort by priority** (highest → lowest)
2. **Check target match** (agent and action)
3. **Check conditions** (all must match)
4. **Return first matching rule**
5. **Default: allow** if no rules match

### Priority Ranges (Convention)

| Range | Use Case | Example |
|-------|----------|---------|
| 900-1000 | Emergency overrides | Kill switch, security incidents |
| 700-899 | High-priority denies | Dangerous operations, PII access |
| 400-699 | Standard policies | Normal allow/deny rules |
| 100-399 | Low-priority allows | Default permissions |
| 0-99 | Fallback rules | Catch-all patterns |

### Example: Deny Overrides Allow

```python
rules = [
    PolicyRule(
        id="deny-delete",
        agent="*",
        action="delete",
        effect="deny",
        priority=100  # Higher priority
    ),
    PolicyRule(
        id="allow-admin-delete",
        agent="admin_agent",
        action="delete",
        effect="allow",
        priority=50   # Lower priority
    )
]

# Result: deny wins (higher priority)
# Even admin_agent cannot delete
```

To fix: Give admin rule higher priority (e.g., 200)

## Conditions

Conditions enable context-based decisions.

### Numeric Comparisons

```python
# >= comparison (numeric values)
conditions={"risk_score": 70}  # Matches if context["risk_score"] >= 70

# Context examples
context = {"risk_score": 85}  # Matches (85 >= 70)
context = {"risk_score": 50}  # Does NOT match (50 < 70)
```

### Exact Match

```python
# String exact match
conditions={"environment": "production"}
# Matches only if context["environment"] == "production"

# Boolean match
conditions={"requires_approval": True}
# Matches only if context["requires_approval"] is True
```

### Multiple Conditions (AND logic)

```python
conditions={
    "changes_count": 1000,        # >= 1000
    "environment": "production"   # == "production"
}
# ALL conditions must match
```

### Example: Conditional Approval

```python
# Allow low-risk quarantine automatically
PolicyRule(
    id="allow-quarantine-low",
    agent="inbox_triage",
    action="quarantine",
    conditions={"risk_score": 70},  # < 70 = low risk
    effect="allow",
    priority=100
)

# Deny high-risk quarantine (requires approval)
PolicyRule(
    id="deny-quarantine-high",
    agent="inbox_triage",
    action="quarantine",
    conditions={"risk_score": 70},  # >= 70 = high risk
    effect="deny",
    reason="High-risk quarantine requires approval",
    priority=100  # Same priority, but condition is inverse
)
```

**Note:** If risk_score < 70, first rule matches. If >= 70, second rule matches (requires approval).

## Testing Policies

### 1. Unit Tests

```python
import pytest
from app.policy import PolicyEngine, PolicyRule

def test_policy_evaluation():
    rules = [
        PolicyRule(
            id="test-deny",
            agent="test_agent",
            action="delete",
            effect="deny",
            priority=100
        )
    ]
    engine = PolicyEngine(rules)
    
    decision = engine.decide(
        agent="test_agent",
        action="delete",
        context={}
    )
    
    assert decision.effect == "deny"
    assert decision.rule_id == "test-deny"
```

### 2. API Testing

```bash
# Test policy decision via API
POST /api/v1/agents/execute
{
    "plan": {
        "agent": "knowledge_update",
        "action": "apply",
        "context": {"changes_count": 1500}
    }
}

# Expected: GuardrailViolation if deny rule matches
```

### 3. Dry Run Mode

```python
# Test policy without executing action
decision = policy_engine.decide(
    agent="inbox_triage",
    action="quarantine",
    context={"risk_score": 85}
)

print(f"Effect: {decision.effect}")
print(f"Requires Approval: {decision.requires_approval}")
print(f"Reason: {decision.reason}")
```

## Common Patterns

### 1. Kill Switch

Emergency stop for all actions:

```python
PolicyRule(
    id="kill-switch-all",
    agent="*",
    action="*",
    effect="deny",
    reason="Emergency: All agent actions disabled",
    priority=1000  # Highest priority
)
```

### 2. Environment-Based

Different rules per environment:

```python
# Production: Strict
PolicyRule(
    id="prod-require-approval",
    agent="knowledge_update",
    action="apply",
    conditions={"environment": "production"},
    effect="deny",
    reason="Production changes require approval",
    priority=100
)

# Dev: Permissive
PolicyRule(
    id="dev-allow-all",
    agent="knowledge_update",
    action="apply",
    conditions={"environment": "development"},
    effect="allow",
    priority=50
)
```

### 3. Risk-Based Thresholds

Graduated rules by risk level:

```python
# Critical risk: Always deny
PolicyRule(
    id="deny-critical-risk",
    agent="*",
    action="*",
    conditions={"risk_score": 90},
    effect="deny",
    reason="Critical risk requires security review",
    priority=200
)

# High risk: Require approval
PolicyRule(
    id="deny-high-risk",
    agent="*",
    action="*",
    conditions={"risk_score": 70},
    effect="deny",
    reason="High risk requires approval",
    priority=100
)

# Low risk: Allow
PolicyRule(
    id="allow-low-risk",
    agent="*",
    action="*",
    conditions={"risk_score": 30},  # < 30
    effect="allow",
    priority=50
)
```

### 4. Cost Controls

Budget-based restrictions:

```python
# Deny expensive operations
PolicyRule(
    id="deny-expensive-ops",
    agent="*",
    action="*",
    conditions={"estimated_cost_cents": 100},  # >= $1.00
    effect="deny",
    reason="Expensive operations require approval",
    priority=150
)
```

## Troubleshooting

### Issue: Rule Not Matching

**Symptoms:**
- Expected rule doesn't apply
- Default allow/deny used instead

**Diagnosis:**
1. Check agent/action match (wildcards vs exact)
2. Verify conditions match context
3. Check priority order

```python
# Debug: Print matching rules
engine = PolicyEngine(rules)
for rule in engine.rules:
    if engine._matches_target(rule, agent, action):
        print(f"Target matches: {rule.id}")
        if engine._matches_conditions(rule.conditions, context):
            print(f"  Conditions match!")
        else:
            print(f"  Conditions MISS: {rule.conditions} vs {context}")
```

**Solution:**
- Use exact match instead of wildcard if needed
- Adjust conditions to match context data
- Increase priority if other rules override

### Issue: Wrong Rule Applied

**Symptoms:**
- Lower-priority rule used instead of higher
- Allow when deny expected (or vice versa)

**Diagnosis:**
1. Check priority values
2. Look for multiple matching rules
3. Verify evaluation order

```python
# Debug: List all matching rules by priority
matching = [
    r for r in engine.rules
    if engine._matches_target(r, agent, action)
    and engine._matches_conditions(r.conditions, context)
]
matching.sort(key=lambda r: r.priority, reverse=True)
for r in matching:
    print(f"{r.priority}: {r.id} → {r.effect}")
```

**Solution:**
- Adjust priorities (deny should be higher if needed)
- Make conditions more specific
- Use priority ranges for clarity

### Issue: Approval Not Required

**Symptoms:**
- Action executes without approval when it should require it

**Diagnosis:**
1. Check `approval_eligible` in context
2. Verify deny rule matches
3. Check `requires_approval` flag

```python
# Check approval requirement
decision = engine.decide(agent, action, context)
print(f"Effect: {decision.effect}")
print(f"Requires Approval: {decision.requires_approval}")
```

**Solution:**
- Ensure context has `approval_eligible=True` (default)
- Use deny effect with `requires_approval` logic
- Check executor integration for approval flow

### Issue: Performance Degradation

**Symptoms:**
- Slow policy evaluation
- High CPU usage

**Diagnosis:**
1. Count number of rules
2. Check condition complexity
3. Profile evaluation time

```python
import time

start = time.time()
decision = engine.decide(agent, action, context)
elapsed = time.time() - start
print(f"Evaluation took {elapsed*1000:.2f}ms")
```

**Solution:**
- Reduce number of rules (< 100 recommended)
- Use specific agent/action instead of wildcards
- Cache policy decisions if context unchanged
- Consider rule consolidation

### Issue: Condition Logic Confusion

**Symptoms:**
- Numeric conditions behave unexpectedly

**Diagnosis:**
- Remember: `conditions={"score": 70}` means `context["score"] >= 70`
- NOT less than 70!

**Solution:**
- Use clear variable names (e.g., `min_risk_score` instead of `risk_score`)
- Document condition semantics in `reason` field
- Add unit tests for boundary conditions

## Best Practices

1. **Use descriptive IDs**: `deny-prod-delete` better than `rule-1`
2. **Add reasons**: Always explain why rule exists
3. **Priority ranges**: Reserve 900+ for emergencies
4. **Test conditions**: Unit test boundary values
5. **Document wildcards**: Note when `*` is intentional
6. **Version control**: Track policy changes in git
7. **Audit logs**: Enable logging for policy decisions
8. **Regular review**: Remove unused rules quarterly

## See Also

- [Approval Workflows Runbook](./APPROVAL_WORKFLOWS.md)
- [Guardrails Configuration](./GUARDRAILS_CONFIG.md)
- [Phase 4 Troubleshooting](./PHASE4_TROUBLESHOOTING.md)
