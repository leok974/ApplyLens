"""
Incident tracking models for Phase 5.4 Interventions.

Incidents are raised when invariants fail, gates trip, or quality degrades.
They track lifecycle, evidence, and remediation actions.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import (
    Column, Integer, String, DateTime, JSON, Text, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Incident(Base):
    """
    Incident raised by watcher when invariants/gates fail.
    
    Lifecycle: open → acknowledged → mitigated → resolved → closed
    
    Fields:
        kind: Type of incident (invariant|budget|planner|bundle|gate)
        key: Unique identifier (e.g., INV_PHISHING_LABEL, planner:v2)
        severity: sev1 (critical) → sev4 (informational)
        status: Current lifecycle state
        summary: One-line description
        details: Full context including metrics, artifacts, trigger info
        issue_url: Link to created GitHub/Jira issue
        playbooks: Suggested remediation actions
        assigned_to: Person/team handling incident
        parent_id: Link to related incident (escalation)
    """
    __tablename__ = "incidents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Classification
    kind: Mapped[str] = mapped_column(String(64), nullable=False)  # invariant|budget|planner|bundle|gate
    key: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g., INV_PHISHING_LABEL
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # sev1..sev4
    
    # Lifecycle
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    mitigated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Content
    summary: Mapped[str] = mapped_column(String(256), nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    
    # Integration
    issue_url: Mapped[Optional[str]] = mapped_column(String(512))  # GitHub/Jira link
    playbooks: Mapped[list] = mapped_column(JSON, default=list)  # Suggested remediation actions
    
    # Ownership
    assigned_to: Mapped[Optional[str]] = mapped_column(String(128))
    parent_id: Mapped[Optional[int]] = mapped_column(Integer)  # Escalation chain
    
    # Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved attribute)
    incident_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_incident_status", "status"),
        Index("idx_incident_severity", "severity"),
        Index("idx_incident_kind_key", "kind", "key"),
        Index("idx_incident_created_at", "created_at"),
        Index("idx_incident_assigned", "assigned_to"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<Incident(id={self.id}, kind={self.kind}, key={self.key}, "
            f"severity={self.severity}, status={self.status})>"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "kind": self.kind,
            "key": self.key,
            "severity": self.severity,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
            "issue_url": self.issue_url,
            "playbooks": self.playbooks,
            "assigned_to": self.assigned_to,
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "mitigated_at": self.mitigated_at.isoformat() if self.mitigated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "metadata": self.incident_metadata,
        }


class IncidentAction(Base):
    """
    Actions taken on incidents (playbook execution, manual interventions).
    
    Tracks what was done, by whom, with what result.
    """
    __tablename__ = "incident_actions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Action details
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)  # playbook|manual|system
    action_name: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g., rerun_dbt
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Execution
    executed_by: Mapped[Optional[str]] = mapped_column(String(128))
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    dry_run: Mapped[bool] = mapped_column(default=True)
    
    # Results
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # pending|success|failed
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    
    # Audit
    approval_id: Mapped[Optional[int]] = mapped_column(Integer)  # Link to approvals table
    
    __table_args__ = (
        Index("idx_incident_action_incident", "incident_id"),
        Index("idx_incident_action_status", "status"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<IncidentAction(id={self.id}, incident_id={self.incident_id}, "
            f"action={self.action_name}, status={self.status})>"
        )
