"""
Prometheus metrics exporters for agent evaluation system.

Exposes evaluation metrics in Prometheus format:
- Agent quality scores (gauge)
- Success rates (gauge)
- Latency percentiles (histogram/gauge)
- Budget violations (counter)
- Invariant failures (counter)
- Red-team detection rates (gauge)

These metrics power Grafana dashboards and Alertmanager alerts.
"""

from prometheus_client import Counter, Gauge, Histogram, Info
from typing import Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import AgentMetricsDaily


# Agent quality metrics
agent_quality_score = Gauge(
    "agent_quality_score",
    "Current quality score for agent (0-100)",
    ["agent"],
)

agent_success_rate = Gauge(
    "agent_success_rate",
    "Success rate for agent (0.0-1.0)",
    ["agent"],
)

# Latency metrics (using both histogram and gauges for flexibility)
agent_latency = Histogram(
    "agent_latency_ms",
    "Agent execution latency in milliseconds",
    ["agent"],
    buckets=[100, 250, 500, 1000, 2000, 5000, 10000],
)

agent_latency_p50 = Gauge(
    "agent_latency_p50_ms",
    "Agent p50 latency in milliseconds",
    ["agent"],
)

agent_latency_p95 = Gauge(
    "agent_latency_p95_ms",
    "Agent p95 latency in milliseconds",
    ["agent"],
)

agent_latency_p99 = Gauge(
    "agent_latency_p99_ms",
    "Agent p99 latency in milliseconds",
    ["agent"],
)

agent_latency_avg = Gauge(
    "agent_latency_avg_ms",
    "Agent average latency in milliseconds",
    ["agent"],
)

# Cost metrics
agent_cost_weight = Gauge(
    "agent_cost_weight",
    "Average cost weight for agent executions",
    ["agent"],
)

# Execution counts
agent_total_runs = Counter(
    "agent_total_runs_total",
    "Total number of agent executions",
    ["agent"],
)

agent_successful_runs = Counter(
    "agent_successful_runs_total",
    "Total number of successful agent executions",
    ["agent"],
)

agent_failed_runs = Counter(
    "agent_failed_runs_total",
    "Total number of failed agent executions",
    ["agent"],
)

# Budget violations
budget_violations_total = Counter(
    "agent_budget_violations_total",
    "Total budget violations by agent and type",
    ["agent", "budget_type", "severity"],
)

# Invariant metrics
invariants_passed = Counter(
    "agent_invariants_passed_total",
    "Total invariant checks passed",
    ["agent"],
)

invariants_failed = Counter(
    "agent_invariants_failed_total",
    "Total invariant checks failed",
    ["agent", "invariant_id"],
)

invariant_pass_rate = Gauge(
    "agent_invariant_pass_rate",
    "Current invariant pass rate (0.0-1.0)",
    ["agent"],
)

# Red team metrics
redteam_attacks_detected = Counter(
    "agent_redteam_attacks_detected_total",
    "Red team attacks successfully detected",
    ["agent"],
)

redteam_attacks_missed = Counter(
    "agent_redteam_attacks_missed_total",
    "Red team attacks missed (false negatives)",
    ["agent"],
)

redteam_false_positives = Counter(
    "agent_redteam_false_positives_total",
    "Red team false positives",
    ["agent"],
)

redteam_detection_rate = Gauge(
    "agent_redteam_detection_rate",
    "Red team attack detection rate (0.0-1.0)",
    ["agent"],
)

# Evaluation info
evaluation_info = Info(
    "agent_evaluation_info",
    "Information about the evaluation system",
)


class MetricsExporter:
    """Exports agent metrics to Prometheus."""

    def __init__(self, db: Session):
        self.db = db

    def export_all_metrics(self, lookback_days: int = 1) -> Dict[str, int]:
        """
        Export all agent metrics for the last N days.

        Args:
            lookback_days: Number of days to look back for metrics

        Returns:
            Dictionary with export statistics
        """
        stats = {
            "agents_exported": 0,
            "metrics_exported": 0,
            "days_covered": lookback_days,
        }

        # Get metrics for last N days
        cutoff_date = datetime.utcnow().date() - timedelta(days=lookback_days)

        metrics = (
            self.db.query(AgentMetricsDaily)
            .filter(AgentMetricsDaily.date >= cutoff_date)
            .all()
        )

        # Group by agent
        agents_metrics: Dict[str, list] = {}
        for m in metrics:
            if m.agent not in agents_metrics:
                agents_metrics[m.agent] = []
            agents_metrics[m.agent].append(m)

        # Export metrics for each agent
        for agent, agent_metrics in agents_metrics.items():
            self._export_agent_metrics(agent, agent_metrics)
            stats["agents_exported"] += 1
            stats["metrics_exported"] += len(agent_metrics)

        # Set evaluation info
        evaluation_info.info(
            {
                "version": "1.0",
                "last_export": datetime.utcnow().isoformat(),
                "agents_monitored": str(len(agents_metrics)),
            }
        )

        return stats

    def _export_agent_metrics(self, agent: str, metrics: list):
        """Export metrics for a single agent."""
        if not metrics:
            return

        # Use most recent metrics for gauges
        latest = max(metrics, key=lambda m: m.date)

        # Quality score
        if latest.avg_quality_score is not None:
            agent_quality_score.labels(agent=agent).set(latest.avg_quality_score)

        # Success rate
        total = latest.total_runs or 0
        successful = latest.successful_runs or 0
        if total > 0:
            success_rate = successful / total
            agent_success_rate.labels(agent=agent).set(success_rate)

        # Latency metrics
        if latest.avg_latency_ms is not None:
            agent_latency_avg.labels(agent=agent).set(latest.avg_latency_ms)
        if latest.p50_latency_ms is not None:
            agent_latency_p50.labels(agent=agent).set(latest.p50_latency_ms)
        if latest.p95_latency_ms is not None:
            agent_latency_p95.labels(agent=agent).set(latest.p95_latency_ms)
        if latest.p99_latency_ms is not None:
            agent_latency_p99.labels(agent=agent).set(latest.p99_latency_ms)

        # Cost
        if latest.avg_cost_weight is not None:
            agent_cost_weight.labels(agent=agent).set(latest.avg_cost_weight)

        # Aggregate counts across all days
        total_runs = sum(m.total_runs or 0 for m in metrics)
        total_successful = sum(m.successful_runs or 0 for m in metrics)
        total_failed = sum(m.failed_runs or 0 for m in metrics)

        # Note: Counters should increment, but we're setting to cumulative values
        # In production, you'd increment as events occur
        agent_total_runs.labels(agent=agent)._value.set(total_runs)
        agent_successful_runs.labels(agent=agent)._value.set(total_successful)
        agent_failed_runs.labels(agent=agent)._value.set(total_failed)

        # Invariants
        total_passed = sum(m.invariants_passed or 0 for m in metrics)
        total_failed_inv = sum(m.invariants_failed or 0 for m in metrics)

        invariants_passed.labels(agent=agent)._value.set(total_passed)

        # Track failed invariants by ID
        for m in metrics:
            if m.failed_invariant_ids:
                for inv_id in m.failed_invariant_ids:
                    invariants_failed.labels(agent=agent, invariant_id=inv_id).inc()

        # Invariant pass rate
        total_invariant_checks = total_passed + total_failed_inv
        if total_invariant_checks > 0:
            pass_rate = total_passed / total_invariant_checks
            invariant_pass_rate.labels(agent=agent).set(pass_rate)

        # Red team metrics
        total_detected = sum(m.redteam_attacks_detected or 0 for m in metrics)
        total_missed = sum(m.redteam_attacks_missed or 0 for m in metrics)
        total_false_pos = sum(m.redteam_false_positives or 0 for m in metrics)

        redteam_attacks_detected.labels(agent=agent)._value.set(total_detected)
        redteam_attacks_missed.labels(agent=agent)._value.set(total_missed)
        redteam_false_positives.labels(agent=agent)._value.set(total_false_pos)

        # Red team detection rate
        total_attacks = total_detected + total_missed
        if total_attacks > 0:
            detection_rate = total_detected / total_attacks
            redteam_detection_rate.labels(agent=agent).set(detection_rate)

    def export_budget_violations(self, agent: str, violations: list):
        """
        Export budget violations as metrics.

        Args:
            agent: Agent name
            violations: List of BudgetViolation objects
        """
        for v in violations:
            budget_violations_total.labels(
                agent=v.agent,
                budget_type=v.budget_type,
                severity=v.severity,
            ).inc()

    def reset_all_metrics(self):
        """Reset all metrics (useful for testing)."""
        # Note: In production, you typically don't reset Prometheus metrics
        # They accumulate over time and Prometheus handles rate calculations
        pass


def get_metrics_exporter(db: Session) -> MetricsExporter:
    """Get metrics exporter instance."""
    return MetricsExporter(db)
