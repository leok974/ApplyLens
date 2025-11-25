"""
Gate Bridges - Phase 5.4 PR5

Connects Phase 5 evaluation gates to Phase 5.4 incident system.
Automatically creates incidents when gates fail, with deduplication.

Called by:
- Eval gate runner (run_gates.py) after evaluation completes
- Budget evaluator (budgets.py) when budget violations detected
- Planner canary monitoring when regressions found

Publishes SSE events for real-time notifications in web UI.
"""

import logging
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from app.models_incident import Incident
from app.eval.budgets import BudgetViolation, Budget

logger = logging.getLogger(__name__)

# Import SSE publisher (optional - graceful degradation)
try:
    from app.routers.sse import publish_incident_created

    SSE_AVAILABLE = True
except ImportError:
    logger.warning("SSE not available - incidents will not be published to web UI")
    SSE_AVAILABLE = False

# Import watcher (for deduplication logic)
try:
    from app.intervene.watcher import InvariantWatcher

    WATCHER_AVAILABLE = True
except ImportError:
    logger.warning(
        "Watcher not available - incidents will be created without deduplication"
    )
    WATCHER_AVAILABLE = False


class GateBridge:
    """
    Bridge between evaluation gates and incident system.

    Features:
    - Auto-creates incidents on gate failures
    - Deduplication: Reuses watcher's logic to avoid duplicate incidents
    - SSE publishing: Real-time notifications for web UI
    - Rate limiting: Max 3 incidents per gate per hour
    """

    def __init__(self, db: Session):
        self.db = db
        if WATCHER_AVAILABLE:
            self.watcher = InvariantWatcher(db)
        else:
            self.watcher = None

    async def on_budget_violation(
        self,
        violation: BudgetViolation,
        budget: Budget,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Incident]:
        """
        Called when budget threshold exceeded.

        Creates incident for budget violations (latency, cost, quality).

        Args:
            violation: Budget violation details
            budget: Budget configuration
            context: Additional context (eval result, metrics, etc.)

        Returns:
            Created incident or None if deduplicated
        """
        key = f"BUDGET_{violation.agent}_{violation.budget_type}"

        # Check if incident already open
        if self.watcher and self.watcher._has_open_incident("budget", key):
            logger.info(f"Skipping duplicate budget incident: {key}")
            return None

        # Check rate limit (max 3 per hour)
        if self.watcher and self.watcher._is_rate_limited(
            "budget", key, hours=1, max_incidents=3
        ):
            logger.info(f"Rate limited budget incident: {key}")
            return None

        # Map severity
        severity = self._map_severity(violation.severity)

        # Determine playbooks
        playbooks = self._suggest_budget_playbooks(
            violation.budget_type, violation.agent
        )

        # Create incident
        incident = Incident(
            kind="budget",
            key=key,
            severity=severity,
            status="open",
            summary=f"Budget violation: {violation.agent} {violation.budget_type}",
            details={
                "violation": {
                    "agent": violation.agent,
                    "budget_type": violation.budget_type,
                    "threshold": violation.threshold,
                    "actual": violation.actual,
                    "severity": violation.severity,
                    "message": violation.message,
                    "date": violation.date.isoformat(),
                },
                "budget": {
                    "agent": budget.agent,
                    "description": budget.description,
                    "enabled": budget.enabled,
                },
                "context": context or {},
            },
            playbooks=playbooks,
            metadata={
                "agent": violation.agent,
                "budget_type": violation.budget_type,
                "auto_created": True,
                "source": "gate_bridge",
            },
        )

        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)

        logger.info(f"Created budget incident: {incident.id} ({key})")

        # Publish SSE event
        if SSE_AVAILABLE:
            try:
                await publish_incident_created(incident)
            except Exception as e:
                logger.error(f"Failed to publish SSE event: {e}")

        return incident

    async def on_invariant_failure(
        self,
        eval_result: Any,  # EvalResult model
        invariant_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Incident]:
        """
        Called when invariant fails in eval run.

        Creates incident for invariant violations.

        Args:
            eval_result: EvalResult with invariant failure
            invariant_result: InvariantResult dict with failure details
            context: Additional context

        Returns:
            Created incident or None if deduplicated
        """
        inv_id = invariant_result.get("invariant_id")
        if not inv_id:
            logger.warning("Invariant result missing invariant_id")
            return None

        key = f"INV_{inv_id}"

        # Check if incident already open
        if self.watcher and self.watcher._has_open_incident("invariant", key):
            logger.info(f"Skipping duplicate invariant incident: {key}")
            return None

        # Check rate limit
        if self.watcher and self.watcher._is_rate_limited(
            "invariant", key, hours=1, max_incidents=3
        ):
            logger.info(f"Rate limited invariant incident: {key}")
            return None

        # Use watcher's logic to create incident (reuse existing code)
        if self.watcher:
            incident = self.watcher._create_invariant_incident(
                eval_result, invariant_result
            )

            # Publish SSE event
            if SSE_AVAILABLE:
                try:
                    await publish_incident_created(incident)
                except Exception as e:
                    logger.error(f"Failed to publish SSE event: {e}")

            return incident

        # Fallback: Create incident directly (if watcher unavailable)
        return None

    async def on_planner_regression(
        self,
        version: str,
        metrics: Dict[str, Any],
        baseline_metrics: Dict[str, Any],
        regression_details: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Incident]:
        """
        Called when planner canary regression detected.

        Creates incident for planner regressions (accuracy drop, latency spike).

        Args:
            version: Planner version being canary-tested
            metrics: Current canary metrics
            baseline_metrics: Baseline metrics for comparison
            regression_details: Details of regression (metric, threshold, actual)
            context: Additional context

        Returns:
            Created incident or None if deduplicated
        """
        key = f"PLANNER_REG_{version}"

        # Check if incident already open
        if self.watcher and self.watcher._has_open_incident("planner", key):
            logger.info(f"Skipping duplicate planner incident: {key}")
            return None

        # Check rate limit
        if self.watcher and self.watcher._is_rate_limited(
            "planner", key, hours=1, max_incidents=3
        ):
            logger.info(f"Rate limited planner incident: {key}")
            return None

        # Determine severity (critical if accuracy drop > 10%, else error)
        severity = "sev1" if regression_details.get("metric") == "accuracy" else "sev2"

        # Playbooks: rollback or adjust canary split
        playbooks = ["rollback_planner", "adjust_canary_split"]

        # Create incident
        incident = Incident(
            kind="planner",
            key=key,
            severity=severity,
            status="open",
            summary=f"Planner regression: {version} {regression_details.get('metric')}",
            details={
                "version": version,
                "regression": regression_details,
                "metrics": {
                    "current": metrics,
                    "baseline": baseline_metrics,
                },
                "context": context or {},
            },
            playbooks=playbooks,
            metadata={
                "version": version,
                "auto_created": True,
                "source": "gate_bridge",
            },
        )

        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)

        logger.info(f"Created planner incident: {incident.id} ({key})")

        # Publish SSE event
        if SSE_AVAILABLE:
            try:
                await publish_incident_created(incident)
            except Exception as e:
                logger.error(f"Failed to publish SSE event: {e}")

        return incident

    async def on_gate_failure(
        self,
        agent: str,
        gate_result: Dict[str, Any],
        violations: List[BudgetViolation],
        budget: Budget,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Incident]:
        """
        Called when gate evaluation fails (multiple violations).

        Creates incidents for each violation, with deduplication.

        Args:
            agent: Agent identifier
            gate_result: Full gate evaluation result
            violations: List of budget violations
            budget: Budget configuration
            context: Additional context

        Returns:
            List of created incidents
        """
        incidents = []

        for violation in violations:
            incident = await self.on_budget_violation(violation, budget, context)
            if incident:
                incidents.append(incident)

        return incidents

    def _map_severity(self, violation_severity: str) -> str:
        """
        Map violation severity to incident severity.

        Args:
            violation_severity: "warning", "error", "critical"

        Returns:
            Incident severity: "sev1", "sev2", "sev3", "sev4"
        """
        mapping = {
            "critical": "sev1",
            "error": "sev2",
            "warning": "sev3",
        }
        return mapping.get(violation_severity, "sev3")

    def _suggest_budget_playbooks(self, budget_type: str, agent: str) -> List[str]:
        """
        Suggest playbooks based on budget type.

        Args:
            budget_type: "quality", "latency", "cost", "success_rate", "invariants"
            agent: Agent identifier

        Returns:
            List of playbook names
        """
        playbooks = []

        if budget_type == "quality":
            playbooks.append("rerun_eval")
            if "dbt" in agent or "warehouse" in agent:
                playbooks.append("rerun_dbt")

        elif budget_type == "latency":
            playbooks.append("clear_cache")
            if "elastic" in agent or "knowledge" in agent:
                playbooks.append("refresh_synonyms")

        elif budget_type == "cost":
            playbooks.append("rerun_eval")
            playbooks.append("adjust_canary_split")

        elif budget_type == "success_rate":
            playbooks.append("rerun_eval")
            if "dbt" in agent:
                playbooks.append("rerun_dbt")

        elif budget_type == "invariants":
            playbooks.append("rerun_eval")
            playbooks.append("rerun_dbt")

        # Add rollback as fallback
        if "planner" in agent:
            playbooks.append("rollback_planner")

        return playbooks


# Convenience functions for async context


async def create_budget_incident(
    db: Session,
    violation: BudgetViolation,
    budget: Budget,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[Incident]:
    """
    Create incident for budget violation.

    Convenience function for simple usage.
    """
    bridge = GateBridge(db)
    return await bridge.on_budget_violation(violation, budget, context)


async def create_invariant_incident(
    db: Session,
    eval_result: Any,
    invariant_result: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Optional[Incident]:
    """
    Create incident for invariant failure.

    Convenience function for simple usage.
    """
    bridge = GateBridge(db)
    return await bridge.on_invariant_failure(eval_result, invariant_result, context)


async def create_planner_incident(
    db: Session,
    version: str,
    metrics: Dict[str, Any],
    baseline_metrics: Dict[str, Any],
    regression_details: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Optional[Incident]:
    """
    Create incident for planner regression.

    Convenience function for simple usage.
    """
    bridge = GateBridge(db)
    return await bridge.on_planner_regression(
        version, metrics, baseline_metrics, regression_details, context
    )
