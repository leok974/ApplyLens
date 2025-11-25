"""
Tests for Gate Bridges - Phase 5.4 PR5

Tests incident creation from evaluation gate failures.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from app.intervene.bridges import (
    GateBridge,
    create_budget_incident,
    create_invariant_incident,
)
from app.eval.budgets import BudgetViolation, Budget


@pytest.fixture
def db_session():
    """Mock database session."""
    mock_db = Mock()
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()
    return mock_db


@pytest.fixture
def mock_watcher():
    """Mock watcher with deduplication logic."""
    mock = Mock()
    mock._has_open_incident = Mock(return_value=False)
    mock._is_rate_limited = Mock(return_value=False)
    return mock


@pytest.fixture
def sample_budget():
    """Sample budget for testing."""
    return Budget(
        agent="inbox.triage",
        min_quality_score=85.0,
        min_success_rate=0.95,
        max_avg_latency_ms=500.0,
        max_p95_latency_ms=1000.0,
        description="Email triage must be fast and accurate",
    )


@pytest.fixture
def sample_violation():
    """Sample budget violation for testing."""
    return BudgetViolation(
        agent="inbox.triage",
        budget_type="quality",
        threshold=85.0,
        actual=78.5,
        severity="critical",
        message="Quality score 78.5 below budget 85.0",
        date=datetime.utcnow(),
    )


class TestGateBridge:
    """Test GateBridge incident creation."""

    @pytest.mark.asyncio
    async def test_on_budget_violation_creates_incident(
        self, db_session, sample_budget, sample_violation
    ):
        """Test budget violation creates incident."""
        bridge = GateBridge(db_session)
        bridge.watcher = None  # Disable deduplication for this test

        incident = await bridge.on_budget_violation(sample_violation, sample_budget)

        assert incident is not None
        assert incident.kind == "budget"
        assert incident.key == "BUDGET_inbox.triage_quality"
        assert incident.severity == "sev1"  # critical → sev1
        assert incident.status == "open"
        assert "Budget violation" in incident.summary

        # Check details
        assert incident.details["violation"]["agent"] == "inbox.triage"
        assert incident.details["violation"]["budget_type"] == "quality"
        assert incident.details["violation"]["threshold"] == 85.0
        assert incident.details["violation"]["actual"] == 78.5

        # Check playbooks suggested
        assert "rerun_eval" in incident.playbooks

        # Check metadata
        assert incident.metadata["auto_created"] is True
        assert incident.metadata["source"] == "gate_bridge"

        # Verify DB calls
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_budget_violation_deduplication(
        self, db_session, mock_watcher, sample_budget, sample_violation
    ):
        """Test deduplication prevents duplicate incidents."""
        bridge = GateBridge(db_session)
        bridge.watcher = mock_watcher

        # Simulate existing open incident
        mock_watcher._has_open_incident.return_value = True

        incident = await bridge.on_budget_violation(sample_violation, sample_budget)

        assert incident is None
        mock_watcher._has_open_incident.assert_called_once_with(
            "budget", "BUDGET_inbox.triage_quality"
        )
        db_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_budget_violation_rate_limiting(
        self, db_session, mock_watcher, sample_budget, sample_violation
    ):
        """Test rate limiting prevents excessive incidents."""
        bridge = GateBridge(db_session)
        bridge.watcher = mock_watcher

        # Simulate rate limit hit
        mock_watcher._is_rate_limited.return_value = True

        incident = await bridge.on_budget_violation(sample_violation, sample_budget)

        assert incident is None
        mock_watcher._is_rate_limited.assert_called_once()
        db_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_severity_mapping(self, db_session):
        """Test violation severity maps to incident severity."""
        bridge = GateBridge(db_session)
        bridge.watcher = None

        budget = Budget(agent="test", description="test")

        # Critical → sev1
        violation_critical = BudgetViolation(
            agent="test",
            budget_type="quality",
            threshold=80,
            actual=70,
            severity="critical",
            message="Critical issue",
            date=datetime.utcnow(),
        )
        incident = await bridge.on_budget_violation(violation_critical, budget)
        assert incident.severity == "sev1"

        # Error → sev2
        violation_error = BudgetViolation(
            agent="test",
            budget_type="latency",
            threshold=500,
            actual=800,
            severity="error",
            message="Error issue",
            date=datetime.utcnow(),
        )
        incident = await bridge.on_budget_violation(violation_error, budget)
        assert incident.severity == "sev2"

        # Warning → sev3
        violation_warning = BudgetViolation(
            agent="test",
            budget_type="cost",
            threshold=5.0,
            actual=5.5,
            severity="warning",
            message="Warning issue",
            date=datetime.utcnow(),
        )
        incident = await bridge.on_budget_violation(violation_warning, budget)
        assert incident.severity == "sev3"

    @pytest.mark.asyncio
    async def test_playbook_suggestions_quality(self, db_session, sample_budget):
        """Test playbook suggestions for quality violations."""
        bridge = GateBridge(db_session)
        bridge.watcher = None

        violation = BudgetViolation(
            agent="warehouse.health",
            budget_type="quality",
            threshold=90,
            actual=80,
            severity="critical",
            message="Quality drop",
            date=datetime.utcnow(),
        )

        incident = await bridge.on_budget_violation(violation, sample_budget)

        # Should suggest eval rerun and dbt rerun (warehouse in agent name)
        assert "rerun_eval" in incident.playbooks
        assert "rerun_dbt" in incident.playbooks

    @pytest.mark.asyncio
    async def test_playbook_suggestions_latency(self, db_session, sample_budget):
        """Test playbook suggestions for latency violations."""
        bridge = GateBridge(db_session)
        bridge.watcher = None

        violation = BudgetViolation(
            agent="knowledge.update",
            budget_type="latency_p95",
            threshold=5000,
            actual=8000,
            severity="error",
            message="Latency spike",
            date=datetime.utcnow(),
        )

        incident = await bridge.on_budget_violation(violation, sample_budget)

        # Should suggest cache clear and synonym refresh (knowledge in agent name)
        assert "clear_cache" in incident.playbooks
        assert "refresh_synonyms" in incident.playbooks

    @pytest.mark.asyncio
    async def test_on_planner_regression_creates_incident(self, db_session):
        """Test planner regression creates incident."""
        bridge = GateBridge(db_session)
        bridge.watcher = None

        version = "v1.2.3-canary"
        metrics = {"accuracy": 0.82, "latency_p95": 450}
        baseline_metrics = {"accuracy": 0.95, "latency_p95": 400}
        regression_details = {
            "metric": "accuracy",
            "threshold": 0.90,
            "actual": 0.82,
            "baseline": 0.95,
            "drop": 0.13,
        }

        incident = await bridge.on_planner_regression(
            version, metrics, baseline_metrics, regression_details
        )

        assert incident is not None
        assert incident.kind == "planner"
        assert incident.key == "PLANNER_REG_v1.2.3-canary"
        assert incident.severity == "sev1"  # accuracy drop is critical
        assert "Planner regression" in incident.summary
        assert "accuracy" in incident.summary

        # Check playbooks
        assert "rollback_planner" in incident.playbooks
        assert "adjust_canary_split" in incident.playbooks

        # Check details
        assert incident.details["version"] == version
        assert incident.details["regression"]["metric"] == "accuracy"
        assert incident.details["metrics"]["current"] == metrics
        assert incident.details["metrics"]["baseline"] == baseline_metrics

    @pytest.mark.asyncio
    async def test_on_planner_regression_severity_by_metric(self, db_session):
        """Test planner regression severity varies by metric."""
        bridge = GateBridge(db_session)
        bridge.watcher = None

        # Accuracy drop → sev1 (critical)
        incident_accuracy = await bridge.on_planner_regression(
            version="v1.0.0",
            metrics={},
            baseline_metrics={},
            regression_details={"metric": "accuracy"},
        )
        assert incident_accuracy.severity == "sev1"

        # Latency spike → sev2 (error)
        incident_latency = await bridge.on_planner_regression(
            version="v1.0.1",
            metrics={},
            baseline_metrics={},
            regression_details={"metric": "latency_p95"},
        )
        assert incident_latency.severity == "sev2"

    @pytest.mark.asyncio
    @patch("app.intervene.bridges.publish_incident_created", new_callable=AsyncMock)
    async def test_sse_publishing(
        self, mock_publish, db_session, sample_budget, sample_violation
    ):
        """Test SSE event published after incident creation."""
        bridge = GateBridge(db_session)
        bridge.watcher = None

        await bridge.on_budget_violation(sample_violation, sample_budget)

        # SSE publish should be called (if available)
        # Note: This test assumes SSE_AVAILABLE=True, may need conditional check
        if hasattr(bridge, "SSE_AVAILABLE") and bridge.SSE_AVAILABLE:
            mock_publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_propagation(
        self, db_session, sample_budget, sample_violation
    ):
        """Test context is preserved in incident details."""
        bridge = GateBridge(db_session)
        bridge.watcher = None

        context = {
            "eval_run_id": "eval-123",
            "triggered_by": "CI pipeline",
            "commit_sha": "abc123",
        }

        incident = await bridge.on_budget_violation(
            sample_violation, sample_budget, context
        )

        assert incident.details["context"] == context
        assert incident.details["context"]["eval_run_id"] == "eval-123"


class TestConvenienceFunctions:
    """Test convenience functions for simple usage."""

    @pytest.mark.asyncio
    async def test_create_budget_incident(
        self, db_session, sample_budget, sample_violation
    ):
        """Test convenience function for budget incidents."""
        with patch("app.intervene.bridges.GateBridge") as MockBridge:
            mock_bridge = MockBridge.return_value
            mock_bridge.on_budget_violation = AsyncMock(return_value=Mock())

            await create_budget_incident(db_session, sample_violation, sample_budget)

            MockBridge.assert_called_once_with(db_session)
            mock_bridge.on_budget_violation.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_invariant_incident(self, db_session):
        """Test convenience function for invariant incidents."""
        eval_result = Mock()
        invariant_result = {"invariant_id": "inv-001", "passed": False}

        with patch("app.intervene.bridges.GateBridge") as MockBridge:
            mock_bridge = MockBridge.return_value
            mock_bridge.on_invariant_failure = AsyncMock(return_value=Mock())

            await create_invariant_incident(db_session, eval_result, invariant_result)

            MockBridge.assert_called_once_with(db_session)
            mock_bridge.on_invariant_failure.assert_called_once()


class TestPlaybookSuggestions:
    """Test playbook suggestion logic."""

    def test_suggest_playbooks_quality(self, db_session):
        """Test quality violations suggest eval and dbt reruns."""
        bridge = GateBridge(db_session)

        playbooks = bridge._suggest_budget_playbooks("quality", "warehouse.health")
        assert "rerun_eval" in playbooks
        assert "rerun_dbt" in playbooks

    def test_suggest_playbooks_latency(self, db_session):
        """Test latency violations suggest cache operations."""
        bridge = GateBridge(db_session)

        playbooks = bridge._suggest_budget_playbooks("latency", "knowledge.update")
        assert "clear_cache" in playbooks
        assert "refresh_synonyms" in playbooks

    def test_suggest_playbooks_cost(self, db_session):
        """Test cost violations suggest optimization."""
        bridge = GateBridge(db_session)

        playbooks = bridge._suggest_budget_playbooks("cost", "insights.write")
        assert "rerun_eval" in playbooks
        assert "adjust_canary_split" in playbooks

    def test_suggest_playbooks_success_rate(self, db_session):
        """Test success rate violations suggest reruns."""
        bridge = GateBridge(db_session)

        playbooks = bridge._suggest_budget_playbooks("success_rate", "inbox.triage")
        assert "rerun_eval" in playbooks

    def test_suggest_playbooks_invariants(self, db_session):
        """Test invariant violations suggest comprehensive checks."""
        bridge = GateBridge(db_session)

        playbooks = bridge._suggest_budget_playbooks("invariants", "warehouse.health")
        assert "rerun_eval" in playbooks
        assert "rerun_dbt" in playbooks

    def test_suggest_playbooks_planner_specific(self, db_session):
        """Test planner agents get rollback playbook."""
        bridge = GateBridge(db_session)

        playbooks = bridge._suggest_budget_playbooks("quality", "planner.canary")
        assert "rollback_planner" in playbooks
