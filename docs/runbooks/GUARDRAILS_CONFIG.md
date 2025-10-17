# Guardrails Configuration Runbook

**Phase 4 - Agent Governance**

This runbook covers configuring, tuning, and troubleshooting execution guardrails for agent actions.

## Table of Contents

- [Overview](#overview)
- [Guardrail Types](#guardrail-types)
- [Pre-Execution Validation](#pre-execution-validation)
- [Post-Execution Validation](#post-execution-validation)
- [Required Parameters](#required-parameters)
- [Tuning Guidelines](#tuning-guidelines)
- [Custom Guardrails](#custom-guardrails)
- [Troubleshooting](#troubleshooting)

## Overview

Execution guardrails provide **automatic validation** at agent execution boundaries:

- **Pre-execution**: Policy checks, parameter validation (hard fail)
- **Post-execution**: Result validation, metric checks (soft fail)
- **Integration**: Built into Executor, transparent to agents

## Guardrail Types

### Hard Fail (Pre-Execution)

**Blocks execution** if validation fails:
- Policy compliance check
- Required parameter validation
- Approval requirement detection

**Raises:** `GuardrailViolation` exception

### Soft Fail (Post-Execution)

**Logs warnings** but doesn't block:
- Result structure validation
- Resource metric validation
- Unexpected side effects

**Behavior:** Execution continues, warnings logged

## Pre-Execution Validation

### 1. Policy Compliance

Enforces policy engine decisions.

**Configuration:**
```python
from app.policy import PolicyEngine, PolicyRule

# Deny dangerous operations
rules = [
    PolicyRule(
        id="deny-prod-delete",
        agent="*",
        action="delete",
        conditions={"environment": "production"},
        effect="deny",
        priority=100
    )
]

engine = PolicyEngine(rules)
```

**Validation Logic:**
```python
# Guardrails check policy
decision = policy_engine.decide(agent, action, context)

if decision.effect == "deny" and not decision.requires_approval:
    raise GuardrailViolation(
        message=f"Action '{action}' denied by policy",
        violation_type="policy_denied",
        details={
            "agent": agent,
            "action": action,
            "rule_id": decision.rule_id,
            "reason": decision.reason
        }
    )
```

**Example Violation:**
```json
{
    "error": "GuardrailViolation",
    "message": "Action 'delete' denied by policy: Production deletes not allowed",
    "violation_type": "policy_denied",
    "details": {
        "agent": "knowledge_update",
        "action": "delete",
        "rule_id": "deny-prod-delete",
        "reason": "Production deletes not allowed"
    }
}
```

### 2. Required Parameters

Validates action-specific parameters present.

**Built-in Requirements:**

| Action | Required Parameters |
|--------|-------------------|
| `quarantine` | `email_id` |
| `label` | `email_id`, `label_name` |
| `apply` | `changes` |
| `generate` | `template_type` |
| `dbt_run` | `models` |
| `query` | `sql` |

**Configuration:**
```python
# In guardrails.py
REQUIRED_PARAMS = {
    "quarantine": ["email_id"],
    "label": ["email_id", "label_name"],
    "apply": ["changes"],
    "generate": ["template_type"],
    "dbt_run": ["models"],
    "query": ["sql"]
}
```

**Adding Custom Requirements:**
```python
# Extend REQUIRED_PARAMS in guardrails module
from app.agents.guardrails import REQUIRED_PARAMS

REQUIRED_PARAMS["custom_action"] = ["param1", "param2"]
```

**Validation Logic:**
```python
def _validate_required_params(action, context, plan):
    """Validate required parameters present."""
    required = REQUIRED_PARAMS.get(action, [])
    
    for param in required:
        if param not in context and param not in plan:
            raise GuardrailViolation(
                message=f"Missing required parameter '{param}' for action '{action}'",
                violation_type="missing_parameter",
                details={
                    "action": action,
                    "required_params": required,
                    "provided": list(context.keys())
                }
            )
```

**Example Violation:**
```json
{
    "error": "GuardrailViolation",
    "message": "Missing required parameter 'email_id' for action 'quarantine'",
    "violation_type": "missing_parameter",
    "details": {
        "action": "quarantine",
        "required_params": ["email_id"],
        "provided": ["risk_score"]
    }
}
```

### 3. Approval Detection

Checks if approval required and blocks if missing.

**Configuration:**
```python
# Policy rule that triggers approval
PolicyRule(
    id="deny-high-risk",
    agent="inbox_triage",
    action="quarantine",
    conditions={"risk_score": 70},  # >= 70
    effect="deny",
    reason="High-risk quarantine requires approval",
    priority=100
)
```

**Validation Logic:**
```python
# Check if approval required
decision = guardrails.validate_pre_execution(...)

if decision.requires_approval and not approval_id:
    raise GuardrailViolation(
        message=f"Action requires human approval: {decision.reason}",
        violation_type="approval_required",
        details={
            "agent": agent,
            "action": action,
            "reason": decision.reason,
            "approval_flow": "Request approval via /api/v1/approvals"
        }
    )
```

**Example Violation:**
```json
{
    "error": "GuardrailViolation",
    "message": "Action requires human approval: High-risk quarantine requires approval",
    "violation_type": "approval_required",
    "details": {
        "agent": "inbox_triage",
        "action": "quarantine",
        "reason": "High-risk quarantine requires approval",
        "approval_flow": "Request approval via /api/v1/approvals"
    }
}
```

## Post-Execution Validation

### 1. Result Structure

Validates result is a dictionary.

**Validation Logic:**
```python
def validate_post_execution(agent, action, context, result):
    """Validate result structure."""
    if not isinstance(result, dict):
        raise GuardrailViolation(
            message=f"Result must be a dict, got {type(result).__name__}",
            violation_type="invalid_result",
            details={
                "agent": agent,
                "action": action,
                "result_type": type(result).__name__
            }
        )
```

**Valid Results:**
```python
# ✅ Valid
{"status": "success", "data": [...]}
{"error": "Database connection failed"}  # Errors OK
{"ops_count": 10, "cost_cents_used": 25}

# ❌ Invalid
"success"  # String
None       # None
[]         # List
```

**Example Warning:**
```
warning: Post-execution guardrail violation: Result must be a dict, got str
```

### 2. Metric Validation

Validates resource usage metrics.

**Validation Logic:**
```python
# Check ops_count
if "ops_count" in result:
    ops = result["ops_count"]
    if not isinstance(ops, int) or ops < 0:
        raise GuardrailViolation(
            message=f"ops_count must be non-negative integer, got {ops}",
            violation_type="invalid_metric",
            details={"metric": "ops_count", "value": ops}
        )

# Check cost_cents_used
if "cost_cents_used" in result:
    cost = result["cost_cents_used"]
    if not isinstance(cost, int) or cost < 0:
        raise GuardrailViolation(
            message=f"cost_cents_used must be non-negative integer, got {cost}",
            violation_type="invalid_metric",
            details={"metric": "cost_cents_used", "value": cost}
        )
```

**Valid Metrics:**
```python
# ✅ Valid
{"ops_count": 10, "cost_cents_used": 25}
{"ops_count": 0}  # Zero OK
{}  # Missing metrics OK

# ❌ Invalid
{"ops_count": -5}  # Negative
{"cost_cents_used": "expensive"}  # Not int
{"ops_count": 3.14}  # Not int
```

**Example Warning:**
```
warning: Post-execution guardrail violation: ops_count must be non-negative integer, got -5
```

## Required Parameters

### Adding New Action Requirements

**Step 1: Update REQUIRED_PARAMS**
```python
# In app/agents/guardrails.py

REQUIRED_PARAMS = {
    # Existing...
    "quarantine": ["email_id"],
    
    # Add new action
    "send_notification": ["recipient", "message"],
    "archive_emails": ["email_ids", "archive_name"],
}
```

**Step 2: Test Requirements**
```python
# In tests/test_executor_guardrails.py

def test_send_notification_requires_params():
    """Test send_notification requires recipient and message."""
    rules = [PolicyRule(id="allow", agent="*", action="*", effect="allow")]
    engine = PolicyEngine(rules)
    guardrails = ExecutionGuardrails(engine)
    
    # Missing recipient
    with pytest.raises(GuardrailViolation) as exc:
        guardrails.validate_pre_execution(
            agent="notifier",
            action="send_notification",
            context={"message": "Hello"},  # Missing recipient
            plan={}
        )
    
    assert "recipient" in exc.value.message
```

**Step 3: Document in Code**
```python
# Add docstring to handler
def send_notification_handler(plan):
    """
    Send notification to recipient.
    
    Required params:
        - recipient: Email or user ID
        - message: Notification text
    
    Optional params:
        - priority: "low" | "normal" | "high"
        - attachment: File path
    """
    ...
```

### Optional vs Required

**Decision Criteria:**

| Parameter | Required If... |
|-----------|---------------|
| Identity (email_id, user_id) | Action targets specific entity |
| Action spec (label_name, template_type) | Action needs configuration |
| Content (message, sql) | Action processes data |
| Metadata (priority, tags) | Optional - has defaults |

**Example: Mixed Requirements**
```python
# send_email action
REQUIRED_PARAMS["send_email"] = ["recipient", "subject", "body"]

# Handler can have optional params
def send_email_handler(plan):
    recipient = plan["recipient"]  # Required
    subject = plan["subject"]      # Required
    body = plan["body"]            # Required
    
    priority = plan.get("priority", "normal")  # Optional with default
    attachments = plan.get("attachments", [])  # Optional
    
    ...
```

## Tuning Guidelines

### 1. Policy Strictness

**Permissive (Development):**
```python
# Allow most actions, deny specific cases
PolicyRule(
    id="default-allow",
    agent="*",
    action="*",
    effect="allow",
    priority=0  # Lowest priority (fallback)
)

PolicyRule(
    id="deny-prod-write",
    agent="*",
    action="delete|update",
    conditions={"environment": "production"},
    effect="deny",
    priority=100
)
```

**Strict (Production):**
```python
# Deny by default, allow specific cases
PolicyRule(
    id="default-deny",
    agent="*",
    action="*",
    effect="deny",
    reason="Explicit allow required",
    priority=0
)

PolicyRule(
    id="allow-safe-reads",
    agent="*",
    action="read|list|get",
    effect="allow",
    priority=50
)
```

### 2. Approval Thresholds

**Risk-Based:**
```python
# Low risk: Auto-allow
PolicyRule(
    id="allow-low-risk",
    agent="*",
    action="*",
    conditions={"risk_score": 30},  # < 30
    effect="allow",
    priority=100
)

# Medium risk: Require approval
PolicyRule(
    id="deny-medium-risk",
    agent="*",
    action="*",
    conditions={"risk_score": 70},  # 30-69
    effect="deny",
    reason="Medium risk requires approval",
    priority=75
)

# High risk: Hard deny
PolicyRule(
    id="deny-high-risk",
    agent="*",
    action="*",
    conditions={"risk_score": 90},  # >= 90
    effect="deny",
    reason="High risk - not permitted",
    priority=150,
    approval_eligible=False  # No approval possible
)
```

**Cost-Based:**
```python
# Free: Auto-allow
PolicyRule(
    id="allow-free",
    agent="*",
    action="*",
    conditions={"estimated_cost_cents": 10},  # < $0.10
    effect="allow",
    priority=100
)

# Expensive: Require approval
PolicyRule(
    id="deny-expensive",
    agent="*",
    action="*",
    conditions={"estimated_cost_cents": 100},  # >= $1.00
    effect="deny",
    reason="Expensive operation requires approval",
    priority=150
)
```

### 3. Parameter Granularity

**Coarse (Faster):**
```python
# Minimal requirements
REQUIRED_PARAMS = {
    "execute": ["plan"],  # Single blob
    "query": ["sql"]      # Just the query
}
```

**Fine-Grained (Safer):**
```python
# Detailed requirements
REQUIRED_PARAMS = {
    "execute": ["agent", "action", "context", "budget"],
    "query": ["sql", "database", "timeout", "max_rows"]
}
```

**Recommendation:** Start coarse, add granularity as needed.

### 4. Post-Execution Strictness

**Lenient (Log Only):**
```python
# Current behavior - logs warnings
try:
    validate_post_execution(...)
except GuardrailViolation as e:
    logger.warning(f"Post-execution violation: {e.message}")
    # Continue processing
```

**Strict (Fail Fast):**
```python
# Raise exceptions for violations
validate_post_execution(...)
# Let exception bubble up
```

**Recommendation:** Lenient for post-execution (action already done), strict for pre-execution.

## Custom Guardrails

### Extending ExecutionGuardrails

```python
from app.agents.guardrails import ExecutionGuardrails, GuardrailViolation

class CustomGuardrails(ExecutionGuardrails):
    """Extended guardrails with custom checks."""
    
    def validate_pre_execution(self, agent, action, context, plan):
        """Add custom pre-execution checks."""
        # Call parent validation
        decision = super().validate_pre_execution(agent, action, context, plan)
        
        # Custom check: Rate limiting
        if self._check_rate_limit_exceeded(agent):
            raise GuardrailViolation(
                message=f"Agent {agent} exceeded rate limit",
                violation_type="rate_limit_exceeded",
                details={"agent": agent, "limit": 100}
            )
        
        # Custom check: Business hours
        if not self._is_business_hours() and action == "send_email":
            raise GuardrailViolation(
                message="Email sending only allowed during business hours",
                violation_type="outside_business_hours",
                details={"current_time": datetime.now().isoformat()}
            )
        
        return decision
    
    def _check_rate_limit_exceeded(self, agent):
        """Check if agent exceeded rate limit."""
        # Implementation...
        return False
    
    def _is_business_hours(self):
        """Check if current time is business hours."""
        from datetime import datetime
        now = datetime.now()
        return 9 <= now.hour < 17 and now.weekday() < 5
```

**Usage:**
```python
# In executor initialization
self.guardrails = CustomGuardrails(self.policy_engine)
```

### Custom Violation Types

```python
# Define custom violation types
VIOLATION_TYPES = {
    "policy_denied": "Action denied by policy",
    "approval_required": "Human approval required",
    "missing_parameter": "Required parameter missing",
    "invalid_result": "Result structure invalid",
    "invalid_metric": "Resource metric invalid",
    
    # Custom types
    "rate_limit_exceeded": "Rate limit exceeded",
    "outside_business_hours": "Outside business hours",
    "duplicate_request": "Duplicate request detected",
    "quota_exceeded": "Resource quota exceeded"
}
```

## Troubleshooting

### Issue: Too Many Policy Denials

**Symptoms:**
- Most actions blocked
- Development slowed down

**Diagnosis:**
```bash
# Check deny rate
grep "policy_denied" logs/*.log | wc -l
```

**Solution:**
1. Review policy priorities (deny might be too high)
2. Add specific allow rules for common actions
3. Use permissive mode in dev/staging
4. Check condition logic (>= vs <=)

### Issue: Missing Parameter Violations

**Symptoms:**
```
GuardrailViolation: Missing required parameter 'email_id'
```

**Diagnosis:**
- Check if parameter in context or plan
- Verify parameter name matches (case-sensitive)
- Review required params list

**Solution:**
```python
# Option 1: Add parameter to context
context = {"email_id": "123", "risk_score": 85}

# Option 2: Add to plan
plan = {
    "agent": "inbox_triage",
    "action": "quarantine",
    "email_id": "123"  # In plan instead of context
}

# Option 3: Remove requirement (if truly optional)
# Remove from REQUIRED_PARAMS in guardrails.py
```

### Issue: Post-Execution Warnings Ignored

**Symptoms:**
- Warnings logged but not addressed
- Invalid results processed

**Diagnosis:**
```bash
# Check warning frequency
grep "Post-execution guardrail violation" logs/*.log | head -20
```

**Solution:**
1. Fix handlers to return valid dict
2. Ensure metrics are integers >= 0
3. Add pre-execution validation if needed
4. Consider making post-execution strict

### Issue: Performance Degradation

**Symptoms:**
- Slow execution
- High CPU usage

**Diagnosis:**
```python
import time

start = time.time()
guardrails.validate_pre_execution(...)
elapsed = time.time() - start
print(f"Validation took {elapsed*1000:.2f}ms")
```

**Solution:**
1. Reduce policy rule count
2. Cache policy decisions
3. Skip validation in dev mode
4. Profile validation logic

## Best Practices

1. **Start permissive, tighten gradually** (avoid over-restriction)
2. **Test guardrails in staging** before production
3. **Log all violations** for analysis
4. **Document required parameters** in handler docstrings
5. **Use meaningful violation types** for debugging
6. **Monitor violation rates** (too high = process issue)
7. **Review guardrails quarterly** (remove unused)
8. **Fail fast on pre-execution** (prevent bad actions)
9. **Warn on post-execution** (action already done)
10. **Make approval thresholds configurable** (tune per environment)

## See Also

- [Policy Management Runbook](./POLICY_MANAGEMENT.md)
- [Approval Workflows Runbook](./APPROVAL_WORKFLOWS.md)
- [Phase 4 Troubleshooting](./PHASE4_TROUBLESHOOTING.md)
