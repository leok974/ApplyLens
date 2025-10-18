"""
Policy bundle activation endpoints.

Provides activation, promotion, and rollback operations with approval gates.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from ..database import get_db
from ..policy.activate import (
    activate_bundle,
    check_canary_gates,
    promote_canary,
    rollback_bundle,
    get_canary_status,
    ActivationError,
    CanaryGate
)


router = APIRouter(prefix="/policy/bundles", tags=["policy-activation"])


# Request/Response Models

class ActivateRequest(BaseModel):
    """Request to activate a policy bundle."""
    approval_id: int = Field(..., description="Required approval ID from Phase 5.4")
    canary_pct: int = Field(10, ge=0, le=100, description="Initial canary percentage")
    activated_by: str = Field(..., min_length=1, description="Username of activator")


class ActivateResponse(BaseModel):
    """Response from bundle activation."""
    id: int
    version: str
    active: bool
    canary_pct: int
    activated_at: str
    activated_by: str
    approval_id: int
    message: str


class CanaryGateConfig(BaseModel):
    """Quality gate configuration."""
    max_error_rate: float = Field(0.05, description="Maximum error rate (default 5%)")
    max_deny_rate: float = Field(0.30, description="Maximum deny rate (default 30%)")
    max_cost_increase: float = Field(0.20, description="Maximum cost increase (default 20%)")
    min_sample_size: int = Field(100, description="Minimum decisions (default 100)")


class CheckGatesRequest(BaseModel):
    """Request to check canary quality gates."""
    metrics: Dict[str, Any] = Field(..., description="Performance metrics from monitoring")
    gate_config: Optional[CanaryGateConfig] = Field(None, description="Custom gate config")


class CheckGatesResponse(BaseModel):
    """Response from gate check."""
    passed: bool
    failures: List[str]
    canary_status: Dict[str, Any]


class PromoteRequest(BaseModel):
    """Request to promote canary."""
    target_pct: int = Field(100, ge=0, le=100, description="Target percentage")


class PromoteResponse(BaseModel):
    """Response from promotion."""
    id: int
    version: str
    canary_pct: int
    message: str


class RollbackRequest(BaseModel):
    """Request to rollback a bundle."""
    reason: str = Field(..., min_length=10, description="Reason for rollback")
    rolled_back_by: str = Field(..., min_length=1, description="Username initiating rollback")
    create_incident: bool = Field(True, description="Whether to create incident")


class RollbackResponse(BaseModel):
    """Response from rollback."""
    id: int
    version: str
    rolled_back_from: str
    active: bool
    canary_pct: int
    message: str
    incident_created: bool


class CanaryStatusResponse(BaseModel):
    """Canary status information."""
    bundle_id: int
    version: str
    active: bool
    canary_pct: int
    activated_at: Optional[str]
    activated_by: Optional[str]
    time_active_seconds: Optional[float]
    promotion_eligible: bool
    fully_promoted: bool


# Endpoints

@router.post("/{bundle_id}/activate", response_model=ActivateResponse, status_code=status.HTTP_200_OK)
async def activate_policy_bundle(
    bundle_id: int,
    request: ActivateRequest,
    db: Session = Depends(get_db)
):
    """
    Activate a policy bundle with approval gate.
    
    Requires approval from Phase 5.4 system. Starts with canary rollout
    (default 10%) for quality monitoring before full promotion.
    
    - Deactivates current active bundle
    - Activates new bundle at canary percentage
    - Records activation metadata
    """
    try:
        bundle = activate_bundle(
            db=db,
            bundle_id=bundle_id,
            approval_id=request.approval_id,
            activated_by=request.activated_by,
            canary_pct=request.canary_pct
        )
        
        return ActivateResponse(
            id=bundle.id,
            version=bundle.version,
            active=bundle.active,
            canary_pct=bundle.canary_pct,
            activated_at=bundle.activated_at.isoformat(),
            activated_by=bundle.activated_by,
            approval_id=bundle.approval_id,
            message=f"Bundle {bundle.version} activated at {bundle.canary_pct}% canary"
        )
    except ActivationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{bundle_id}/check-gates", response_model=CheckGatesResponse, status_code=status.HTTP_200_OK)
async def check_bundle_gates(
    bundle_id: int,
    request: CheckGatesRequest,
    db: Session = Depends(get_db)
):
    """
    Check if canary meets quality gates for promotion.
    
    Evaluates performance metrics against thresholds:
    - Error rate < 5%
    - Deny rate < 30%
    - Cost increase < 20%
    - Sample size >= 100 decisions
    
    Returns pass/fail with specific failure reasons.
    """
    # Build gate config
    gate = None
    if request.gate_config:
        gate = CanaryGate(
            max_error_rate=request.gate_config.max_error_rate,
            max_deny_rate=request.gate_config.max_deny_rate,
            max_cost_increase=request.gate_config.max_cost_increase,
            min_sample_size=request.gate_config.min_sample_size
        )
    
    passed, failures = check_canary_gates(
        db=db,
        bundle_id=bundle_id,
        metrics=request.metrics,
        gate=gate
    )
    
    canary_status = get_canary_status(db=db, bundle_id=bundle_id)
    
    return CheckGatesResponse(
        passed=passed,
        failures=failures,
        canary_status=canary_status
    )


@router.post("/{bundle_id}/promote", response_model=PromoteResponse, status_code=status.HTTP_200_OK)
async def promote_policy_bundle(
    bundle_id: int,
    request: PromoteRequest,
    db: Session = Depends(get_db)
):
    """
    Promote canary to higher percentage.
    
    Increases canary traffic allocation. Typically:
    - 10% → 50% (partial promotion)
    - 50% → 100% (full promotion)
    
    Requires quality gates to pass before promotion.
    """
    try:
        bundle = promote_canary(
            db=db,
            bundle_id=bundle_id,
            target_pct=request.target_pct
        )
        
        return PromoteResponse(
            id=bundle.id,
            version=bundle.version,
            canary_pct=bundle.canary_pct,
            message=f"Bundle {bundle.version} promoted to {bundle.canary_pct}%"
        )
    except ActivationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{bundle_id}/rollback", response_model=RollbackResponse, status_code=status.HTTP_200_OK)
async def rollback_policy_bundle(
    bundle_id: int,
    request: RollbackRequest,
    db: Session = Depends(get_db)
):
    """
    Rollback to previous policy version.
    
    Emergency operation to revert to last stable version:
    - Deactivates current bundle
    - Reactivates previous version at 100%
    - Records rollback metadata
    - Creates high-severity incident (if enabled)
    
    Used when:
    - Quality gates fail during canary
    - Unexpected policy behavior detected
    - Manual intervention required
    """
    try:
        previous = rollback_bundle(
            db=db,
            bundle_id=bundle_id,
            reason=request.reason,
            rolled_back_by=request.rolled_back_by,
            create_incident=request.create_incident
        )
        
        # Get current bundle version for response
        from ..models_policy import PolicyBundle
        current = db.query(PolicyBundle).filter(PolicyBundle.id == bundle_id).first()
        
        return RollbackResponse(
            id=previous.id,
            version=previous.version,
            rolled_back_from=current.version if current else "unknown",
            active=previous.active,
            canary_pct=previous.canary_pct,
            message=f"Rolled back to {previous.version}",
            incident_created=request.create_incident
        )
    except ActivationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{bundle_id}/canary-status", response_model=CanaryStatusResponse, status_code=status.HTTP_200_OK)
async def get_bundle_canary_status(
    bundle_id: int,
    db: Session = Depends(get_db)
):
    """
    Get current canary status for monitoring.
    
    Returns:
    - Canary percentage
    - Time since activation
    - Promotion eligibility (24h minimum)
    - Activation metadata
    
    Used for dashboards and monitoring tools.
    """
    status_data = get_canary_status(db=db, bundle_id=bundle_id)
    
    if "error" in status_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=status_data["error"])
    
    return CanaryStatusResponse(**status_data)
