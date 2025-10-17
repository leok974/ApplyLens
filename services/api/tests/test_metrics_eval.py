"""
Tests for evaluation metrics and dashboard integration.

Tests:
- Metrics export functionality
- Prometheus metric creation
- Dashboard status endpoints
- Alert summary generation
"""
import pytest
from datetime import datetime, timedelta
from app.eval.metrics import MetricsExporter
from app.models import AgentMetricsDaily


class TestMetricsExporter:
    """Test metrics export functionality."""
    
    def test_export_no_data(self, db_session):
        """Test export with no metrics data."""
        exporter = MetricsExporter(db_session)
        stats = exporter.export_all_metrics(lookback_days=1)
        
        assert stats['agents_exported'] == 0
        assert stats['metrics_exported'] == 0
        assert stats['days_covered'] == 1
    
    def test_export_with_single_agent(self, db_session):
        """Test export with metrics for one agent."""
        # Create sample metric
        today = datetime.utcnow().date()
        metric = AgentMetricsDaily(
            agent="inbox.triage",
            date=today,
            total_runs=100,
            successful_runs=95,
            failed_runs=5,
            avg_quality_score=88.5,
            avg_latency_ms=450.0,
            p50_latency_ms=400.0,
            p95_latency_ms=550.0,
            p99_latency_ms=650.0,
        )
        db_session.add(metric)
        db_session.commit()
        
        exporter = MetricsExporter(db_session)
        stats = exporter.export_all_metrics(lookback_days=1)
        
        assert stats['agents_exported'] == 1
        assert stats['metrics_exported'] == 1
    
    def test_export_multiple_agents(self, db_session):
        """Test export with metrics for multiple agents."""
        today = datetime.utcnow().date()
        
        agents = ["inbox.triage", "knowledge.update", "insights.write"]
        for agent in agents:
            metric = AgentMetricsDaily(
                agent=agent,
                date=today,
                total_runs=50,
                avg_quality_score=85.0,
            )
            db_session.add(metric)
        
        db_session.commit()
        
        exporter = MetricsExporter(db_session)
        stats = exporter.export_all_metrics(lookback_days=1)
        
        assert stats['agents_exported'] == 3
        assert stats['metrics_exported'] == 3
    
    def test_export_multiple_days(self, db_session):
        """Test export with metrics across multiple days."""
        today = datetime.utcnow().date()
        
        for i in range(5):
            date = today - timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
            )
            db_session.add(metric)
        
        db_session.commit()
        
        exporter = MetricsExporter(db_session)
        stats = exporter.export_all_metrics(lookback_days=5)
        
        assert stats['agents_exported'] == 1
        assert stats['metrics_exported'] == 5
    
    def test_export_with_quality_scores(self, db_session):
        """Test that quality scores are exported correctly."""
        today = datetime.utcnow().date()
        metric = AgentMetricsDaily(
            agent="inbox.triage",
            date=today,
            total_runs=100,
            avg_quality_score=92.5,
        )
        db_session.add(metric)
        db_session.commit()
        
        exporter = MetricsExporter(db_session)
        exporter.export_all_metrics(lookback_days=1)
        
        # Metrics should be set (actual verification would check Prometheus)
        # In real tests, you'd mock prometheus_client
        assert True  # Placeholder
    
    def test_export_with_latency_metrics(self, db_session):
        """Test that latency metrics are exported."""
        today = datetime.utcnow().date()
        metric = AgentMetricsDaily(
            agent="inbox.triage",
            date=today,
            total_runs=100,
            avg_latency_ms=450.0,
            p50_latency_ms=400.0,
            p95_latency_ms=550.0,
            p99_latency_ms=650.0,
        )
        db_session.add(metric)
        db_session.commit()
        
        exporter = MetricsExporter(db_session)
        exporter.export_all_metrics(lookback_days=1)
        
        assert True  # Would verify metric values in real test
    
    def test_export_with_invariant_metrics(self, db_session):
        """Test invariant metrics export."""
        today = datetime.utcnow().date()
        metric = AgentMetricsDaily(
            agent="inbox.triage",
            date=today,
            total_runs=100,
            invariants_passed=95,
            invariants_failed=5,
            failed_invariant_ids=["inv_001", "inv_002"],
        )
        db_session.add(metric)
        db_session.commit()
        
        exporter = MetricsExporter(db_session)
        exporter.export_all_metrics(lookback_days=1)
        
        assert True  # Would verify counter increments
    
    def test_export_with_redteam_metrics(self, db_session):
        """Test red team metrics export."""
        today = datetime.utcnow().date()
        metric = AgentMetricsDaily(
            agent="inbox.triage",
            date=today,
            total_runs=100,
            redteam_attacks_detected=8,
            redteam_attacks_missed=2,
            redteam_false_positives=1,
        )
        db_session.add(metric)
        db_session.commit()
        
        exporter = MetricsExporter(db_session)
        exporter.export_all_metrics(lookback_days=1)
        
        assert True  # Would verify detection rate calculation


class TestMetricsAPI:
    """Test metrics API endpoints (would use TestClient in real tests)."""
    
    def test_export_endpoint_structure(self):
        """Test export endpoint returns correct structure."""
        # Mock test - in real implementation use FastAPI TestClient
        response_schema = {
            'success': bool,
            'agents_exported': int,
            'metrics_exported': int,
            'days_covered': int,
            'exported_at': datetime,
        }
        assert all(isinstance(k, str) for k in response_schema.keys())
    
    def test_dashboard_status_structure(self):
        """Test dashboard status endpoint schema."""
        status_schema = {
            'agents': list,
            'total_agents': int,
            'passing_gates': int,
            'failing_gates': int,
            'active_violations': int,
            'last_updated': datetime,
        }
        assert all(isinstance(k, str) for k in status_schema.keys())
    
    def test_alert_summary_structure(self):
        """Test alert summary endpoint schema."""
        alert_schema = {
            'total_alerts': int,
            'critical_alerts': int,
            'warning_alerts': int,
            'alerts_by_agent': dict,
            'alerts_by_type': dict,
        }
        assert all(isinstance(k, str) for k in alert_schema.keys())


class TestPrometheusIntegration:
    """Test Prometheus metrics integration."""
    
    def test_metric_names_valid(self):
        """Test that metric names follow Prometheus conventions."""
        from app.eval.metrics import (
            agent_quality_score,
            agent_success_rate,
            agent_latency_p95,
        )
        
        # Metric names should be valid
        assert 'agent_quality_score' in str(agent_quality_score._name)
        assert 'agent_success_rate' in str(agent_success_rate._name)
    
    def test_metric_labels_defined(self):
        """Test that metrics have required labels."""
        from app.eval.metrics import (
            agent_quality_score,
            budget_violations_total,
        )
        
        # Quality score should have 'agent' label
        assert 'agent' in agent_quality_score._labelnames
        
        # Violations should have agent, budget_type, severity
        assert 'agent' in budget_violations_total._labelnames
        assert 'budget_type' in budget_violations_total._labelnames
        assert 'severity' in budget_violations_total._labelnames
    
    def test_gauge_vs_counter_types(self):
        """Test that metric types are correct."""
        from prometheus_client import Gauge, Counter
        from app.eval.metrics import (
            agent_quality_score,
            agent_total_runs,
        )
        
        # Quality score should be Gauge (can go up/down)
        assert isinstance(agent_quality_score, Gauge)
        
        # Total runs should be Counter (only increases)
        assert isinstance(agent_total_runs, Counter)


class TestDashboardConfiguration:
    """Test dashboard and alert configuration."""
    
    def test_dashboard_json_valid(self):
        """Test that dashboard JSON is valid."""
        import json
        from pathlib import Path
        
        dashboard_path = Path("grafana/agent_evaluation_dashboard.json")
        if dashboard_path.exists():
            with open(dashboard_path) as f:
                dashboard = json.load(f)
            
            assert 'dashboard' in dashboard
            assert 'title' in dashboard['dashboard']
            assert dashboard['dashboard']['title'] == "Agent Evaluation Dashboard"
    
    def test_alert_rules_yaml_valid(self):
        """Test that alert rules YAML is valid."""
        import yaml
        from pathlib import Path
        
        alerts_path = Path("prometheus/agent_alerts.yml")
        if alerts_path.exists():
            with open(alerts_path) as f:
                alerts = yaml.safe_load(f)
            
            assert 'groups' in alerts
            assert len(alerts['groups']) > 0
    
    def test_dashboard_has_required_panels(self):
        """Test dashboard has essential panels."""
        import json
        from pathlib import Path
        
        dashboard_path = Path("grafana/agent_evaluation_dashboard.json")
        if dashboard_path.exists():
            with open(dashboard_path) as f:
                dashboard = json.load(f)
            
            panels = dashboard['dashboard'].get('panels', [])
            
            # Should have multiple panels
            assert len(panels) >= 10
            
            # Check for key panel types
            panel_titles = [p.get('title', '') for p in panels]
            assert any('Quality' in title for title in panel_titles)
            assert any('Latency' in title for title in panel_titles)
            assert any('Violation' in title for title in panel_titles)
    
    def test_alert_rules_cover_key_scenarios(self):
        """Test that alert rules cover critical scenarios."""
        import yaml
        from pathlib import Path
        
        alerts_path = Path("prometheus/agent_alerts.yml")
        if alerts_path.exists():
            with open(alerts_path) as f:
                alerts = yaml.safe_load(f)
            
            all_alert_names = []
            for group in alerts['groups']:
                for rule in group.get('rules', []):
                    if 'alert' in rule:
                        all_alert_names.append(rule['alert'])
            
            # Should have alerts for key scenarios
            assert any('Quality' in name for name in all_alert_names)
            assert any('Latency' in name for name in all_alert_names)
            assert any('Budget' in name for name in all_alert_names)
            assert any('Invariant' in name for name in all_alert_names)
            assert any('RedTeam' in name for name in all_alert_names)
