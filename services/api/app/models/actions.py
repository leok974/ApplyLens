"""
Action models for Phase 4: Agentic Actions & Approval Loop

Models:
- ProposedAction: Queued, explainable action suggestions
- AuditAction: Immutable audit trail (who/what/why/features/screenshot)
- Policy: "Yardstick" JSON rules (enabled, priority, condition, action, confidence_threshold)
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    Boolean,
    ForeignKey,
    Float,
    Enum,
    Text,
)
from datetime import datetime
import enum

from ..db import Base


class ActionType(str, enum.Enum):
    """Available action types for agentic automation"""

    label_email = "label_email"
    archive_email = "archive_email"
    move_to_folder = "move_to_folder"
    unsubscribe_via_header = "unsubscribe_via_header"
    create_calendar_event = "create_calendar_event"
    create_task = "create_task"
    block_sender = "block_sender"
    quarantine_attachment = "quarantine_attachment"


class ProposedAction(Base):
    """
    Queued action proposals pending human-in-the-loop review.

    Lifecycle:
    1. Created by policy evaluation (status=pending)
    2. Reviewed by user (status=approved/rejected)
    3. Executed (status=executed/failed)
    """

    __tablename__ = "proposed_actions"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, index=True, nullable=False)
    action = Column(Enum(ActionType), nullable=False)
    params = Column(
        JSON, default=dict
    )  # Action-specific parameters (label name, folder, etc.)
    confidence = Column(Float, nullable=False)  # 0.0-1.0 confidence score
    rationale = Column(JSON, default=dict)  # Features, aggs, neighbors, regex hits
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(
        String, default="pending", nullable=False
    )  # pending|approved|rejected|executed|failed
    reviewed_by = Column(String, nullable=True)  # User email/id for HIL
    reviewed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ProposedAction(id={self.id}, action={self.action.value}, email_id={self.email_id}, status={self.status})>"


class AuditAction(Base):
    """
    Immutable audit trail for all executed actions.

    Records:
    - Who performed the action (user or system)
    - What action was taken with what parameters
    - Why (rationale/features that triggered it)
    - Outcome (success/fail/noop)
    - Optional screenshot for visual proof
    """

    __tablename__ = "audit_actions"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, index=True, nullable=False)
    action = Column(Enum(ActionType), nullable=False)
    params = Column(JSON, default=dict)
    actor = Column(String, nullable=False)  # "system" | user id/email
    outcome = Column(String, nullable=False)  # success|fail|noop
    error = Column(Text, nullable=True)  # Error message if outcome=fail
    why = Column(
        JSON, default=dict
    )  # Same schema as rationale (features, aggs, narrative)
    screenshot_path = Column(String, nullable=True)  # Path to PNG screenshot
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<AuditAction(id={self.id}, action={self.action.value}, actor={self.actor}, outcome={self.outcome})>"


class Policy(Base):
    """
    Yardstick policy rules for automated action proposals.

    DSL Schema:
    - condition: JSON object with Yardstick DSL (all/any/not, comparators)
    - action: ActionType enum value
    - confidence_threshold: Minimum confidence to propose (0.0-1.0)
    - priority: Lower number runs first (allows override/short-circuit)

    Example condition:
    {
      "all": [
        {"eq": ["category", "promo"]},
        {"lt": ["expires_at", "now"]}
      ]
    }
    """

    __tablename__ = "policies"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=100, nullable=False)  # Lower runs first
    condition = Column(JSON, default=dict, nullable=False)  # Yardstick DSL (JSON)
    action = Column(Enum(ActionType), nullable=False)
    confidence_threshold = Column(Float, default=0.7, nullable=False)  # 0.0-1.0
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<Policy(id={self.id}, name={self.name}, enabled={self.enabled}, priority={self.priority})>"
