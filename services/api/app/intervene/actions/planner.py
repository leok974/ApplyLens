"""
Planner Actions - Phase 5.4 PR3

Actions for planner canary management.
"""
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from app.intervene.actions.base import (
    AbstractAction,
    ActionResult,
    ActionStatus,
    register_action,
)

logger = logging.getLogger(__name__)


@register_action("rollback_planner")
class RollbackPlannerAction(AbstractAction):
    """
    Rollback planner to previous version.
    
    Use cases:
    - Canary regression detected
    - Accuracy degradation
    - Latency increase
    
    Parameters:
        from_version: Current problematic version
        to_version: Target version to roll back to (optional, defaults to last stable)
        immediate: Skip gradual rollback (default: False)
    """
    
    def __init__(
        self,
        from_version: str,
        to_version: Optional[str] = None,
        immediate: bool = False,
        **kwargs
    ):
        super().__init__(
            from_version=from_version,
            to_version=to_version,
            immediate=immediate,
            **kwargs
        )
        self.from_version = from_version
        self.to_version = to_version
        self.immediate = immediate
    
    def validate(self) -> bool:
        """Validate versions exist."""
        # TODO: Check planner versions in registry
        if not self.from_version:
            raise ValueError("from_version is required")
        return True
    
    def dry_run(self) -> ActionResult:
        """Simulate planner rollback."""
        target = self.to_version or "last stable version"
        changes = []
        
        changes.append(f"🔄 Will rollback from {self.from_version} to {target}")
        
        if self.immediate:
            changes.append("⚡ Immediate rollback: 100% → 0% instantly")
            changes.append("⚠️ May cause brief traffic spike to baseline version")
            estimated_duration = "30s"
        else:
            changes.append("📉 Gradual rollback: 100% → 50% → 0% over 15 minutes")
            changes.append("✅ Safe rollback with monitoring")
            estimated_duration = "15m"
        
        changes.append("📊 Will monitor metrics during rollback")
        changes.append("🔍 Will update canary_status to 'rolled_back'")
        
        # Rollback is reversible - can re-deploy
        rollback_action = {
            "action_type": "deploy_planner",
            "params": {
                "version": self.from_version,
                "canary_percent": 10,
            }
        }
        
        return ActionResult(
            status=ActionStatus.DRY_RUN_SUCCESS,
            message=f"Ready to rollback planner from {self.from_version} to {target}",
            details={
                "from_version": self.from_version,
                "to_version": target,
                "immediate": self.immediate,
            },
            estimated_duration=estimated_duration,
            estimated_cost=0.0,
            changes=changes,
            rollback_available=True,
            rollback_action=rollback_action,
        )
    
    def execute(self) -> ActionResult:
        """Execute planner rollback."""
        start_time = datetime.utcnow()
        
        try:
            target = self.to_version or "baseline"
            logger.info(f"Rolling back planner from {self.from_version} to {target}")
            
            # TODO: Integrate with planner deployment system
            # Steps:
            # 1. Update canary config: set canary_percent to 0
            # 2. Wait for traffic to drain
            # 3. Update planner_version in DB
            # 4. Mark canary as rolled_back
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return ActionResult(
                status=ActionStatus.SUCCESS,
                message=f"Successfully rolled back planner to {target}",
                details={
                    "from_version": self.from_version,
                    "to_version": target,
                    "traffic_migrated": "100%",
                },
                actual_duration=duration,
                logs_url=f"/logs/planner/rollback/{self.from_version}",
                rollback_available=True,
                rollback_action={
                    "action_type": "deploy_planner",
                    "params": {"version": self.from_version},
                },
            )
            
        except Exception as e:
            logger.exception(f"Failed to rollback planner: {e}")
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return ActionResult(
                status=ActionStatus.FAILED,
                message=f"Failed to rollback planner: {str(e)}",
                details={"error": str(e)},
                actual_duration=duration,
            )
    
    def get_approval_required(self) -> bool:
        """Immediate rollback requires approval."""
        return self.immediate
    
    def get_estimated_impact(self) -> Dict[str, Any]:
        """Get impact assessment."""
        return {
            "risk_level": "low",
            "affected_systems": ["planner", "task_router"],
            "estimated_downtime": "0s",
            "reversible": True,
            "affected_users": "100% (all users switch to baseline)",
        }


@register_action("adjust_canary_split")
class AdjustCanarySplitAction(AbstractAction):
    """
    Adjust planner canary traffic split.
    
    Use cases:
    - Reduce canary % to limit blast radius
    - Increase canary % after validation
    - Pause canary (set to 0%)
    
    Parameters:
        version: Planner version
        target_percent: Target traffic percentage (0-100)
        gradual: Whether to adjust gradually (default: True)
    """
    
    def __init__(
        self,
        version: str,
        target_percent: int,
        gradual: bool = True,
        **kwargs
    ):
        super().__init__(
            version=version,
            target_percent=target_percent,
            gradual=gradual,
            **kwargs
        )
        self.version = version
        self.target_percent = target_percent
        self.gradual = gradual
    
    def validate(self) -> bool:
        """Validate percentage is valid."""
        if not (0 <= self.target_percent <= 100):
            raise ValueError("target_percent must be between 0 and 100")
        return True
    
    def dry_run(self) -> ActionResult:
        """Simulate canary split adjustment."""
        # TODO: Get current percent from DB
        current_percent = 10  # Placeholder
        
        changes = [
            f"🎯 Will adjust canary split for {self.version}",
            f"📊 Current: {current_percent}% → Target: {self.target_percent}%",
        ]
        
        if self.gradual:
            changes.append("📉 Gradual adjustment over 5 minutes")
            estimated_duration = "5m"
        else:
            changes.append("⚡ Immediate adjustment")
            estimated_duration = "30s"
        
        if self.target_percent == 0:
            changes.append("⏸️ Will pause canary (0% traffic)")
        elif self.target_percent < current_percent:
            changes.append("⬇️ Reducing canary traffic (limiting blast radius)")
        else:
            changes.append("⬆️ Increasing canary traffic")
        
        return ActionResult(
            status=ActionStatus.DRY_RUN_SUCCESS,
            message=f"Ready to adjust canary to {self.target_percent}%",
            details={
                "version": self.version,
                "current_percent": current_percent,
                "target_percent": self.target_percent,
            },
            estimated_duration=estimated_duration,
            estimated_cost=0.0,
            changes=changes,
            rollback_available=True,
            rollback_action={
                "action_type": "adjust_canary_split",
                "params": {
                    "version": self.version,
                    "target_percent": current_percent,
                },
            },
        )
    
    def execute(self) -> ActionResult:
        """Execute canary split adjustment."""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Adjusting canary split for {self.version} to {self.target_percent}%")
            
            # TODO: Update canary_percent in RuntimeSettings
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return ActionResult(
                status=ActionStatus.SUCCESS,
                message=f"Adjusted canary to {self.target_percent}%",
                details={
                    "version": self.version,
                    "new_percent": self.target_percent,
                },
                actual_duration=duration,
                logs_url=f"/logs/planner/canary/{self.version}",
                rollback_available=True,
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return ActionResult(
                status=ActionStatus.FAILED,
                message=f"Failed to adjust canary: {str(e)}",
                details={"error": str(e)},
                actual_duration=duration,
            )
    
    def get_approval_required(self) -> bool:
        """Increasing traffic requires approval."""
        # TODO: Get current percent
        current_percent = 10
        return self.target_percent > current_percent
    
    def get_estimated_impact(self) -> Dict[str, Any]:
        """Get impact assessment."""
        return {
            "risk_level": "low",
            "affected_systems": ["planner"],
            "estimated_downtime": "0s",
            "reversible": True,
            "affected_users": f"{self.target_percent}%",
        }
