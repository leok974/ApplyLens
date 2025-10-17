"""
Cost and latency budgets for agent quality gates.

Budgets define acceptable thresholds for:
- Quality score (min acceptable)
- Latency (P50, P95, P99 max)
- Cost weight (max relative cost)
- Success rate (min acceptable)

Gates enforce budgets in CI:
- Fail build if quality drops below threshold
- Fail if latency exceeds budget
- Fail if new invariant violations appear
- Compare against historical baseline
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from ..models import AgentMetricsDaily


@dataclass
class Budget:
    """
    Quality budget for an agent.
    
    Defines acceptable thresholds that must not be violated.
    Used for regression gates in CI and production monitoring.
    """
    agent: str
    
    # Quality thresholds
    min_quality_score: Optional[float] = None  # 0-100 scale
    min_success_rate: Optional[float] = None  # 0.0-1.0
    
    # Latency budgets (milliseconds)
    max_p50_latency_ms: Optional[float] = None
    max_p95_latency_ms: Optional[float] = None
    max_p99_latency_ms: Optional[float] = None
    max_avg_latency_ms: Optional[float] = None
    
    # Cost budget
    max_avg_cost_weight: Optional[float] = None
    
    # Invariant budget
    max_invariant_failures: int = 0  # Zero tolerance by default
    
    # Context
    description: Optional[str] = None
    enabled: bool = True


# Default budgets per agent
DEFAULT_BUDGETS = {
    "inbox.triage": Budget(
        agent="inbox.triage",
        min_quality_score=85.0,
        min_success_rate=0.95,
        max_avg_latency_ms=500.0,
        max_p95_latency_ms=1000.0,
        max_p99_latency_ms=2000.0,
        max_avg_cost_weight=2.0,
        max_invariant_failures=0,
        description="Email triage must be fast and accurate",
    ),
    "knowledge.update": Budget(
        agent="knowledge.update",
        min_quality_score=80.0,
        min_success_rate=0.90,
        max_avg_latency_ms=2000.0,
        max_p95_latency_ms=5000.0,
        max_p99_latency_ms=10000.0,
        max_avg_cost_weight=5.0,
        max_invariant_failures=0,
        description="Knowledge updates can be slower but must be accurate",
    ),
    "insights.write": Budget(
        agent="insights.write",
        min_quality_score=75.0,
        min_success_rate=0.85,
        max_avg_latency_ms=3000.0,
        max_p95_latency_ms=8000.0,
        max_p99_latency_ms=15000.0,
        max_avg_cost_weight=8.0,
        max_invariant_failures=0,
        description="Insights generation is complex, balanced thresholds",
    ),
    "warehouse.health": Budget(
        agent="warehouse.health",
        min_quality_score=90.0,
        min_success_rate=0.98,
        max_avg_latency_ms=1000.0,
        max_p95_latency_ms=3000.0,
        max_p99_latency_ms=5000.0,
        max_avg_cost_weight=3.0,
        max_invariant_failures=0,
        description="Warehouse health checks must be highly reliable",
    ),
}


@dataclass
class BudgetViolation:
    """A budget threshold violation."""
    agent: str
    budget_type: str  # "quality", "latency", "cost", "success_rate", "invariants"
    threshold: float
    actual: float
    severity: str  # "warning", "error", "critical"
    message: str
    date: datetime


class GateEvaluator:
    """
    Evaluates quality gates against budgets.
    
    Used in CI to fail builds on regressions.
    Also used in production for alerting.
    """
    
    def __init__(self, db: Session, budgets: Optional[Dict[str, Budget]] = None):
        """
        Initialize gate evaluator.
        
        Args:
            db: Database session
            budgets: Custom budgets (uses defaults if None)
        """
        self.db = db
        self.budgets = budgets or DEFAULT_BUDGETS
    
    def evaluate_agent(
        self,
        agent: str,
        lookback_days: int = 7,
        baseline_days: int = 14,
    ) -> Dict[str, Any]:
        """
        Evaluate agent against budget and baseline.
        
        Compares recent metrics (last N days) against:
        1. Absolute budget thresholds
        2. Historical baseline (previous M days)
        
        Args:
            agent: Agent identifier
            lookback_days: Days to evaluate (default 7 for weekly)
            baseline_days: Days to use as baseline (default 14, 2 weeks ago)
            
        Returns:
            Dict with:
            - passed: bool (all gates passed)
            - violations: List[BudgetViolation]
            - current_metrics: Dict (recent avg metrics)
            - baseline_metrics: Dict (historical avg metrics)
            - budget: Budget object
        """
        if agent not in self.budgets:
            return {
                "passed": True,
                "violations": [],
                "message": f"No budget defined for {agent}",
            }
        
        budget = self.budgets[agent]
        
        if not budget.enabled:
            return {
                "passed": True,
                "violations": [],
                "message": f"Budget disabled for {agent}",
            }
        
        # Get recent metrics
        end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=lookback_days)
        
        current_metrics = self._get_avg_metrics(agent, start_date, end_date)
        
        # Get baseline metrics (2 weeks ago)
        baseline_end = start_date
        baseline_start = baseline_end - timedelta(days=baseline_days)
        baseline_metrics = self._get_avg_metrics(agent, baseline_start, baseline_end)
        
        # Check violations
        violations = []
        
        # Quality score
        if budget.min_quality_score is not None and current_metrics.get("avg_quality_score"):
            if current_metrics["avg_quality_score"] < budget.min_quality_score:
                violations.append(BudgetViolation(
                    agent=agent,
                    budget_type="quality",
                    threshold=budget.min_quality_score,
                    actual=current_metrics["avg_quality_score"],
                    severity="critical",
                    message=f"Quality score {current_metrics['avg_quality_score']:.1f} below budget {budget.min_quality_score:.1f}",
                    date=end_date,
                ))
        
        # Success rate
        if budget.min_success_rate is not None and current_metrics.get("success_rate"):
            if current_metrics["success_rate"] < budget.min_success_rate:
                violations.append(BudgetViolation(
                    agent=agent,
                    budget_type="success_rate",
                    threshold=budget.min_success_rate,
                    actual=current_metrics["success_rate"],
                    severity="critical",
                    message=f"Success rate {current_metrics['success_rate']:.1%} below budget {budget.min_success_rate:.1%}",
                    date=end_date,
                ))
        
        # Latency (avg)
        if budget.max_avg_latency_ms is not None and current_metrics.get("avg_latency_ms"):
            if current_metrics["avg_latency_ms"] > budget.max_avg_latency_ms:
                violations.append(BudgetViolation(
                    agent=agent,
                    budget_type="latency_avg",
                    threshold=budget.max_avg_latency_ms,
                    actual=current_metrics["avg_latency_ms"],
                    severity="error",
                    message=f"Avg latency {current_metrics['avg_latency_ms']:.0f}ms exceeds budget {budget.max_avg_latency_ms:.0f}ms",
                    date=end_date,
                ))
        
        # Latency (P95)
        if budget.max_p95_latency_ms is not None and current_metrics.get("p95_latency_ms"):
            if current_metrics["p95_latency_ms"] > budget.max_p95_latency_ms:
                violations.append(BudgetViolation(
                    agent=agent,
                    budget_type="latency_p95",
                    threshold=budget.max_p95_latency_ms,
                    actual=current_metrics["p95_latency_ms"],
                    severity="error",
                    message=f"P95 latency {current_metrics['p95_latency_ms']:.0f}ms exceeds budget {budget.max_p95_latency_ms:.0f}ms",
                    date=end_date,
                ))
        
        # Latency (P99)
        if budget.max_p99_latency_ms is not None and current_metrics.get("p99_latency_ms"):
            if current_metrics["p99_latency_ms"] > budget.max_p99_latency_ms:
                violations.append(BudgetViolation(
                    agent=agent,
                    budget_type="latency_p99",
                    threshold=budget.max_p99_latency_ms,
                    actual=current_metrics["p99_latency_ms"],
                    severity="warning",
                    message=f"P99 latency {current_metrics['p99_latency_ms']:.0f}ms exceeds budget {budget.max_p99_latency_ms:.0f}ms",
                    date=end_date,
                ))
        
        # Cost
        if budget.max_avg_cost_weight is not None and current_metrics.get("avg_cost_per_run"):
            if current_metrics["avg_cost_per_run"] > budget.max_avg_cost_weight:
                violations.append(BudgetViolation(
                    agent=agent,
                    budget_type="cost",
                    threshold=budget.max_avg_cost_weight,
                    actual=current_metrics["avg_cost_per_run"],
                    severity="error",
                    message=f"Avg cost {current_metrics['avg_cost_per_run']:.2f} exceeds budget {budget.max_avg_cost_weight:.2f}",
                    date=end_date,
                ))
        
        # Invariants
        if current_metrics.get("invariants_failed", 0) > budget.max_invariant_failures:
            violations.append(BudgetViolation(
                agent=agent,
                budget_type="invariants",
                threshold=budget.max_invariant_failures,
                actual=current_metrics["invariants_failed"],
                severity="critical",
                message=f"{current_metrics['invariants_failed']} invariant failures (budget allows {budget.max_invariant_failures})",
                date=end_date,
            ))
        
        # Regression detection (compare to baseline)
        if baseline_metrics:
            # Quality regression (>10% drop)
            if (current_metrics.get("avg_quality_score") and 
                baseline_metrics.get("avg_quality_score")):
                drop = baseline_metrics["avg_quality_score"] - current_metrics["avg_quality_score"]
                if drop > 10.0:
                    violations.append(BudgetViolation(
                        agent=agent,
                        budget_type="quality_regression",
                        threshold=baseline_metrics["avg_quality_score"] - 10.0,
                        actual=current_metrics["avg_quality_score"],
                        severity="critical",
                        message=f"Quality dropped {drop:.1f} points from baseline {baseline_metrics['avg_quality_score']:.1f}",
                        date=end_date,
                    ))
            
            # Latency regression (>30% increase)
            if (current_metrics.get("avg_latency_ms") and 
                baseline_metrics.get("avg_latency_ms")):
                increase_pct = (current_metrics["avg_latency_ms"] - baseline_metrics["avg_latency_ms"]) / baseline_metrics["avg_latency_ms"]
                if increase_pct > 0.30:
                    violations.append(BudgetViolation(
                        agent=agent,
                        budget_type="latency_regression",
                        threshold=baseline_metrics["avg_latency_ms"] * 1.30,
                        actual=current_metrics["avg_latency_ms"],
                        severity="error",
                        message=f"Latency increased {increase_pct:.1%} from baseline {baseline_metrics['avg_latency_ms']:.0f}ms",
                        date=end_date,
                    ))
        
        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "current_metrics": current_metrics,
            "baseline_metrics": baseline_metrics,
            "budget": budget,
            "agent": agent,
        }
    
    def evaluate_all_agents(
        self,
        lookback_days: int = 7,
        baseline_days: int = 14,
    ) -> Dict[str, Any]:
        """
        Evaluate all agents against budgets.
        
        Returns:
            Dict with:
            - passed: bool (all agents passed)
            - results: Dict[agent, evaluation_result]
            - total_violations: int
            - critical_violations: int
        """
        results = {}
        total_violations = 0
        critical_violations = 0
        
        for agent in self.budgets.keys():
            result = self.evaluate_agent(agent, lookback_days, baseline_days)
            results[agent] = result
            total_violations += len(result["violations"])
            critical_violations += sum(
                1 for v in result["violations"] 
                if v.severity == "critical"
            )
        
        return {
            "passed": total_violations == 0,
            "results": results,
            "total_violations": total_violations,
            "critical_violations": critical_violations,
            "evaluated_agents": list(self.budgets.keys()),
        }
    
    def _get_avg_metrics(
        self,
        agent: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get average metrics for agent in date range."""
        metrics = self.db.query(AgentMetricsDaily).filter(
            and_(
                AgentMetricsDaily.agent == agent,
                AgentMetricsDaily.date >= start_date,
                AgentMetricsDaily.date < end_date,
            )
        ).all()
        
        if not metrics:
            return {}
        
        # Compute averages
        total_runs = sum(m.total_runs for m in metrics)
        successful_runs = sum(m.successful_runs for m in metrics)
        failed_runs = sum(m.failed_runs for m in metrics)
        
        # Weighted averages
        quality_scores = [m.avg_quality_score for m in metrics if m.avg_quality_score is not None]
        latencies_avg = [m.avg_latency_ms for m in metrics if m.avg_latency_ms is not None]
        latencies_p95 = [m.p95_latency_ms for m in metrics if m.p95_latency_ms is not None]
        latencies_p99 = [m.p99_latency_ms for m in metrics if m.p99_latency_ms is not None]
        costs = [m.avg_cost_per_run for m in metrics if m.avg_cost_per_run is not None]
        
        invariants_passed = sum(m.invariants_passed for m in metrics)
        invariants_failed = sum(m.invariants_failed for m in metrics)
        
        return {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": successful_runs / total_runs if total_runs > 0 else None,
            "avg_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else None,
            "avg_latency_ms": sum(latencies_avg) / len(latencies_avg) if latencies_avg else None,
            "p95_latency_ms": sum(latencies_p95) / len(latencies_p95) if latencies_p95 else None,
            "p99_latency_ms": sum(latencies_p99) / len(latencies_p99) if latencies_p99 else None,
            "avg_cost_per_run": sum(costs) / len(costs) if costs else None,
            "invariants_passed": invariants_passed,
            "invariants_failed": invariants_failed,
            "days_evaluated": len(metrics),
        }


def format_gate_report(evaluation: Dict[str, Any]) -> str:
    """
    Format gate evaluation as human-readable report.
    
    Used for CI output and Slack notifications.
    """
    lines = []
    
    if "results" in evaluation:
        # Multi-agent report
        lines.append("# Agent Quality Gate Report\n")
        lines.append(f"**Status**: {'✅ PASSED' if evaluation['passed'] else '❌ FAILED'}\n")
        lines.append(f"**Violations**: {evaluation['total_violations']} total, {evaluation['critical_violations']} critical\n")
        
        for agent, result in evaluation["results"].items():
            lines.append(f"\n## {agent}")
            if result["passed"]:
                lines.append("✅ All gates passed")
            else:
                lines.append(f"❌ {len(result['violations'])} violation(s)")
                for v in result["violations"]:
                    icon = "🔴" if v.severity == "critical" else "⚠️"
                    lines.append(f"  {icon} {v.message}")
    else:
        # Single agent report
        agent = evaluation["agent"]
        lines.append(f"# {agent} Quality Gate\n")
        lines.append(f"**Status**: {'✅ PASSED' if evaluation['passed'] else '❌ FAILED'}\n")
        
        if evaluation["violations"]:
            lines.append("\n## Violations")
            for v in evaluation["violations"]:
                icon = "🔴" if v.severity == "critical" else "⚠️"
                lines.append(f"- {icon} {v.message}")
        
        if evaluation["current_metrics"]:
            lines.append("\n## Current Metrics")
            m = evaluation["current_metrics"]
            if m.get("avg_quality_score"):
                lines.append(f"- Quality: {m['avg_quality_score']:.1f}/100")
            if m.get("success_rate"):
                lines.append(f"- Success Rate: {m['success_rate']:.1%}")
            if m.get("avg_latency_ms"):
                lines.append(f"- Latency: {m['avg_latency_ms']:.0f}ms avg")
    
    return "\n".join(lines)
