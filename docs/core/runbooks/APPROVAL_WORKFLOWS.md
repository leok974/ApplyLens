# Approval Workflows Runbook

**Phase 4 - Agent Governance**

This runbook covers requesting, signing, verifying, and managing approval workflows for agent actions.

## Table of Contents

- [Overview](#overview)
- [Approval Lifecycle](#approval-lifecycle)
- [Requesting Approvals](#requesting-approvals)
- [Approving/Rejecting](#approvingrerejecting)
- [Signature Verification](#signature-verification)
- [Integration with Agents](#integration-with-agents)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Approval workflows provide **human-in-the-loop** gates for high-risk agent actions. Features:

- **HMAC-SHA256 signatures** prevent tampering
- **Expiration timestamps** (default 1 hour)
- **Audit logging** of all decisions
- **Replay protection** via signature verification
- **Rich context** for informed decisions

## Approval Lifecycle

```
1. Request  → 2. Review → 3. Sign → 4. Execute → 5. Audit
   ↓             ↓          ↓         ↓           ↓
 pending    (human view) approved  executed   logged
                 ↓
              rejected
```

### States

| State | Description | Next States |
|-------|-------------|-------------|
| `pending` | Awaiting review | `approved`, `rejected` |
| `approved` | Human approved | `executed` (by agent) |
| `rejected` | Human rejected | (terminal) |
| `executed` | Action completed | (terminal) |
| `expired` | Timeout reached | (terminal) |

## Requesting Approvals

### 1. Basic Request

```bash
POST /api/v1/approvals
Content-Type: application/json

{
    "agent": "knowledge_update",
    "action": "apply",
    "context": {
        "file": "config/production.yaml",
        "changes_count": 1500,
        "risk_score": 85
    },
    "reason": "Large configuration change for production deployment"
}

# Response
{
    "id": "appr_abc123",
    "status": "pending",
    "requested_by": "agent:knowledge_update",
    "requested_at": "2025-10-17T10:30:00Z",
    "expires_at": "2025-10-17T11:30:00Z",
    "agent": "knowledge_update",
    "action": "apply",
    "context": {...},
    "reason": "Large configuration change for production deployment"
}
```

### 2. With Custom Expiration

```bash
POST /api/v1/approvals

{
    "agent": "inbox_triage",
    "action": "quarantine",
    "context": {"email_id": "email_123", "risk_score": 92},
    "reason": "High-risk email quarantine",
    "expires_in_seconds": 7200  # 2 hours
}
```

### 3. Programmatic Request

```python
from app.schemas_approvals import ApprovalRequest
from app.routers.approvals import create_approval_request

request = ApprovalRequest(
    agent="knowledge_update",
    action="apply",
    context={"file": "config.yaml", "changes_count": 1500},
    reason="Large config change"
)

approval = await create_approval_request(request, db)
print(f"Approval ID: {approval.id}")
print(f"Expires: {approval.expires_at}")
```

## Approving/Rejecting

### 1. Approve Request

```bash
POST /api/v1/approvals/appr_abc123/approve
Content-Type: application/json

{
    "decision": "approved",
    "approver": "user@company.com",
    "comment": "Reviewed changes - looks safe",
    "signature": "a3f7c2d1e5b8..."  # HMAC-SHA256
}

# Response
{
    "id": "appr_abc123",
    "status": "approved",
    "decision": "approved",
    "approver": "user@company.com",
    "approved_at": "2025-10-17T10:45:00Z",
    "comment": "Reviewed changes - looks safe",
    "signature": "a3f7c2d1e5b8..."
}
```

### 2. Reject Request

```bash
POST /api/v1/approvals/appr_abc123/approve

{
    "decision": "rejected",
    "approver": "user@company.com",
    "comment": "Changes too risky - needs redesign",
    "signature": "b8e5d1c2a3f7..."
}
```

### 3. Generate Signature

The signature prevents tampering and proves the approver reviewed the request.

**Formula:**
```
signature = HMAC-SHA256(
    key=HMAC_SECRET,
    message=f"{approval_id}:{decision}:{approver}:{expires_at_iso}"
)
```

**Python Example:**
```python
import hmac
import hashlib
from datetime import datetime

def generate_approval_signature(
    approval_id: str,
    decision: str,
    approver: str,
    expires_at: datetime,
    secret: str
) -> str:
    """Generate HMAC-SHA256 signature for approval."""
    expires_iso = expires_at.isoformat()
    message = f"{approval_id}:{decision}:{approver}:{expires_iso}"
    
    signature = hmac.new(
        key=secret.encode(),
        msg=message.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return signature

# Usage
from app.settings import settings

approval_id = "appr_abc123"
decision = "approved"
approver = "user@company.com"
expires_at = datetime(2025, 10, 17, 11, 30, 0)

sig = generate_approval_signature(
    approval_id, decision, approver, expires_at,
    secret=settings.HMAC_SECRET
)

print(f"Signature: {sig}")
```

**CLI Helper:**
```bash
# Generate signature using Python
python -c "
import hmac, hashlib
from datetime import datetime

approval_id = 'appr_abc123'
decision = 'approved'
approver = 'user@company.com'
expires_at = '2025-10-17T11:30:00+00:00'
secret = 'your-hmac-secret'

msg = f'{approval_id}:{decision}:{approver}:{expires_at}'
sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
print(sig)
"
```

## Signature Verification

### 1. Verify Approval

```bash
POST /api/v1/approvals/appr_abc123/verify
Content-Type: application/json

{
    "signature": "a3f7c2d1e5b8..."
}

# Response (valid)
{
    "valid": true,
    "approval": {
        "id": "appr_abc123",
        "status": "approved",
        "decision": "approved",
        "approver": "user@company.com",
        "expires_at": "2025-10-17T11:30:00Z"
    }
}

# Response (invalid)
{
    "valid": false,
    "error": "Invalid signature"
}
```

### 2. Programmatic Verification

```python
from app.utils.approvals import verify_approval_signature

is_valid = verify_approval_signature(
    approval_id="appr_abc123",
    decision="approved",
    approver="user@company.com",
    expires_at=datetime(2025, 10, 17, 11, 30, 0),
    signature="a3f7c2d1e5b8...",
    secret=settings.HMAC_SECRET
)

if not is_valid:
    raise ValueError("Invalid approval signature")
```

### 3. Expiration Check

```python
from datetime import datetime, timezone

if approval.expires_at < datetime.now(timezone.utc):
    raise ValueError("Approval has expired")
```

## Integration with Agents

### 1. Agent Requests Approval

```python
from app.routers.approvals import create_approval_request

# Agent detects high-risk action
if risk_score >= 70:
    # Request approval
    approval_request = ApprovalRequest(
        agent="inbox_triage",
        action="quarantine",
        context={
            "email_id": email_id,
            "risk_score": risk_score,
            "reason": "Suspected phishing"
        },
        reason=f"High-risk email (score={risk_score}) requires review"
    )
    
    approval = await create_approval_request(approval_request, db)
    
    # Wait for approval (polling or webhook)
    logger.info(f"Waiting for approval: {approval.id}")
    return {"status": "pending_approval", "approval_id": approval.id}
```

### 2. Agent Executes with Approval

```python
from app.agents.executor import Executor

# Agent receives approval
approval_id = "appr_abc123"

# Execute with approval
executor = Executor(db, policy_engine)
result = await executor.execute(
    plan={
        "agent": "inbox_triage",
        "action": "quarantine",
        "context": {"email_id": "email_123"}
    },
    approval_id=approval_id  # Pass approval ID
)

# Executor verifies:
# 1. Approval exists
# 2. Status is "approved"
# 3. Signature is valid
# 4. Not expired
# 5. Agent/action match request
```

### 3. Guardrails Check Approval

```python
from app.agents.guardrails import ExecutionGuardrails

guardrails = ExecutionGuardrails(policy_engine)

# Pre-execution validation
decision = guardrails.validate_pre_execution(
    agent="inbox_triage",
    action="quarantine",
    context={"risk_score": 85, "email_id": "email_123"},
    plan={...}
)

# If requires_approval=True, executor must have approval_id
if decision.requires_approval and not approval_id:
    raise GuardrailViolation(
        message="Action requires human approval",
        violation_type="approval_required",
        details={
            "agent": agent,
            "action": action,
            "reason": decision.reason
        }
    )
```

## Security Best Practices

### 1. Secret Management

**DO:**
- Store `HMAC_SECRET` in secure vault (e.g., AWS Secrets Manager)
- Rotate secrets regularly (quarterly recommended)
- Use different secrets per environment
- Never commit secrets to git

**DON'T:**
- Use default/weak secrets
- Share secrets via email/chat
- Log or print secrets
- Reuse secrets across systems

**Example: Environment-Specific Secrets**
```bash
# .env.production
HMAC_SECRET=prod-secret-abc123...

# .env.staging
HMAC_SECRET=staging-secret-def456...

# .env.development
HMAC_SECRET=dev-secret-ghi789...
```

### 2. Expiration Times

**Recommendations:**

| Action Type | Expiration | Rationale |
|-------------|------------|-----------|
| Urgent (quarantine) | 30 min | Quick response needed |
| Standard (config change) | 1 hour | Default |
| Non-urgent (reports) | 24 hours | Can wait for business hours |
| Emergency override | 5 min | Minimize attack window |

**Configuration:**
```python
# Short-lived for critical actions
ApprovalRequest(
    ...,
    expires_in_seconds=300  # 5 minutes
)

# Longer for routine approvals
ApprovalRequest(
    ...,
    expires_in_seconds=86400  # 24 hours
)
```

### 3. Audit Logging

Enable comprehensive audit trails:

```python
import logging

logger = logging.getLogger("approvals")

# Log all approval events
logger.info(
    "approval_requested",
    extra={
        "approval_id": approval.id,
        "agent": approval.agent,
        "action": approval.action,
        "requested_by": approval.requested_by,
        "context": approval.context
    }
)

logger.info(
    "approval_decided",
    extra={
        "approval_id": approval.id,
        "decision": approval.decision,
        "approver": approval.approver,
        "signature_valid": True
    }
)
```

### 4. Replay Protection

Prevent reuse of old approvals:

```python
# Mark approval as executed
approval.status = "executed"
approval.executed_at = datetime.now(timezone.utc)
db.commit()

# Check status before use
if approval.status != "approved":
    raise ValueError(f"Approval not in approved state: {approval.status}")
```

### 5. Context Validation

Ensure approval context matches execution:

```python
# Store context hash with approval
import hashlib
import json

context_json = json.dumps(context, sort_keys=True)
context_hash = hashlib.sha256(context_json.encode()).hexdigest()

# Verify at execution time
if approval.context_hash != context_hash:
    raise ValueError("Execution context doesn't match approval")
```

## Troubleshooting

### Issue: Invalid Signature

**Symptoms:**
```
{"valid": false, "error": "Invalid signature"}
```

**Diagnosis:**
1. Check HMAC_SECRET matches between systems
2. Verify signature generation formula
3. Check for whitespace/encoding issues
4. Validate expires_at format (ISO 8601)

**Solution:**
```python
# Debug: Print signature components
approval_id = "appr_abc123"
decision = "approved"
approver = "user@company.com"
expires_at = "2025-10-17T11:30:00+00:00"

message = f"{approval_id}:{decision}:{approver}:{expires_at}"
print(f"Message: {message}")

# Ensure timezone info present
from datetime import datetime, timezone
dt = datetime(2025, 10, 17, 11, 30, 0, tzinfo=timezone.utc)
print(f"Expires ISO: {dt.isoformat()}")
```

### Issue: Approval Expired

**Symptoms:**
```
ValueError: Approval has expired
```

**Diagnosis:**
- Check expires_at timestamp
- Verify system clocks synchronized
- Review expiration time setting

**Solution:**
```python
# Extend expiration (if allowed)
from datetime import timedelta

approval.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
db.commit()

# Or request new approval
```

### Issue: Agent/Action Mismatch

**Symptoms:**
```
GuardrailViolation: Agent/action doesn't match approval
```

**Diagnosis:**
- Compare approval.agent vs execution agent
- Compare approval.action vs execution action
- Check for typos in names

**Solution:**
```python
# Ensure exact match
assert execution_agent == approval.agent
assert execution_action == approval.action
```

### Issue: Approval Not Found

**Symptoms:**
```
404 Not Found: Approval not found
```

**Diagnosis:**
- Verify approval_id format
- Check database connection
- Confirm approval wasn't deleted

**Solution:**
```python
# List recent approvals
approvals = db.query(Approval).order_by(
    Approval.requested_at.desc()
).limit(10).all()

for appr in approvals:
    print(f"{appr.id}: {appr.agent}/{appr.action} - {appr.status}")
```

### Issue: Cannot Approve Twice

**Symptoms:**
```
ValueError: Approval already decided
```

**Diagnosis:**
- Check approval.status
- Review audit logs for previous decision

**Solution:**
- This is intentional (prevents tampering)
- Request new approval if needed

```python
# Check status before attempting to approve
if approval.status != "pending":
    logger.error(f"Approval {approval.id} already {approval.status}")
    # Request new approval
```

## Best Practices

1. **Short expiration for high-risk actions** (5-30 min)
2. **Always log approval decisions** (audit trail)
3. **Validate context matches** between request and execution
4. **Use structured context** (JSON serializable)
5. **Include rich reason** for human reviewers
6. **Mark as executed** after use (prevent replay)
7. **Monitor approval rates** (too many = process issue)
8. **Regular secret rotation** (quarterly minimum)

## See Also

- [Policy Management Runbook](./POLICY_MANAGEMENT.md)
- [Guardrails Configuration](./GUARDRAILS_CONFIG.md)
- [Phase 4 Troubleshooting](./PHASE4_TROUBLESHOOTING.md)
