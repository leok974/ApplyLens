"""Tests for PlannerSwitchboard canary routing.

Tests:
- Shadow execution (both planners run)
- Canary traffic split
- Kill switch enforcement
- Diff tracking
- Metrics recording
"""

import pytest
from unittest.mock import Mock, patch
from app.agents.planner_switch import PlannerSwitchboard


class TestPlannerSwitchboard:
    """Test switchboard routing logic."""

    def test_shadow_execution_both_planners_run(self):
        """Both V1 and V2 should run regardless of selection."""
        switchboard = PlannerSwitchboard(canary_pct=0.0)  # Force V1

        with (
            patch.object(switchboard.v1, "plan") as mock_v1,
            patch.object(switchboard.v2, "plan") as mock_v2,
        ):
            mock_v1.return_value = {"agent": "inbox_triage", "steps": ["a", "b"]}
            mock_v2.return_value = {"agent": "inbox_triage", "steps": ["x", "y"]}

            plan, meta = switchboard.plan("Process email", {"agent": "inbox_triage"})

            # Both should be called
            assert mock_v1.called
            assert mock_v2.called

    def test_kill_switch_forces_v1(self):
        """Kill switch should force V1 selection."""
        switchboard = PlannerSwitchboard(canary_pct=100.0, kill_switch=True)

        with (
            patch.object(switchboard.v1, "plan") as mock_v1,
            patch.object(switchboard.v2, "plan") as mock_v2,
        ):
            mock_v1.return_value = {"agent": "v1_agent", "steps": ["a"]}
            mock_v2.return_value = {"agent": "v2_agent", "steps": ["b"]}

            plan, meta = switchboard.plan("Test", {})

            assert meta["selected"] == "v1"
            assert meta["kill_switch"] is True
            assert plan["agent"] == "v1_agent"

    def test_canary_0_percent_selects_v1(self):
        """0% canary should always select V1."""
        switchboard = PlannerSwitchboard(canary_pct=0.0, kill_switch=False)

        with (
            patch.object(switchboard.v1, "plan") as mock_v1,
            patch.object(switchboard.v2, "plan") as mock_v2,
        ):
            mock_v1.return_value = {"agent": "v1_agent"}
            mock_v2.return_value = {"agent": "v2_agent"}

            # Run 10 times, should always be V1
            for _ in range(10):
                plan, meta = switchboard.plan("Test", {})
                assert meta["selected"] == "v1"

    def test_canary_100_percent_selects_v2(self):
        """100% canary should always select V2 (when kill switch off)."""
        switchboard = PlannerSwitchboard(canary_pct=100.0, kill_switch=False)

        with (
            patch.object(switchboard.v1, "plan") as mock_v1,
            patch.object(switchboard.v2, "plan") as mock_v2,
        ):
            mock_v1.return_value = {"agent": "v1_agent"}
            mock_v2.return_value = {"agent": "v2_agent"}

            # Run 10 times, should always be V2
            for _ in range(10):
                plan, meta = switchboard.plan("Test", {})
                assert meta["selected"] == "v2"

    @patch("random.random")
    def test_canary_50_percent_distribution(self, mock_random):
        """50% canary should split traffic evenly."""
        switchboard = PlannerSwitchboard(canary_pct=50.0, kill_switch=False)

        with (
            patch.object(switchboard.v1, "plan") as mock_v1,
            patch.object(switchboard.v2, "plan") as mock_v2,
        ):
            mock_v1.return_value = {"agent": "v1_agent"}
            mock_v2.return_value = {"agent": "v2_agent"}

            # Mock random.random() to return 0.3 (< 0.5), should select V2
            mock_random.return_value = 0.3
            plan, meta = switchboard.plan("Test", {})
            assert meta["selected"] == "v2"

            # Mock random.random() to return 0.7 (>= 0.5), should select V1
            mock_random.return_value = 0.7
            plan, meta = switchboard.plan("Test", {})
            assert meta["selected"] == "v1"

    def test_diff_computation_agent_changed(self):
        """Diff should detect agent changes."""
        switchboard = PlannerSwitchboard(canary_pct=0.0)

        with (
            patch.object(switchboard.v1, "plan") as mock_v1,
            patch.object(switchboard.v2, "plan") as mock_v2,
        ):
            mock_v1.return_value = {"agent": "inbox_triage", "steps": ["a"]}
            mock_v2.return_value = {"agent": "inbox_priority", "steps": ["a"]}

            plan, meta = switchboard.plan("Test", {})

            assert meta["diff"]["agent_changed"] is True
            assert meta["diff"]["v1_agent"] == "inbox_triage"
            assert meta["diff"]["v2_agent"] == "inbox_priority"

    def test_diff_computation_steps_changed(self):
        """Diff should detect step changes."""
        switchboard = PlannerSwitchboard(canary_pct=0.0)

        with (
            patch.object(switchboard.v1, "plan") as mock_v1,
            patch.object(switchboard.v2, "plan") as mock_v2,
        ):
            mock_v1.return_value = {
                "agent": "inbox",
                "steps": ["validate", "prepare_tools", "act", "summarize"],
            }
            mock_v2.return_value = {
                "agent": "inbox",
                "steps": ["prepare", "execute", "summarize"],
            }

            plan, meta = switchboard.plan("Test", {})

            assert meta["diff"]["steps_changed"] is True
            assert meta["diff"]["v1_steps_count"] == 4
            assert meta["diff"]["v2_steps_count"] == 3

    def test_diff_computation_no_changes(self):
        """Diff should show no changes when decisions match."""
        switchboard = PlannerSwitchboard(canary_pct=0.0)

        with (
            patch.object(switchboard.v1, "plan") as mock_v1,
            patch.object(switchboard.v2, "plan") as mock_v2,
        ):
            mock_v1.return_value = {"agent": "inbox", "steps": ["a", "b"], "tools": []}
            mock_v2.return_value = {
                "agent": "inbox",
                "steps": ["a", "b"],
                "required_capabilities": [],
            }

            plan, meta = switchboard.plan("Test", {})

            assert meta["diff"]["agent_changed"] is False
            assert meta["diff"]["steps_changed"] is False

    def test_metadata_includes_all_fields(self):
        """Metadata should include all required fields."""
        switchboard = PlannerSwitchboard(canary_pct=15.0, kill_switch=False)

        with (
            patch.object(switchboard.v1, "plan") as mock_v1,
            patch.object(switchboard.v2, "plan") as mock_v2,
        ):
            mock_v1.return_value = {"agent": "test"}
            mock_v2.return_value = {"agent": "test"}

            plan, meta = switchboard.plan("Test", {})

            assert "selected" in meta
            assert "shadow" in meta
            assert "diff" in meta
            assert "latency_ms" in meta
            assert "canary_pct" in meta
            assert "kill_switch" in meta
            assert meta["canary_pct"] == 15.0
            assert meta["kill_switch"] is False

    def test_update_config(self):
        """Should be able to update config dynamically."""
        switchboard = PlannerSwitchboard(canary_pct=0.0, kill_switch=False)

        # Update canary percentage
        switchboard.update_config(canary_pct=25.0)
        assert switchboard.canary_pct == 25.0

        # Update kill switch
        switchboard.update_config(kill_switch=True)
        assert switchboard.kill_switch is True

        # Update both
        switchboard.update_config(canary_pct=50.0, kill_switch=False)
        assert switchboard.canary_pct == 50.0
        assert switchboard.kill_switch is False

    def test_get_config(self):
        """Should return current config."""
        switchboard = PlannerSwitchboard(canary_pct=33.3, kill_switch=True)
        config = switchboard.get_config()

        assert config["canary_pct"] == 33.3
        assert config["kill_switch"] is True
        assert "v1_type" in config
        assert "v2_type" in config

    def test_canary_pct_clamping(self):
        """Canary percentage should be clamped to [0, 100]."""
        # Test negative values
        switchboard = PlannerSwitchboard(canary_pct=-10.0)
        assert switchboard.canary_pct == 0.0

        # Test values > 100
        switchboard = PlannerSwitchboard(canary_pct=150.0)
        assert switchboard.canary_pct == 100.0

        # Test update with invalid values
        switchboard.update_config(canary_pct=-5.0)
        assert switchboard.canary_pct == 0.0

        switchboard.update_config(canary_pct=200.0)
        assert switchboard.canary_pct == 100.0

    def test_latency_tracking(self):
        """Metadata should include planning latency."""
        switchboard = PlannerSwitchboard(canary_pct=0.0)

        with (
            patch.object(switchboard.v1, "plan") as mock_v1,
            patch.object(switchboard.v2, "plan") as mock_v2,
        ):
            mock_v1.return_value = {"agent": "test"}
            mock_v2.return_value = {"agent": "test"}

            plan, meta = switchboard.plan("Test", {})

            assert "latency_ms" in meta
            assert isinstance(meta["latency_ms"], float)
            assert meta["latency_ms"] >= 0.0

    @patch("app.agents.planner_switch.planner_selection")
    @patch("app.agents.planner_switch.planner_diff")
    def test_metrics_recording(self, mock_diff, mock_selection):
        """Should record metrics for selection and diff."""
        switchboard = PlannerSwitchboard(canary_pct=0.0, kill_switch=False)

        with (
            patch.object(switchboard.v1, "plan") as mock_v1,
            patch.object(switchboard.v2, "plan") as mock_v2,
        ):
            mock_v1.return_value = {"agent": "inbox_triage", "steps": ["a"]}
            mock_v2.return_value = {"agent": "inbox_priority", "steps": ["a"]}

            plan, meta = switchboard.plan("Test", {})

            # Should record selection metric
            assert mock_selection.labels.called

            # Should record diff metric
            assert mock_diff.labels.called


class TestRuntimeSettingsDAO:
    """Test runtime settings data access."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    def test_get_initializes_defaults(self, mock_db):
        """Should create default settings if not exists."""
        from app.models_runtime import RuntimeSettingsDAO

        # Mock query to return None (no settings exist)
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        dao = RuntimeSettingsDAO(mock_db)

        # Should create new settings
        dao.get()

        assert mock_db.add.called
        assert mock_db.commit.called

    def test_update_settings(self, mock_db):
        """Should update settings correctly."""
        from app.models_runtime import RuntimeSettingsDAO, RuntimeSettings

        # Mock existing settings
        mock_settings = RuntimeSettings(
            id=1, planner_canary_pct=0.0, planner_kill_switch=False
        )
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            mock_settings
        )

        dao = RuntimeSettingsDAO(mock_db)
        dao.update(
            {"planner_canary_pct": 25.0, "planner_kill_switch": True},
            updated_by="admin",
            reason="testing canary",
        )

        assert mock_settings.planner_canary_pct == 25.0
        assert mock_settings.planner_kill_switch is True
        assert mock_settings.updated_by == "admin"
        assert mock_settings.update_reason == "testing canary"
        assert mock_db.commit.called

    def test_reset_canary(self, mock_db):
        """Should reset canary to safe defaults."""
        from app.models_runtime import RuntimeSettingsDAO, RuntimeSettings

        mock_settings = RuntimeSettings(
            id=1, planner_canary_pct=50.0, planner_kill_switch=False
        )
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            mock_settings
        )

        dao = RuntimeSettingsDAO(mock_db)
        dao.reset_canary(updated_by="auto_rollback", reason="quality_regression")

        assert mock_settings.planner_canary_pct == 0.0
        assert mock_settings.planner_kill_switch is True
        assert mock_settings.updated_by == "auto_rollback"
        assert mock_settings.update_reason == "quality_regression"

    def test_get_planner_config(self, mock_db):
        """Should return planner-specific config."""
        from app.models_runtime import RuntimeSettingsDAO, RuntimeSettings

        mock_settings = RuntimeSettings(
            id=1, planner_canary_pct=33.3, planner_kill_switch=True
        )
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            mock_settings
        )

        dao = RuntimeSettingsDAO(mock_db)
        config = dao.get_planner_config()

        assert config["canary_pct"] == 33.3
        assert config["kill_switch"] is True
