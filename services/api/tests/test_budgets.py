"""
Tests for budget gates and quality thresholds.

Tests cover:
- Budget configuration
- Gate evaluation
- Violation detection
- Regression detection
- CLI integration
"""

import pytest
from datetime import datetime, timedelta
from app.eval.budgets import (
    GateEvaluator,
    BudgetViolation,
    DEFAULT_BUDGETS,
    format_gate_report,
)
from app.models import AgentMetricsDaily


class TestBudget:
    """Test budget configuration."""

    def test_default_budgets_exist(self):
        """Test that default budgets are defined for all agents."""
        assert "inbox.triage" in DEFAULT_BUDGETS
        assert "knowledge.update" in DEFAULT_BUDGETS
        assert "insights.write" in DEFAULT_BUDGETS
        assert "warehouse.health" in DEFAULT_BUDGETS

    def test_inbox_budget_strict(self):
        """Test that inbox budget is strict (fast, accurate)."""
        budget = DEFAULT_BUDGETS["inbox.triage"]

        assert budget.min_quality_score >= 80.0
        assert budget.min_success_rate >= 0.90
        assert budget.max_avg_latency_ms <= 1000.0
        assert budget.max_invariant_failures == 0

    def test_budget_enabled_by_default(self):
        """Test that budgets are enabled by default."""
        for budget in DEFAULT_BUDGETS.values():
            assert budget.enabled is True


class TestGateEvaluator:
    """Test gate evaluation."""

    def test_evaluate_agent_no_data(self, db_session):
        """Test evaluating agent with no metrics."""
        evaluator = GateEvaluator(db_session)

        result = evaluator.evaluate_agent("inbox.triage")

        # Should pass if no data (nothing to violate)
        assert result["passed"] is True
        assert len(result["violations"]) == 0

    def test_evaluate_agent_passing(self, db_session):
        """Test evaluating agent that passes all gates."""
        # Create good metrics
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(7):
            date = today - timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=98,
                failed_runs=2,
                success_rate=0.98,
                avg_quality_score=90.0,
                quality_samples=10,
                avg_latency_ms=300.0,
                p95_latency_ms=600.0,
                p99_latency_ms=1000.0,
                avg_cost_per_run=1.5,
                invariants_passed=10,
                invariants_failed=0,
            )
            db_session.add(metric)

        db_session.commit()

        evaluator = GateEvaluator(db_session)
        result = evaluator.evaluate_agent("inbox.triage", lookback_days=7)

        assert result["passed"] is True
        assert len(result["violations"]) == 0
        assert result["current_metrics"]["avg_quality_score"] == 90.0
        assert result["current_metrics"]["success_rate"] == 0.98

    def test_evaluate_agent_quality_violation(self, db_session):
        """Test detecting quality score violation."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Create metrics with low quality
        for i in range(7):
            date = today - timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=95,
                success_rate=0.95,
                avg_quality_score=70.0,  # Below 85.0 budget
                quality_samples=10,
                avg_latency_ms=300.0,
                invariants_passed=10,
                invariants_failed=0,
            )
            db_session.add(metric)

        db_session.commit()

        evaluator = GateEvaluator(db_session)
        result = evaluator.evaluate_agent("inbox.triage", lookback_days=7)

        assert result["passed"] is False
        assert len(result["violations"]) > 0

        # Find quality violation
        quality_violations = [
            v for v in result["violations"] if v.budget_type == "quality"
        ]
        assert len(quality_violations) == 1
        assert quality_violations[0].severity == "critical"
        assert quality_violations[0].threshold == 85.0
        assert quality_violations[0].actual == 70.0

    def test_evaluate_agent_success_rate_violation(self, db_session):
        """Test detecting success rate violation."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(7):
            date = today - timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=85,  # 85% success rate, below 95% budget
                failed_runs=15,
                success_rate=0.85,
                avg_quality_score=90.0,
                quality_samples=10,
                invariants_passed=10,
                invariants_failed=0,
            )
            db_session.add(metric)

        db_session.commit()

        evaluator = GateEvaluator(db_session)
        result = evaluator.evaluate_agent("inbox.triage", lookback_days=7)

        assert result["passed"] is False

        success_violations = [
            v for v in result["violations"] if v.budget_type == "success_rate"
        ]
        assert len(success_violations) == 1
        assert success_violations[0].actual == 0.85

    def test_evaluate_agent_latency_violation(self, db_session):
        """Test detecting latency violation."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(7):
            date = today - timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=98,
                success_rate=0.98,
                avg_quality_score=90.0,
                quality_samples=10,
                avg_latency_ms=800.0,  # Above 500ms budget
                p95_latency_ms=1500.0,  # Above 1000ms budget
                invariants_passed=10,
                invariants_failed=0,
            )
            db_session.add(metric)

        db_session.commit()

        evaluator = GateEvaluator(db_session)
        result = evaluator.evaluate_agent("inbox.triage", lookback_days=7)

        assert result["passed"] is False

        latency_violations = [
            v
            for v in result["violations"]
            if v.budget_type in ("latency_avg", "latency_p95")
        ]
        assert len(latency_violations) >= 1

    def test_evaluate_agent_invariant_violation(self, db_session):
        """Test detecting invariant violations."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(7):
            date = today - timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=98,
                success_rate=0.98,
                avg_quality_score=90.0,
                quality_samples=10,
                avg_latency_ms=300.0,
                invariants_passed=9,
                invariants_failed=2,  # Violates zero-tolerance
            )
            db_session.add(metric)

        db_session.commit()

        evaluator = GateEvaluator(db_session)
        result = evaluator.evaluate_agent("inbox.triage", lookback_days=7)

        assert result["passed"] is False

        invariant_violations = [
            v for v in result["violations"] if v.budget_type == "invariants"
        ]
        assert len(invariant_violations) == 1
        assert invariant_violations[0].severity == "critical"

    def test_evaluate_agent_regression_quality_drop(self, db_session):
        """Test detecting quality regression."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        current_week = today - timedelta(days=today.weekday())
        prev_week = current_week - timedelta(days=7)
        baseline_start = prev_week - timedelta(days=14)

        # Baseline: high quality
        for i in range(14):
            date = baseline_start + timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=98,
                success_rate=0.98,
                avg_quality_score=92.0,  # Baseline
                quality_samples=10,
                avg_latency_ms=300.0,
            )
            db_session.add(metric)

        # Current: dropped quality
        for i in range(7):
            date = current_week + timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=98,
                success_rate=0.98,
                avg_quality_score=75.0,  # 17 point drop (>10 threshold)
                quality_samples=10,
                avg_latency_ms=300.0,
            )
            db_session.add(metric)

        db_session.commit()

        evaluator = GateEvaluator(db_session)
        result = evaluator.evaluate_agent(
            "inbox.triage",
            lookback_days=7,
            baseline_days=14,
        )

        assert result["passed"] is False

        regression_violations = [
            v for v in result["violations"] if v.budget_type == "quality_regression"
        ]
        assert len(regression_violations) == 1
        assert regression_violations[0].severity == "critical"

    def test_evaluate_agent_regression_latency_increase(self, db_session):
        """Test detecting latency regression."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        current_week = today - timedelta(days=today.weekday())
        prev_week = current_week - timedelta(days=7)
        baseline_start = prev_week - timedelta(days=14)

        # Baseline: fast
        for i in range(14):
            date = baseline_start + timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=98,
                success_rate=0.98,
                avg_quality_score=90.0,
                quality_samples=10,
                avg_latency_ms=200.0,  # Baseline
            )
            db_session.add(metric)

        # Current: slow (>30% increase)
        for i in range(7):
            date = current_week + timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=98,
                success_rate=0.98,
                avg_quality_score=90.0,
                quality_samples=10,
                avg_latency_ms=400.0,  # 100% increase
            )
            db_session.add(metric)

        db_session.commit()

        evaluator = GateEvaluator(db_session)
        result = evaluator.evaluate_agent(
            "inbox.triage",
            lookback_days=7,
            baseline_days=14,
        )

        assert result["passed"] is False

        regression_violations = [
            v for v in result["violations"] if v.budget_type == "latency_regression"
        ]
        assert len(regression_violations) == 1

    def test_evaluate_all_agents(self, db_session):
        """Test evaluating all agents at once."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Good metrics for inbox
        for i in range(7):
            date = today - timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=98,
                success_rate=0.98,
                avg_quality_score=90.0,
                quality_samples=10,
            )
            db_session.add(metric)

        # Bad metrics for knowledge
        for i in range(7):
            date = today - timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="knowledge.update",
                date=date,
                total_runs=100,
                successful_runs=85,
                success_rate=0.85,
                avg_quality_score=70.0,  # Below 80.0 budget
                quality_samples=10,
            )
            db_session.add(metric)

        db_session.commit()

        evaluator = GateEvaluator(db_session)
        result = evaluator.evaluate_all_agents(lookback_days=7)

        assert result["passed"] is False
        assert result["total_violations"] > 0
        assert "inbox.triage" in result["results"]
        assert "knowledge.update" in result["results"]

        # Inbox should pass
        assert result["results"]["inbox.triage"]["passed"] is True

        # Knowledge should fail
        assert result["results"]["knowledge.update"]["passed"] is False


class TestReportFormatting:
    """Test report formatting."""

    def test_format_passing_report(self):
        """Test formatting report for passing evaluation."""
        evaluation = {
            "passed": True,
            "violations": [],
            "agent": "inbox.triage",
            "current_metrics": {
                "avg_quality_score": 90.0,
                "success_rate": 0.98,
                "avg_latency_ms": 300.0,
            },
        }

        report = format_gate_report(evaluation)

        assert "inbox.triage" in report
        assert "PASSED" in report
        assert "90.0" in report

    def test_format_failing_report(self):
        """Test formatting report for failing evaluation."""
        evaluation = {
            "passed": False,
            "violations": [
                BudgetViolation(
                    agent="inbox.triage",
                    budget_type="quality",
                    threshold=85.0,
                    actual=70.0,
                    severity="critical",
                    message="Quality too low",
                    date=datetime.utcnow(),
                ),
            ],
            "agent": "inbox.triage",
            "current_metrics": {
                "avg_quality_score": 70.0,
            },
        }

        report = format_gate_report(evaluation)

        assert "FAILED" in report
        assert "Quality too low" in report

    def test_format_multi_agent_report(self):
        """Test formatting report for multiple agents."""
        evaluation = {
            "passed": False,
            "total_violations": 2,
            "critical_violations": 1,
            "results": {
                "inbox.triage": {
                    "passed": True,
                    "violations": [],
                },
                "knowledge.update": {
                    "passed": False,
                    "violations": [
                        BudgetViolation(
                            agent="knowledge.update",
                            budget_type="quality",
                            threshold=80.0,
                            actual=70.0,
                            severity="critical",
                            message="Quality too low",
                            date=datetime.utcnow(),
                        ),
                    ],
                },
            },
        }

        report = format_gate_report(evaluation)

        assert "inbox.triage" in report
        assert "knowledge.update" in report
        assert "2 total" in report


# Fixtures


@pytest.fixture
def db_session():
    """Mock database session for testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db import Base

    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
