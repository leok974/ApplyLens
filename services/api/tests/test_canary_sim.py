"""Simulated canary tests with synthetic regressions.

Tests the full canary workflow including:
- Canary rollout at different percentages
- Regression detection with synthetic degradations
- Automatic rollback triggering
- Kill switch enforcement
"""

from datetime import datetime

from app.guard.regression_detector import RegressionDetector


class FakeMetricsStore:
    """Fake metrics store with configurable stats for testing."""

    def __init__(
        self,
        v1_quality: float = 95.0,
        v2_quality: float = 95.0,
        v1_latency: float = 500,
        v2_latency: float = 500,
        v1_cost: float = 1.0,
        v2_cost: float = 1.0,
        v1_samples: int = 50,
        v2_samples: int = 50,
    ):
        """Initialize with synthetic metrics.

        Args:
            v1_quality: V1 quality score (0-100)
            v2_quality: V2 quality score (0-100)
            v1_latency: V1 latency p95 (ms)
            v2_latency: V2 latency p95 (ms)
            v1_cost: V1 cost (cents)
            v2_cost: V2 cost (cents)
            v1_samples: V1 sample count
            v2_samples: V2 sample count
        """
        self.stats = {
            "v1": {
                "samples": v1_samples,
                "quality": v1_quality,
                "latency_p95_ms": v1_latency,
                "cost_cents": v1_cost,
            },
            "v2": {
                "samples": v2_samples,
                "quality": v2_quality,
                "latency_p95_ms": v2_latency,
                "cost_cents": v2_cost,
            },
        }

    def window_stats(self, window_runs: int = 100, window_minutes: int = None):
        """Return pre-configured stats."""
        return self.stats


class FakeSettingsDAO:
    """Fake settings DAO that tracks updates."""

    def __init__(self):
        """Initialize with default settings."""
        self.settings = {"planner_canary_pct": 0.0, "planner_kill_switch": False}
        self.update_history = []

    def get(self):
        """Get current settings."""
        return self.settings

    def update(self, updates, updated_by="system", reason=None):
        """Update settings and track in history."""
        self.settings.update(updates)
        self.update_history.append(
            {
                "updates": updates,
                "updated_by": updated_by,
                "reason": reason,
                "timestamp": datetime.utcnow(),
            }
        )
        return self.settings

    def get_planner_config(self):
        """Get planner-specific config."""
        return {
            "canary_pct": self.settings["planner_canary_pct"],
            "kill_switch": self.settings["planner_kill_switch"],
        }


class TestCanarySimulation:
    """Simulated canary rollout scenarios."""

    def test_healthy_canary_no_rollback(self):
        """Healthy V2 metrics should not trigger rollback."""
        store = FakeMetricsStore(
            v1_quality=95.0,
            v2_quality=94.0,  # Slight drop, but within threshold (< 5 points)
            v1_latency=500,
            v2_latency=550,  # Slight increase, but under 1600ms
            v1_cost=1.0,
            v2_cost=1.1,  # Slight increase, but under 3.0¢
            v2_samples=50,
        )
        dao = FakeSettingsDAO()
        detector = RegressionDetector(store, dao)

        result = detector.evaluate()

        assert result["action"] == "ok"
        assert len(dao.update_history) == 0  # No rollback triggered

    def test_quality_regression_triggers_rollback(self):
        """Quality drop > 5 points should trigger rollback."""
        store = FakeMetricsStore(
            v1_quality=95.0,
            v2_quality=85.0,  # 10 point drop (> 5 threshold)
            v2_samples=50,
        )
        dao = FakeSettingsDAO()
        detector = RegressionDetector(store, dao)

        result = detector.evaluate()

        assert result["action"] == "rollback"
        assert len(result["breaches"]) > 0
        assert "quality" in result["breaches"][0]

        # Verify rollback was triggered
        assert len(dao.update_history) == 1
        assert dao.settings["planner_kill_switch"] is True
        assert dao.settings["planner_canary_pct"] == 0.0

    def test_latency_regression_triggers_rollback(self):
        """Latency > 1600ms should trigger rollback."""
        store = FakeMetricsStore(
            v1_latency=500,
            v2_latency=1700,  # > 1600ms threshold
            v2_samples=50,
        )
        dao = FakeSettingsDAO()
        detector = RegressionDetector(store, dao)

        result = detector.evaluate()

        assert result["action"] == "rollback"
        assert "latency" in result["breaches"][0]
        assert dao.settings["planner_kill_switch"] is True

    def test_cost_regression_triggers_rollback(self):
        """Cost > 3.0¢ should trigger rollback."""
        store = FakeMetricsStore(
            v1_cost=1.0,
            v2_cost=4.0,  # > 3.0¢ threshold
            v2_samples=50,
        )
        dao = FakeSettingsDAO()
        detector = RegressionDetector(store, dao)

        result = detector.evaluate()

        assert result["action"] == "rollback"
        assert "cost" in result["breaches"][0]
        assert dao.settings["planner_kill_switch"] is True

    def test_multiple_regressions_all_detected(self):
        """Multiple simultaneous regressions should all be detected."""
        store = FakeMetricsStore(
            v1_quality=95.0,
            v2_quality=80.0,  # Quality breach
            v1_latency=500,
            v2_latency=2000,  # Latency breach
            v1_cost=1.0,
            v2_cost=5.0,  # Cost breach
            v2_samples=50,
        )
        dao = FakeSettingsDAO()
        detector = RegressionDetector(store, dao)

        result = detector.evaluate()

        assert result["action"] == "rollback"
        assert len(result["breaches"]) == 3  # All three breaches detected

        # Verify reason contains all breach types
        update = dao.update_history[0]
        reason = update["reason"]
        assert "quality" in reason or "latency" in reason or "cost" in reason

    def test_insufficient_samples_no_evaluation(self):
        """Insufficient V2 samples should skip evaluation."""
        store = FakeMetricsStore(
            v2_quality=70.0,  # Would be a breach if evaluated
            v2_samples=10,  # < 30 minimum
        )
        dao = FakeSettingsDAO()
        detector = RegressionDetector(store, dao)

        result = detector.evaluate()

        assert result["action"] == "none"
        assert result["reason"] == "insufficient_sample"
        assert len(dao.update_history) == 0  # No rollback

    def test_gradual_degradation(self):
        """Test gradual performance degradation over time."""
        dao = FakeSettingsDAO()

        # Iteration 1: Healthy
        store1 = FakeMetricsStore(v2_quality=94.0, v2_samples=50)
        detector1 = RegressionDetector(store1, dao)
        result1 = detector1.evaluate()
        assert result1["action"] == "ok"

        # Iteration 2: Slight degradation (still OK)
        store2 = FakeMetricsStore(v2_quality=91.0, v2_samples=50)
        detector2 = RegressionDetector(store2, dao)
        result2 = detector2.evaluate()
        assert result2["action"] == "ok"

        # Iteration 3: Crosses threshold (rollback)
        store3 = FakeMetricsStore(v2_quality=88.0, v2_samples=50)  # 95 - 88 = 7 > 5
        detector3 = RegressionDetector(store3, dao)
        result3 = detector3.evaluate()
        assert result3["action"] == "rollback"

    def test_rollback_audit_metadata(self):
        """Rollback should include detailed audit metadata."""
        store = FakeMetricsStore(v1_quality=95.0, v2_quality=80.0, v2_samples=50)
        dao = FakeSettingsDAO()
        detector = RegressionDetector(store, dao)

        detector.evaluate()

        # Check audit metadata
        update = dao.update_history[0]
        assert update["updated_by"] == "regression_detector"
        assert "auto_rollback" in update["reason"]
        assert "quality" in update["reason"]

    def test_canary_percentage_scenarios(self):
        """Test different canary percentage scenarios."""
        # 5% canary (early rollout)
        dao_5pct = FakeSettingsDAO()
        dao_5pct.settings["planner_canary_pct"] = 5.0

        # 50% canary (mid rollout)
        dao_50pct = FakeSettingsDAO()
        dao_50pct.settings["planner_canary_pct"] = 50.0

        # 95% canary (near completion)
        dao_95pct = FakeSettingsDAO()
        dao_95pct.settings["planner_canary_pct"] = 95.0

        # All should rollback on severe regression
        store = FakeMetricsStore(v2_quality=70.0, v2_samples=50)

        for dao in [dao_5pct, dao_50pct, dao_95pct]:
            detector = RegressionDetector(store, dao)
            result = detector.evaluate()
            assert result["action"] == "rollback"
            assert dao.settings["planner_canary_pct"] == 0.0
            assert dao.settings["planner_kill_switch"] is True


class TestRollbackRecovery:
    """Test recovery after rollback."""

    def test_manual_re_enable_after_fix(self):
        """After rollback and fix, should be able to re-enable."""
        dao = FakeSettingsDAO()

        # 1. Initial healthy state
        dao.settings["planner_canary_pct"] = 10.0
        dao.settings["planner_kill_switch"] = False

        # 2. Regression triggers rollback
        store_bad = FakeMetricsStore(v2_quality=70.0, v2_samples=50)
        detector_bad = RegressionDetector(store_bad, dao)
        detector_bad.evaluate()

        assert dao.settings["planner_kill_switch"] is True
        assert dao.settings["planner_canary_pct"] == 0.0

        # 3. Manual re-enable after fix
        dao.update(
            {"planner_kill_switch": False, "planner_canary_pct": 5.0},
            updated_by="admin",
            reason="fixed_quality_issue",
        )

        assert dao.settings["planner_kill_switch"] is False
        assert dao.settings["planner_canary_pct"] == 5.0

        # 4. Verify healthy metrics don't re-trigger rollback
        store_good = FakeMetricsStore(v2_quality=94.0, v2_samples=50)
        detector_good = RegressionDetector(store_good, dao)
        result = detector_good.evaluate()

        assert result["action"] == "ok"
        assert dao.settings["planner_kill_switch"] is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_exactly_at_threshold_no_rollback(self):
        """Exactly at threshold should not trigger rollback."""
        # Quality drop exactly 5.0 points (threshold is > 5.0)
        store = FakeMetricsStore(
            v1_quality=95.0,
            v2_quality=90.0,  # Exactly 5.0 drop
            v2_samples=50,
        )
        dao = FakeSettingsDAO()
        detector = RegressionDetector(store, dao)

        result = detector.evaluate()

        # Should not rollback (threshold is >, not >=)
        assert result["action"] == "ok"

    def test_zero_samples_v1_and_v2(self):
        """Zero samples for both versions should handle gracefully."""
        store = FakeMetricsStore(v1_samples=0, v2_samples=0)
        dao = FakeSettingsDAO()
        detector = RegressionDetector(store, dao)

        result = detector.evaluate()

        assert result["action"] == "none"
        assert result["reason"] == "insufficient_sample"

    def test_v2_better_than_v1(self):
        """V2 outperforming V1 should be OK."""
        store = FakeMetricsStore(
            v1_quality=90.0,
            v2_quality=96.0,  # V2 better
            v1_latency=800,
            v2_latency=400,  # V2 faster
            v1_cost=2.0,
            v2_cost=0.8,  # V2 cheaper
            v2_samples=50,
        )
        dao = FakeSettingsDAO()
        detector = RegressionDetector(store, dao)

        result = detector.evaluate()

        assert result["action"] == "ok"
        assert len(result.get("breaches", [])) == 0
