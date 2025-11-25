"""Runtime settings model for dynamic configuration.

Stores runtime configuration that can be updated without redeployment:
- Feature flags
- Canary percentages
- Kill switches
- Rate limits
"""

from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func

from .db import Base


class RuntimeSettings(Base):
    """Runtime configuration settings.

    Singleton table (only one row) with columns for various runtime settings.
    Updated via API/admin panel; read by application at startup and periodically.
    """

    __tablename__ = "runtime_settings"

    id = Column(Integer, primary_key=True, default=1)  # Singleton: always id=1

    # Planner canary controls
    planner_canary_pct = Column(Float, nullable=False, default=0.0)  # 0.0-100.0
    planner_kill_switch = Column(Boolean, nullable=False, default=False)

    # Feature flags (future use)
    feature_flags = Column(JSON, nullable=False, default=dict, server_default="{}")

    # Audit fields
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
    updated_by = Column(String(255), nullable=True)  # User/system that updated
    update_reason = Column(
        Text, nullable=True
    )  # Reason for update (e.g., "rollback triggered")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "planner_canary_pct": self.planner_canary_pct,
            "planner_kill_switch": self.planner_kill_switch,
            "feature_flags": self.feature_flags,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
            "update_reason": self.update_reason,
        }


class RuntimeSettingsDAO:
    """Data access object for RuntimeSettings.

    Handles reading and updating the singleton settings row.
    """

    def __init__(self, db_session):
        """Initialize DAO.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def get(self) -> Dict[str, Any]:
        """Get current runtime settings.

        Returns:
            Settings as dictionary, or defaults if not initialized
        """
        settings = self.db.query(RuntimeSettings).filter_by(id=1).first()
        if not settings:
            # Initialize with defaults
            settings = RuntimeSettings(
                id=1,
                planner_canary_pct=0.0,
                planner_kill_switch=False,
                feature_flags={},
                updated_by="system",
                update_reason="initial_setup",
            )
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings.to_dict()

    def update(
        self,
        updates: Dict[str, Any],
        updated_by: str = "system",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update runtime settings.

        Args:
            updates: Dictionary of fields to update
            updated_by: User/system making the update
            reason: Reason for update

        Returns:
            Updated settings as dictionary
        """
        settings = self.db.query(RuntimeSettings).filter_by(id=1).first()
        if not settings:
            # Initialize if missing
            settings = RuntimeSettings(id=1)
            self.db.add(settings)

        # Apply updates
        for key, value in updates.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        # Set audit fields
        settings.updated_by = updated_by
        settings.update_reason = reason

        self.db.commit()
        self.db.refresh(settings)
        return settings.to_dict()

    def reset_canary(self, updated_by: str = "system", reason: str = "manual_reset"):
        """Reset canary to safe defaults (0%, kill switch on).

        Args:
            updated_by: User/system making the reset
            reason: Reason for reset

        Returns:
            Updated settings
        """
        return self.update(
            {"planner_canary_pct": 0.0, "planner_kill_switch": True},
            updated_by=updated_by,
            reason=reason,
        )

    def get_planner_config(self) -> Dict[str, Any]:
        """Get planner-specific config.

        Returns:
            Canary pct and kill switch state
        """
        settings = self.get()
        return {
            "canary_pct": settings["planner_canary_pct"],
            "kill_switch": settings["planner_kill_switch"],
        }
