"""Regression detector for planner canary rollout.

Monitors V1 vs V2 performance metrics and triggers automatic rollback
when regressions are detected across quality, latency, or cost dimensions.
"""

import logging
from datetime import datetime, timedelta
from statistics import mean
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session

from ..models import AgentAuditLog
from ..models_runtime import RuntimeSettingsDAO

logger = logging.getLogger(__name__)


# Regression thresholds (from spec)
REGRESS_MAX_QUALITY_DROP = 5.0  # points (0-100 scale)
REGRESS_MAX_LATENCY_P95_MS = 1600  # milliseconds
REGRESS_MAX_COST_CENTS = 3.0  # cents per run
REGRESS_MIN_SAMPLE = 30  # minimum canary runs to judge


class MetricsStore:
    """Aggregates planner metrics from audit logs.

    Queries recent agent runs to compute V1 vs V2 statistics.
    """

    def __init__(self, db_session: Session):
        """Initialize metrics store.

        Args:
            db_session: Database session for querying audit logs
        """
        self.db = db_session

    def window_stats(
        self, window_runs: int = 100, window_minutes: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Compute V1 vs V2 statistics over recent window.

        Args:
            window_runs: Number of recent runs to analyze
            window_minutes: Alternative window by time (minutes)

        Returns:
            Statistics dictionary: {
                "v1": {"samples": int, "quality": float, "latency_p95_ms": float, "cost_cents": float},
                "v2": {"samples": int, "quality": float, "latency_p95_ms": float, "cost_cents": float}
            }
        """
        # Query recent runs
        query = self.db.query(AgentAuditLog).filter(AgentAuditLog.status == "succeeded")

        if window_minutes:
            cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
            query = query.filter(AgentAuditLog.started_at >= cutoff)

        runs = query.order_by(AgentAuditLog.started_at.desc()).limit(window_runs).all()

        # Separate V1 and V2 runs based on planner_meta
        v1_runs = []
        v2_runs = []

        for run in runs:
            if run.plan and isinstance(run.plan, dict):
                planner_meta = run.plan.get("planner_meta", {})
                selected = planner_meta.get("selected")

                if selected == "v1":
                    v1_runs.append(run)
                elif selected == "v2":
                    v2_runs.append(run)

        # Compute stats for each version
        v1_stats = self._compute_stats(v1_runs, "v1")
        v2_stats = self._compute_stats(v2_runs, "v2")

        return {"v1": v1_stats, "v2": v2_stats}

    def _compute_stats(self, runs: List[AgentAuditLog], version: str) -> Dict[str, Any]:
        """Compute aggregate statistics for a set of runs.

        Args:
            runs: List of audit log entries
            version: "v1" or "v2"

        Returns:
            Stats: {samples, quality, latency_p95_ms, cost_cents}
        """
        if not runs:
            return {
                "samples": 0,
                "quality": 0.0,
                "latency_p95_ms": 0.0,
                "cost_cents": 0.0,
            }

        # Extract metrics
        quality_scores = []
        latencies = []
        costs = []

        for run in runs:
            # Quality score (mock: use success=100, failure=0)
            # In production, extract from run.artifacts["quality_score"]
            quality_scores.append(100.0)  # Placeholder

            # Latency
            if run.duration_ms:
                latencies.append(run.duration_ms)

            # Cost (mock: estimate from duration)
            # In production, extract from run.artifacts["cost_cents"]
            cost = (run.duration_ms or 0) / 1000.0 * 0.001  # Mock cost model
            costs.append(cost)

        # Compute aggregates
        quality = mean(quality_scores) if quality_scores else 0.0
        latency_p95 = self._percentile(latencies, 95) if latencies else 0.0
        cost = mean(costs) if costs else 0.0

        return {
            "samples": len(runs),
            "quality": quality,
            "latency_p95_ms": latency_p95,
            "cost_cents": cost,
        }

    @staticmethod
    def _percentile(values: List[float], percentile: int) -> float:
        """Compute percentile of values.

        Args:
            values: List of numeric values
            percentile: Percentile to compute (0-100)

        Returns:
            Percentile value
        """
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100.0))
        return sorted_values[min(index, len(sorted_values) - 1)]


class RegressionDetector:
    """Detects regressions in planner V2 performance.

    Evaluates quality, latency, and cost metrics against thresholds
    and triggers automatic rollback when breaches occur.
    """

    def __init__(self, store: MetricsStore, settings_dao: RuntimeSettingsDAO):
        """Initialize regression detector.

        Args:
            store: Metrics store for querying performance data
            settings_dao: DAO for updating runtime settings
        """
        self.store = store
        self.settings = settings_dao

    def evaluate(self, window_runs: int = 100) -> Dict[str, Any]:
        """Evaluate for regressions and trigger rollback if needed.

        Args:
            window_runs: Number of recent runs to analyze

        Returns:
            Evaluation result: {
                "action": "none"|"ok"|"rollback",
                "reason": str,
                "breaches": List[str],
                "stats": Dict
            }
        """
        # Get metrics
        stats = self.store.window_stats(window_runs=window_runs)

        # Check minimum sample size
        if stats["v2"]["samples"] < REGRESS_MIN_SAMPLE:
            logger.info(
                f"Insufficient V2 samples: {stats['v2']['samples']} < {REGRESS_MIN_SAMPLE}"
            )
            return {"action": "none", "reason": "insufficient_sample", "stats": stats}

        # Detect breaches
        breaches = []

        # Quality regression (V2 significantly worse than V1)
        quality_drop = stats["v1"]["quality"] - stats["v2"]["quality"]
        if quality_drop > REGRESS_MAX_QUALITY_DROP:
            breaches.append(
                f"quality (V1: {stats['v1']['quality']:.1f}, V2: {stats['v2']['quality']:.1f}, drop: {quality_drop:.1f})"
            )

        # Latency regression (V2 p95 exceeds threshold)
        if stats["v2"]["latency_p95_ms"] > REGRESS_MAX_LATENCY_P95_MS:
            breaches.append(
                f"latency (V2 p95: {stats['v2']['latency_p95_ms']:.1f}ms > {REGRESS_MAX_LATENCY_P95_MS}ms)"
            )

        # Cost regression (V2 exceeds threshold)
        if stats["v2"]["cost_cents"] > REGRESS_MAX_COST_CENTS:
            breaches.append(
                f"cost (V2: {stats['v2']['cost_cents']:.3f}¢ > {REGRESS_MAX_COST_CENTS}¢)"
            )

        # Trigger rollback if breaches detected
        if breaches:
            logger.warning(f"Regression detected: {breaches}")
            self._trigger_rollback(breaches, stats)
            return {
                "action": "rollback",
                "reason": "regression_detected",
                "breaches": breaches,
                "stats": stats,
            }

        # No regressions
        logger.info("No regressions detected")
        return {"action": "ok", "reason": "within_thresholds", "stats": stats}

    def _trigger_rollback(self, breaches: List[str], stats: Dict[str, Any]):
        """Trigger automatic rollback.

        Sets kill switch = True and canary_pct = 0 in runtime settings.

        Args:
            breaches: List of breach descriptions
            stats: Performance statistics that triggered rollback
        """
        reason = f"auto_rollback: {', '.join(breaches)}"
        logger.critical(f"TRIGGERING ROLLBACK: {reason}")

        # Update runtime settings
        self.settings.update(
            {"planner_kill_switch": True, "planner_canary_pct": 0.0},
            updated_by="regression_detector",
            reason=reason,
        )

        # TODO: Emit SSE event for real-time notification
        # TODO: Send Prometheus alert
        # TODO: Post to Slack incident channel


class RollbackAudit:
    """Audit log for rollback events.

    Tracks when and why automatic rollbacks occurred.
    """

    def __init__(self, db_session: Session):
        """Initialize rollback audit.

        Args:
            db_session: Database session
        """
        self.db = db_session

    def record(
        self, triggered_by: str, reason: str, breaches: List[str], stats: Dict[str, Any]
    ):
        """Record a rollback event.

        Args:
            triggered_by: What triggered rollback (system, user, etc.)
            reason: Human-readable reason
            breaches: List of breached thresholds
            stats: Performance statistics at rollback time
        """
        # Store in audit log (could be separate table or reuse AgentAuditLog)
        logger.info(f"Rollback audit: {triggered_by} - {reason}")
        # TODO: Persist to database table
        pass
