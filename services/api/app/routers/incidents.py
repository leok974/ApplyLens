"""
Incidents API Router - Phase 5.4 PR1

CRUD operations for incidents plus state transitions.
SSE endpoint for live updates.

Endpoints:
- GET /incidents - List incidents (filterable)
- GET /incidents/:id - Get incident details
- POST /incidents/:id/acknowledge - Acknowledge incident
- POST /incidents/:id/mitigate - Mark as mitigated
- POST /incidents/:id/resolve - Mark as resolved
- POST /incidents/:id/close - Close incident
- GET /incidents/events - SSE stream for live updates
"""
import logging
from datetime import datetime
from typing import List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from pydantic import BaseModel, Field

from app.db import get_db
from app.models_incident import Incident, IncidentAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


# === Pydantic Models ===

class IncidentStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentSeverity(str, Enum):
    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"
    SEV4 = "sev4"


class IncidentCreate(BaseModel):
    kind: str = Field(..., max_length=64)
    key: str = Field(..., max_length=128)
    severity: IncidentSeverity
    summary: str = Field(..., max_length=256)
    details: dict = Field(default_factory=dict)
    playbooks: List[str] = Field(default_factory=list)
    assigned_to: Optional[str] = None


class IncidentUpdate(BaseModel):
    summary: Optional[str] = None
    assigned_to: Optional[str] = None
    playbooks: Optional[List[str]] = None
    metadata: Optional[dict] = None


class IncidentResponse(BaseModel):
    id: int
    kind: str
    key: str
    severity: str
    status: str
    summary: str
    details: dict
    issue_url: Optional[str]
    playbooks: List[str]
    assigned_to: Optional[str]
    parent_id: Optional[int]
    created_at: str
    acknowledged_at: Optional[str]
    mitigated_at: Optional[str]
    resolved_at: Optional[str]
    closed_at: Optional[str]
    metadata: dict

    class Config:
        from_attributes = True


class IncidentListResponse(BaseModel):
    incidents: List[IncidentResponse]
    total: int
    page: int
    per_page: int


class StateTransitionRequest(BaseModel):
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


# === Endpoints ===

@router.get("", response_model=IncidentListResponse)
def list_incidents(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    kind: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    List incidents with optional filters.
    
    Query params:
    - status: Filter by status (open, acknowledged, etc.)
    - severity: Filter by severity (sev1-sev4)
    - kind: Filter by kind (invariant, budget, planner, etc.)
    - assigned_to: Filter by assignee
    - page: Page number (1-indexed)
    - per_page: Results per page
    """
    query = db.query(Incident)
    
    # Apply filters
    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)
    if kind:
        query = query.filter(Incident.kind == kind)
    if assigned_to:
        query = query.filter(Incident.assigned_to == assigned_to)
    
    # Count total
    total = query.count()
    
    # Paginate
    offset = (page - 1) * per_page
    incidents = (
        query
        .order_by(desc(Incident.created_at))
        .offset(offset)
        .limit(per_page)
        .all()
    )
    
    return IncidentListResponse(
        incidents=[IncidentResponse(**inc.to_dict()) for inc in incidents],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
):
    """Get incident details by ID."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return IncidentResponse(**incident.to_dict())


@router.post("/{incident_id}/acknowledge")
def acknowledge_incident(
    incident_id: int,
    request: StateTransitionRequest,
    db: Session = Depends(get_db),
):
    """
    Acknowledge incident (someone is looking at it).
    
    Transition: open → acknowledged
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if incident.status != "open":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot acknowledge incident in {incident.status} state"
        )
    
    incident.status = "acknowledged"
    incident.acknowledged_at = datetime.utcnow()
    
    if request.assigned_to:
        incident.assigned_to = request.assigned_to
    
    if request.notes:
        incident.metadata = incident.metadata or {}
        incident.metadata["ack_notes"] = request.notes
    
    db.commit()
    db.refresh(incident)
    
    logger.info(f"Incident {incident_id} acknowledged")
    
    return {"success": True, "incident": IncidentResponse(**incident.to_dict())}


@router.post("/{incident_id}/mitigate")
def mitigate_incident(
    incident_id: int,
    request: StateTransitionRequest,
    db: Session = Depends(get_db),
):
    """
    Mark incident as mitigated (temporary fix applied).
    
    Transition: acknowledged → mitigated
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if incident.status not in ["open", "acknowledged"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot mitigate incident in {incident.status} state"
        )
    
    incident.status = "mitigated"
    incident.mitigated_at = datetime.utcnow()
    
    if request.notes:
        incident.metadata = incident.metadata or {}
        incident.metadata["mitigation_notes"] = request.notes
    
    db.commit()
    db.refresh(incident)
    
    logger.info(f"Incident {incident_id} mitigated")
    
    return {"success": True, "incident": IncidentResponse(**incident.to_dict())}


@router.post("/{incident_id}/resolve")
def resolve_incident(
    incident_id: int,
    request: StateTransitionRequest,
    db: Session = Depends(get_db),
):
    """
    Mark incident as resolved (root cause fixed).
    
    Transition: mitigated → resolved
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if incident.status not in ["acknowledged", "mitigated"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resolve incident in {incident.status} state"
        )
    
    incident.status = "resolved"
    incident.resolved_at = datetime.utcnow()
    
    if request.notes:
        incident.metadata = incident.metadata or {}
        incident.metadata["resolution_notes"] = request.notes
    
    db.commit()
    db.refresh(incident)
    
    logger.info(f"Incident {incident_id} resolved")
    
    return {"success": True, "incident": IncidentResponse(**incident.to_dict())}


@router.post("/{incident_id}/close")
def close_incident(
    incident_id: int,
    request: StateTransitionRequest,
    db: Session = Depends(get_db),
):
    """
    Close incident (verified no longer occurring).
    
    Transition: resolved → closed
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if incident.status not in ["resolved", "mitigated"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot close incident in {incident.status} state"
        )
    
    incident.status = "closed"
    incident.closed_at = datetime.utcnow()
    
    if request.notes:
        incident.metadata = incident.metadata or {}
        incident.metadata["close_notes"] = request.notes
    
    db.commit()
    db.refresh(incident)
    
    logger.info(f"Incident {incident_id} closed")
    
    return {"success": True, "incident": IncidentResponse(**incident.to_dict())}


@router.patch("/{incident_id}")
def update_incident(
    incident_id: int,
    update: IncidentUpdate,
    db: Session = Depends(get_db),
):
    """Update incident fields (summary, assigned_to, playbooks, metadata)."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if update.summary is not None:
        incident.summary = update.summary
    if update.assigned_to is not None:
        incident.assigned_to = update.assigned_to
    if update.playbooks is not None:
        incident.playbooks = update.playbooks
    if update.metadata is not None:
        incident.metadata = {**(incident.metadata or {}), **update.metadata}
    
    db.commit()
    db.refresh(incident)
    
    return {"success": True, "incident": IncidentResponse(**incident.to_dict())}


@router.get("/events")
async def incidents_sse(db: Session = Depends(get_db)):
    """
    Server-Sent Events stream for live incident updates.
    
    Emits events when incidents are created or updated.
    (Placeholder - full implementation would use pubsub)
    """
    async def event_generator():
        # Placeholder for SSE stream
        # In production, this would subscribe to a Redis/NATS pubsub
        yield "data: {\"type\": \"connected\"}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
