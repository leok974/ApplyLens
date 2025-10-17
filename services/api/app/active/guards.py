"""Online learning guardrails for active learning.

Provides safety checks for deployed bundles:
- Auto-apply approved bundles as canary (10%)
- Monitor quality via RegressionDetector
- Auto-promote or rollback based on performance
- Gradual rollout (10% → 50% → 100%)

Design:
- Integrates with Phase 5.1 canary infrastructure
- Runs nightly to check canary performance
- Automatic promotion on success
- Automatic rollback on regression
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

from app.models import RuntimeSetting
from app.active.bundles import BundleManager
from app.canary.detector import RegressionDetector

logger = logging.getLogger(__name__)


class OnlineLearningGuard:
    """Safety guardrails for online learning."""
    
    def __init__(self, db_session):
        self.db = db_session
        self.bundle_mgr = BundleManager(db_session)
        self.detector = RegressionDetector(db_session)
    
    def auto_apply_approved_bundles(self, initial_canary_percent: int = 10):
        """Auto-apply all approved bundles as canary.
        
        Args:
            initial_canary_percent: Initial canary traffic %
        
        Returns:
            Count of bundles deployed
        """
        pending_approvals = self.bundle_mgr.list_pending_approvals()
        
        # Filter for approved
        approved = [
            a for a in pending_approvals
            if self.db.query(self.db.query(RuntimeSetting).filter_by(
                key=f"approval.{a['id']}.status"
            ).first()).first()
        ]
        
        deployed_count = 0
        
        for approval in approved:
            try:
                self.bundle_mgr.apply_approved_bundle(
                    approval["id"],
                    canary_percent=initial_canary_percent
                )
                deployed_count += 1
                logger.info(f"Auto-deployed bundle {approval['bundle_id']} as {initial_canary_percent}% canary")
            except Exception as e:
                logger.error(f"Failed to auto-deploy {approval['bundle_id']}: {e}")
        
        return deployed_count
    
    def check_canary_performance(
        self,
        agent: str,
        lookback_hours: int = 24,
        regression_threshold: float = 0.05
    ) -> Dict[str, any]:
        """Check if canary is performing well.
        
        Args:
            agent: Agent name
            lookback_hours: Hours to look back
            regression_threshold: Max acceptable regression (5% default)
        
        Returns:
            {
                "has_regression": bool,
                "quality_delta": float,
                "latency_delta": float,
                "recommendation": "promote" | "rollback" | "monitor"
            }
        """
        # Use RegressionDetector from Phase 5.1
        regression = self.detector.detect_regression(
            agent,
            since_hours=lookback_hours,
            threshold=regression_threshold
        )
        
        if regression["has_regression"]:
            logger.warning(
                f"Canary regression detected for {agent}: "
                f"quality_delta={regression['quality_delta']}, "
                f"latency_delta={regression['latency_delta']}"
            )
            
            return {
                "has_regression": True,
                "quality_delta": regression["quality_delta"],
                "latency_delta": regression["latency_delta"],
                "recommendation": "rollback",
                "reason": regression.get("regression_type")
            }
        
        # Check if canary is performing better
        quality_delta = regression.get("quality_delta", 0)
        latency_delta = regression.get("latency_delta", 0)
        
        if quality_delta > 0.02 or latency_delta < -0.1:  # 2% quality improvement or 10% faster
            return {
                "has_regression": False,
                "quality_delta": quality_delta,
                "latency_delta": latency_delta,
                "recommendation": "promote",
                "reason": "performance_improvement"
            }
        
        # Neutral - continue monitoring
        return {
            "has_regression": False,
            "quality_delta": quality_delta,
            "latency_delta": latency_delta,
            "recommendation": "monitor",
            "reason": "neutral_performance"
        }
    
    def promote_canary(
        self,
        agent: str,
        target_percent: int = 100
    ):
        """Promote canary to higher traffic or full deployment.
        
        Args:
            agent: Agent name
            target_percent: Target traffic % (50 or 100)
        """
        # Load canary bundle
        canary_bundle = self._load_canary_bundle(agent)
        
        if not canary_bundle:
            logger.warning(f"No canary bundle to promote for {agent}")
            return
        
        if target_percent == 100:
            # Full promotion - make canary the active bundle
            self.bundle_mgr._apply_bundle(agent, canary_bundle)
            
            # Clear canary settings
            self._clear_canary(agent)
            
            logger.info(f"Promoted {agent} canary to 100% (now active)")
        else:
            # Partial promotion - increase canary percent
            self._update_canary_percent(agent, target_percent)
            
            logger.info(f"Promoted {agent} canary to {target_percent}%")
    
    def rollback_canary(self, agent: str):
        """Rollback canary deployment.
        
        Args:
            agent: Agent name
        """
        # Clear canary settings (traffic goes to active)
        self._clear_canary(agent)
        
        logger.info(f"Rolled back {agent} canary (reverted to active)")
    
    def gradual_rollout(
        self,
        agent: str,
        stages: list = [10, 50, 100],
        check_interval_hours: int = 24
    ) -> Dict[str, any]:
        """Gradual canary rollout with safety checks.
        
        Args:
            agent: Agent name
            stages: Traffic % stages
            check_interval_hours: Hours between stages
        
        Returns:
            Rollout status dict
        """
        current_percent = self._get_canary_percent(agent)
        
        if current_percent == 0:
            logger.info(f"No active canary for {agent}")
            return {"status": "no_canary"}
        
        # Check performance
        performance = self.check_canary_performance(agent, lookback_hours=check_interval_hours)
        
        if performance["recommendation"] == "rollback":
            self.rollback_canary(agent)
            return {
                "status": "rolled_back",
                "reason": performance["reason"],
                "performance": performance
            }
        
        if performance["recommendation"] == "monitor":
            return {
                "status": "monitoring",
                "current_percent": current_percent,
                "performance": performance
            }
        
        # Promotion logic
        next_stage = None
        for stage in stages:
            if stage > current_percent:
                next_stage = stage
                break
        
        if next_stage:
            self.promote_canary(agent, next_stage)
            return {
                "status": "promoted",
                "from_percent": current_percent,
                "to_percent": next_stage,
                "performance": performance
            }
        else:
            # Already at max
            return {
                "status": "complete",
                "current_percent": current_percent,
                "performance": performance
            }
    
    def nightly_guard_check(self):
        """Nightly job to check all active canaries.
        
        Returns:
            Dict of agent -> action taken
        """
        logger.info("Starting nightly online learning guard check")
        
        # Find all agents with active canaries
        canary_settings = (
            self.db.query(RuntimeSetting)
            .filter(RuntimeSetting.key.like("planner_canary.%.canary_percent"))
            .all()
        )
        
        agents_with_canaries = []
        for setting in canary_settings:
            if int(setting.value) > 0:
                # Extract agent from key: planner_canary.{agent}.canary_percent
                agent = setting.key.split(".")[1]
                agents_with_canaries.append(agent)
        
        results = {}
        
        for agent in agents_with_canaries:
            try:
                result = self.gradual_rollout(agent)
                results[agent] = result
                logger.info(f"Guard check for {agent}: {result['status']}")
            except Exception as e:
                logger.error(f"Guard check failed for {agent}: {e}")
                results[agent] = {"status": "error", "error": str(e)}
        
        return results
    
    def _load_canary_bundle(self, agent: str):
        """Load canary bundle from runtime_settings."""
        key = f"bundle.{agent}.canary"
        setting = self.db.query(RuntimeSetting).filter_by(key=key).first()
        
        if not setting:
            return None
        
        import json
        return json.loads(setting.value)
    
    def _get_canary_percent(self, agent: str) -> int:
        """Get current canary traffic percent."""
        key = f"planner_canary.{agent}.canary_percent"
        setting = self.db.query(RuntimeSetting).filter_by(key=key).first()
        
        if not setting:
            return 0
        
        return int(setting.value)
    
    def _update_canary_percent(self, agent: str, percent: int):
        """Update canary traffic percent."""
        key = f"planner_canary.{agent}.canary_percent"
        setting = self.db.query(RuntimeSetting).filter_by(key=key).first()
        
        if setting:
            setting.value = str(percent)
            setting.updated_at = datetime.utcnow()
        else:
            setting = RuntimeSetting(
                key=key,
                value=str(percent),
                category="planner_canary"
            )
            self.db.add(setting)
        
        self.db.commit()
    
    def _clear_canary(self, agent: str):
        """Clear canary settings."""
        # Set canary percent to 0
        self._update_canary_percent(agent, 0)
        
        # Optionally delete canary bundle
        key = f"bundle.{agent}.canary"
        setting = self.db.query(RuntimeSetting).filter_by(key=key).first()
        
        if setting:
            self.db.delete(setting)
            self.db.commit()
