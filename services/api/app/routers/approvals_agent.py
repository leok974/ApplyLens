"""
Approvals API router - Phase 4 PR2.

Handles agent action approval requests, HMAC signatures, and lifecycle management.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps.user import get_current_user_email
from ..models import AgentApproval
from ..schemas_approvals import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalSignature,
    ApprovalsList,
)
from ..settings import settings

router = APIRouter(prefix="/approvals", tags=["approvals"])


def generate_signature(request_id: str, nonce: str, secret_key: str) -> str:
    """
    Generate HMAC-SHA256 signature for approval request.
    
    Args:
        request_id: Unique approval request ID
        nonce: One-time nonce
        secret_key: Secret key for HMAC
    
    Returns:
        Hex-encoded HMAC signature
    """
    message = f"{request_id}:{nonce}".encode("utf-8")
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_signature(request_id: str, nonce: str, signature: str, secret_key: str) -> bool:
    """
    Verify HMAC-SHA256 signature for approval request.
    
    Args:
        request_id: Unique approval request ID
        nonce: One-time nonce
        signature: Signature to verify
        secret_key: Secret key for HMAC
    
    Returns:
        True if signature is valid
    """
    expected = generate_signature(request_id, nonce, secret_key)
    return hmac.compare_digest(signature, expected)


@router.post("/", response_model=ApprovalResponse)
def create_approval_request(
    body: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_email)
):
    """
    Create a new approval request for an agent action.
    
    Generates HMAC signature and nonce for secure approval links.
    """
    # Generate unique IDs
    request_id = f"apr_{secrets.token_urlsafe(16)}"
    nonce = secrets.token_urlsafe(32)
    
    # Generate signature
    secret_key = settings.SECRET_KEY or "dev-secret-key-change-in-production"
    signature = generate_signature(request_id, nonce, secret_key)
    
    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(hours=body.expires_in_hours)
    
    # Create approval record
    approval = AgentApproval(
        request_id=request_id,
        agent=body.agent,
        action=body.action,
        context=body.context,
        reason=body.reason,
        policy_rule_id=body.policy_rule_id,
        requested_by=body.requested_by or current_user,
        expires_at=expires_at,
        signature=signature,
        nonce=nonce,
        status="pending"
    )
    
    db.add(approval)
    db.commit()
    db.refresh(approval)
    
    return approval


@router.get("/", response_model=ApprovalsList)
def list_approvals(
    status: Optional[str] = Query(None, description="Filter by status"),
    agent: Optional[str] = Query(None, description="Filter by agent"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_email)
):
    """
    List approval requests with optional filters.
    
    Returns pending, approved, rejected, canceled, and expired requests.
    """
    # Build query
    query = db.query(AgentApproval)
    
    # Apply filters
    if status:
        query = query.filter(AgentApproval.status == status)
    if agent:
        query = query.filter(AgentApproval.agent == agent)
    
    # Get counts
    total = query.count()
    pending = db.query(AgentApproval).filter(AgentApproval.status == "pending").count()
    approved = db.query(AgentApproval).filter(AgentApproval.status == "approved").count()
    rejected = db.query(AgentApproval).filter(AgentApproval.status == "rejected").count()
    
    # Get paginated results
    approvals = query.order_by(AgentApproval.requested_at.desc()).offset(offset).limit(limit).all()
    
    return ApprovalsList(
        approvals=approvals,
        total=total,
        pending=pending,
        approved=approved,
        rejected=rejected
    )


@router.get("/{request_id}", response_model=ApprovalResponse)
def get_approval(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_email)
):
    """
    Get details of a specific approval request.
    """
    approval = db.query(AgentApproval).filter(AgentApproval.request_id == request_id).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    return approval


@router.post("/{request_id}/decide", response_model=ApprovalResponse)
def decide_approval(
    request_id: str,
    body: ApprovalDecision,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_email)
):
    """
    Approve or reject an approval request.
    
    Validates status and updates the approval record.
    """
    approval = db.query(AgentApproval).filter(AgentApproval.request_id == request_id).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    # Validate status
    if approval.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot decide on approval with status '{approval.status}'"
        )
    
    # Check expiration
    if approval.expires_at and datetime.utcnow() > approval.expires_at:
        approval.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Approval request has expired")
    
    # Validate decision
    if body.decision not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'")
    
    # Update approval
    approval.status = "approved" if body.decision == "approve" else "rejected"
    approval.reviewed_by = body.reviewed_by or current_user
    approval.reviewed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(approval)
    
    return approval


@router.post("/{request_id}/verify", response_model=dict)
def verify_approval_signature(
    request_id: str,
    body: ApprovalSignature,
    db: Session = Depends(get_db)
):
    """
    Verify HMAC signature and nonce for approval link.
    
    Used to validate approval links before processing.
    Implements nonce reuse protection.
    """
    approval = db.query(AgentApproval).filter(AgentApproval.request_id == request_id).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    # Check nonce reuse
    if approval.nonce_used:
        raise HTTPException(
            status_code=400,
            detail="Nonce has already been used (replay attack detected)"
        )
    
    # Check nonce match
    if approval.nonce != body.nonce:
        raise HTTPException(status_code=400, detail="Invalid nonce")
    
    # Verify signature
    secret_key = settings.SECRET_KEY or "dev-secret-key-change-in-production"
    if not verify_signature(request_id, body.nonce, body.signature, secret_key):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Mark nonce as used
    approval.nonce_used = True
    db.commit()
    
    return {
        "valid": True,
        "request_id": request_id,
        "agent": approval.agent,
        "action": approval.action,
        "status": approval.status
    }


@router.post("/{request_id}/cancel", response_model=ApprovalResponse)
def cancel_approval(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_email)
):
    """
    Cancel a pending approval request.
    
    Can only cancel requests with status 'pending'.
    """
    approval = db.query(AgentApproval).filter(AgentApproval.request_id == request_id).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel approval with status '{approval.status}'"
        )
    
    approval.status = "canceled"
    approval.reviewed_by = current_user
    approval.reviewed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(approval)
    
    return approval


@router.post("/{request_id}/execute", response_model=ApprovalResponse)
def execute_approved_action(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_email)
):
    """
    Execute an approved action.
    
    Placeholder for actual execution logic - will be implemented in PR3.
    """
    approval = db.query(AgentApproval).filter(AgentApproval.request_id == request_id).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval.status != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute action with approval status '{approval.status}'"
        )
    
    if approval.executed:
        raise HTTPException(status_code=400, detail="Action has already been executed")
    
    # Mark as executed (actual execution will be implemented in PR3)
    approval.executed = True
    approval.executed_at = datetime.utcnow()
    approval.execution_result = {
        "status": "success",
        "message": "Execution not yet implemented (Phase 4 PR3)"
    }
    
    db.commit()
    db.refresh(approval)
    
    return approval
