# Phase 5.5 PR1: Policy Bundle Model
# Policy registry with semantic versioning and JSON schema-validated rules

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, text, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class PolicyBundle(Base):
    """
    Policy bundle with semantic versioning.
    
    Stores a complete set of policy rules with version history.
    Only one bundle can be active at a time (canary or full rollout).
    """
    
    __tablename__ = "policy_bundles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Semantic version: MAJOR.MINOR.PATCH
    version: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    
    # JSON array of policy rules (validated against schema.json)
    rules: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Release notes / changelog
    notes: Mapped[str] = mapped_column(String(512), nullable=True)
    
    # Author/creator
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Activation status
    # - active=True: fully activated (100% traffic)
    # - active=False, canary_pct>0: canary rollout in progress
    # - active=False, canary_pct=0: draft/inactive
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Canary rollout percentage (0-100)
    canary_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Activation metadata
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    activated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    # Approval ID from Phase 4 (if activation required approval)
    approval_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Provenance (for imported bundles)
    source: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True
    )  # e.g., "imported", "api", "ui"
    
    source_signature: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True
    )  # HMAC signature for imported bundles
    
    # Metadata (tags, labels, etc.)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    
    __table_args__ = (
        Index("ix_policy_bundles_active", "active"),
        Index("ix_policy_bundles_version", "version"),
        Index("ix_policy_bundles_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<PolicyBundle(id={self.id}, version={self.version}, active={self.active}, canary_pct={self.canary_pct})>"
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "version": self.version,
            "rules": self.rules,
            "notes": self.notes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "active": self.active,
            "canary_pct": self.canary_pct,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "activated_by": self.activated_by,
            "approval_id": self.approval_id,
            "source": self.source,
            "metadata": self.metadata,
        }
