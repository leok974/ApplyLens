# Phase 4 Troubleshooting Guide

**Agent Governance & Safety - Common Issues and Solutions**

This guide covers common problems with Phase 4 features: Policy Engine, Approvals, and Guardrails.

## Quick Diagnosis

```bash
# Check Phase 4 test status
pytest tests/test_policy_engine.py tests/test_approvals_api.py tests/test_executor_guardrails.py -v

# Check logs for guardrail violations
grep -i "guardrail" logs/api.log | tail -20

# Check policy decisions
grep -i "policy" logs/api.log | tail -20

# Check approval status
curl http://localhost:8003/api/v1/approvals?status=pending
```

## Policy Engine Issues

### Issue: Action Allowed When Should Be Denied

**Symptoms:**
- Action executes despite deny rule
- Wrong policy decision

**Diagnosis:**
```python
from app.policy import PolicyEngine

# Check rule matching
decision = engine.decide(agent, action, context)
print(f"Effect: {decision.effect}")
print(f"Rule: {decision.rule_id}")
print(f"Reason: {decision.reason}")

# List all rules
for rule in engine.get_rules(agent, action):
    print(f"{rule.priority}: {rule.id} → {rule.effect}")
```

**Common Causes:**

1. **Lower priority** - Allow rule has higher priority than deny
   ```python
   # Problem
   PolicyRule(id="allow", priority=100, effect="allow")
   PolicyRule(id="deny", priority=50, effect="deny")  # Lower!
   
   # Solution: Increase deny priority
   PolicyRule(id="deny", priority=150, effect="deny")
   ```

2. **Condition mismatch** - Deny rule conditions don't match context
   ```python
   # Problem
   PolicyRule(
       conditions={"risk_score": 70},  # >= 70
       effect="deny"
   )
   context = {"risk_score": 50}  # Doesn't match!
   
   # Solution: Check context values
   print(f"Context: {context}")
   ```

3. **Wildcard override** - Specific allow overrides general deny
   ```python
   # Problem
   PolicyRule(id="deny-all", agent="*", action="*", effect="deny", priority=50)
   PolicyRule(id="allow-specific", agent="my_agent", action="read", effect="allow", priority=100)
   
   # Result: allow-specific wins (higher priority + more specific)
   ```

**Solutions:**
- Increase deny rule priority
- Fix condition logic (>= vs <=)
- Make agent/action more specific
- Review all matching rules

### Issue: Default Allow/Deny Not Working

**Symptoms:**
- Unexpected default behavior
- No rules match but wrong effect

**Diagnosis:**
```python
# Check if any rules match
matching = [r for r in engine.rules if engine._matches_target(r, agent, action)]
print(f"Matching rules: {len(matching)}")

if not matching:
    print("No rules match - using default")
```

**Common Causes:**

1. **Implicit rule exists** - Forgot about wildcard rule
   ```python
   # Hidden rule
   PolicyRule(id="default", agent="*", action="*", effect="deny", priority=0)
   # This overrides built-in default allow!
   ```

2. **Default changed in code** - Engine default modified
   ```python
   # Check default in engine.py
   decision = PolicyDecision(
       effect="allow",  # Or "deny"?
       reason="default-allow: no matching policy rules"
   )
   ```

**Solutions:**
- Remove unintended wildcard rules
- Set explicit low-priority defaults
- Review engine default behavior

### Issue: Condition Logic Confusing

**Symptoms:**
- Numeric conditions behave opposite of expected

**Diagnosis:**
```python
# Remember: conditions={"score": 70} means context["score"] >= 70
# NOT less than 70!

# Test condition
rule = PolicyRule(conditions={"score": 70}, ...)
context = {"score": 80}
matches = engine._matches_conditions(rule.conditions, context)
print(f"Matches: {matches}")  # True if 80 >= 70
```

**Common Causes:**

1. **Inverted logic** - Thinking >= as <=
   ```python
   # What you want: Deny if score >= 70
   PolicyRule(conditions={"risk_score": 70}, effect="deny")  # Correct!
   
   # NOT this (won't work):
   PolicyRule(conditions={"risk_score": 70}, effect="allow")  # Wrong!
   ```

2. **Missing condition** - Forgot to add threshold
   ```python
   # Problem: Always matches
   PolicyRule(effect="deny")  # No conditions!
   
   # Solution: Add condition
   PolicyRule(conditions={"risk_score": 70}, effect="deny")
   ```

**Solutions:**
- Use clear variable names (`min_risk_score` instead of `risk_score`)
- Document condition semantics in `reason` field
- Add unit tests for boundary values
- Use this cheat sheet:
  ```
  conditions={"x": 10} → context["x"] >= 10
  ```

## Approval Workflow Issues

### Issue: Invalid Signature

**Symptoms:**
```
{"valid": false, "error": "Invalid signature"}
```

**Diagnosis:**
```bash
# Check HMAC_SECRET
echo $HMAC_SECRET

# Regenerate signature
python -c "
import hmac, hashlib
approval_id = 'appr_123'
decision = 'approved'
approver = 'user@company.com'
expires_at = '2025-10-17T11:30:00+00:00'
secret = '$HMAC_SECRET'
msg = f'{approval_id}:{decision}:{approver}:{expires_at}'
sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
print(f'Signature: {sig}')
"
```

**Common Causes:**

1. **Wrong secret** - Different HMAC_SECRET between systems
   ```bash
   # Check secrets match
   # System 1
   echo $HMAC_SECRET
   
   # System 2 (must match!)
   echo $HMAC_SECRET
   ```

2. **Timezone issues** - Expires timestamp without timezone
   ```python
   # Problem
   expires_at = "2025-10-17T11:30:00"  # No timezone!
   
   # Solution
   expires_at = "2025-10-17T11:30:00+00:00"  # With UTC
   
   # Or use datetime
   from datetime import datetime, timezone
   dt = datetime(2025, 10, 17, 11, 30, 0, tzinfo=timezone.utc)
   expires_at = dt.isoformat()
   ```

3. **Whitespace** - Extra spaces in message
   ```python
   # Ensure exact format
   message = f"{approval_id}:{decision}:{approver}:{expires_at}"
   # NO spaces around colons!
   ```

**Solutions:**
- Verify HMAC_SECRET matches
- Use timezone-aware datetimes
- Strip whitespace from inputs
- Test signature generation

### Issue: Approval Expired

**Symptoms:**
```
ValueError: Approval has expired
```

**Diagnosis:**
```bash
# Check approval status
curl http://localhost:8003/api/v1/approvals/{id}

# Check system time
date -u

# Calculate time remaining
python -c "
from datetime import datetime
expires = datetime.fromisoformat('2025-10-17T11:30:00+00:00')
now = datetime.now(datetime.timezone.utc)
remaining = (expires - now).total_seconds()
print(f'Remaining: {remaining:.0f} seconds')
"
```

**Common Causes:**

1. **Too short expiration** - 5 min default too tight
   ```python
   # Problem
   ApprovalRequest(..., expires_in_seconds=300)  # 5 min
   
   # Solution: Longer window
   ApprovalRequest(..., expires_in_seconds=3600)  # 1 hour
   ```

2. **Clock skew** - Systems have different times
   ```bash
   # Check clocks
   # Server 1
   date -u
   
   # Server 2 (should match!)
   date -u
   
   # Sync clocks
   sudo ntpdate pool.ntp.org
   ```

3. **Slow review** - Human takes too long
   ```
   # Monitor approval age
   SELECT id, requested_at, expires_at, 
          EXTRACT(EPOCH FROM (expires_at - NOW())) as seconds_remaining
   FROM approvals
   WHERE status = 'pending';
   ```

**Solutions:**
- Increase expiration time
- Sync system clocks
- Add approval reminders
- Allow expiration extension

### Issue: Cannot Execute with Approval

**Symptoms:**
```
GuardrailViolation: Invalid approval for action
```

**Diagnosis:**
```python
# Check approval details
approval = db.query(Approval).filter_by(id=approval_id).first()
print(f"Status: {approval.status}")
print(f"Agent: {approval.agent}")
print(f"Action: {approval.action}")
print(f"Expires: {approval.expires_at}")

# Check execution request
print(f"Execution agent: {execution_agent}")
print(f"Execution action: {execution_action}")
```

**Common Causes:**

1. **Agent mismatch** - Different agent in approval vs execution
   ```python
   # Approval
   approval.agent = "inbox_triage"
   
   # Execution
   execution_agent = "knowledge_update"  # Mismatch!
   ```

2. **Already executed** - Approval used once already
   ```python
   # Check status
   if approval.status == "executed":
       print("Approval already used")
   ```

3. **Wrong status** - Approval not yet approved
   ```python
   # Must be approved
   if approval.status != "approved":
       print(f"Approval is {approval.status}, not approved")
   ```

**Solutions:**
- Verify agent/action match
- Request new approval if used
- Check approval status before execution

## Guardrail Issues

### Issue: Missing Parameter Violation

**Symptoms:**
```
GuardrailViolation: Missing required parameter 'email_id' for action 'quarantine'
```

**Diagnosis:**
```python
# Check context and plan
print(f"Context: {context}")
print(f"Plan: {plan}")

# Check required params
from app.agents.guardrails import REQUIRED_PARAMS
print(f"Required for {action}: {REQUIRED_PARAMS.get(action, [])}")
```

**Common Causes:**

1. **Parameter in wrong place** - In plan but should be in context
   ```python
   # Problem
   context = {}
   plan = {"email_id": "123"}  # Won't be found!
   
   # Solution
   context = {"email_id": "123"}
   plan = {}
   ```

2. **Typo in parameter name** - Case-sensitive
   ```python
   # Problem
   context = {"emailId": "123"}  # Wrong case!
   
   # Solution
   context = {"email_id": "123"}  # Snake case
   ```

3. **Parameter not passed** - Missing from API call
   ```json
   // Problem
   {
     "agent": "inbox_triage",
     "action": "quarantine"
     // Missing email_id!
   }
   
   // Solution
   {
     "agent": "inbox_triage",
     "action": "quarantine",
     "context": {"email_id": "email_123"}
   }
   ```

**Solutions:**
- Add parameter to context (preferred) or plan
- Fix parameter name typo
- Check API request body
- Remove requirement if truly optional

### Issue: Invalid Result Structure

**Symptoms:**
```
warning: Post-execution guardrail violation: Result must be a dict, got str
```

**Diagnosis:**
```python
# Check handler return value
result = handler(plan)
print(f"Result type: {type(result)}")
print(f"Result: {result}")
```

**Common Causes:**

1. **Handler returns wrong type**
   ```python
   # Problem
   def handler(plan):
       return "success"  # String!
   
   # Solution
   def handler(plan):
       return {"status": "success"}  # Dict
   ```

2. **Error not caught** - Exception becomes string
   ```python
   # Problem
   def handler(plan):
       try:
           ...
       except Exception as e:
           return str(e)  # String!
   
   # Solution
   def handler(plan):
       try:
           ...
       except Exception as e:
           return {"error": str(e)}  # Dict with error
   ```

**Solutions:**
- Always return dict from handlers
- Wrap errors in dict structure
- Add post-execution tests

### Issue: Invalid Metric Values

**Symptoms:**
```
warning: Post-execution guardrail violation: ops_count must be non-negative integer, got -5
```

**Diagnosis:**
```python
# Check result metrics
result = handler(plan)
print(f"ops_count: {result.get('ops_count')} (type: {type(result.get('ops_count'))})")
print(f"cost_cents_used: {result.get('cost_cents_used')} (type: {type(result.get('cost_cents_used'))})")
```

**Common Causes:**

1. **Negative values** - Calculation bug
   ```python
   # Problem
   ops_count = start_count - end_count  # Could be negative!
   
   # Solution
   ops_count = max(0, end_count - start_count)
   ```

2. **Float instead of int** - Decimal not allowed
   ```python
   # Problem
   cost_cents_used = 25.50  # Float!
   
   # Solution
   cost_cents_used = 26  # Round up to int
   # Or: int(cost_cents_used)
   ```

3. **String value** - Not converted
   ```python
   # Problem
   ops_count = "10"  # String!
   
   # Solution
   ops_count = 10  # Int
   # Or: int(ops_count)
   ```

**Solutions:**
- Ensure metrics are int >= 0
- Add validation before returning
- Use max(0, value) for safety

## Performance Issues

### Issue: Slow Policy Evaluation

**Symptoms:**
- High latency on execute endpoint
- CPU spikes during evaluation

**Diagnosis:**
```python
import time

start = time.time()
decision = policy_engine.decide(agent, action, context)
elapsed = time.time() - start
print(f"Evaluation took {elapsed*1000:.2f}ms")
```

**Common Causes:**

1. **Too many rules** - 100+ rules
   ```sql
   -- Count rules
   SELECT COUNT(*) FROM policy_rules;
   
   -- Check rule distribution
   SELECT agent, action, COUNT(*) as rule_count
   FROM policy_rules
   GROUP BY agent, action
   ORDER BY rule_count DESC;
   ```

2. **Complex conditions** - Expensive matching
   ```python
   # Problem
   conditions = {
       "field1": value1,
       "field2": value2,
       "field3": value3,
       ...
   }  # Too many conditions!
   ```

3. **Wildcard overuse** - Every rule matches
   ```python
   # Problem
   PolicyRule(agent="*", action="*", ...)  # Matches everything!
   ```

**Solutions:**
- Reduce number of rules (< 50 recommended)
- Use specific agent/action instead of wildcards
- Cache policy decisions
- Profile condition matching
- Consider rule consolidation

### Issue: High Memory Usage

**Symptoms:**
- Memory growth over time
- OOM errors

**Diagnosis:**
```bash
# Check memory usage
ps aux | grep uvicorn

# Profile memory
python -m memory_profiler app/main.py
```

**Common Causes:**

1. **Approval accumulation** - Never cleaned up
   ```sql
   -- Count old approvals
   SELECT COUNT(*) FROM approvals
   WHERE requested_at < NOW() - INTERVAL '30 days';
   ```

2. **Large context objects** - MB-sized contexts
   ```python
   # Check context size
   import sys
   print(f"Context size: {sys.getsizeof(context)} bytes")
   ```

**Solutions:**
- Clean up old approvals (cron job)
- Limit context size (< 1MB)
- Use pagination for large results
- Add memory monitoring

## Integration Issues

### Issue: Guardrails Not Applied

**Symptoms:**
- Actions execute without validation
- No guardrail logs

**Diagnosis:**
```python
# Check executor initialization
from app.agents.executor import Executor

executor = Executor(db, policy_engine)
print(f"Has guardrails: {hasattr(executor, 'guardrails')}")
print(f"Guardrails type: {type(executor.guardrails)}")
```

**Common Causes:**

1. **Guardrails not initialized** - Missing in __init__
   ```python
   # Problem
   def __init__(self, db, policy_engine):
       self.db = db
       self.policy_engine = policy_engine
       # Missing: self.guardrails = create_guardrails(policy_engine)
   ```

2. **Old code path** - Not using executor
   ```python
   # Problem
   result = handler(plan)  # Direct call!
   
   # Solution
   executor = Executor(db, policy_engine)
   result = executor.execute(plan)  # Goes through guardrails
   ```

**Solutions:**
- Verify guardrails initialization
- Use executor for all agent calls
- Check logs for guardrail messages

### Issue: Policy Changes Not Applied

**Symptoms:**
- Updated rules not used
- Old behavior persists

**Diagnosis:**
```bash
# Check policy endpoint
curl http://localhost:8003/api/v1/policy | jq .rules

# Check policy engine state
python -c "
from app.policy import PolicyEngine
from app.deps import get_db
# Check current rules
engine = ... # Get from app state
print(f'Rules: {len(engine.rules)}')
for r in engine.rules[:5]:
    print(f'  {r.id}: {r.effect} (priority {r.priority})')
"
```

**Common Causes:**

1. **Policy not saved** - PUT request failed
   ```bash
   # Check response
   curl -X PUT http://localhost:8003/api/v1/policy \
     -H "Content-Type: application/json" \
     -d '{"rules": [...]}' \
     -v  # Verbose to see status
   ```

2. **Engine not reloaded** - Using cached instance
   ```python
   # Force reload
   engine = PolicyEngine.from_file("policies.json")
   ```

3. **Wrong environment** - Updated staging not prod
   ```bash
   # Check environment
   echo $ENVIRONMENT
   
   # Ensure updating correct system
   ```

**Solutions:**
- Verify PUT request succeeded
- Restart service to reload policies
- Check correct environment
- Add policy version tracking

## Debug Helpers

### Enable Debug Logging

```python
import logging

# Set policy engine logging
logging.getLogger("app.policy").setLevel(logging.DEBUG)

# Set guardrails logging
logging.getLogger("app.agents.guardrails").setLevel(logging.DEBUG)

# Set approvals logging
logging.getLogger("app.routers.approvals").setLevel(logging.DEBUG)
```

### Dry Run Mode

```python
# Test policy without executing
decision = policy_engine.decide(agent, action, context)
print(f"Would execute: {decision.effect == 'allow'}")
print(f"Reason: {decision.reason}")

# Test guardrails without executing
try:
    guardrails.validate_pre_execution(agent, action, context, plan)
    print("Guardrails passed")
except GuardrailViolation as e:
    print(f"Guardrail failed: {e.message}")
```

### Inspection Tools

```python
# List all policy rules
for rule in policy_engine.rules:
    print(f"{rule.priority:4d} | {rule.id:30s} | {rule.agent:15s} | {rule.action:15s} | {rule.effect}")

# List pending approvals
approvals = db.query(Approval).filter_by(status="pending").all()
for appr in approvals:
    age = (datetime.now(timezone.utc) - appr.requested_at).total_seconds()
    print(f"{appr.id}: {appr.agent}/{appr.action} ({age:.0f}s old)")

# Check guardrail required params
from app.agents.guardrails import REQUIRED_PARAMS
for action, params in REQUIRED_PARAMS.items():
    print(f"{action}: {', '.join(params)}")
```

## Best Practices

1. **Start permissive, tighten gradually** - Avoid over-restriction
2. **Test in staging first** - Verify behavior before prod
3. **Monitor violation rates** - Too high = process issue
4. **Log all decisions** - Essential for debugging
5. **Document complex policies** - Add reasons
6. **Regular reviews** - Remove unused rules quarterly
7. **Version policies** - Track changes in git
8. **Use structured logging** - JSON for parsing
9. **Add metrics** - Policy evaluation time, approval rates
10. **Run tests regularly** - Phase 4 has 78 tests!

## Emergency Procedures

### Kill Switch - Disable All Agents

```python
# Add emergency override rule
PolicyRule(
    id="emergency-kill-switch",
    agent="*",
    action="*",
    effect="deny",
    reason="Emergency: All agent actions disabled",
    priority=1000  # Highest priority
)
```

### Disable Policy Enforcement

```bash
# Set environment variable
export POLICY_ENFORCEMENT=disabled

# Restart service
systemctl restart applylens-api
```

### Clear Stuck Approvals

```sql
-- Mark expired approvals as rejected
UPDATE approvals
SET status = 'rejected',
    decision = 'rejected',
    approver = 'system',
    comment = 'Auto-rejected: expired'
WHERE status = 'pending'
  AND expires_at < NOW();
```

## See Also

- [Policy Management Runbook](./POLICY_MANAGEMENT.md)
- [Approval Workflows Runbook](./APPROVAL_WORKFLOWS.md)
- [Guardrails Configuration](./GUARDRAILS_CONFIG.md)
- [Phase 4 README](../../README.md#-phase-4-agent-governance--safety)
