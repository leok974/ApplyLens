"""
Tests for data quality monitoring and lineage tracking.
"""

import pytest

from app.analytics.data_quality import (
    DataQualityConfig,
    DataQualityMonitor,
    QualityCheckType,
    QualityCheckStatus,
    QualityCheckResult,
    LineageTracker,
    LineageNode,
    LineageEdge,
)


class TestDataQualityConfig:
    """Test data quality configuration."""

    def test_config_creation(self):
        """Test creating quality config."""
        config = DataQualityConfig(
            table_name="my_table",
            null_checks=["id", "created_at"],
            unique_keys=["id"],
            freshness_column="updated_at",
            freshness_max_hours=24,
        )

        assert config.table_name == "my_table"
        assert "id" in config.null_checks
        assert config.unique_keys == ["id"]
        assert config.freshness_max_hours == 24


class TestQualityCheckResult:
    """Test quality check result model."""

    def test_result_creation(self):
        """Test creating a check result."""
        result = QualityCheckResult(
            table_name="test_table",
            column_name="test_column",
            check_type=QualityCheckType.NULL_CHECK,
            status=QualityCheckStatus.PASSED,
            failed_rows=0,
        )

        assert result.table_name == "test_table"
        assert result.check_type == QualityCheckType.NULL_CHECK
        assert result.is_passing is True

    def test_failing_result(self):
        """Test a failing check result."""
        result = QualityCheckResult(
            table_name="test_table",
            column_name="test_column",
            check_type=QualityCheckType.DUPLICATE_CHECK,
            status=QualityCheckStatus.FAILED,
            failed_rows=5,
        )

        assert result.is_passing is False
        assert result.failed_rows == 5


class TestDataQualityMonitor:
    """Test data quality monitor."""

    @pytest.fixture
    def monitor(self):
        """Create data quality monitor."""
        return DataQualityMonitor(dbt_project_dir="./test_dbt")

    @pytest.fixture
    def sample_config(self):
        """Create sample quality config."""
        return DataQualityConfig(
            table_name="inbox_events",
            null_checks=["id", "created_at", "user_email"],
            unique_keys=["id"],
            freshness_column="created_at",
            freshness_max_hours=24,
            value_ranges={"score": (0.0, 1.0)},
            expected_values={"status": ["pending", "completed", "failed"]},
        )

    def test_register_table(self, monitor, sample_config):
        """Test registering a table for monitoring."""
        monitor.register_table(sample_config)

        assert "inbox_events" in monitor.quality_configs
        config = monitor.quality_configs["inbox_events"]
        assert config.table_name == "inbox_events"
        assert len(config.null_checks) == 3

    def test_check_table_quality(self, monitor, sample_config):
        """Test running quality checks on a table."""
        monitor.register_table(sample_config)

        results = monitor.check_table_quality("inbox_events")

        # Should have multiple check results
        assert len(results) > 0

        # Check types should match config
        check_types = {r.check_type for r in results}
        assert QualityCheckType.NULL_CHECK in check_types
        assert QualityCheckType.DUPLICATE_CHECK in check_types
        assert QualityCheckType.FRESHNESS in check_types
        assert QualityCheckType.VALUE_RANGE in check_types

    def test_check_unregistered_table(self, monitor):
        """Test checking unregistered table raises error."""
        with pytest.raises(ValueError, match="not registered"):
            monitor.check_table_quality("unknown_table")

    def test_null_check(self, monitor):
        """Test null check logic."""
        result = monitor._check_nulls("test_table", "test_column")

        assert result.check_type == QualityCheckType.NULL_CHECK
        assert result.table_name == "test_table"
        assert result.column_name == "test_column"
        # Mock returns 0 failed rows
        assert result.status == QualityCheckStatus.PASSED

    def test_duplicate_check(self, monitor):
        """Test duplicate check logic."""
        result = monitor._check_duplicates("test_table", ["id", "email"])

        assert result.check_type == QualityCheckType.DUPLICATE_CHECK
        assert result.table_name == "test_table"
        assert "id" in result.column_name
        assert "email" in result.column_name

    def test_freshness_check(self, monitor):
        """Test freshness check logic."""
        result = monitor._check_freshness("test_table", "updated_at", 24)

        assert result.check_type == QualityCheckType.FRESHNESS
        assert result.table_name == "test_table"
        assert "age_hours" in result.details
        assert "max_hours" in result.details

    def test_value_range_check(self, monitor):
        """Test value range check logic."""
        result = monitor._check_value_range("test_table", "score", 0.0, 1.0)

        assert result.check_type == QualityCheckType.VALUE_RANGE
        assert result.details["min_value"] == 0.0
        assert result.details["max_value"] == 1.0

    def test_value_distribution_check(self, monitor):
        """Test value distribution check logic."""
        expected = ["active", "pending", "completed"]
        result = monitor._check_value_distribution("test_table", "status", expected)

        assert result.check_type == QualityCheckType.VALUE_DISTRIBUTION
        assert result.details["expected_values"] == expected

    def test_get_quality_summary(self, monitor, sample_config):
        """Test getting quality summary."""
        monitor.register_table(sample_config)

        # Add some mock results
        monitor.check_results = [
            QualityCheckResult(
                table_name="test1",
                check_type=QualityCheckType.NULL_CHECK,
                status=QualityCheckStatus.PASSED,
                failed_rows=0,
            ),
            QualityCheckResult(
                table_name="test2",
                check_type=QualityCheckType.DUPLICATE_CHECK,
                status=QualityCheckStatus.FAILED,
                failed_rows=5,
            ),
            QualityCheckResult(
                table_name="test2",
                check_type=QualityCheckType.FRESHNESS,
                status=QualityCheckStatus.WARNING,
                failed_rows=0,
            ),
        ]

        summary = monitor.get_quality_summary(days=7)

        assert summary["total_checks"] == 3
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert summary["warnings"] == 1
        assert "test2" in summary["failing_tables"]
        assert summary["pass_rate"] < 100.0

    def test_generate_quality_report(self, monitor, sample_config):
        """Test generating quality report."""
        monitor.register_table(sample_config)

        # Add mock results
        monitor.check_results = [
            QualityCheckResult(
                table_name="test_table",
                column_name="test_column",
                check_type=QualityCheckType.NULL_CHECK,
                status=QualityCheckStatus.FAILED,
                failed_rows=10,
            ),
        ]

        report = monitor.generate_quality_report()

        assert "Data Quality Report" in report
        assert "test_table" in report
        assert "NULL_CHECK" in report or "null_check" in report
        assert "10" in report  # Failed rows


class TestLineageNode:
    """Test lineage node model."""

    def test_node_creation(self):
        """Test creating a lineage node."""
        node = LineageNode(
            node_id="analytics.inbox_events",
            node_name="inbox_events",
            node_type="dbt_model",
            depth_level=1,
            downstream_count=3,
            impact_level="high",
        )

        assert node.node_id == "analytics.inbox_events"
        assert node.node_type == "dbt_model"
        assert node.impact_level == "high"


class TestLineageEdge:
    """Test lineage edge model."""

    def test_edge_creation(self):
        """Test creating a lineage edge."""
        edge = LineageEdge(
            from_node="source.table",
            to_node="dbt.model",
            flow_type="transformation",
        )

        assert edge.from_node == "source.table"
        assert edge.to_node == "dbt.model"
        assert edge.flow_type == "transformation"


class TestLineageTracker:
    """Test lineage tracker."""

    @pytest.fixture
    def tracker(self):
        """Create lineage tracker."""
        return LineageTracker()

    def test_load_lineage(self, tracker):
        """Test loading lineage from dbt."""
        lineage = tracker.load_lineage_from_dbt()

        assert "nodes" in lineage
        assert "edges" in lineage
        assert len(lineage["nodes"]) > 0
        assert len(lineage["edges"]) > 0

    def test_get_downstream_impact(self, tracker):
        """Test getting downstream impact."""
        tracker.load_lineage_from_dbt()

        # Get downstream from source table
        downstream = tracker.get_downstream_impact("public.raw_inbox_events")

        assert len(downstream) > 0
        assert "analytics.inbox_triage_events" in downstream
        # Should include transitive dependencies
        assert "agent.inbox.triage" in downstream

    def test_get_upstream_dependencies(self, tracker):
        """Test getting upstream dependencies."""
        tracker.load_lineage_from_dbt()

        # Get upstream for agent
        upstream = tracker.get_upstream_dependencies("agent.inbox.triage")

        assert len(upstream) > 0
        assert "analytics.inbox_triage_events" in upstream
        # Should include transitive dependencies
        assert "public.raw_inbox_events" in upstream

    def test_impact_analysis(self, tracker):
        """Test impact analysis for schema changes."""
        tracker.load_lineage_from_dbt()

        # If we change raw_inbox_events schema
        impact = tracker.get_downstream_impact("public.raw_inbox_events")

        # Should affect dbt model and agent
        assert len(impact) >= 2

        # High impact tables should have many downstream dependencies
        node = tracker.nodes.get("analytics.inbox_triage_events")
        if node:
            assert node.downstream_count > 0


class TestDbtIntegration:
    """Test dbt integration."""

    def test_run_dbt_tests_mock(self):
        """Test running dbt tests (mocked)."""
        monitor = DataQualityMonitor(dbt_project_dir="./test_dbt")

        # This would call dbt in production, but we're just testing structure
        # In real tests, we'd mock subprocess.run
        assert monitor.dbt_project_dir == "./test_dbt"

    def test_quality_check_types_complete(self):
        """Test all quality check types are defined."""
        check_types = [
            QualityCheckType.NULL_CHECK,
            QualityCheckType.DUPLICATE_CHECK,
            QualityCheckType.SCHEMA_DRIFT,
            QualityCheckType.REFERENTIAL_INTEGRITY,
            QualityCheckType.VALUE_RANGE,
            QualityCheckType.FRESHNESS,
            QualityCheckType.NULL_RATE,
            QualityCheckType.VALUE_DISTRIBUTION,
            QualityCheckType.MONOTONIC_IDS,
        ]

        assert len(check_types) == 9
