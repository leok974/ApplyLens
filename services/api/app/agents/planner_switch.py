"""PlannerSwitchboard for canary routing with shadow comparison.

Routes requests between PlannerV1 and PlannerV2 based on:
- Canary percentage (gradual rollout)
- Kill switch (emergency rollback to V1)
- Shadow execution (always run both, compare decisions)
"""

import random
import time
from typing import Any, Dict, Tuple

from .planner import Planner as PlannerV1
from .planner_v2 import PlannerV2
from ..observability.metrics import planner_selection, planner_diff


class PlannerSwitchboard:
    """Routes traffic between PlannerV1 and PlannerV2 with canary controls.
    
    Features:
    - Canary traffic split (0-100%)
    - Kill switch for instant rollback
    - Shadow execution (both planners run, decisions compared)
    - Metrics for selection and diff tracking
    
    The selected planner's decision is returned, while the shadow
    planner's decision is included in metadata for analysis.
    """
    
    def __init__(self, canary_pct: float = 0.0, kill_switch: bool = False):
        """Initialize switchboard.
        
        Args:
            canary_pct: Percentage of traffic to route to V2 (0.0-100.0)
            kill_switch: If True, force all traffic to V1
        """
        self.v1 = PlannerV1()
        self.v2 = PlannerV2()
        self.canary_pct = max(0.0, min(100.0, canary_pct))  # Clamp to [0, 100]
        self.kill_switch = kill_switch
    
    def plan(
        self, 
        objective: str, 
        params: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Create execution plan with canary routing and shadow comparison.
        
        Args:
            objective: High-level task objective
            params: Planning parameters (agent, tools, dry_run, etc.)
            
        Returns:
            Tuple of (selected_plan, metadata)
            - selected_plan: The plan to execute (from V1 or V2)
            - metadata: {
                "selected": "v1"|"v2",
                "shadow": shadow_plan,
                "diff": diff_summary,
                "latency_ms": planning_time,
                "canary_pct": current_canary_percentage,
                "kill_switch": kill_switch_state
              }
        """
        start_time = time.time()
        
        # Extract agent name (V1 needs it as first param, V2 extracts from params)
        agent_name = params.get("agent", "auto")
        
        # Always run both planners (shadow execution)
        plan_v1 = self.v1.plan(agent_name, objective, params)
        plan_v2 = self.v2.plan(objective, params)
        
        # Compute diff between decisions
        diff = self._compute_diff(plan_v1, plan_v2)
        
        # Record diff metrics
        planner_diff.labels(
            agent_v1=plan_v1.get("agent", "unknown"),
            agent_v2=plan_v2.get("agent", "unknown"),
            changed=str(diff["agent_changed"])
        ).inc()
        
        # Planning latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Build metadata
        metadata = {
            "latency_ms": latency_ms,
            "diff": diff,
            "canary_pct": self.canary_pct,
            "kill_switch": self.kill_switch
        }
        
        # Kill switch forces V1
        if self.kill_switch:
            planner_selection.labels(planner="v1", reason="kill_switch").inc()
            metadata["selected"] = "v1"
            metadata["shadow"] = plan_v2
            return plan_v1, metadata
        
        # Canary routing (random selection based on percentage)
        if random.random() < (self.canary_pct / 100.0):
            planner_selection.labels(planner="v2", reason="canary").inc()
            metadata["selected"] = "v2"
            metadata["shadow"] = plan_v1
            return plan_v2, metadata
        
        # Default to V1
        planner_selection.labels(planner="v1", reason="default").inc()
        metadata["selected"] = "v1"
        metadata["shadow"] = plan_v2
        return plan_v1, metadata
    
    def _compute_diff(self, plan_v1: Dict[str, Any], plan_v2: Dict[str, Any]) -> Dict[str, Any]:
        """Compute differences between V1 and V2 plans.
        
        Args:
            plan_v1: Plan from PlannerV1
            plan_v2: Plan from PlannerV2
            
        Returns:
            Diff summary with boolean flags for key changes
        """
        # Agent selection changed
        agent_changed = plan_v1.get("agent") != plan_v2.get("agent")
        
        # Steps changed (comparing lists)
        steps_v1 = plan_v1.get("steps", [])
        steps_v2 = plan_v2.get("steps", [])
        steps_changed = steps_v1 != steps_v2
        
        # Tools changed
        tools_v1 = set(plan_v1.get("tools", []))
        tools_v2 = set(plan_v2.get("required_capabilities", []))
        tools_changed = tools_v1 != tools_v2
        
        # Dry run mode changed
        dry_run_changed = plan_v1.get("dry_run") != plan_v2.get("dry_run")
        
        # Overall: any change?
        any_change = agent_changed or steps_changed or tools_changed or dry_run_changed
        
        return {
            "agent_changed": agent_changed,
            "steps_changed": steps_changed,
            "tools_changed": tools_changed,
            "dry_run_changed": dry_run_changed,
            "any_change": any_change,
            "v1_agent": plan_v1.get("agent"),
            "v2_agent": plan_v2.get("agent"),
            "v1_steps_count": len(steps_v1),
            "v2_steps_count": len(steps_v2),
        }
    
    def update_config(self, canary_pct: float = None, kill_switch: bool = None):
        """Update switchboard configuration dynamically.
        
        Args:
            canary_pct: New canary percentage (optional)
            kill_switch: New kill switch state (optional)
        """
        if canary_pct is not None:
            self.canary_pct = max(0.0, min(100.0, canary_pct))
        if kill_switch is not None:
            self.kill_switch = kill_switch
    
    def get_config(self) -> Dict[str, Any]:
        """Get current switchboard configuration.
        
        Returns:
            Current config (canary_pct, kill_switch)
        """
        return {
            "canary_pct": self.canary_pct,
            "kill_switch": self.kill_switch,
            "v1_type": type(self.v1).__name__,
            "v2_type": type(self.v2).__name__,
        }
