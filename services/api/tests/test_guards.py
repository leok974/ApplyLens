"""Tests for online learning guardrails.

Tests:
- Auto-apply approved bundles as canary
- Canary performance checking
- Promotion and rollback
- Gradual rollout
- Nightly guard checks
"""

import pytest
from unittest.mock import Mock, patch

from app.active.guards import OnlineLearningGuard
from app.models import RuntimeSetting


class TestOnlineLearningGuard:
    """Test online learning safety guardrails."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    def test_check_canary_performance_regression(self, mock_db):
        """Should detect regression and recommend rollback."""
        guard = OnlineLearningGuard(mock_db)

        with patch.object(guard.detector, "detect_regression") as mock_detect:
            mock_detect.return_value = {
                "has_regression": True,
                "quality_delta": -0.08,
                "latency_delta": 0.15,
                "regression_type": "quality",
            }

            result = guard.check_canary_performance("inbox_triage")

        assert result["has_regression"] is True
        assert result["recommendation"] == "rollback"
        assert result["reason"] == "quality"

    def test_check_canary_performance_improvement(self, mock_db):
        """Should detect improvement and recommend promotion."""
        guard = OnlineLearningGuard(mock_db)

        with patch.object(guard.detector, "detect_regression") as mock_detect:
            mock_detect.return_value = {
                "has_regression": False,
                "quality_delta": 0.05,  # 5% improvement
                "latency_delta": -0.2,  # 20% faster
            }

            result = guard.check_canary_performance("inbox_triage")

        assert result["has_regression"] is False
        assert result["recommendation"] == "promote"
        assert result["reason"] == "performance_improvement"

    def test_check_canary_performance_neutral(self, mock_db):
        """Should recommend monitoring if neutral."""
        guard = OnlineLearningGuard(mock_db)

        with patch.object(guard.detector, "detect_regression") as mock_detect:
            mock_detect.return_value = {
                "has_regression": False,
                "quality_delta": 0.01,  # Small improvement
                "latency_delta": 0.02,
            }

            result = guard.check_canary_performance("inbox_triage")

        assert result["recommendation"] == "monitor"
        assert result["reason"] == "neutral_performance"

    def test_promote_canary_full(self, mock_db):
        """Should promote canary to 100%."""
        guard = OnlineLearningGuard(mock_db)

        canary_bundle = {"agent": "inbox_triage", "thresholds": {}}

        with patch.object(guard, "_load_canary_bundle") as mock_load:
            mock_load.return_value = canary_bundle

            with patch.object(guard.bundle_mgr, "_apply_bundle") as mock_apply:
                with patch.object(guard, "_clear_canary") as mock_clear:
                    guard.promote_canary("inbox_triage", target_percent=100)

        assert mock_apply.called
        assert mock_clear.called

    def test_promote_canary_partial(self, mock_db):
        """Should promote canary to intermediate %."""
        guard = OnlineLearningGuard(mock_db)

        canary_bundle = {"agent": "inbox_triage"}

        with patch.object(guard, "_load_canary_bundle") as mock_load:
            mock_load.return_value = canary_bundle

            with patch.object(guard, "_update_canary_percent") as mock_update:
                guard.promote_canary("inbox_triage", target_percent=50)

        assert mock_update.called
        mock_update.assert_called_with("inbox_triage", 50)

    def test_rollback_canary(self, mock_db):
        """Should rollback canary deployment."""
        guard = OnlineLearningGuard(mock_db)

        with patch.object(guard, "_clear_canary") as mock_clear:
            guard.rollback_canary("inbox_triage")

        assert mock_clear.called

    def test_gradual_rollout_promote(self, mock_db):
        """Should promote through stages."""
        guard = OnlineLearningGuard(mock_db)

        with patch.object(guard, "_get_canary_percent") as mock_get_percent:
            mock_get_percent.return_value = 10  # Currently at 10%

            with patch.object(guard, "check_canary_performance") as mock_check:
                mock_check.return_value = {
                    "recommendation": "promote",
                    "quality_delta": 0.03,
                    "latency_delta": -0.1,
                }

                with patch.object(guard, "promote_canary") as mock_promote:
                    result = guard.gradual_rollout("inbox_triage", stages=[10, 50, 100])

        assert result["status"] == "promoted"
        assert result["from_percent"] == 10
        assert result["to_percent"] == 50
        assert mock_promote.called

    def test_gradual_rollout_rollback(self, mock_db):
        """Should rollback on regression."""
        guard = OnlineLearningGuard(mock_db)

        with patch.object(guard, "_get_canary_percent") as mock_get_percent:
            mock_get_percent.return_value = 50

            with patch.object(guard, "check_canary_performance") as mock_check:
                mock_check.return_value = {
                    "recommendation": "rollback",
                    "reason": "quality_regression",
                }

                with patch.object(guard, "rollback_canary") as mock_rollback:
                    result = guard.gradual_rollout("inbox_triage")

        assert result["status"] == "rolled_back"
        assert result["reason"] == "quality_regression"
        assert mock_rollback.called

    def test_gradual_rollout_monitor(self, mock_db):
        """Should continue monitoring if neutral."""
        guard = OnlineLearningGuard(mock_db)

        with patch.object(guard, "_get_canary_percent") as mock_get_percent:
            mock_get_percent.return_value = 10

            with patch.object(guard, "check_canary_performance") as mock_check:
                mock_check.return_value = {
                    "recommendation": "monitor",
                    "quality_delta": 0.01,
                }

                result = guard.gradual_rollout("inbox_triage")

        assert result["status"] == "monitoring"
        assert result["current_percent"] == 10

    def test_nightly_guard_check(self, mock_db):
        """Should check all active canaries nightly."""
        guard = OnlineLearningGuard(mock_db)

        # Mock canary settings
        setting1 = Mock(spec=RuntimeSetting)
        setting1.key = "planner_canary.inbox_triage.canary_percent"
        setting1.value = "10"

        setting2 = Mock(spec=RuntimeSetting)
        setting2.key = "planner_canary.insights_writer.canary_percent"
        setting2.value = "50"

        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [setting1, setting2]

        mock_db.query.return_value = query_mock

        with patch.object(guard, "gradual_rollout") as mock_rollout:
            mock_rollout.return_value = {"status": "promoted"}

            results = guard.nightly_guard_check()

        assert len(results) == 2
        assert "inbox_triage" in results
        assert "insights_writer" in results
        assert mock_rollout.call_count == 2
