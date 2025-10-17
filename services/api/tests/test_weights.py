"""Tests for judge reliability weighting.

Tests:
- Weight calculation based on agreement + calibration
- Exponential time decay
- Saving/loading weights from runtime_settings
- Nightly update job
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.active.weights import JudgeWeights, nightly_update_weights
from app.models import RuntimeSetting
from app.models_al import LabeledExample
from app.eval.models import EvaluationResult


class TestJudgeWeights:
    """Test judge reliability weight calculations."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def sample_eval_results(self):
        """Generate sample evaluation results."""
        now = datetime.utcnow()
        results = []
        
        # 10 results for gpt-4 (80% agreement, high confidence)
        for i in range(10):
            result = Mock(spec=EvaluationResult)
            result.agent = "inbox_triage"
            result.task_key = f"thread-{i}"
            result.created_at = now - timedelta(days=i)
            result.judge_scores = json.dumps({
                "gpt-4": {
                    "verdict": "quarantine" if i < 8 else "safe",
                    "confidence": 90
                }
            })
            results.append(result)
        
        # 10 results for gpt-3.5-turbo (60% agreement, overconfident)
        for i in range(10):
            result = Mock(spec=EvaluationResult)
            result.agent = "inbox_triage"
            result.task_key = f"thread-{i}"
            result.created_at = now - timedelta(days=i)
            result.judge_scores = json.dumps({
                "gpt-3.5-turbo": {
                    "verdict": "quarantine" if i < 6 else "safe",
                    "confidence": 95  # Overconfident
                }
            })
            results.append(result)
        
        return results
    
    @pytest.fixture
    def sample_labeled_examples(self):
        """Generate sample labeled examples."""
        examples = []
        
        # 10 labeled examples (ground truth)
        for i in range(10):
            ex = Mock(spec=LabeledExample)
            ex.agent = "inbox_triage"
            ex.key = f"thread-{i}"
            ex.label = "quarantine" if i < 8 else "safe"  # 80% quarantine
            ex.source = "approvals"
            ex.created_at = datetime.utcnow() - timedelta(days=i)
            examples.append(ex)
        
        return examples
    
    def test_update_weights_for_agent(self, mock_db, sample_eval_results, sample_labeled_examples):
        """Should calculate weights based on agreement and calibration."""
        weights_mgr = JudgeWeights(mock_db)
        
        # Mock query chains
        eval_query = Mock()
        eval_query.filter.return_value = eval_query
        eval_query.all.return_value = sample_eval_results
        
        labeled_query = Mock()
        labeled_query.filter.return_value = labeled_query
        labeled_query.all.return_value = sample_labeled_examples
        
        # Mock RuntimeSetting query for save
        setting_query = Mock()
        setting_query.filter_by.return_value.first.return_value = None
        
        mock_db.query.side_effect = [eval_query, labeled_query, setting_query]
        
        weights = weights_mgr.update_weights_for_agent("inbox_triage")
        
        assert "gpt-4" in weights
        assert "gpt-3.5-turbo" in weights
        
        # gpt-4 should have higher weight (better calibration)
        assert weights["gpt-4"] > weights["gpt-3.5-turbo"]
        
        # Weights should be in valid range
        assert 0.1 <= weights["gpt-4"] <= 1.0
        assert 0.1 <= weights["gpt-3.5-turbo"] <= 1.0
    
    def test_update_weights_insufficient_data(self, mock_db):
        """Should return default weights when insufficient data."""
        weights_mgr = JudgeWeights(mock_db)
        
        # Mock empty results
        eval_query = Mock()
        eval_query.filter.return_value = eval_query
        eval_query.all.return_value = []
        
        mock_db.query.return_value = eval_query
        
        weights = weights_mgr.update_weights_for_agent("inbox_triage")
        
        # Should return defaults
        assert weights["gpt-4"] == 0.8
        assert weights["gpt-3.5-turbo"] == 0.6
    
    def test_get_weights(self, mock_db):
        """Should retrieve weights from runtime_settings."""
        weights_mgr = JudgeWeights(mock_db)
        
        # Mock stored weights
        setting = Mock(spec=RuntimeSetting)
        setting.value = json.dumps({"gpt-4": 0.85, "claude-3-opus": 0.78})
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = setting
        
        weights = weights_mgr.get_weights("inbox_triage")
        
        assert weights["gpt-4"] == 0.85
        assert weights["claude-3-opus"] == 0.78
    
    def test_get_weights_not_found(self, mock_db):
        """Should return defaults when weights not found."""
        weights_mgr = JudgeWeights(mock_db)
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        weights = weights_mgr.get_weights("inbox_triage")
        
        # Should return defaults
        assert weights["gpt-4"] == 0.8
        assert weights["gpt-3.5-turbo"] == 0.6
    
    def test_save_weights(self, mock_db):
        """Should save weights to runtime_settings."""
        weights_mgr = JudgeWeights(mock_db)
        
        # Mock no existing setting
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        weights = {"gpt-4": 0.85, "claude-3-opus": 0.78}
        weights_mgr._save_weights("inbox_triage", weights)
        
        # Should create new setting
        assert mock_db.add.called
        assert mock_db.commit.called
        
        # Check saved value
        saved_setting = mock_db.add.call_args[0][0]
        assert saved_setting.key == "judge_weights.inbox_triage"
        assert json.loads(saved_setting.value) == weights
        assert saved_setting.category == "active_learning"
    
    def test_update_all_agents(self, mock_db):
        """Should update weights for all agents."""
        weights_mgr = JudgeWeights(mock_db)
        
        # Mock distinct agents
        agents_query = Mock()
        agents_query.distinct.return_value.all.return_value = [
            ("inbox_triage",),
            ("insights_writer",)
        ]
        
        mock_db.query.return_value = agents_query
        
        with patch.object(weights_mgr, 'update_weights_for_agent') as mock_update:
            mock_update.return_value = {"gpt-4": 0.85}
            
            results = weights_mgr.update_all_agents()
        
        assert len(results) == 2
        assert "inbox_triage" in results
        assert "insights_writer" in results


class TestNightlyUpdate:
    """Test nightly weight update job."""
    
    def test_nightly_update_weights(self, monkeypatch):
        """Should update weights for all agents."""
        mock_db = Mock()
        
        with patch('app.active.weights.JudgeWeights') as mock_weights_class:
            mock_weights_mgr = Mock()
            mock_weights_mgr.update_all_agents.return_value = {
                "inbox_triage": {"gpt-4": 0.85},
                "insights_writer": {"claude-3-opus": 0.78}
            }
            mock_weights_class.return_value = mock_weights_mgr
            
            results = nightly_update_weights(mock_db)
        
        assert len(results) == 2
        assert "inbox_triage" in results
        assert mock_weights_mgr.update_all_agents.called
