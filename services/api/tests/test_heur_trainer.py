"""Tests for heuristic trainer.

Tests:
- Feature extraction per agent
- Model training with labeled examples
- Config bundle generation
- Diff generation between configs
"""

import pytest
import numpy as np
from unittest.mock import Mock

from app.active.heur_trainer import FeatureExtractor, HeuristicTrainer
from app.models_al import LabeledExample


class TestFeatureExtractor:
    """Test feature extraction for different agents."""

    def test_extract_inbox_triage(self):
        """Should extract 7 features for inbox triage."""
        payload = {
            "risk_score": 85,
            "spf_fail": True,
            "dkim_fail": False,
            "suspicious_keywords": ["urgent", "verify", "password"],
            "attachments": ["invoice.pdf"],
            "sender_domain_age_days": 5,
            "recipient_count": 1,
        }

        features = FeatureExtractor.extract_inbox_triage(payload)

        assert len(features) == 7
        assert features[0] == 85  # risk_score
        assert features[1] == 1  # spf_fail
        assert features[2] == 0  # dkim_fail
        assert features[3] == 3  # suspicious_keywords_count
        assert features[4] == 1  # attachment_count
        assert features[5] == 5  # sender_domain_age_days
        assert features[6] == 1  # recipient_count

    def test_extract_insights_writer(self):
        """Should extract 5 features for insights writer."""
        payload = {
            "pattern_strength": 85,
            "data_points_count": 120,
            "confidence_score": 92,
            "statistical_significance": 0.95,
            "novelty_score": 78,
        }

        features = FeatureExtractor.extract_insights_writer(payload)

        assert len(features) == 5
        assert features[0] == 85  # pattern_strength
        assert features[1] == 120  # data_points_count
        assert features[2] == 92  # confidence_score
        assert features[3] == 0.95  # statistical_significance
        assert features[4] == 78  # novelty_score

    def test_extract_knowledge_update(self):
        """Should extract 4 features for knowledge update."""
        payload = {
            "similarity_score": 88,
            "frequency_delta": 15,
            "co_occurrence_count": 25,
            "context_overlap_ratio": 0.75,
        }

        features = FeatureExtractor.extract_knowledge_update(payload)

        assert len(features) == 4
        assert features[0] == 88  # similarity_score
        assert features[1] == 15  # frequency_delta
        assert features[2] == 25  # co_occurrence_count
        assert features[3] == 0.75  # context_overlap_ratio

    def test_extract_for_agent(self):
        """Should route to correct extractor."""
        payload = {"risk_score": 50}

        features = FeatureExtractor.extract_for_agent("inbox_triage", payload)
        assert features is not None
        assert len(features) == 7

        # Unknown agent
        features = FeatureExtractor.extract_for_agent("unknown_agent", payload)
        assert features is None


class TestHeuristicTrainer:
    """Test model training and bundle generation."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def sample_examples(self):
        """Generate sample labeled examples."""
        examples = []

        # 30 high-risk quarantine examples
        for i in range(30):
            ex = Mock(spec=LabeledExample)
            ex.agent = "inbox_triage"
            ex.label = "quarantine"
            ex.source = "approvals"
            ex.payload = {
                "risk_score": 80 + np.random.randint(-10, 20),
                "spf_fail": True,
                "dkim_fail": False,
                "suspicious_keywords": ["urgent", "verify"],
                "attachments": [],
                "sender_domain_age_days": 2,
                "recipient_count": 1,
            }
            examples.append(ex)

        # 30 low-risk safe examples
        for i in range(30):
            ex = Mock(spec=LabeledExample)
            ex.agent = "inbox_triage"
            ex.label = "safe"
            ex.source = "approvals"
            ex.payload = {
                "risk_score": 20 + np.random.randint(-10, 20),
                "spf_fail": False,
                "dkim_fail": False,
                "suspicious_keywords": [],
                "attachments": [],
                "sender_domain_age_days": 365,
                "recipient_count": 1,
            }
            examples.append(ex)

        return examples

    def test_train_for_agent_insufficient_data(self, mock_db):
        """Should return None if insufficient examples."""
        trainer = HeuristicTrainer(mock_db)

        # Only 10 examples
        mock_examples = [Mock(spec=LabeledExample) for _ in range(10)]
        mock_db.query.return_value.filter_by.return_value.all.return_value = (
            mock_examples
        )

        bundle = trainer.train_for_agent("inbox_triage", min_examples=50)

        assert bundle is None

    def test_train_for_agent_logistic(self, mock_db, sample_examples):
        """Should train logistic regression model."""
        trainer = HeuristicTrainer(mock_db)

        mock_db.query.return_value.filter_by.return_value.all.return_value = (
            sample_examples
        )

        bundle = trainer.train_for_agent(
            "inbox_triage", min_examples=50, model_type="logistic"
        )

        assert bundle is not None
        assert bundle["agent"] == "inbox_triage"
        assert bundle["training_count"] == 60
        assert bundle["accuracy"] > 0.5  # Should be reasonably accurate
        assert "thresholds" in bundle
        assert "risk_score_threshold" in bundle["thresholds"]
        assert bundle["model_type"] == "LogisticRegression"

    def test_train_for_agent_tree(self, mock_db, sample_examples):
        """Should train decision tree model."""
        trainer = HeuristicTrainer(mock_db)

        mock_db.query.return_value.filter_by.return_value.all.return_value = (
            sample_examples
        )

        bundle = trainer.train_for_agent(
            "inbox_triage", min_examples=50, model_type="tree"
        )

        assert bundle is not None
        assert bundle["model_type"] == "DecisionTreeClassifier"
        assert "feature_importances" in bundle
        assert len(bundle["feature_importances"]) == 7  # 7 features for inbox_triage

    def test_generate_diff_initial(self, mock_db):
        """Should generate initial diff when no old bundle."""
        trainer = HeuristicTrainer(mock_db)

        new_bundle = {
            "agent": "inbox_triage",
            "accuracy": 0.85,
            "thresholds": {"risk_score_threshold": 65.0, "spf_dkim_weight": 1.5},
        }

        diff = trainer.generate_diff("inbox_triage", None, new_bundle)

        assert diff["type"] == "initial"
        assert len(diff["additions"]) == 2
        assert "risk_score_threshold" in diff["additions"]
        assert len(diff["changes"]) == 0

    def test_generate_diff_update(self, mock_db):
        """Should generate diff showing changes."""
        trainer = HeuristicTrainer(mock_db)

        old_bundle = {
            "agent": "inbox_triage",
            "accuracy": 0.80,
            "thresholds": {"risk_score_threshold": 70.0, "spf_dkim_weight": 1.2},
        }

        new_bundle = {
            "agent": "inbox_triage",
            "accuracy": 0.85,
            "thresholds": {
                "risk_score_threshold": 65.0,
                "spf_dkim_weight": 1.5,
                "new_param": 10,
            },
        }

        diff = trainer.generate_diff("inbox_triage", old_bundle, new_bundle)

        assert diff["type"] == "update"
        assert len(diff["changes"]) == 2  # risk_score and spf_dkim changed
        assert len(diff["additions"]) == 1  # new_param added
        assert diff["accuracy_delta"] == 0.05

        # Check change details
        risk_change = next(
            c for c in diff["changes"] if c["param"] == "risk_score_threshold"
        )
        assert risk_change["old"] == 70.0
        assert risk_change["new"] == 65.0
        assert risk_change["delta"] == -5.0
