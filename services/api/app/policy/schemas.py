"""
Policy schemas for agent authorization and budgets.
"""

from typing import Literal, Dict, Any, Optional
from pydantic import BaseModel, Field


# Effect types for policy rules
Effect = Literal["allow", "deny"]


class PolicyRule(BaseModel):
    """
    A policy rule that controls agent actions.
    
    Rules are evaluated in order with precedence: deny > allow > default.
    """
    id: str = Field(..., description="Unique identifier for the rule")
    agent: str | Literal["*"] = Field(
        default="*",
        description="Agent name or '*' for all agents"
    )
    action: str | Literal["*"] = Field(
        default="*",
        description="Action name or '*' for all actions"
    )
    conditions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Conditions that must match for rule to apply"
    )
    effect: Effect = Field(
        default="deny",
        description="Whether to allow or deny the action"
    )
    reason: str = Field(
        default="",
        description="Human-readable reason for the policy"
    )
    priority: int = Field(
        default=0,
        description="Higher priority rules are evaluated first"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "deny-large-diffs",
                "agent": "knowledge_update",
                "action": "apply",
                "conditions": {"changes_count": 1000},
                "effect": "deny",
                "reason": "Large diffs (>1000 changes) require manual review",
                "priority": 100
            }
        }


class Budget(BaseModel):
    """
    Resource budgets for agent execution.
    
    All budgets are optional. If not specified, no limit is enforced.
    """
    ms: Optional[int] = Field(
        default=None,
        description="Maximum execution time in milliseconds",
        ge=0
    )
    ops: Optional[int] = Field(
        default=None,
        description="Maximum number of operations (queries, API calls)",
        ge=0
    )
    cost_cents: Optional[int] = Field(
        default=None,
        description="Maximum estimated cost in cents (for cloud APIs)",
        ge=0
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "ms": 30000,
                "ops": 100,
                "cost_cents": 50
            }
        }
    
    def has_limit(self) -> bool:
        """Check if any budget limit is set."""
        return self.ms is not None or self.ops is not None or self.cost_cents is not None
    
    def is_exceeded(
        self,
        elapsed_ms: Optional[int] = None,
        ops_used: Optional[int] = None,
        cost_cents_used: Optional[int] = None
    ) -> dict:
        """
        Check if budget limits are exceeded.
        
        Returns:
            Dict with exceeded status and details
        """
        exceeded = False
        details = {}
        
        if self.ms is not None and elapsed_ms is not None:
            time_exceeded = elapsed_ms > self.ms
            details["time_exceeded"] = time_exceeded
            details["time_limit"] = self.ms
            details["time_used"] = elapsed_ms
            exceeded = exceeded or time_exceeded
        
        if self.ops is not None and ops_used is not None:
            ops_exceeded = ops_used > self.ops
            details["ops_exceeded"] = ops_exceeded
            details["ops_limit"] = self.ops
            details["ops_used"] = ops_used
            exceeded = exceeded or ops_exceeded
        
        if self.cost_cents is not None and cost_cents_used is not None:
            cost_exceeded = cost_cents_used > self.cost_cents
            details["cost_exceeded"] = cost_exceeded
            details["cost_limit"] = self.cost_cents
            details["cost_used"] = cost_cents_used
            exceeded = exceeded or cost_exceeded
        
        return {
            "exceeded": exceeded,
            **details
        }


class PolicyDecision(BaseModel):
    """
    Result of policy evaluation.
    """
    effect: Effect = Field(..., description="Whether the action is allowed or denied")
    reason: str = Field(..., description="Reason for the decision")
    rule_id: Optional[str] = Field(None, description="ID of the matching rule")
    requires_approval: bool = Field(
        default=False,
        description="Whether human approval is required"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "effect": "deny",
                "reason": "Large diffs (>1000 changes) require manual review",
                "rule_id": "deny-large-diffs",
                "requires_approval": True
            }
        }
