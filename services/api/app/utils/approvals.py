"""
Approvals utility for agent actions.

Phase 3: Stub implementation with policy checks.
Phase 4: Full policy engine integration with human-in-the-loop approvals.
"""

from typing import Any, Dict, Optional


class Approvals:
    """
    Approval gateway for agent actions.
    
    Enforces policy checks before allowing agents to execute
    potentially dangerous or costly operations.
    """
    
    @staticmethod
    def allow(
        agent_name: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if an action is allowed for the given agent.
        
        Args:
            agent_name: Name of the agent requesting approval
            action: Action type (e.g., 'quarantine', 'apply', 'update')
            context: Additional context for policy evaluation
                    (e.g., {'size': 100, 'risk_score': 85})
        
        Returns:
            True if action is approved, False otherwise
        
        Phase 3 Stub Logic:
        - Always allow read-only actions (query, fetch, read)
        - Deny high-risk actions without explicit approval
        - Apply basic size/budget limits
        
        Phase 4 Enhancement:
        - Full policy engine with allowlists/denylists
        - Human-in-the-loop approval workflows
        - Signed action tokens with audit trails
        - Canary mode for gradual rollouts
        """
        context = context or {}
        
        # Read-only actions are always allowed
        readonly_actions = {'query', 'fetch', 'read', 'get', 'list', 'search'}
        if action.lower() in readonly_actions:
            return True
        
        # High-risk actions require explicit gating (Phase 4)
        high_risk_actions = {'quarantine', 'delete', 'purge', 'drop'}
        if action.lower() in high_risk_actions:
            # Phase 3: Deny by default (Phase 4 will add approval workflows)
            return False
        
        # Apply basic size limits
        size_limit = context.get('size_limit', 1000)
        if 'size' in context and context['size'] > size_limit:
            return False  # Too many items to process
        
        # Apply basic budget limits
        if 'budget_exceeded' in context and context['budget_exceeded']:
            return False
        
        # Apply basic risk limits
        risk_threshold = context.get('risk_threshold', 95)
        if 'risk_score' in context and context['risk_score'] > risk_threshold:
            return False  # Too risky
        
        # Default: Allow moderate-risk actions
        # Phase 4 will add more sophisticated policy evaluation
        return True
    
    @staticmethod
    def require_approval(
        agent_name: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Request human approval for an action (Phase 4 feature).
        
        Phase 3: Returns stub response
        Phase 4: Creates approval request in database and returns ticket
        
        Args:
            agent_name: Name of the agent
            action: Action requiring approval
            context: Context for approval decision
        
        Returns:
            Approval ticket with status and ticket_id
        """
        # Phase 3 stub: Return immediate rejection
        return {
            "approved": False,
            "ticket_id": None,
            "reason": "Phase 3: Human approvals not yet implemented",
            "next_step": "Phase 4 will add approval workflows"
        }
    
    @staticmethod
    def check_budget(
        elapsed_ms: int,
        ops_count: int,
        budget_ms: Optional[int] = None,
        budget_ops: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Check if execution is within budget limits.
        
        Args:
            elapsed_ms: Time elapsed in milliseconds
            ops_count: Number of operations executed
            budget_ms: Maximum allowed time (None = no limit)
            budget_ops: Maximum allowed operations (None = no limit)
        
        Returns:
            Dict with exceeded status and details
        """
        time_exceeded = budget_ms is not None and elapsed_ms > budget_ms
        ops_exceeded = budget_ops is not None and ops_count > budget_ops
        
        return {
            "exceeded": time_exceeded or ops_exceeded,
            "time_exceeded": time_exceeded,
            "ops_exceeded": ops_exceeded,
            "elapsed_ms": elapsed_ms,
            "ops_count": ops_count,
            "budget_ms": budget_ms,
            "budget_ops": budget_ops
        }


# Convenience alias
approvals = Approvals()
