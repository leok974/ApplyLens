"""Tests for active learning feed loaders.

Tests:
- Loading labeled examples from approvals
- Loading from feedback API
- Loading from gold sets
- Deduplication
- Statistics aggregation
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from app.active.feeds import FeedLoader, load_all_feeds
from app.models import AgentApproval, AgentMetricsDaily
from app.models_al import LabeledExample
from app.eval.models import GoldenTask


class TestFeedLoader:
    """Test feed loading from various sources."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    def test_load_from_approvals(self, mock_db):
        """Should load labeled examples from approvals."""
        loader = FeedLoader(mock_db)
        
        # Mock approvals
        approval1 = Mock(spec=AgentApproval)
        approval1.request_id = "req-123"
        approval1.agent = "inbox_triage"
        approval1.action = "quarantine"
        approval1.status = "approved"
        approval1.context = {"risk_score": 85}
        approval1.rationale = "Suspicious sender"
        approval1.created_at = datetime.utcnow()
        
        approval2 = Mock(spec=AgentApproval)
        approval2.request_id = "req-456"
        approval2.agent = "inbox_triage"
        approval2.action = "archive"
        approval2.status = "rejected"
        approval2.context = {"risk_score": 20}
        approval2.rationale = "False positive"
        approval2.created_at = datetime.utcnow()
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            approval1, approval2
        ]
        
        # Mock no existing examples
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        count = loader.load_from_approvals()
        
        assert count == 2
        assert mock_db.add.call_count == 2
        assert mock_db.commit.called
    
    def test_load_from_approvals_deduplication(self, mock_db):
        """Should skip already-loaded approvals."""
        loader = FeedLoader(mock_db)
        
        approval = Mock(spec=AgentApproval)
        approval.request_id = "req-123"
        approval.agent = "inbox_triage"
        approval.action = "quarantine"
        approval.status = "approved"
        approval.context = {}
        approval.created_at = datetime.utcnow()
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [approval]
        
        # Mock existing example (already loaded)
        existing = Mock(spec=LabeledExample)
        mock_db.query.return_value.filter_by.return_value.first.return_value = existing
        
        count = loader.load_from_approvals()
        
        assert count == 0  # Skipped duplicate
        assert not mock_db.add.called
    
    def test_load_from_feedback(self, mock_db):
        """Should load labeled examples from feedback metrics."""
        loader = FeedLoader(mock_db)
        
        # Mock metrics with feedback
        metric1 = Mock(spec=AgentMetricsDaily)
        metric1.id = 1
        metric1.agent = "inbox_triage"
        metric1.date = datetime.utcnow()
        metric1.feedback_count = 10
        metric1.thumbs_up = 9
        metric1.thumbs_down = 1
        metric1.avg_quality_score = 92.0
        metric1.success_rate = 0.95
        
        metric2 = Mock(spec=AgentMetricsDaily)
        metric2.id = 2
        metric2.agent = "insights_writer"
        metric2.date = datetime.utcnow()
        metric2.feedback_count = 20
        metric2.thumbs_up = 8
        metric2.thumbs_down = 12
        metric2.avg_quality_score = 65.0
        metric2.success_rate = 0.75
        
        mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = [metric1, metric2]
        
        # Mock no existing examples
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        count = loader.load_from_feedback()
        
        assert count == 2
        assert mock_db.add.call_count == 2
    
    def test_load_from_goldsets(self, mock_db):
        """Should load labeled examples from gold sets."""
        loader = FeedLoader(mock_db)
        
        # Mock golden tasks
        task1 = Mock(spec=GoldenTask)
        task1.id = "task-1"
        task1.agent = "inbox_triage"
        task1.description = "Phishing email detection"
        task1.input_data = {"subject": "Urgent: Update payment info"}
        task1.expected_action = "quarantine"
        
        task2 = Mock(spec=GoldenTask)
        task2.id = "task-2"
        task2.agent = "knowledge_update"
        task2.description = "Synonym merge"
        task2.input_data = {"term": "ML", "synonym": "machine learning"}
        task2.expected_action = "merge"
        
        mock_db.query.return_value.limit.return_value.all.return_value = [task1, task2]
        
        # Mock no existing examples
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        count = loader.load_from_goldsets()
        
        assert count == 2
        assert mock_db.add.call_count == 2
    
    def test_get_stats(self, mock_db):
        """Should return statistics on labeled examples."""
        loader = FeedLoader(mock_db)
        
        # Mock total count
        mock_db.query.return_value.count.return_value = 100
        
        # Mock counts by source
        source_counts = {"approvals": 40, "feedback": 30, "gold": 25, "synthetic": 5}
        mock_db.query.return_value.filter_by.return_value.count.side_effect = source_counts.values()
        
        # Mock distinct agents
        mock_db.query.return_value.distinct.return_value.all.return_value = [
            ("inbox_triage",),
            ("insights_writer",)
        ]
        
        # Mock recent count
        mock_db.query.return_value.filter.return_value.count.return_value = 15
        
        stats = loader.get_stats()
        
        assert stats["total"] == 100
        assert "by_source" in stats
        assert "by_agent" in stats
        assert stats["recent_7d"] == 15


class TestLoadAllFeeds:
    """Test loading from all sources."""
    
    def test_load_all_feeds(self, monkeypatch):
        """Should load from all sources and return counts."""
        mock_db = Mock()
        
        # Mock FeedLoader methods
        mock_loader = Mock()
        mock_loader.load_from_approvals.return_value = 10
        mock_loader.load_from_feedback.return_value = 20
        mock_loader.load_from_goldsets.return_value = 15
        
        def mock_init(self, db):
            return mock_loader
        
        monkeypatch.setattr("app.active.feeds.FeedLoader.__init__", lambda self, db: None)
        monkeypatch.setattr("app.active.feeds.FeedLoader.load_from_approvals", lambda self: 10)
        monkeypatch.setattr("app.active.feeds.FeedLoader.load_from_feedback", lambda self: 20)
        monkeypatch.setattr("app.active.feeds.FeedLoader.load_from_goldsets", lambda self: 15)
        
        counts = load_all_feeds(mock_db)
        
        assert counts["approvals"] == 10
        assert counts["feedback"] == 20
        assert counts["gold"] == 15
