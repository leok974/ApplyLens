"""
Tests for online eval and telemetry.

Tests cover:
- Feedback collection
- Online evaluation
- Red-team catalog
- Metrics aggregation
- Regression detection
"""
import pytest
from datetime import datetime, timedelta
from app.eval.telemetry import (
    FeedbackCollector,
    OnlineEvaluator,
    RedTeamCatalog,
    MetricsAggregator,
)
from app.eval.runner import MockAgentExecutor
from app.models import AgentMetricsDaily


class TestFeedbackCollector:
    """Test feedback collection."""
    
    def test_record_thumbs_up(self, db_session):
        """Test recording thumbs up feedback."""
        collector = FeedbackCollector(db_session)
        
        collector.record_feedback(
            agent="inbox.triage",
            run_id="run_001",
            feedback_type="thumbs_up",
            comment="Good catch!",
        )
        
        # Check metrics updated
        metrics = db_session.query(AgentMetricsDaily).filter(
            AgentMetricsDaily.agent == "inbox.triage"
        ).first()
        
        assert metrics is not None
        assert metrics.thumbs_up == 1
        assert metrics.thumbs_down == 0
    
    def test_record_thumbs_down(self, db_session):
        """Test recording thumbs down feedback."""
        collector = FeedbackCollector(db_session)
        
        collector.record_feedback(
            agent="inbox.triage",
            run_id="run_001",
            feedback_type="thumbs_down",
            comment="Missed phishing",
        )
        
        metrics = db_session.query(AgentMetricsDaily).first()
        
        assert metrics.thumbs_up == 0
        assert metrics.thumbs_down == 1
    
    def test_satisfaction_rate_calculation(self, db_session):
        """Test satisfaction rate calculation."""
        collector = FeedbackCollector(db_session)
        
        # Record mixed feedback
        for i in range(7):
            collector.record_feedback(
                agent="inbox.triage",
                run_id=f"run_{i}",
                feedback_type="thumbs_up",
            )
        
        for i in range(3):
            collector.record_feedback(
                agent="inbox.triage",
                run_id=f"run_down_{i}",
                feedback_type="thumbs_down",
            )
        
        metrics = db_session.query(AgentMetricsDaily).first()
        
        assert metrics.thumbs_up == 7
        assert metrics.thumbs_down == 3
        assert metrics.satisfaction_rate == 0.7


class TestOnlineEvaluator:
    """Test online evaluation."""
    
    def test_should_sample(self):
        """Test sampling decision."""
        evaluator = OnlineEvaluator(None, sample_rate=0.0)
        assert not evaluator.should_sample()
        
        evaluator = OnlineEvaluator(None, sample_rate=1.0)
        assert evaluator.should_sample()
    
    def test_evaluate_run(self, db_session):
        """Test evaluating a production run."""
        evaluator = OnlineEvaluator(db_session, sample_rate=1.0)
        
        result = evaluator.evaluate_run(
            agent="inbox.triage",
            run_id="run_001",
            objective="Analyze suspicious email",
            context={
                "subject": "Urgent: Verify account",
                "sender": "phishing@bad.com",
            },
            output={
                "risk_level": "high",
                "is_phishing": True,
                "category": "phishing",
            },
            latency_ms=250.0,
            cost_weight=1.0,
            invariant_ids=["no_false_negatives_phishing"],
        )
        
        assert result.success
        assert result.quality_score > 0
        assert len(result.passed_invariants) > 0
        
        # Check metrics updated
        metrics = db_session.query(AgentMetricsDaily).first()
        assert metrics is not None
        assert metrics.quality_samples == 1
        assert metrics.avg_quality_score > 0
    
    def test_invariant_tracking(self, db_session):
        """Test invariant pass/fail tracking."""
        evaluator = OnlineEvaluator(db_session, sample_rate=1.0)
        
        # Run that passes invariant
        evaluator.evaluate_run(
            agent="inbox.triage",
            run_id="run_good",
            objective="Detect phishing",
            context={"suspicious": True},
            output={"is_phishing": True, "risk_level": "high"},
            latency_ms=200.0,
            invariant_ids=["no_false_negatives_phishing"],
        )
        
        metrics = db_session.query(AgentMetricsDaily).first()
        assert metrics.invariants_passed > 0
        assert metrics.invariants_failed == 0


class TestRedTeamCatalog:
    """Test red-team catalog."""
    
    def test_inbox_redteam_tasks(self):
        """Test inbox red-team tasks exist."""
        tasks = RedTeamCatalog.get_inbox_redteam_tasks()
        
        assert len(tasks) > 0
        assert all(t.agent == "inbox.triage" for t in tasks)
        assert all("red_team" in t.tags for t in tasks)
        
        # Check for specific attack types
        categories = [t.category for t in tasks]
        assert "phishing_detection" in categories
        assert "spam" in categories or "edge_case" in categories
    
    def test_knowledge_redteam_tasks(self):
        """Test knowledge red-team tasks exist."""
        tasks = RedTeamCatalog.get_knowledge_redteam_tasks()
        
        assert len(tasks) > 0
        assert all(t.agent == "knowledge.update" for t in tasks)
    
    def test_insights_redteam_tasks(self):
        """Test insights red-team tasks exist."""
        tasks = RedTeamCatalog.get_insights_redteam_tasks()
        
        assert len(tasks) > 0
        assert all(t.agent == "insights.write" for t in tasks)
    
    def test_warehouse_redteam_tasks(self):
        """Test warehouse red-team tasks exist."""
        tasks = RedTeamCatalog.get_warehouse_redteam_tasks()
        
        assert len(tasks) > 0
        assert all(t.agent == "warehouse.health" for t in tasks)
    
    def test_all_redteam_tasks(self):
        """Test getting all red-team tasks."""
        all_tasks = RedTeamCatalog.get_all_redteam_tasks()
        
        assert len(all_tasks) > 0
        
        # Should have tasks from all agents
        agents = set(t.agent for t in all_tasks)
        assert "inbox.triage" in agents
        assert "knowledge.update" in agents
        assert "insights.write" in agents
        assert "warehouse.health" in agents


class TestMetricsAggregator:
    """Test metrics aggregation."""
    
    def test_get_agent_metrics_empty(self, db_session):
        """Test getting metrics when none exist."""
        aggregator = MetricsAggregator(db_session)
        
        today = datetime.utcnow()
        week_ago = today - timedelta(days=7)
        
        metrics = aggregator.get_agent_metrics("inbox.triage", week_ago, today)
        
        assert metrics == []
    
    def test_get_agent_metrics_with_data(self, db_session):
        """Test getting metrics with data."""
        # Create sample metrics
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(7):
            date = today - timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=95,
                success_rate=0.95,
                avg_quality_score=85.0,
                quality_samples=10,
            )
            db_session.add(metric)
        
        db_session.commit()
        
        aggregator = MetricsAggregator(db_session)
        week_ago = today - timedelta(days=7)
        
        metrics = aggregator.get_agent_metrics("inbox.triage", week_ago, today)
        
        assert len(metrics) == 7
    
    def test_weekly_summary(self, db_session):
        """Test weekly summary calculation."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())  # Monday
        
        # Create metrics for the week
        for i in range(7):
            date = week_start + timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=95,
                success_rate=0.95,
                avg_quality_score=85.0,
                quality_samples=10,
                thumbs_up=8,
                thumbs_down=2,
            )
            db_session.add(metric)
        
        db_session.commit()
        
        aggregator = MetricsAggregator(db_session)
        summary = aggregator.get_weekly_summary("inbox.triage", week_start)
        
        assert summary["agent"] == "inbox.triage"
        assert summary["total_runs"] == 700
        assert summary["success_rate"] == 0.95
        assert summary["avg_quality_score"] == 85.0
        assert summary["thumbs_up"] == 56
        assert summary["thumbs_down"] == 14
        assert summary["satisfaction_rate"] == 0.8
    
    def test_regression_detection_quality_drop(self, db_session):
        """Test detecting quality regression."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        current_week = today - timedelta(days=today.weekday())
        prev_week = current_week - timedelta(days=7)
        
        # Previous week: good quality
        for i in range(7):
            date = prev_week + timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=95,
                avg_quality_score=85.0,
                quality_samples=10,
            )
            db_session.add(metric)
        
        # Current week: degraded quality
        for i in range(7):
            date = current_week + timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=95,
                avg_quality_score=70.0,  # 15 point drop
                quality_samples=10,
            )
            db_session.add(metric)
        
        db_session.commit()
        
        aggregator = MetricsAggregator(db_session)
        regression = aggregator.detect_regression("inbox.triage", current_week)
        
        assert regression is not None
        assert regression["regression_type"] == "quality_drop"
        assert regression["drop_amount"] == 15.0
        assert regression["severity"] == "critical"
    
    def test_regression_detection_invariant_failure(self, db_session):
        """Test detecting new invariant failures."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        current_week = today - timedelta(days=today.weekday())
        prev_week = current_week - timedelta(days=7)
        
        # Previous week: no failures
        for i in range(7):
            date = prev_week + timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=95,
                avg_quality_score=85.0,
                quality_samples=10,
                failed_invariant_ids=[],
            )
            db_session.add(metric)
        
        # Current week: new failure
        for i in range(7):
            date = current_week + timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=95,
                avg_quality_score=85.0,
                quality_samples=10,
                failed_invariant_ids=["no_false_negatives_phishing"],
            )
            db_session.add(metric)
        
        db_session.commit()
        
        aggregator = MetricsAggregator(db_session)
        regression = aggregator.detect_regression("inbox.triage", current_week)
        
        assert regression is not None
        assert regression["regression_type"] == "invariant_failures"
        assert "no_false_negatives_phishing" in regression["new_failures"]
        assert regression["severity"] == "critical"
    
    def test_no_regression_when_stable(self, db_session):
        """Test no regression detected when quality is stable."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        current_week = today - timedelta(days=today.weekday())
        prev_week = current_week - timedelta(days=7)
        
        # Both weeks: stable quality
        for week_start in [prev_week, current_week]:
            for i in range(7):
                date = week_start + timedelta(days=i)
                metric = AgentMetricsDaily(
                    agent="inbox.triage",
                    date=date,
                    total_runs=100,
                    successful_runs=95,
                    avg_quality_score=85.0,
                    quality_samples=10,
                )
                db_session.add(metric)
        
        db_session.commit()
        
        aggregator = MetricsAggregator(db_session)
        regression = aggregator.detect_regression("inbox.triage", current_week)
        
        assert regression is None


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
