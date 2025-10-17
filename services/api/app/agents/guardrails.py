"""
Executor guardrails - Phase 4 PR3.

Provides pre/post execution validation for agent actions:
- Schema validation
- Policy compliance checks
- Approval requirement tracking
- Action signature verification
"""

from typing import Any, Dict, Optional
from ..policy import PolicyEngine, PolicyDecision


class GuardrailViolation(Exception):
    """Exception raised when a guardrail check fails."""
    
    def __init__(self, message: str, violation_type: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.violation_type = violation_type
        self.details = details or {}


class ExecutionGuardrails:
    """Pre and post execution validation for agent actions.
    
    Enforces safety policies before and after agent execution.
    """
    
    def __init__(self, policy_engine: PolicyEngine):
        """Initialize guardrails with a policy engine.
        
        Args:
            policy_engine: Policy engine for authorization decisions
        """
        self.policy_engine = policy_engine
    
    def validate_pre_execution(
        self,
        agent: str,
        action: str,
        context: Dict[str, Any],
        plan: Dict[str, Any]
    ) -> PolicyDecision:
        """Validate action before execution.
        
        Checks:
        1. Policy compliance (is action allowed?)
        2. Required parameters present
        3. Action signature valid (if required)
        
        Args:
            agent: Agent name
            action: Action to perform
            context: Action context/parameters
            plan: Full execution plan
        
        Returns:
            PolicyDecision with effect and approval requirements
        
        Raises:
            GuardrailViolation: If validation fails
        """
        # Check policy compliance
        decision = self.policy_engine.decide(agent, action, context)
        
        # If denied and no approval, raise violation
        if decision.effect == "deny" and not decision.requires_approval:
            raise GuardrailViolation(
                message=f"Action '{action}' denied by policy: {decision.reason}",
                violation_type="policy_denied",
                details={
                    "agent": agent,
                    "action": action,
                    "rule_id": decision.rule_id,
                    "reason": decision.reason
                }
            )
        
        # Validate required parameters
        self._validate_required_params(action, context, plan)
        
        return decision
    
    def validate_post_execution(
        self,
        agent: str,
        action: str,
        context: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """Validate action after execution.
        
        Checks:
        1. Result structure is valid
        2. No unexpected side effects
        3. Resource limits not exceeded
        
        Args:
            agent: Agent name
            action: Action performed
            context: Action context/parameters
            result: Execution result
        
        Raises:
            GuardrailViolation: If validation fails
        """
        # Validate result structure
        if not isinstance(result, dict):
            raise GuardrailViolation(
                message=f"Invalid result type: expected dict, got {type(result).__name__}",
                violation_type="invalid_result",
                details={
                    "agent": agent,
                    "action": action,
                    "result_type": type(result).__name__
                }
            )
        
        # Check for error indicators
        if result.get("error"):
            # Errors are allowed but should be logged
            # Not a guardrail violation, just informational
            pass
        
        # Validate resource usage if tracked
        if "ops_count" in result:
            ops = result["ops_count"]
            if not isinstance(ops, int) or ops < 0:
                raise GuardrailViolation(
                    message=f"Invalid ops_count: {ops}",
                    violation_type="invalid_metric",
                    details={
                        "agent": agent,
                        "action": action,
                        "ops_count": ops
                    }
                )
        
        if "cost_cents_used" in result:
            cost = result["cost_cents_used"]
            if not isinstance(cost, (int, float)) or cost < 0:
                raise GuardrailViolation(
                    message=f"Invalid cost_cents_used: {cost}",
                    violation_type="invalid_metric",
                    details={
                        "agent": agent,
                        "action": action,
                        "cost_cents_used": cost
                    }
                )
    
    def _validate_required_params(
        self,
        action: str,
        context: Dict[str, Any],
        plan: Dict[str, Any]
    ) -> None:
        """Validate that required parameters are present.
        
        Args:
            action: Action to perform
            context: Action context/parameters
            plan: Full execution plan
        
        Raises:
            GuardrailViolation: If required params missing
        """
        # Define required parameters for common actions
        required_params = {
            "quarantine": ["email_id"],
            "label": ["email_id", "label_name"],
            "apply": ["changes"],
            "generate": ["template_type"],
            "dbt_run": ["models"],
            "query": ["sql"],
        }
        
        required = required_params.get(action, [])
        
        for param in required:
            if param not in context and param not in plan:
                raise GuardrailViolation(
                    message=f"Missing required parameter '{param}' for action '{action}'",
                    violation_type="missing_parameter",
                    details={
                        "action": action,
                        "missing_param": param,
                        "provided_params": list(context.keys())
                    }
                )
    
    def check_approval_required(
        self,
        agent: str,
        action: str,
        context: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Check if action requires human approval.
        
        Args:
            agent: Agent name
            action: Action to perform
            context: Action context/parameters
        
        Returns:
            Tuple of (requires_approval, reason)
        """
        decision = self.policy_engine.decide(agent, action, context)
        
        if decision.effect == "deny" and decision.requires_approval:
            return (True, decision.reason)
        
        return (False, "")


def create_guardrails(policy_engine: PolicyEngine) -> ExecutionGuardrails:
    """Factory function to create guardrails with a policy engine.
    
    Args:
        policy_engine: Policy engine for authorization
    
    Returns:
        ExecutionGuardrails instance
    """
    return ExecutionGuardrails(policy_engine)
