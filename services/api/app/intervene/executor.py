"""
Playbook Executor - Phase 5.4 PR3

Executes remediation actions with approval gates and tracking.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from sqlalchemy.orm import Session

from app.models_incident import Incident, IncidentAction
from app.intervene.actions.base import (
    ActionRegistry,
    AbstractAction,
    ActionResult,
    ActionStatus,
)

logger = logging.getLogger(__name__)


class PlaybookExecutor:
    """
    Orchestrates playbook execution for incidents.
    
    Features:
    - Dry-run before real execution
    - Approval gate integration (Phase 4)
    - Action history tracking
    - Error handling and rollback
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def list_available_actions(
        self,
        incident: Incident
    ) -> List[Dict[str, Any]]:
        """
        Get list of recommended actions for incident.
        
        Returns:
            List of action configs with metadata
        """
        actions = []
        
        # Get recommended actions from incident playbooks
        playbooks = incident.playbooks or []
        
        for playbook_name in playbooks:
            action_config = self._playbook_to_action(incident, playbook_name)
            if action_config:
                actions.append(action_config)
        
        return actions
    
    def dry_run_action(
        self,
        incident: Incident,
        action_type: str,
        params: Dict[str, Any]
    ) -> ActionResult:
        """
        Perform dry-run of action without making changes.
        
        Args:
            incident: Incident to remediate
            action_type: Type of action to simulate
            params: Action parameters
            
        Returns:
            ActionResult with dry-run details
        """
        try:
            # Create action instance
            action = ActionRegistry.create(action_type, **params)
            
            # Validate
            if not action.validate():
                return ActionResult(
                    status=ActionStatus.DRY_RUN_FAILED,
                    message="Action validation failed",
                )
            
            # Dry run
            result = action.dry_run()
            
            # Track dry run
            incident_action = IncidentAction(
                incident_id=incident.id,
                action_type=action_type,
                params=params,
                dry_run=True,
                status=result.status.value,
                result=result.to_dict(),
            )
            self.db.add(incident_action)
            self.db.commit()
            
            logger.info(f"Dry-run complete for incident {incident.id}: {action_type}")
            return result
            
        except Exception as e:
            logger.exception(f"Dry-run failed: {e}")
            return ActionResult(
                status=ActionStatus.DRY_RUN_FAILED,
                message=f"Dry-run failed: {str(e)}",
                details={"error": str(e)},
            )
    
    def execute_action(
        self,
        incident: Incident,
        action_type: str,
        params: Dict[str, Any],
        approved_by: Optional[str] = None,
    ) -> ActionResult:
        """
        Execute remediation action.
        
        Args:
            incident: Incident to remediate
            action_type: Type of action to execute
            params: Action parameters
            approved_by: User who approved (required if approval needed)
            
        Returns:
            ActionResult with execution details
        """
        try:
            # Create action instance
            action = ActionRegistry.create(action_type, **params)
            
            # Check approval requirement
            if action.get_approval_required():
                if not approved_by:
                    return ActionResult(
                        status=ActionStatus.FAILED,
                        message="Action requires approval but none provided",
                    )
                logger.info(f"Action approved by {approved_by}")
            
            # Validate
            if not action.validate():
                return ActionResult(
                    status=ActionStatus.FAILED,
                    message="Action validation failed",
                )
            
            # Execute
            logger.info(f"Executing action {action_type} for incident {incident.id}")
            result = action.execute()
            
            # Track execution
            incident_action = IncidentAction(
                incident_id=incident.id,
                action_type=action_type,
                params=params,
                dry_run=False,
                status=result.status.value,
                result=result.to_dict(),
                approved_by=approved_by,
            )
            self.db.add(incident_action)
            
            # Update incident if action succeeded
            if result.status == ActionStatus.SUCCESS:
                # Add to incident history
                history = incident.metadata.get("action_history", [])
                history.append({
                    "action_type": action_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "success",
                    "approved_by": approved_by,
                })
                incident.metadata["action_history"] = history
            
            self.db.commit()
            
            return result
            
        except Exception as e:
            logger.exception(f"Action execution failed: {e}")
            
            # Track failure
            incident_action = IncidentAction(
                incident_id=incident.id,
                action_type=action_type,
                params=params,
                dry_run=False,
                status=ActionStatus.FAILED.value,
                result={"error": str(e)},
                approved_by=approved_by,
            )
            self.db.add(incident_action)
            self.db.commit()
            
            return ActionResult(
                status=ActionStatus.FAILED,
                message=f"Execution failed: {str(e)}",
                details={"error": str(e)},
            )
    
    def rollback_action(
        self,
        incident: Incident,
        action_id: int,
    ) -> ActionResult:
        """
        Rollback a previous action.
        
        Args:
            incident: Incident
            action_id: ID of action to rollback
            
        Returns:
            ActionResult with rollback details
        """
        # Get action
        incident_action = (
            self.db.query(IncidentAction)
            .filter(
                IncidentAction.id == action_id,
                IncidentAction.incident_id == incident.id,
            )
            .first()
        )
        
        if not incident_action:
            return ActionResult(
                status=ActionStatus.FAILED,
                message=f"Action {action_id} not found",
            )
        
        # Check if rollback available
        result_dict = incident_action.result or {}
        if not result_dict.get("rollback_available"):
            return ActionResult(
                status=ActionStatus.FAILED,
                message=f"Action {incident_action.action_type} does not support rollback",
            )
        
        # Get rollback action config
        rollback_config = result_dict.get("rollback_action")
        if not rollback_config:
            return ActionResult(
                status=ActionStatus.FAILED,
                message="Rollback config not found",
            )
        
        # Execute rollback
        return self.execute_action(
            incident=incident,
            action_type=rollback_config["action_type"],
            params=rollback_config["params"],
            approved_by="system_rollback",
        )
    
    def get_action_history(self, incident: Incident) -> List[Dict[str, Any]]:
        """
        Get execution history for incident.
        
        Returns:
            List of action executions
        """
        actions = (
            self.db.query(IncidentAction)
            .filter(IncidentAction.incident_id == incident.id)
            .order_by(IncidentAction.created_at.desc())
            .all()
        )
        
        return [
            {
                "id": action.id,
                "action_type": action.action_type,
                "params": action.params,
                "dry_run": action.dry_run,
                "status": action.status,
                "result": action.result,
                "approved_by": action.approved_by,
                "created_at": action.created_at.isoformat() if action.created_at else None,
            }
            for action in actions
        ]
    
    def _playbook_to_action(
        self,
        incident: Incident,
        playbook_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Convert playbook name to action config.
        
        Maps incident-specific playbook names to concrete actions.
        """
        details = incident.details or {}
        
        # Invariant playbooks
        if playbook_name == "rerun_eval":
            return {
                "action_type": "rerun_dbt",
                "display_name": "Re-run DBT Models",
                "description": "Re-run failed dbt models to refresh data",
                "params": {
                    "task_id": details.get("task_id"),
                    "models": [],  # User must specify
                },
                "requires_approval": False,
            }
        
        # Budget playbooks
        elif playbook_name == "reduce_traffic":
            return {
                "action_type": "adjust_canary_split",
                "display_name": "Reduce Canary Traffic",
                "description": "Reduce planner canary % to lower costs",
                "params": {
                    "version": "current",  # Placeholder
                    "target_percent": 5,
                },
                "requires_approval": False,
            }
        
        elif playbook_name == "pause_agent":
            return {
                "action_type": "adjust_canary_split",
                "display_name": "Pause Canary",
                "description": "Set canary traffic to 0%",
                "params": {
                    "version": "current",
                    "target_percent": 0,
                },
                "requires_approval": True,
            }
        
        # Planner playbooks
        elif playbook_name == "rollback_planner":
            return {
                "action_type": "rollback_planner",
                "display_name": "Rollback Planner",
                "description": "Rollback to previous stable version",
                "params": {
                    "from_version": details.get("version"),
                    "to_version": None,  # Auto-detect last stable
                    "immediate": False,
                },
                "requires_approval": False,
            }
        
        elif playbook_name == "analyze_regression":
            # Not an action, just a manual step
            return {
                "action_type": "manual",
                "display_name": "Analyze Regression",
                "description": "Review metrics and logs before deciding",
                "params": {},
                "requires_approval": False,
            }
        
        else:
            logger.warning(f"Unknown playbook: {playbook_name}")
            return None
