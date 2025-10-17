"""
Schemas for agent approval requests - Phase 4 PR2.

Handles approval lifecycle, HMAC signatures, and nonce protection.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    """Request for agent action approval."""
    
    agent: str = Field(..., description="Agent requesting approval")
    action: str = Field(..., description="Action requiring approval")
    context: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    reason: str = Field(..., description="Why approval is needed")
    policy_rule_id: Optional[str] = Field(None, description="Policy rule that triggered approval requirement")
    requested_by: Optional[str] = Field(None, description="User email who triggered the action")
    expires_in_hours: int = Field(24, ge=1, le=168, description="Hours until approval expires (1-168)")


class ApprovalResponse(BaseModel):
    """Response containing approval request details and signature."""
    
    request_id: str = Field(..., description="Unique approval request ID")
    agent: str
    action: str
    context: Dict[str, Any]
    reason: str
    policy_rule_id: Optional[str]
    
    status: str = Field(..., description="pending, approved, rejected, canceled, expired")
    requested_by: Optional[str]
    requested_at: datetime
    
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    expires_at: Optional[datetime] = None
    
    # Signature for secure approval links
    signature: str = Field(..., description="HMAC-SHA256 signature")
    nonce: str = Field(..., description="One-time use nonce")
    
    executed: bool = False
    executed_at: Optional[datetime] = None
    execution_result: Optional[Dict[str, Any]] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ApprovalDecision(BaseModel):
    """Approve or reject an approval request."""
    
    decision: str = Field(..., description="'approve' or 'reject'")
    comment: Optional[str] = Field(None, max_length=1024, description="Optional comment")
    reviewed_by: str = Field(..., description="User email making the decision")


class ApprovalSignature(BaseModel):
    """Signature verification for approval links."""
    
    request_id: str = Field(..., description="Approval request ID")
    nonce: str = Field(..., description="One-time nonce")
    signature: str = Field(..., description="HMAC-SHA256 signature to verify")


class ApprovalsList(BaseModel):
    """List of approval requests."""
    
    approvals: list[ApprovalResponse]
    total: int
    pending: int
    approved: int
    rejected: int
