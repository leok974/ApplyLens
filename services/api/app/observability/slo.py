"""
Service Level Objectives (SLOs) for ApplyLens agents.

Defines performance targets for latency, freshness, precision, and cost.
Integrates with Prometheus for metrics export and monitoring.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class SLOMetric(str, Enum):
    """SLO metric types."""
    LATENCY_P95 = "latency_p95_ms"
    LATENCY_P99 = "latency_p99_ms"
    FRESHNESS = "freshness_minutes"
    PRECISION = "precision_rate"
    SUCCESS_RATE = "success_rate"
    COST_PER_REQUEST = "cost_per_request"
    ERROR_RATE = "error_rate"


class SLOSeverity(str, Enum):
    """SLO violation severity levels."""
    INFO = "info"          # Within budget, no action needed
    WARNING = "warning"    # Approaching threshold, monitor
    CRITICAL = "critical"  # Threshold breached, immediate action


class SLOSpec(BaseModel):
    """Service Level Objective specification for an agent."""
    
    agent_name: str = Field(..., description="Agent identifier (e.g., inbox.triage)")
    
    # Latency targets (milliseconds)
    latency_p95_ms: Optional[int] = Field(None, description="95th percentile latency target")
    latency_p99_ms: Optional[int] = Field(None, description="99th percentile latency target")
    
    # Freshness target (minutes)
    freshness_minutes: Optional[int] = Field(None, description="Maximum data staleness")
    freshness_min_rate: Optional[float] = Field(None, ge=0, le=1, description="Minimum freshness rate")
    
    # Quality targets
    precision_min: Optional[float] = Field(None, ge=0, le=1, description="Minimum precision rate")
    success_rate_min: Optional[float] = Field(None, ge=0, le=1, description="Minimum success rate")
    
    # Cost targets
    cost_per_request_max: Optional[float] = Field(None, description="Maximum cost per request ($)")
    
    # Error targets
    error_rate_max: Optional[float] = Field(None, ge=0, le=1, description="Maximum error rate")
    
    # Burn rate configuration
    burn_rate_fast: float = Field(default=14.4, description="Fast burn rate threshold (1h window)")
    burn_rate_slow: float = Field(default=6.0, description="Slow burn rate threshold (6h window)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_name": "inbox.triage",
                "latency_p95_ms": 1500,
                "latency_p99_ms": 3000,
                "freshness_minutes": 30,
                "freshness_min_rate": 0.99,
                "precision_min": 0.95,
                "success_rate_min": 0.98,
                "error_rate_max": 0.02,
            }
        }


class SLOViolation(BaseModel):
    """SLO violation record."""
    
    agent_name: str
    metric: SLOMetric
    severity: SLOSeverity
    threshold: float
    actual: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message: str


class SLOStatus(BaseModel):
    """Current SLO compliance status for an agent."""
    
    agent_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Metric measurements
    latency_p95_ms: Optional[float] = None
    latency_p99_ms: Optional[float] = None
    freshness_minutes: Optional[float] = None
    freshness_rate: Optional[float] = None
    precision_rate: Optional[float] = None
    success_rate: Optional[float] = None
    cost_per_request: Optional[float] = None
    error_rate: Optional[float] = None
    
    # Compliance status
    compliant: bool = True
    violations: List[SLOViolation] = Field(default_factory=list)
    
    # Burn rate status
    burn_rate_1h: Optional[float] = None
    burn_rate_6h: Optional[float] = None
    burn_rate_alert: bool = False


# Default SLO specifications for ApplyLens agents
DEFAULT_SLOS: Dict[str, SLOSpec] = {
    "inbox.triage": SLOSpec(
        agent_name="inbox.triage",
        latency_p95_ms=1500,
        latency_p99_ms=3000,
        freshness_minutes=30,
        freshness_min_rate=0.99,
        precision_min=0.95,
        success_rate_min=0.98,
        error_rate_max=0.02,
        cost_per_request_max=0.05,
    ),
    "inbox.search": SLOSpec(
        agent_name="inbox.search",
        latency_p95_ms=800,
        latency_p99_ms=1500,
        success_rate_min=0.99,
        error_rate_max=0.01,
        cost_per_request_max=0.02,
    ),
    "knowledge.search": SLOSpec(
        agent_name="knowledge.search",
        latency_p95_ms=1000,
        latency_p99_ms=2000,
        success_rate_min=0.98,
        error_rate_max=0.02,
        cost_per_request_max=0.03,
    ),
    "planner.deploy": SLOSpec(
        agent_name="planner.deploy",
        latency_p95_ms=5000,
        latency_p99_ms=10000,
        success_rate_min=0.95,
        error_rate_max=0.05,
        cost_per_request_max=0.20,
    ),
    "warehouse.health": SLOSpec(
        agent_name="warehouse.health",
        latency_p95_ms=2000,
        latency_p99_ms=4000,
        freshness_minutes=60,
        freshness_min_rate=0.95,
        success_rate_min=0.98,
        error_rate_max=0.02,
        cost_per_request_max=0.10,
    ),
    "analytics.insights": SLOSpec(
        agent_name="analytics.insights",
        latency_p95_ms=3000,
        latency_p99_ms=6000,
        success_rate_min=0.97,
        error_rate_max=0.03,
        cost_per_request_max=0.15,
    ),
}


class SLOEvaluator:
    """Evaluates SLO compliance and detects violations."""
    
    def __init__(self, slo_specs: Optional[Dict[str, SLOSpec]] = None):
        """
        Initialize SLO evaluator.
        
        Args:
            slo_specs: Custom SLO specifications (defaults to DEFAULT_SLOS)
        """
        self.slo_specs = slo_specs or DEFAULT_SLOS
    
    def evaluate(
        self,
        agent_name: str,
        metrics: Dict[str, float],
    ) -> SLOStatus:
        """
        Evaluate SLO compliance for an agent.
        
        Args:
            agent_name: Agent identifier
            metrics: Current metric measurements
        
        Returns:
            SLOStatus with compliance information
        """
        spec = self.slo_specs.get(agent_name)
        if not spec:
            # No SLO defined for this agent
            return SLOStatus(
                agent_name=agent_name,
                compliant=True,
            )
        
        status = SLOStatus(agent_name=agent_name)
        violations = []
        
        # Check latency P95
        if spec.latency_p95_ms and "latency_p95_ms" in metrics:
            status.latency_p95_ms = metrics["latency_p95_ms"]
            if metrics["latency_p95_ms"] > spec.latency_p95_ms:
                violations.append(SLOViolation(
                    agent_name=agent_name,
                    metric=SLOMetric.LATENCY_P95,
                    severity=SLOSeverity.CRITICAL if metrics["latency_p95_ms"] > spec.latency_p95_ms * 1.5 else SLOSeverity.WARNING,
                    threshold=spec.latency_p95_ms,
                    actual=metrics["latency_p95_ms"],
                    message=f"P95 latency {metrics['latency_p95_ms']:.0f}ms exceeds target {spec.latency_p95_ms}ms",
                ))
        
        # Check latency P99
        if spec.latency_p99_ms and "latency_p99_ms" in metrics:
            status.latency_p99_ms = metrics["latency_p99_ms"]
            if metrics["latency_p99_ms"] > spec.latency_p99_ms:
                violations.append(SLOViolation(
                    agent_name=agent_name,
                    metric=SLOMetric.LATENCY_P99,
                    severity=SLOSeverity.CRITICAL if metrics["latency_p99_ms"] > spec.latency_p99_ms * 1.5 else SLOSeverity.WARNING,
                    threshold=spec.latency_p99_ms,
                    actual=metrics["latency_p99_ms"],
                    message=f"P99 latency {metrics['latency_p99_ms']:.0f}ms exceeds target {spec.latency_p99_ms}ms",
                ))
        
        # Check freshness rate
        if spec.freshness_min_rate and "freshness_rate" in metrics:
            status.freshness_rate = metrics["freshness_rate"]
            if metrics["freshness_rate"] < spec.freshness_min_rate:
                violations.append(SLOViolation(
                    agent_name=agent_name,
                    metric=SLOMetric.FRESHNESS,
                    severity=SLOSeverity.CRITICAL if metrics["freshness_rate"] < spec.freshness_min_rate * 0.9 else SLOSeverity.WARNING,
                    threshold=spec.freshness_min_rate,
                    actual=metrics["freshness_rate"],
                    message=f"Freshness rate {metrics['freshness_rate']:.2%} below target {spec.freshness_min_rate:.2%}",
                ))
        
        # Check precision
        if spec.precision_min and "precision_rate" in metrics:
            status.precision_rate = metrics["precision_rate"]
            if metrics["precision_rate"] < spec.precision_min:
                violations.append(SLOViolation(
                    agent_name=agent_name,
                    metric=SLOMetric.PRECISION,
                    severity=SLOSeverity.CRITICAL if metrics["precision_rate"] < spec.precision_min * 0.9 else SLOSeverity.WARNING,
                    threshold=spec.precision_min,
                    actual=metrics["precision_rate"],
                    message=f"Precision {metrics['precision_rate']:.2%} below target {spec.precision_min:.2%}",
                ))
        
        # Check success rate
        if spec.success_rate_min and "success_rate" in metrics:
            status.success_rate = metrics["success_rate"]
            if metrics["success_rate"] < spec.success_rate_min:
                violations.append(SLOViolation(
                    agent_name=agent_name,
                    metric=SLOMetric.SUCCESS_RATE,
                    severity=SLOSeverity.CRITICAL if metrics["success_rate"] < spec.success_rate_min * 0.95 else SLOSeverity.WARNING,
                    threshold=spec.success_rate_min,
                    actual=metrics["success_rate"],
                    message=f"Success rate {metrics['success_rate']:.2%} below target {spec.success_rate_min:.2%}",
                ))
        
        # Check error rate
        if spec.error_rate_max and "error_rate" in metrics:
            status.error_rate = metrics["error_rate"]
            if metrics["error_rate"] > spec.error_rate_max:
                violations.append(SLOViolation(
                    agent_name=agent_name,
                    metric=SLOMetric.ERROR_RATE,
                    severity=SLOSeverity.CRITICAL if metrics["error_rate"] > spec.error_rate_max * 2 else SLOSeverity.WARNING,
                    threshold=spec.error_rate_max,
                    actual=metrics["error_rate"],
                    message=f"Error rate {metrics['error_rate']:.2%} exceeds target {spec.error_rate_max:.2%}",
                ))
        
        # Check cost per request
        if spec.cost_per_request_max and "cost_per_request" in metrics:
            status.cost_per_request = metrics["cost_per_request"]
            if metrics["cost_per_request"] > spec.cost_per_request_max:
                violations.append(SLOViolation(
                    agent_name=agent_name,
                    metric=SLOMetric.COST_PER_REQUEST,
                    severity=SLOSeverity.WARNING,  # Cost is usually a warning, not critical
                    threshold=spec.cost_per_request_max,
                    actual=metrics["cost_per_request"],
                    message=f"Cost per request ${metrics['cost_per_request']:.3f} exceeds target ${spec.cost_per_request_max:.3f}",
                ))
        
        # Check burn rates (error budget consumption)
        if "burn_rate_1h" in metrics:
            status.burn_rate_1h = metrics["burn_rate_1h"]
            if metrics["burn_rate_1h"] > spec.burn_rate_fast:
                status.burn_rate_alert = True
                violations.append(SLOViolation(
                    agent_name=agent_name,
                    metric=SLOMetric.ERROR_RATE,
                    severity=SLOSeverity.CRITICAL,
                    threshold=spec.burn_rate_fast,
                    actual=metrics["burn_rate_1h"],
                    message=f"Fast burn rate {metrics['burn_rate_1h']:.1f}x exceeds threshold {spec.burn_rate_fast}x",
                ))
        
        if "burn_rate_6h" in metrics:
            status.burn_rate_6h = metrics["burn_rate_6h"]
            if metrics["burn_rate_6h"] > spec.burn_rate_slow:
                status.burn_rate_alert = True
                violations.append(SLOViolation(
                    agent_name=agent_name,
                    metric=SLOMetric.ERROR_RATE,
                    severity=SLOSeverity.WARNING,
                    threshold=spec.burn_rate_slow,
                    actual=metrics["burn_rate_6h"],
                    message=f"Slow burn rate {metrics['burn_rate_6h']:.1f}x exceeds threshold {spec.burn_rate_slow}x",
                ))
        
        status.violations = violations
        status.compliant = len(violations) == 0
        
        return status
    
    def get_slo(self, agent_name: str) -> Optional[SLOSpec]:
        """Get SLO specification for an agent."""
        return self.slo_specs.get(agent_name)
    
    def list_agents(self) -> List[str]:
        """List all agents with SLO specifications."""
        return list(self.slo_specs.keys())


def calculate_error_budget(
    slo_target: float,
    measurement_window_hours: int = 720,  # 30 days
) -> Dict[str, Any]:
    """
    Calculate error budget for an SLO.
    
    Args:
        slo_target: Target success rate (e.g., 0.99 for 99%)
        measurement_window_hours: Measurement window in hours
    
    Returns:
        Error budget information
    """
    error_budget_pct = 1.0 - slo_target
    allowed_failures_per_hour = error_budget_pct
    total_error_budget = error_budget_pct * measurement_window_hours
    
    return {
        "slo_target": slo_target,
        "error_budget_pct": error_budget_pct,
        "measurement_window_hours": measurement_window_hours,
        "allowed_failures_per_hour": allowed_failures_per_hour,
        "total_error_budget_hours": total_error_budget,
        "burn_rate_fast_threshold": 14.4,  # 1h window, alerts at 5% budget consumed
        "burn_rate_slow_threshold": 6.0,   # 6h window, alerts at 10% budget consumed
    }


# Global SLO evaluator instance
_slo_evaluator: Optional[SLOEvaluator] = None


def get_slo_evaluator() -> SLOEvaluator:
    """Get global SLO evaluator instance."""
    global _slo_evaluator
    if _slo_evaluator is None:
        _slo_evaluator = SLOEvaluator()
    return _slo_evaluator
