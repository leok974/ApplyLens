"""
Base Action Classes - Phase 5.4 PR3

Abstract base for all remediation actions with dry-run support.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class ActionStatus(str, Enum):
    """Action execution status."""

    PENDING = "pending"
    DRY_RUN_SUCCESS = "dry_run_success"
    DRY_RUN_FAILED = "dry_run_failed"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ActionResult:
    """
    Result of an action execution (dry-run or real).

    Attributes:
        status: Execution status
        message: Human-readable result message
        details: Structured result data
        estimated_duration: Estimated time (dry-run only)
        estimated_cost: Estimated cost in USD (dry-run only)
        changes: List of changes that would be made (dry-run only)
        actual_duration: Actual execution time in seconds (real run only)
        logs_url: URL to execution logs (real run only)
        rollback_available: Whether this action can be rolled back
        rollback_action: Action config for rollback (if available)
    """

    status: ActionStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    estimated_duration: Optional[str] = None
    estimated_cost: Optional[float] = None
    changes: List[str] = field(default_factory=list)
    actual_duration: Optional[float] = None
    logs_url: Optional[str] = None
    rollback_available: bool = False
    rollback_action: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "estimated_duration": self.estimated_duration,
            "estimated_cost": self.estimated_cost,
            "changes": self.changes,
            "actual_duration": self.actual_duration,
            "logs_url": self.logs_url,
            "rollback_available": self.rollback_available,
            "rollback_action": self.rollback_action,
        }


class AbstractAction(ABC):
    """
    Base class for all remediation actions.

    Subclasses must implement:
    - validate(): Check prerequisites
    - dry_run(): Simulate execution
    - execute(): Perform actual remediation

    Optional:
    - rollback(): Undo the action (if supported)
    """

    def __init__(self, **kwargs):
        """Initialize action with parameters."""
        self.params = kwargs
        self.action_type = self.__class__.__name__

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate action prerequisites.

        Check that:
        - Required parameters are present
        - Referenced resources exist
        - User has necessary permissions

        Returns:
            True if validation passes

        Raises:
            ValueError: If validation fails with specific reason
        """
        pass

    @abstractmethod
    def dry_run(self) -> ActionResult:
        """
        Simulate action execution without making changes.

        Should return:
        - List of changes that would be made
        - Estimated duration and cost
        - Potential risks or side effects

        Returns:
            ActionResult with dry-run details
        """
        pass

    @abstractmethod
    def execute(self) -> ActionResult:
        """
        Execute the remediation action.

        Must:
        - Make actual changes to systems
        - Log all operations
        - Return detailed results

        Returns:
            ActionResult with execution details
        """
        pass

    def rollback(self) -> ActionResult:
        """
        Rollback the action (optional).

        Override this if the action supports rollback.

        Returns:
            ActionResult with rollback details
        """
        return ActionResult(
            status=ActionStatus.FAILED,
            message=f"Rollback not supported for {self.action_type}",
        )

    def get_approval_required(self) -> bool:
        """
        Check if action requires approval before execution.

        Default: True for safety.
        Override to return False for low-risk actions.

        Returns:
            True if approval required
        """
        return True

    def get_estimated_impact(self) -> Dict[str, Any]:
        """
        Get impact assessment for approval UI.

        Returns:
            Dict with impact metrics (cost, downtime, affected_users, etc.)
        """
        return {
            "risk_level": "medium",
            "affected_systems": [],
            "estimated_downtime": "0s",
            "reversible": False,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize action config to dict."""
        return {
            "action_type": self.action_type,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AbstractAction":
        """Deserialize action from dict."""
        return cls(**data.get("params", {}))


class ActionRegistry:
    """
    Registry for action types.

    Allows dynamic lookup of action classes by name.
    """

    _registry: Dict[str, type] = {}

    @classmethod
    def register(cls, action_type: str, action_class: type):
        """Register an action type."""
        cls._registry[action_type] = action_class
        logger.info(f"Registered action type: {action_type}")

    @classmethod
    def get(cls, action_type: str) -> Optional[type]:
        """Get action class by type name."""
        return cls._registry.get(action_type)

    @classmethod
    def list_actions(cls) -> List[str]:
        """List all registered action types."""
        return list(cls._registry.keys())

    @classmethod
    def create(cls, action_type: str, **params) -> Optional[AbstractAction]:
        """Create action instance by type."""
        action_class = cls.get(action_type)
        if not action_class:
            raise ValueError(f"Unknown action type: {action_type}")
        return action_class(**params)


# Decorator for auto-registration
def register_action(action_type: str):
    """
    Decorator to auto-register action classes.

    Usage:
        @register_action("rerun_dbt")
        class RerunDbtAction(AbstractAction):
            ...
    """

    def decorator(cls):
        ActionRegistry.register(action_type, cls)
        return cls

    return decorator
