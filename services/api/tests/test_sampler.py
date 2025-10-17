"""Tests for uncertainty sampler.

Tests:
- Uncertainty calculation (disagreement, low confidence, variance)
- Review queue sampling
- Filtering already-labeled examples
- Daily sampling job
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.active.sampler import UncertaintySampler, daily_sample_review_queue
from app.models_al import LabeledExample
from app.eval.models import EvaluationResult


class TestUncertaintySampler:
    """Test uncertainty calculation and sampling."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    def test_calculate_uncertainty_disagreement(self):
        """Should detect disagreement between judges."""
        sampler = UncertaintySampler(Mock())
        
        judge_scores = {
            "gpt-4": {"verdict": "quarantine", "confidence": 80},
            "claude-3-opus": {"verdict": "safe", "confidence": 75}
        }
        
        judge_weights = {"gpt-4": 0.8, "claude-3-opus": 0.8}
        
        uncertainty, method = sampler.calculate_uncertainty(judge_scores, judge_weights)
        
        assert method == "disagreement"
        assert uncertainty > 0.5  # High disagreement
    
    def test_calculate_uncertainty_low_confidence(self):
        """Should detect low confidence predictions."""
        sampler = UncertaintySampler(Mock())
        
        judge_scores = {
            "gpt-4": {"verdict": "quarantine", "confidence": 45},
            "claude-3-opus": {"verdict": "quarantine", "confidence": 50}
        }
        
        judge_weights = {"gpt-4": 0.8, "claude-3-opus": 0.8}
        
        uncertainty, method = sampler.calculate_uncertainty(judge_scores, judge_weights)
        
        assert method == "low_confidence"
        assert uncertainty > 0.4  # Low confidence
    
    def test_calculate_uncertainty_weighted_variance(self):
        """Should calculate variance in confidences."""
        sampler = UncertaintySampler(Mock())
        
        judge_scores = {
            "gpt-4": {"verdict": "quarantine", "confidence": 95},
            "claude-3-opus": {"verdict": "quarantine", "confidence": 65}
        }
        
        judge_weights = {"gpt-4": 0.8, "claude-3-opus": 0.8}
        
        uncertainty, method = sampler.calculate_uncertainty(judge_scores, judge_weights)
        
        assert method == "weighted_variance"
        assert uncertainty > 0  # Some variance
    
    def test_calculate_uncertainty_no_judges(self):
        """Should handle no judges."""
        sampler = UncertaintySampler(Mock())
        
        uncertainty, method = sampler.calculate_uncertainty({}, {})
        
        assert method == "no_judges"
        assert uncertainty == 1.0
    
    def test_sample_for_review(self, mock_db):
        """Should sample uncertain predictions."""
        sampler = UncertaintySampler(mock_db)
        
        # Mock evaluation results
        result1 = Mock(spec=EvaluationResult)
        result1.id = 1
        result1.agent = "inbox_triage"
        result1.task_key = "thread-1"
        result1.created_at = datetime.utcnow()
        result1.task_input = {"subject": "Test"}
        result1.judge_scores = json.dumps({
            "gpt-4": {"verdict": "quarantine", "confidence": 80},
            "claude-3-opus": {"verdict": "safe", "confidence": 75}
        })
        
        result2 = Mock(spec=EvaluationResult)
        result2.id = 2
        result2.agent = "inbox_triage"
        result2.task_key = "thread-2"
        result2.created_at = datetime.utcnow()
        result2.task_input = {"subject": "Test 2"}
        result2.judge_scores = json.dumps({
            "gpt-4": {"verdict": "quarantine", "confidence": 95},
            "claude-3-opus": {"verdict": "quarantine", "confidence": 90}
        })
        
        # Mock query chains
        eval_query = Mock()
        eval_query.filter.return_value = eval_query
        eval_query.all.return_value = [result1, result2]
        
        labeled_query = Mock()
        labeled_query.filter.return_value = labeled_query
        labeled_query.all.return_value = []  # No labeled examples
        
        mock_db.query.side_effect = [eval_query, labeled_query]
        
        with patch('app.active.sampler.JudgeWeights') as mock_weights_class:
            mock_weights_mgr = Mock()
            mock_weights_mgr.get_weights.return_value = {"gpt-4": 0.8, "claude-3-opus": 0.8}
            mock_weights_class.return_value = mock_weights_mgr
            
            candidates = sampler.sample_for_review("inbox_triage", top_n=50)
        
        # Should return result1 (high disagreement), maybe not result2 (low disagreement)
        assert len(candidates) >= 1
        assert candidates[0]["task_key"] == "thread-1"
        assert candidates[0]["uncertainty"] > 0.5
        assert candidates[0]["method"] == "disagreement"
    
    def test_sample_for_review_filters_labeled(self, mock_db):
        """Should skip already-labeled examples."""
        sampler = UncertaintySampler(mock_db)
        
        # Mock evaluation result
        result = Mock(spec=EvaluationResult)
        result.agent = "inbox_triage"
        result.task_key = "thread-1"
        result.created_at = datetime.utcnow()
        result.judge_scores = json.dumps({
            "gpt-4": {"verdict": "quarantine", "confidence": 50}
        })
        
        # Mock labeled example (already labeled)
        labeled = Mock(spec=LabeledExample)
        labeled.key = "thread-1"
        
        eval_query = Mock()
        eval_query.filter.return_value = eval_query
        eval_query.all.return_value = [result]
        
        labeled_query = Mock()
        labeled_query.filter.return_value = labeled_query
        labeled_query.all.return_value = [labeled]
        
        mock_db.query.side_effect = [eval_query, labeled_query]
        
        with patch('app.active.sampler.JudgeWeights') as mock_weights_class:
            mock_weights_mgr = Mock()
            mock_weights_mgr.get_weights.return_value = {"gpt-4": 0.8}
            mock_weights_class.return_value = mock_weights_mgr
            
            candidates = sampler.sample_for_review("inbox_triage")
        
        # Should skip labeled example
        assert len(candidates) == 0
    
    def test_sample_all_agents(self, mock_db):
        """Should sample for all agents."""
        sampler = UncertaintySampler(mock_db)
        
        # Mock distinct agents
        agents_query = Mock()
        agents_query.distinct.return_value.all.return_value = [
            ("inbox_triage",),
            ("insights_writer",)
        ]
        
        mock_db.query.return_value = agents_query
        
        with patch.object(sampler, 'sample_for_review') as mock_sample:
            mock_sample.return_value = [{"task_key": "test-1", "uncertainty": 0.8}]
            
            results = sampler.sample_all_agents()
        
        assert len(results) == 2
        assert "inbox_triage" in results
        assert "insights_writer" in results
    
    def test_get_review_queue_stats(self, mock_db):
        """Should return review queue statistics."""
        sampler = UncertaintySampler(mock_db)
        
        # Mock counts
        mock_db.query.return_value.count.return_value = 100  # Total eval results
        
        # Mock agents
        agents_query = Mock()
        agents_query.distinct.return_value.all.return_value = [
            ("inbox_triage",),
            ("insights_writer",)
        ]
        
        # Mock per-agent counts
        count_query = Mock()
        count_query.filter.return_value.count.side_effect = [80, 60, 30, 20]  # eval counts, labeled counts
        
        mock_db.query.side_effect = [
            Mock(count=lambda: 100),  # total eval
            Mock(count=lambda: 50),   # total labeled
            agents_query,
            count_query,
            count_query,
            count_query,
            count_query
        ]
        
        stats = sampler.get_review_queue_stats()
        
        assert stats["total_unlabeled"] == 50
        assert stats["total_eval_results"] == 100
        assert stats["total_labeled"] == 50


class TestDailySampling:
    """Test daily sampling job."""
    
    def test_daily_sample_review_queue(self):
        """Should sample candidates for all agents."""
        mock_db = Mock()
        
        with patch('app.active.sampler.UncertaintySampler') as mock_sampler_class:
            mock_sampler = Mock()
            mock_sampler.sample_all_agents.return_value = {
                "inbox_triage": [{"task_key": "test-1"}],
                "insights_writer": [{"task_key": "test-2"}]
            }
            mock_sampler_class.return_value = mock_sampler
            
            results = daily_sample_review_queue(mock_db, top_n_per_agent=20)
        
        assert len(results) == 2
        assert "inbox_triage" in results
        assert mock_sampler.sample_all_agents.called
