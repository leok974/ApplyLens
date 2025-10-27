"""
Playbooks Router - Phase 5.4 PR3

API endpoints for executing remediation actions.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models_incident import Incident
from app.intervene.executor import PlaybookExecutor
from app.intervene.actions.base import ActionStatus

# Import actions to register them

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


# Pydantic models
class ActionRequest(BaseModel):
    """Request to execute an action."""

    action_type: str = Field(..., description="Type of action to execute")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Action parameters"
    )
    approved_by: Optional[str] = Field(
        None, description="User who approved (required if approval needed)"
    )


class ActionResponse(BaseModel):
    """Response from action execution."""

    status: str
    message: str
    details: Dict[str, Any]
    estimated_duration: Optional[str]
    estimated_cost: Optional[float]
    changes: List[str]
    actual_duration: Optional[float]
    logs_url: Optional[str]
    rollback_available: bool
    rollback_action: Optional[Dict[str, Any]]


class AvailableAction(BaseModel):
    """Available action for incident."""

    action_type: str
    display_name: str
    description: str
    params: Dict[str, Any]
    requires_approval: bool


class ActionHistoryItem(BaseModel):
    """Historical action execution."""

    id: int
    action_type: str
    params: Dict[str, Any]
    dry_run: bool
    status: str
    result: Optional[Dict[str, Any]]
    approved_by: Optional[str]
    created_at: Optional[str]


# Endpoints
@router.get("/incidents/{incident_id}/actions", response_model=List[AvailableAction])
def list_available_actions(
    incident_id: int,
    db: Session = Depends(get_db),
):
    """
    List available remediation actions for incident.

    Returns recommended actions based on incident type and playbooks.
    """
    # Get incident
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    # Get available actions
    executor = PlaybookExecutor(db)
    actions = executor.list_available_actions(incident)

    return actions


@router.post("/incidents/{incident_id}/actions/dry-run", response_model=ActionResponse)
def dry_run_action(
    incident_id: int,
    request: ActionRequest,
    db: Session = Depends(get_db),
):
    """
    Dry-run an action without making changes.

    Shows:
    - What changes would be made
    - Estimated duration and cost
    - Potential risks
    """
    # Get incident
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    # Execute dry-run
    executor = PlaybookExecutor(db)
    result = executor.dry_run_action(
        incident=incident,
        action_type=request.action_type,
        params=request.params,
    )

    return ActionResponse(**result.to_dict())


@router.post("/incidents/{incident_id}/actions/execute", response_model=ActionResponse)
def execute_action(
    incident_id: int,
    request: ActionRequest,
    db: Session = Depends(get_db),
):
    """
    Execute a remediation action.

    Requires approval if action is high-risk.
    """
    # Get incident
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    # Execute action
    executor = PlaybookExecutor(db)
    result = executor.execute_action(
        incident=incident,
        action_type=request.action_type,
        params=request.params,
        approved_by=request.approved_by,
    )

    # Return error status if failed
    if result.status == ActionStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    return ActionResponse(**result.to_dict())


@router.post(
    "/incidents/{incident_id}/actions/{action_id}/rollback",
    response_model=ActionResponse,
)
def rollback_action(
    incident_id: int,
    action_id: int,
    db: Session = Depends(get_db),
):
    """
    Rollback a previous action.

    Only works for reversible actions.
    """
    # Get incident
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    # Rollback
    executor = PlaybookExecutor(db)
    result = executor.rollback_action(incident, action_id)

    if result.status == ActionStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    return ActionResponse(**result.to_dict())


@router.get(
    "/incidents/{incident_id}/actions/history", response_model=List[ActionHistoryItem]
)
def get_action_history(
    incident_id: int,
    db: Session = Depends(get_db),
):
    """
    Get execution history for incident.

    Shows all past dry-runs and executions.
    """
    # Get incident
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    # Get history
    executor = PlaybookExecutor(db)
    history = executor.get_action_history(incident)

    return history
