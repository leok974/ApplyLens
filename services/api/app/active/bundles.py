"""Config bundle management for active learning.

Handles:
- Bundle generation from trained models
- Approval workflow for config changes
- Atomic apply with backup/rollback
- Canary deployment integration

Design:
- Bundles stored in runtime_settings
- Approval required before apply
- Automatic backup of old configs
- Canary rollout via PlannerSwitchboard
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from app.models import AgentApproval
from app.models_runtime import RuntimeSettings
from app.active.heur_trainer import HeuristicTrainer

logger = logging.getLogger(__name__)


class BundleManager:
    """Manage config bundles and deployment."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_bundle(
        self,
        agent: str,
        min_examples: int = 50,
        model_type: str = "logistic"
    ) -> Optional[Dict[str, Any]]:
        """Create a new config bundle for an agent.
        
        Args:
            agent: Agent name
            min_examples: Minimum labeled examples required
            model_type: "logistic" or "tree"
        
        Returns:
            Bundle dict, or None if insufficient data
        """
        trainer = HeuristicTrainer(self.db)
        
        bundle = trainer.train_for_agent(agent, min_examples=min_examples, model_type=model_type)
        
        if not bundle:
            logger.info(f"Could not create bundle for {agent}: insufficient data")
            return None
        
        # Add bundle ID and status
        bundle["bundle_id"] = f"{agent}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        bundle["status"] = "pending"
        
        # Store bundle in runtime_settings
        self._save_bundle(agent, bundle)
        
        logger.info(f"Created bundle {bundle['bundle_id']} for {agent}")
        
        return bundle
    
    def propose_bundle(
        self,
        agent: str,
        bundle_id: str,
        proposer: str = "system"
    ) -> str:
        """Propose a bundle for approval.
        
        Args:
            agent: Agent name
            bundle_id: Bundle identifier
            proposer: Who is proposing (user or system)
        
        Returns:
            Approval request ID
        """
        bundle = self._load_bundle(agent, bundle_id)
        
        if not bundle:
            raise ValueError(f"Bundle {bundle_id} not found for {agent}")
        
        # Get current bundle for diff
        current_bundle = self._load_active_bundle(agent)
        
        # Generate diff
        trainer = HeuristicTrainer(self.db)
        diff = trainer.generate_diff(agent, current_bundle, bundle)
        
        # Create approval request
        approval = AgentApproval(
            agent=agent,
            action="apply_bundle",
            context={
                "bundle_id": bundle_id,
                "diff": diff,
                "bundle": bundle
            },
            status="pending",
            requested_by=proposer
        )
        
        self.db.add(approval)
        self.db.commit()
        
        logger.info(f"Proposed bundle {bundle_id} for {agent} (approval {approval.id})")
        
        return approval.id
    
    def approve_bundle(
        self,
        approval_id: str,
        approver: str,
        rationale: Optional[str] = None
    ):
        """Approve a bundle for deployment.
        
        Args:
            approval_id: Approval request ID
            approver: Who is approving
            rationale: Approval rationale
        """
        approval = self.db.query(AgentApproval).filter_by(id=approval_id).first()
        
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval.status != "pending":
            raise ValueError(f"Approval {approval_id} is not pending (status={approval.status})")
        
        # Update approval
        approval.status = "approved"
        approval.approved_by = approver
        approval.rationale = rationale
        approval.approved_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Approved bundle {approval.context['bundle_id']} for {approval.agent}")
        
        # Note: Actual apply happens separately via apply_approved_bundle
    
    def apply_approved_bundle(
        self,
        approval_id: str,
        canary_percent: Optional[int] = None
    ):
        """Apply an approved bundle.
        
        Args:
            approval_id: Approval request ID
            canary_percent: If set, deploy as canary with this traffic %
        """
        approval = self.db.query(AgentApproval).filter_by(id=approval_id).first()
        
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval.status != "approved":
            raise ValueError(f"Approval {approval_id} is not approved (status={approval.status})")
        
        agent = approval.agent
        bundle_id = approval.context["bundle_id"]
        bundle = approval.context["bundle"]
        
        # Backup current config
        self._backup_active_bundle(agent)
        
        # Apply bundle
        if canary_percent:
            self._apply_as_canary(agent, bundle, canary_percent)
        else:
            self._apply_bundle(agent, bundle)
        
        # Update approval
        approval.context["applied_at"] = datetime.utcnow().isoformat()
        approval.context["canary_percent"] = canary_percent
        self.db.commit()
        
        logger.info(f"Applied bundle {bundle_id} for {agent} (canary={canary_percent}%)")
    
    def rollback_bundle(self, agent: str):
        """Rollback to previous config.
        
        Args:
            agent: Agent name
        """
        backup = self._load_backup_bundle(agent)
        
        if not backup:
            raise ValueError(f"No backup found for {agent}")
        
        self._apply_bundle(agent, backup)
        
        logger.info(f"Rolled back {agent} to backup config")
    
    def _save_bundle(self, agent: str, bundle: Dict[str, Any]):
        """Save bundle to runtime_settings."""
        key = f"bundle.{agent}.{bundle['bundle_id']}"
        
        setting = RuntimeSettings(
            key=key,
            value=json.dumps(bundle),
            category="active_learning"
        )
        
        self.db.add(setting)
        self.db.commit()
    
    def _load_bundle(self, agent: str, bundle_id: str) -> Optional[Dict[str, Any]]:
        """Load a bundle from runtime_settings."""
        key = f"bundle.{agent}.{bundle_id}"
        setting = self.db.query(RuntimeSettings).filter_by(key=key).first()
        
        if not setting:
            return None
        
        return json.loads(setting.value)
    
    def _load_active_bundle(self, agent: str) -> Optional[Dict[str, Any]]:
        """Load the currently active bundle."""
        key = f"bundle.{agent}.active"
        setting = self.db.query(RuntimeSettings).filter_by(key=key).first()
        
        if not setting:
            return None
        
        return json.loads(setting.value)
    
    def _load_backup_bundle(self, agent: str) -> Optional[Dict[str, Any]]:
        """Load the backup bundle."""
        key = f"bundle.{agent}.backup"
        setting = self.db.query(RuntimeSettings).filter_by(key=key).first()
        
        if not setting:
            return None
        
        return json.loads(setting.value)
    
    def _backup_active_bundle(self, agent: str):
        """Backup the current active bundle."""
        active = self._load_active_bundle(agent)
        
        if not active:
            logger.info(f"No active bundle to backup for {agent}")
            return
        
        key = f"bundle.{agent}.backup"
        
        setting = self.db.query(RuntimeSettings).filter_by(key=key).first()
        
        if setting:
            setting.value = json.dumps(active)
            setting.updated_at = datetime.utcnow()
        else:
            setting = RuntimeSettings(
                key=key,
                value=json.dumps(active),
                category="active_learning"
            )
            self.db.add(setting)
        
        self.db.commit()
        logger.info(f"Backed up active bundle for {agent}")
    
    def _apply_bundle(self, agent: str, bundle: Dict[str, Any]):
        """Apply bundle as active config."""
        key = f"bundle.{agent}.active"
        
        setting = self.db.query(RuntimeSettings).filter_by(key=key).first()
        
        if setting:
            setting.value = json.dumps(bundle)
            setting.updated_at = datetime.utcnow()
        else:
            setting = RuntimeSettings(
                key=key,
                value=json.dumps(bundle),
                category="active_learning"
            )
            self.db.add(setting)
        
        self.db.commit()
        logger.info(f"Applied bundle for {agent}")
    
    def _apply_as_canary(self, agent: str, bundle: Dict[str, Any], canary_percent: int):
        """Apply bundle as canary deployment.
        
        Note: This updates the planner_canary settings.
        Actual traffic split is handled by PlannerSwitchboard.
        """
        # Save bundle as canary config
        key = f"bundle.{agent}.canary"
        
        setting = self.db.query(RuntimeSettings).filter_by(key=key).first()
        
        if setting:
            setting.value = json.dumps(bundle)
            setting.updated_at = datetime.utcnow()
        else:
            setting = RuntimeSettings(
                key=key,
                value=json.dumps(bundle),
                category="active_learning"
            )
            self.db.add(setting)
        
        # Update canary percent
        canary_key = f"planner_canary.{agent}.canary_percent"
        canary_setting = self.db.query(RuntimeSettings).filter_by(key=canary_key).first()
        
        if canary_setting:
            canary_setting.value = str(canary_percent)
            canary_setting.updated_at = datetime.utcnow()
        else:
            canary_setting = RuntimeSettings(
                key=canary_key,
                value=str(canary_percent),
                category="planner_canary"
            )
            self.db.add(canary_setting)
        
        self.db.commit()
        logger.info(f"Deployed {agent} bundle as canary at {canary_percent}%")
    
    def list_pending_approvals(self) -> List[Dict[str, Any]]:
        """List all pending bundle approvals.
        
        Returns:
            List of approval dicts
        """
        approvals = (
            self.db.query(AgentApproval)
            .filter_by(action="apply_bundle", status="pending")
            .order_by(AgentApproval.created_at.desc())
            .all()
        )
        
        return [
            {
                "id": a.id,
                "agent": a.agent,
                "bundle_id": a.context.get("bundle_id"),
                "diff": a.context.get("diff"),
                "requested_by": a.requested_by,
                "created_at": a.created_at.isoformat()
            }
            for a in approvals
        ]
