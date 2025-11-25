"""
SLO alerting and monitoring integration.

Exports metrics to Prometheus and generates alerts based on burn rate.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from pydantic import BaseModel, Field

from .slo import (
    SLOEvaluator,
    SLOStatus,
    SLOViolation,
    SLOSeverity,
    get_slo_evaluator,
)

logger = logging.getLogger(__name__)


class AlertChannel(str, Enum):
    """Alert notification channels."""

    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"
    WEBHOOK = "webhook"


class AlertRule(BaseModel):
    """Alert rule configuration."""

    name: str
    description: str
    condition: str  # e.g., "burn_rate_1h > 14.4"
    severity: SLOSeverity
    channels: List[AlertChannel]
    cooldown_minutes: int = 30  # Minimum time between alerts

    class Config:
        use_enum_values = True


class Alert(BaseModel):
    """Alert instance."""

    rule_name: str
    agent_name: str
    severity: SLOSeverity
    message: str
    channels: List[AlertChannel]
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None


# Prometheus metric templates
PROMETHEUS_METRICS = """
# HELP applylens_agent_latency_p95_seconds Agent P95 latency in seconds
# TYPE applylens_agent_latency_p95_seconds gauge
applylens_agent_latency_p95_seconds{{agent="{agent}"}} {value}

# HELP applylens_agent_latency_p99_seconds Agent P99 latency in seconds
# TYPE applylens_agent_latency_p99_seconds gauge
applylens_agent_latency_p99_seconds{{agent="{agent}"}} {value}

# HELP applylens_agent_success_rate Agent success rate (0-1)
# TYPE applylens_agent_success_rate gauge
applylens_agent_success_rate{{agent="{agent}"}} {value}

# HELP applylens_agent_error_rate Agent error rate (0-1)
# TYPE applylens_agent_error_rate gauge
applylens_agent_error_rate{{agent="{agent}"}} {value}

# HELP applylens_agent_precision_rate Agent precision rate (0-1)
# TYPE applylens_agent_precision_rate gauge
applylens_agent_precision_rate{{agent="{agent}"}} {value}

# HELP applylens_agent_freshness_rate Agent freshness rate (0-1)
# TYPE applylens_agent_freshness_rate gauge
applylens_agent_freshness_rate{{agent="{agent}"}} {value}

# HELP applylens_agent_cost_per_request Agent cost per request in dollars
# TYPE applylens_agent_cost_per_request gauge
applylens_agent_cost_per_request{{agent="{agent}"}} {value}

# HELP applylens_agent_slo_compliant Agent SLO compliance (0=non-compliant, 1=compliant)
# TYPE applylens_agent_slo_compliant gauge
applylens_agent_slo_compliant{{agent="{agent}"}} {value}

# HELP applylens_agent_burn_rate_1h Agent error budget burn rate (1h window)
# TYPE applylens_agent_burn_rate_1h gauge
applylens_agent_burn_rate_1h{{agent="{agent}"}} {value}

# HELP applylens_agent_burn_rate_6h Agent error budget burn rate (6h window)
# TYPE applylens_agent_burn_rate_6h gauge
applylens_agent_burn_rate_6h{{agent="{agent}"}} {value}
"""


# Default alert rules
DEFAULT_ALERT_RULES: List[AlertRule] = [
    # Critical: Fast burn rate (1h window)
    AlertRule(
        name="slo_fast_burn_rate",
        description="Error budget burning at >14.4x rate (1h window)",
        condition="burn_rate_1h > 14.4",
        severity=SLOSeverity.CRITICAL,
        channels=[AlertChannel.PAGERDUTY, AlertChannel.SLACK],
        cooldown_minutes=15,
    ),
    # Warning: Slow burn rate (6h window)
    AlertRule(
        name="slo_slow_burn_rate",
        description="Error budget burning at >6x rate (6h window)",
        condition="burn_rate_6h > 6.0",
        severity=SLOSeverity.WARNING,
        channels=[AlertChannel.SLACK],
        cooldown_minutes=60,
    ),
    # Critical: Latency P95 exceeded significantly
    AlertRule(
        name="slo_latency_p95_critical",
        description="P95 latency exceeds target by >50%",
        condition="latency_p95_ms > target * 1.5",
        severity=SLOSeverity.CRITICAL,
        channels=[AlertChannel.PAGERDUTY, AlertChannel.SLACK],
        cooldown_minutes=30,
    ),
    # Warning: Latency P95 exceeded
    AlertRule(
        name="slo_latency_p95_warning",
        description="P95 latency exceeds target",
        condition="latency_p95_ms > target",
        severity=SLOSeverity.WARNING,
        channels=[AlertChannel.SLACK],
        cooldown_minutes=60,
    ),
    # Critical: Precision dropped significantly
    AlertRule(
        name="slo_precision_critical",
        description="Precision dropped below 90% of target",
        condition="precision_rate < target * 0.9",
        severity=SLOSeverity.CRITICAL,
        channels=[AlertChannel.PAGERDUTY, AlertChannel.SLACK],
        cooldown_minutes=30,
    ),
    # Warning: Precision below target
    AlertRule(
        name="slo_precision_warning",
        description="Precision below target",
        condition="precision_rate < target",
        severity=SLOSeverity.WARNING,
        channels=[AlertChannel.SLACK],
        cooldown_minutes=60,
    ),
    # Warning: Cost exceeded
    AlertRule(
        name="slo_cost_warning",
        description="Cost per request exceeds target",
        condition="cost_per_request > target",
        severity=SLOSeverity.WARNING,
        channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
        cooldown_minutes=120,  # Longer cooldown for cost alerts
    ),
    # Critical: Error rate exceeded
    AlertRule(
        name="slo_error_rate_critical",
        description="Error rate exceeds target by 2x",
        condition="error_rate > target * 2",
        severity=SLOSeverity.CRITICAL,
        channels=[AlertChannel.PAGERDUTY, AlertChannel.SLACK],
        cooldown_minutes=15,
    ),
]


class AlertManager:
    """Manages SLO alerts and notifications."""

    def __init__(
        self,
        evaluator: Optional[SLOEvaluator] = None,
        alert_rules: Optional[List[AlertRule]] = None,
    ):
        """
        Initialize alert manager.

        Args:
            evaluator: SLO evaluator instance
            alert_rules: Custom alert rules (defaults to DEFAULT_ALERT_RULES)
        """
        self.evaluator = evaluator or get_slo_evaluator()
        self.alert_rules = alert_rules or DEFAULT_ALERT_RULES
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []

    def check_alerts(
        self,
        agent_name: str,
        status: SLOStatus,
    ) -> List[Alert]:
        """
        Check SLO status and generate alerts if needed.

        Args:
            agent_name: Agent identifier
            status: Current SLO status

        Returns:
            List of triggered alerts
        """
        triggered_alerts = []

        for violation in status.violations:
            # Check if we should alert on this violation
            alert_key = f"{agent_name}:{violation.metric.value}"

            # Check cooldown period
            if alert_key in self.active_alerts:
                existing_alert = self.active_alerts[alert_key]
                if not existing_alert.resolved:
                    # Alert still active, check if we should re-alert
                    # (we don't re-alert within cooldown period)
                    continue

            # Find matching alert rule
            matching_rule = self._find_matching_rule(violation)
            if not matching_rule:
                continue

            # Create alert
            alert = Alert(
                rule_name=matching_rule.name,
                agent_name=agent_name,
                severity=violation.severity,
                message=violation.message,
                channels=matching_rule.channels,
            )

            self.active_alerts[alert_key] = alert
            self.alert_history.append(alert)
            triggered_alerts.append(alert)

            logger.warning(
                f"SLO alert triggered: {alert.rule_name} for {agent_name} - {alert.message}"
            )

        return triggered_alerts

    def _find_matching_rule(self, violation: SLOViolation) -> Optional[AlertRule]:
        """Find alert rule matching a violation."""
        # Simple matching based on metric and severity
        # In production, this would evaluate the rule condition
        for rule in self.alert_rules:
            if (
                violation.severity.value in rule.name
                or violation.metric.value in rule.name
            ):
                return rule
        return None

    def acknowledge_alert(
        self,
        alert_key: str,
        acknowledged_by: str,
    ) -> bool:
        """
        Acknowledge an active alert.

        Args:
            alert_key: Alert key (agent:metric)
            acknowledged_by: User acknowledging the alert

        Returns:
            True if acknowledged
        """
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            alert.acknowledged = True
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
            logger.info(f"Alert acknowledged: {alert_key} by {acknowledged_by}")
            return True
        return False

    def resolve_alert(self, alert_key: str) -> bool:
        """
        Resolve an active alert.

        Args:
            alert_key: Alert key (agent:metric)

        Returns:
            True if resolved
        """
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            logger.info(f"Alert resolved: {alert_key}")
            return True
        return False

    def get_active_alerts(
        self,
        agent_name: Optional[str] = None,
        severity: Optional[SLOSeverity] = None,
    ) -> List[Alert]:
        """
        Get active alerts.

        Args:
            agent_name: Filter by agent (optional)
            severity: Filter by severity (optional)

        Returns:
            List of active alerts
        """
        alerts = [alert for alert in self.active_alerts.values() if not alert.resolved]

        if agent_name:
            alerts = [a for a in alerts if a.agent_name == agent_name]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert status."""
        active_alerts = self.get_active_alerts()

        return {
            "total_active": len(active_alerts),
            "critical": len(
                [a for a in active_alerts if a.severity == SLOSeverity.CRITICAL]
            ),
            "warning": len(
                [a for a in active_alerts if a.severity == SLOSeverity.WARNING]
            ),
            "acknowledged": len([a for a in active_alerts if a.acknowledged]),
            "unacknowledged": len([a for a in active_alerts if not a.acknowledged]),
            "total_historical": len(self.alert_history),
        }


def export_prometheus_metrics(status: SLOStatus) -> str:
    """
    Export SLO status as Prometheus metrics.

    Args:
        status: SLO status to export

    Returns:
        Prometheus metrics in text format
    """
    metrics = []
    agent = status.agent_name

    if status.latency_p95_ms is not None:
        metrics.append(
            f'applylens_agent_latency_p95_seconds{{agent="{agent}"}} {status.latency_p95_ms / 1000:.3f}'
        )

    if status.latency_p99_ms is not None:
        metrics.append(
            f'applylens_agent_latency_p99_seconds{{agent="{agent}"}} {status.latency_p99_ms / 1000:.3f}'
        )

    if status.success_rate is not None:
        metrics.append(
            f'applylens_agent_success_rate{{agent="{agent}"}} {status.success_rate:.4f}'
        )

    if status.error_rate is not None:
        metrics.append(
            f'applylens_agent_error_rate{{agent="{agent}"}} {status.error_rate:.4f}'
        )

    if status.precision_rate is not None:
        metrics.append(
            f'applylens_agent_precision_rate{{agent="{agent}"}} {status.precision_rate:.4f}'
        )

    if status.freshness_rate is not None:
        metrics.append(
            f'applylens_agent_freshness_rate{{agent="{agent}"}} {status.freshness_rate:.4f}'
        )

    if status.cost_per_request is not None:
        metrics.append(
            f'applylens_agent_cost_per_request{{agent="{agent}"}} {status.cost_per_request:.6f}'
        )

    metrics.append(
        f'applylens_agent_slo_compliant{{agent="{agent}"}} {1 if status.compliant else 0}'
    )

    if status.burn_rate_1h is not None:
        metrics.append(
            f'applylens_agent_burn_rate_1h{{agent="{agent}"}} {status.burn_rate_1h:.2f}'
        )

    if status.burn_rate_6h is not None:
        metrics.append(
            f'applylens_agent_burn_rate_6h{{agent="{agent}"}} {status.burn_rate_6h:.2f}'
        )

    return "\n".join(metrics)


def generate_grafana_dashboard(agents: List[str]) -> Dict[str, Any]:
    """
    Generate Grafana dashboard JSON for SLO monitoring.

    Args:
        agents: List of agent names to monitor

    Returns:
        Grafana dashboard configuration
    """
    panels = []

    # Panel 1: SLO Compliance Status
    panels.append(
        {
            "title": "SLO Compliance Status",
            "type": "stat",
            "targets": [
                {
                    "expr": f'applylens_agent_slo_compliant{{agent="{agent}"}}'
                    for agent in agents
                }
            ],
            "gridPos": {"x": 0, "y": 0, "w": 24, "h": 4},
        }
    )

    # Panel 2: Latency P95
    panels.append(
        {
            "title": "Agent Latency P95",
            "type": "graph",
            "targets": [
                {
                    "expr": f'applylens_agent_latency_p95_seconds{{agent="{agent}"}}'
                    for agent in agents
                }
            ],
            "gridPos": {"x": 0, "y": 4, "w": 12, "h": 8},
        }
    )

    # Panel 3: Error Rate
    panels.append(
        {
            "title": "Agent Error Rate",
            "type": "graph",
            "targets": [
                {
                    "expr": f'applylens_agent_error_rate{{agent="{agent}"}}'
                    for agent in agents
                }
            ],
            "gridPos": {"x": 12, "y": 4, "w": 12, "h": 8},
        }
    )

    # Panel 4: Burn Rate
    panels.append(
        {
            "title": "Error Budget Burn Rate",
            "type": "graph",
            "targets": [
                {
                    "expr": f'applylens_agent_burn_rate_1h{{agent="{agent}"}}'
                    for agent in agents
                },
                {
                    "expr": f'applylens_agent_burn_rate_6h{{agent="{agent}"}}'
                    for agent in agents
                },
            ],
            "gridPos": {"x": 0, "y": 12, "w": 12, "h": 8},
        }
    )

    # Panel 5: Cost per Request
    panels.append(
        {
            "title": "Cost per Request",
            "type": "graph",
            "targets": [
                {
                    "expr": f'applylens_agent_cost_per_request{{agent="{agent}"}}'
                    for agent in agents
                }
            ],
            "gridPos": {"x": 12, "y": 12, "w": 12, "h": 8},
        }
    )

    return {
        "dashboard": {
            "title": "ApplyLens SLO Dashboard",
            "tags": ["applylens", "slo", "observability"],
            "timezone": "utc",
            "panels": panels,
            "refresh": "30s",
            "time": {"from": "now-6h", "to": "now"},
        }
    }


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
