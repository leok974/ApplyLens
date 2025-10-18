"""
Tests for SLO definitions, evaluation, and alerting.
"""

import pytest
from datetime import datetime

from app.observability.slo import (
    SLOSpec,
    SLOStatus,
    SLOViolation,
    SLOMetric,
    SLOSeverity,
    SLOEvaluator,
    DEFAULT_SLOS,
    calculate_error_budget,
    get_slo_evaluator,
)
from app.observability.alerts import (
    AlertRule,
    Alert,
    AlertChannel,
    AlertManager,
    DEFAULT_ALERT_RULES,
    export_prometheus_metrics,
    generate_grafana_dashboard,
)


class TestSLOSpec:
    """Test SLO specifications."""
    
    def test_default_slos_defined(self):
        """Test default SLOs are defined for key agents."""
        assert "inbox.triage" in DEFAULT_SLOS
        assert "knowledge.search" in DEFAULT_SLOS
        assert "planner.deploy" in DEFAULT_SLOS
        assert "warehouse.health" in DEFAULT_SLOS
    
    def test_inbox_triage_slo(self):
        """Test inbox.triage SLO specification."""
        slo = DEFAULT_SLOS["inbox.triage"]
        
        assert slo.agent_name == "inbox.triage"
        assert slo.latency_p95_ms == 1500
        assert slo.latency_p99_ms == 3000
        assert slo.freshness_minutes == 30
        assert slo.freshness_min_rate == 0.99
        assert slo.precision_min == 0.95
        assert slo.success_rate_min == 0.98
        assert slo.error_rate_max == 0.02
        assert slo.cost_per_request_max == 0.05
    
    def test_slo_spec_validation(self):
        """Test SLO spec field validation."""
        # Valid spec
        slo = SLOSpec(
            agent_name="test.agent",
            latency_p95_ms=1000,
            precision_min=0.95,
        )
        assert slo.precision_min == 0.95
        
        # Invalid precision (>1)
        with pytest.raises(ValueError):
            SLOSpec(
                agent_name="test.agent",
                precision_min=1.5,
            )
        
        # Invalid precision (<0)
        with pytest.raises(ValueError):
            SLOSpec(
                agent_name="test.agent",
                precision_min=-0.1,
            )


class TestSLOEvaluator:
    """Test SLO evaluation logic."""
    
    @pytest.fixture
    def evaluator(self):
        """Create SLO evaluator."""
        return SLOEvaluator()
    
    def test_evaluate_compliant_metrics(self, evaluator):
        """Test evaluation with compliant metrics."""
        metrics = {
            "latency_p95_ms": 1200,  # Target: 1500
            "latency_p99_ms": 2500,  # Target: 3000
            "precision_rate": 0.97,  # Target: 0.95
            "success_rate": 0.99,    # Target: 0.98
            "error_rate": 0.01,      # Target: 0.02
            "cost_per_request": 0.03,  # Target: 0.05
        }
        
        status = evaluator.evaluate("inbox.triage", metrics)
        
        assert status.compliant is True
        assert len(status.violations) == 0
        assert status.latency_p95_ms == 1200
        assert status.precision_rate == 0.97
    
    def test_evaluate_latency_violation(self, evaluator):
        """Test evaluation with latency violation."""
        metrics = {
            "latency_p95_ms": 2000,  # Exceeds 1500 target
            "success_rate": 0.99,
        }
        
        status = evaluator.evaluate("inbox.triage", metrics)
        
        assert status.compliant is False
        assert len(status.violations) == 1
        
        violation = status.violations[0]
        assert violation.metric == SLOMetric.LATENCY_P95
        assert violation.severity == SLOSeverity.WARNING
        assert violation.threshold == 1500
        assert violation.actual == 2000
    
    def test_evaluate_critical_latency_violation(self, evaluator):
        """Test evaluation with critical latency violation (>1.5x target)."""
        metrics = {
            "latency_p95_ms": 2500,  # >1.5x target (1500)
        }
        
        status = evaluator.evaluate("inbox.triage", metrics)
        
        assert status.compliant is False
        violation = status.violations[0]
        assert violation.severity == SLOSeverity.CRITICAL
    
    def test_evaluate_precision_violation(self, evaluator):
        """Test evaluation with precision violation."""
        metrics = {
            "precision_rate": 0.92,  # Below 0.95 target
        }
        
        status = evaluator.evaluate("inbox.triage", metrics)
        
        assert status.compliant is False
        violation = status.violations[0]
        assert violation.metric == SLOMetric.PRECISION
        assert violation.threshold == 0.95
        assert violation.actual == 0.92
    
    def test_evaluate_error_rate_violation(self, evaluator):
        """Test evaluation with error rate violation."""
        metrics = {
            "error_rate": 0.05,  # Exceeds 0.02 target
        }
        
        status = evaluator.evaluate("inbox.triage", metrics)
        
        assert status.compliant is False
        violation = status.violations[0]
        assert violation.metric == SLOMetric.ERROR_RATE
        assert violation.threshold == 0.02
        assert violation.actual == 0.05
    
    def test_evaluate_cost_violation(self, evaluator):
        """Test evaluation with cost violation."""
        metrics = {
            "cost_per_request": 0.08,  # Exceeds 0.05 target
        }
        
        status = evaluator.evaluate("inbox.triage", metrics)
        
        assert status.compliant is False
        violation = status.violations[0]
        assert violation.metric == SLOMetric.COST_PER_REQUEST
        assert violation.severity == SLOSeverity.WARNING  # Cost is warning
    
    def test_evaluate_burn_rate_fast(self, evaluator):
        """Test evaluation with fast burn rate."""
        metrics = {
            "burn_rate_1h": 20.0,  # Exceeds 14.4 threshold
        }
        
        status = evaluator.evaluate("inbox.triage", metrics)
        
        assert status.compliant is False
        assert status.burn_rate_alert is True
        violation = status.violations[0]
        assert violation.severity == SLOSeverity.CRITICAL
    
    def test_evaluate_burn_rate_slow(self, evaluator):
        """Test evaluation with slow burn rate."""
        metrics = {
            "burn_rate_6h": 8.0,  # Exceeds 6.0 threshold
        }
        
        status = evaluator.evaluate("inbox.triage", metrics)
        
        assert status.compliant is False
        assert status.burn_rate_alert is True
        violation = status.violations[0]
        assert violation.severity == SLOSeverity.WARNING
    
    def test_evaluate_multiple_violations(self, evaluator):
        """Test evaluation with multiple violations."""
        metrics = {
            "latency_p95_ms": 2000,
            "precision_rate": 0.90,
            "error_rate": 0.05,
        }
        
        status = evaluator.evaluate("inbox.triage", metrics)
        
        assert status.compliant is False
        assert len(status.violations) == 3
        
        metrics_violated = {v.metric for v in status.violations}
        assert SLOMetric.LATENCY_P95 in metrics_violated
        assert SLOMetric.PRECISION in metrics_violated
        assert SLOMetric.ERROR_RATE in metrics_violated
    
    def test_evaluate_unknown_agent(self, evaluator):
        """Test evaluation for agent without SLO."""
        metrics = {"latency_p95_ms": 5000}
        
        status = evaluator.evaluate("unknown.agent", metrics)
        
        assert status.compliant is True
        assert len(status.violations) == 0
    
    def test_get_slo(self, evaluator):
        """Test getting SLO specification."""
        slo = evaluator.get_slo("inbox.triage")
        
        assert slo is not None
        assert slo.agent_name == "inbox.triage"
        assert slo.latency_p95_ms == 1500
    
    def test_list_agents(self, evaluator):
        """Test listing agents with SLOs."""
        agents = evaluator.list_agents()
        
        assert "inbox.triage" in agents
        assert "knowledge.search" in agents
        assert len(agents) >= 6


class TestErrorBudget:
    """Test error budget calculations."""
    
    def test_calculate_error_budget_99(self):
        """Test error budget for 99% SLO."""
        budget = calculate_error_budget(0.99, measurement_window_hours=720)
        
        assert budget["slo_target"] == 0.99
        assert budget["error_budget_pct"] == 0.01
        assert budget["measurement_window_hours"] == 720
        assert budget["total_error_budget_hours"] == 7.2
        assert budget["burn_rate_fast_threshold"] == 14.4
        assert budget["burn_rate_slow_threshold"] == 6.0
    
    def test_calculate_error_budget_95(self):
        """Test error budget for 95% SLO."""
        budget = calculate_error_budget(0.95, measurement_window_hours=720)
        
        assert budget["error_budget_pct"] == 0.05
        assert budget["total_error_budget_hours"] == 36.0


class TestAlertRules:
    """Test alert rule definitions."""
    
    def test_default_alert_rules_defined(self):
        """Test default alert rules are defined."""
        assert len(DEFAULT_ALERT_RULES) > 0
        
        rule_names = {rule.name for rule in DEFAULT_ALERT_RULES}
        assert "slo_fast_burn_rate" in rule_names
        assert "slo_slow_burn_rate" in rule_names
        assert "slo_latency_p95_critical" in rule_names
    
    def test_critical_rules_use_pagerduty(self):
        """Test critical rules notify PagerDuty."""
        critical_rules = [
            rule for rule in DEFAULT_ALERT_RULES
            if rule.severity == SLOSeverity.CRITICAL
        ]
        
        for rule in critical_rules:
            assert AlertChannel.PAGERDUTY in rule.channels
    
    def test_warning_rules_use_slack(self):
        """Test warning rules notify Slack."""
        warning_rules = [
            rule for rule in DEFAULT_ALERT_RULES
            if rule.severity == SLOSeverity.WARNING
        ]
        
        for rule in warning_rules:
            assert AlertChannel.SLACK in rule.channels


class TestAlertManager:
    """Test alert management."""
    
    @pytest.fixture
    def manager(self):
        """Create alert manager."""
        return AlertManager()
    
    @pytest.fixture
    def compliant_status(self):
        """Create compliant SLO status."""
        return SLOStatus(
            agent_name="test.agent",
            compliant=True,
            violations=[],
        )
    
    @pytest.fixture
    def violation_status(self):
        """Create SLO status with violation."""
        return SLOStatus(
            agent_name="test.agent",
            compliant=False,
            violations=[
                SLOViolation(
                    agent_name="test.agent",
                    metric=SLOMetric.LATENCY_P95,
                    severity=SLOSeverity.CRITICAL,
                    threshold=1500,
                    actual=2500,
                    message="Latency exceeded",
                )
            ],
        )
    
    def test_check_alerts_no_violations(self, manager, compliant_status):
        """Test checking alerts with no violations."""
        alerts = manager.check_alerts("test.agent", compliant_status)
        
        assert len(alerts) == 0
        assert len(manager.active_alerts) == 0
    
    def test_check_alerts_with_violation(self, manager, violation_status):
        """Test checking alerts with violation."""
        alerts = manager.check_alerts("test.agent", violation_status)
        
        assert len(alerts) >= 1
        assert len(manager.active_alerts) >= 1
    
    def test_acknowledge_alert(self, manager, violation_status):
        """Test acknowledging an alert."""
        manager.check_alerts("test.agent", violation_status)
        
        alert_key = "test.agent:latency_p95_ms"
        success = manager.acknowledge_alert(alert_key, "user@example.com")
        
        assert success is True
        alert = manager.active_alerts[alert_key]
        assert alert.acknowledged is True
        assert alert.acknowledged_by == "user@example.com"
    
    def test_resolve_alert(self, manager, violation_status):
        """Test resolving an alert."""
        manager.check_alerts("test.agent", violation_status)
        
        alert_key = "test.agent:latency_p95_ms"
        success = manager.resolve_alert(alert_key)
        
        assert success is True
        alert = manager.active_alerts[alert_key]
        assert alert.resolved is True
        assert alert.resolved_at is not None
    
    def test_get_active_alerts(self, manager, violation_status):
        """Test getting active alerts."""
        manager.check_alerts("test.agent", violation_status)
        
        active = manager.get_active_alerts()
        assert len(active) >= 1
        
        # Filter by agent
        agent_alerts = manager.get_active_alerts(agent_name="test.agent")
        assert len(agent_alerts) >= 1
        
        # Filter by severity
        critical_alerts = manager.get_active_alerts(severity=SLOSeverity.CRITICAL)
        assert len(critical_alerts) >= 1
    
    def test_get_alert_summary(self, manager, violation_status):
        """Test getting alert summary."""
        manager.check_alerts("test.agent", violation_status)
        
        summary = manager.get_alert_summary()
        
        assert "total_active" in summary
        assert "critical" in summary
        assert "warning" in summary
        assert summary["total_active"] >= 1


class TestPrometheusExport:
    """Test Prometheus metrics export."""
    
    def test_export_prometheus_metrics(self):
        """Test exporting SLO status as Prometheus metrics."""
        status = SLOStatus(
            agent_name="test.agent",
            latency_p95_ms=1200,
            latency_p99_ms=2500,
            success_rate=0.99,
            error_rate=0.01,
            precision_rate=0.97,
            cost_per_request=0.03,
            compliant=True,
            burn_rate_1h=2.5,
            burn_rate_6h=1.2,
        )
        
        metrics = export_prometheus_metrics(status)
        
        assert 'applylens_agent_latency_p95_seconds{agent="test.agent"}' in metrics
        assert 'applylens_agent_success_rate{agent="test.agent"}' in metrics
        assert 'applylens_agent_slo_compliant{agent="test.agent"} 1' in metrics
        assert 'applylens_agent_burn_rate_1h{agent="test.agent"}' in metrics
    
    def test_export_non_compliant_status(self):
        """Test exporting non-compliant status."""
        status = SLOStatus(
            agent_name="test.agent",
            compliant=False,
        )
        
        metrics = export_prometheus_metrics(status)
        
        assert 'applylens_agent_slo_compliant{agent="test.agent"} 0' in metrics


class TestGrafanaDashboard:
    """Test Grafana dashboard generation."""
    
    def test_generate_grafana_dashboard(self):
        """Test generating Grafana dashboard config."""
        agents = ["inbox.triage", "knowledge.search"]
        
        dashboard = generate_grafana_dashboard(agents)
        
        assert "dashboard" in dashboard
        assert dashboard["dashboard"]["title"] == "ApplyLens SLO Dashboard"
        assert "panels" in dashboard["dashboard"]
        assert len(dashboard["dashboard"]["panels"]) > 0
        
        # Check panel titles
        panel_titles = {p["title"] for p in dashboard["dashboard"]["panels"]}
        assert "SLO Compliance Status" in panel_titles
        assert "Agent Latency P95" in panel_titles
        assert "Error Budget Burn Rate" in panel_titles


class TestGlobalInstances:
    """Test global singleton instances."""
    
    def test_get_slo_evaluator(self):
        """Test getting global SLO evaluator."""
        evaluator1 = get_slo_evaluator()
        evaluator2 = get_slo_evaluator()
        
        assert evaluator1 is evaluator2  # Same instance
        assert len(evaluator1.list_agents()) > 0
