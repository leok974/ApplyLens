"""Tests for regression detector and auto-rollback.

Tests:
- Metrics aggregation from audit logs
- Regression detection (quality, latency, cost)
- Automatic rollback triggering
- Threshold enforcement
"""

import pytest
from unittest.mock import Mock

from app.guard.regression_detector import RegressionDetector, MetricsStore
from app.models import AgentAuditLog


class TestMetricsStore:
    """Test metrics aggregation."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    def test_window_stats_separates_v1_v2(self, mock_db):
        """Should correctly separate V1 and V2 runs."""
        store = MetricsStore(mock_db)

        # Mock runs
        v1_run = Mock(spec=AgentAuditLog)
        v1_run.status = "succeeded"
        v1_run.plan = {"planner_meta": {"selected": "v1"}}
        v1_run.duration_ms = 500.0

        v2_run = Mock(spec=AgentAuditLog)
        v2_run.status = "succeeded"
        v2_run.plan = {"planner_meta": {"selected": "v2"}}
        v2_run.duration_ms = 1200.0

        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            v1_run,
            v2_run,
        ]

        stats = store.window_stats(window_runs=10)

        assert stats["v1"]["samples"] == 1
        assert stats["v2"]["samples"] == 1

    def test_window_stats_computes_aggregates(self, mock_db):
        """Should compute quality, latency, cost aggregates."""
        store = MetricsStore(mock_db)

        # Mock V2 runs with varying latencies
        runs = []
        for latency in [100, 200, 500, 1000, 2000]:
            run = Mock(spec=AgentAuditLog)
            run.status = "succeeded"
            run.plan = {"planner_meta": {"selected": "v2"}}
            run.duration_ms = float(latency)
            runs.append(run)

        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = runs

        stats = store.window_stats(window_runs=10)

        assert stats["v2"]["samples"] == 5
        assert stats["v2"]["latency_p95_ms"] > 1000  # p95 should be high

    def test_window_stats_handles_no_runs(self, mock_db):
        """Should handle case with no runs."""
        store = MetricsStore(mock_db)

        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        stats = store.window_stats(window_runs=10)

        assert stats["v1"]["samples"] == 0
        assert stats["v2"]["samples"] == 0


class TestRegressionDetector:
    """Test regression detection logic."""

    @pytest.fixture
    def mock_store(self):
        """Mock metrics store."""
        return Mock(spec=MetricsStore)

    @pytest.fixture
    def mock_settings_dao(self):
        """Mock runtime settings DAO."""
        return Mock()

    def test_insufficient_sample_no_action(self, mock_store, mock_settings_dao):
        """Should not evaluate with insufficient V2 samples."""
        detector = RegressionDetector(mock_store, mock_settings_dao)

        # Mock insufficient samples
        mock_store.window_stats.return_value = {
            "v1": {
                "samples": 100,
                "quality": 95.0,
                "latency_p95_ms": 500,
                "cost_cents": 1.0,
            },
            "v2": {
                "samples": 10,
                "quality": 90.0,
                "latency_p95_ms": 600,
                "cost_cents": 1.2,
            },  # < 30 samples
        }

        result = detector.evaluate()

        assert result["action"] == "none"
        assert result["reason"] == "insufficient_sample"
        assert not mock_settings_dao.update.called

    def test_quality_regression_triggers_rollback(self, mock_store, mock_settings_dao):
        """Should detect quality regression and trigger rollback."""
        detector = RegressionDetector(mock_store, mock_settings_dao)

        # Mock quality drop > 5 points
        mock_store.window_stats.return_value = {
            "v1": {
                "samples": 50,
                "quality": 95.0,
                "latency_p95_ms": 500,
                "cost_cents": 1.0,
            },
            "v2": {
                "samples": 50,
                "quality": 85.0,
                "latency_p95_ms": 500,
                "cost_cents": 1.0,
            },  # 10 point drop
        }

        result = detector.evaluate()

        assert result["action"] == "rollback"
        assert result["reason"] == "regression_detected"
        assert len(result["breaches"]) > 0
        assert "quality" in result["breaches"][0]

        # Should trigger settings update
        assert mock_settings_dao.update.called
        call_args = mock_settings_dao.update.call_args[0][0]
        assert call_args["planner_kill_switch"] is True
        assert call_args["planner_canary_pct"] == 0.0

    def test_latency_regression_triggers_rollback(self, mock_store, mock_settings_dao):
        """Should detect latency regression and trigger rollback."""
        detector = RegressionDetector(mock_store, mock_settings_dao)

        # Mock latency > 1600ms
        mock_store.window_stats.return_value = {
            "v1": {
                "samples": 50,
                "quality": 95.0,
                "latency_p95_ms": 500,
                "cost_cents": 1.0,
            },
            "v2": {
                "samples": 50,
                "quality": 95.0,
                "latency_p95_ms": 2000,
                "cost_cents": 1.0,
            },  # > 1600ms
        }

        result = detector.evaluate()

        assert result["action"] == "rollback"
        assert "latency" in result["breaches"][0]

    def test_cost_regression_triggers_rollback(self, mock_store, mock_settings_dao):
        """Should detect cost regression and trigger rollback."""
        detector = RegressionDetector(mock_store, mock_settings_dao)

        # Mock cost > 3.0 cents
        mock_store.window_stats.return_value = {
            "v1": {
                "samples": 50,
                "quality": 95.0,
                "latency_p95_ms": 500,
                "cost_cents": 1.0,
            },
            "v2": {
                "samples": 50,
                "quality": 95.0,
                "latency_p95_ms": 500,
                "cost_cents": 4.0,
            },  # > 3.0¢
        }

        result = detector.evaluate()

        assert result["action"] == "rollback"
        assert "cost" in result["breaches"][0]

    def test_multiple_breaches(self, mock_store, mock_settings_dao):
        """Should detect multiple simultaneous breaches."""
        detector = RegressionDetector(mock_store, mock_settings_dao)

        # Mock all three breaches
        mock_store.window_stats.return_value = {
            "v1": {
                "samples": 50,
                "quality": 95.0,
                "latency_p95_ms": 500,
                "cost_cents": 1.0,
            },
            "v2": {
                "samples": 50,
                "quality": 80.0,
                "latency_p95_ms": 2000,
                "cost_cents": 5.0,
            },
        }

        result = detector.evaluate()

        assert result["action"] == "rollback"
        assert len(result["breaches"]) == 3  # All three should be detected

    def test_no_regression_ok_status(self, mock_store, mock_settings_dao):
        """Should return OK when no regressions detected."""
        detector = RegressionDetector(mock_store, mock_settings_dao)

        # Mock good stats (no breaches)
        mock_store.window_stats.return_value = {
            "v1": {
                "samples": 50,
                "quality": 95.0,
                "latency_p95_ms": 500,
                "cost_cents": 1.0,
            },
            "v2": {
                "samples": 50,
                "quality": 94.0,
                "latency_p95_ms": 550,
                "cost_cents": 1.1,
            },  # All within bounds
        }

        result = detector.evaluate()

        assert result["action"] == "ok"
        assert result["reason"] == "within_thresholds"
        assert not mock_settings_dao.update.called

    def test_exact_threshold_no_rollback(self, mock_store, mock_settings_dao):
        """Should not rollback when exactly at threshold."""
        detector = RegressionDetector(mock_store, mock_settings_dao)

        # Mock exactly at thresholds (should not breach)
        mock_store.window_stats.return_value = {
            "v1": {
                "samples": 50,
                "quality": 95.0,
                "latency_p95_ms": 500,
                "cost_cents": 1.0,
            },
            "v2": {
                "samples": 50,
                "quality": 90.0,
                "latency_p95_ms": 1600,
                "cost_cents": 3.0,
            },  # Exactly at limits
        }

        result = detector.evaluate()

        # Should be OK (thresholds use >, not >=)
        assert result["action"] == "ok"


class TestRollbackIntegration:
    """Integration tests for rollback workflow."""

    def test_rollback_sets_correct_values(self):
        """Rollback should set kill_switch=True and canary_pct=0."""
        mock_settings_dao = Mock()
        mock_store = Mock(spec=MetricsStore)

        # Mock severe regression
        mock_store.window_stats.return_value = {
            "v1": {
                "samples": 50,
                "quality": 95.0,
                "latency_p95_ms": 500,
                "cost_cents": 1.0,
            },
            "v2": {
                "samples": 50,
                "quality": 70.0,
                "latency_p95_ms": 3000,
                "cost_cents": 10.0,
            },
        }

        detector = RegressionDetector(mock_store, mock_settings_dao)
        result = detector.evaluate()

        assert result["action"] == "rollback"

        # Verify settings update
        call_args = mock_settings_dao.update.call_args
        updates = call_args[0][0]
        assert updates["planner_kill_switch"] is True
        assert updates["planner_canary_pct"] == 0.0

        # Verify audit metadata
        assert call_args[1]["updated_by"] == "regression_detector"
        assert "auto_rollback" in call_args[1]["reason"]

    def test_rollback_includes_breach_details(self):
        """Rollback reason should include breach details."""
        mock_settings_dao = Mock()
        mock_store = Mock(spec=MetricsStore)

        mock_store.window_stats.return_value = {
            "v1": {
                "samples": 50,
                "quality": 95.0,
                "latency_p95_ms": 500,
                "cost_cents": 1.0,
            },
            "v2": {
                "samples": 50,
                "quality": 80.0,
                "latency_p95_ms": 2500,
                "cost_cents": 1.0,
            },
        }

        detector = RegressionDetector(mock_store, mock_settings_dao)
        detector.evaluate()

        # Check reason contains breach info
        call_args = mock_settings_dao.update.call_args
        reason = call_args[1]["reason"]
        assert "quality" in reason or "latency" in reason
