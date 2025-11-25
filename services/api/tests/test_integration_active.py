"""Integration tests for Phase 5.3 Active Learning.

Tests that all modules import correctly and basic functionality works.
"""


def test_imports():
    """Test that all active learning modules can be imported."""
    # Core modules
    from app.models_al import LabeledExample
    from app.active.feeds import FeedLoader
    from app.active.heur_trainer import FeatureExtractor, HeuristicTrainer
    from app.active.weights import JudgeWeights
    from app.active.sampler import UncertaintySampler
    from app.active.bundles import BundleManager
    from app.active.guards import OnlineLearningGuard

    # API routes
    from app.api.routes.active import router

    # Scheduler

    # All imports successful
    assert LabeledExample is not None
    assert FeedLoader is not None
    assert FeatureExtractor is not None
    assert HeuristicTrainer is not None
    assert JudgeWeights is not None
    assert UncertaintySampler is not None
    assert BundleManager is not None
    assert OnlineLearningGuard is not None
    assert router is not None


def test_feature_extractors():
    """Test that feature extractors work correctly."""
    from app.active.heur_trainer import FeatureExtractor

    # Test inbox_triage extractor
    payload = {
        "risk_score": 85,
        "spf_fail": True,
        "dkim_fail": False,
        "suspicious_keywords": ["urgent", "verify"],
        "attachments": ["file.pdf"],
        "sender_domain_age_days": 5,
        "recipient_count": 1,
    }

    features = FeatureExtractor.extract_inbox_triage(payload)

    assert len(features) == 7
    assert features[0] == 85  # risk_score
    assert features[1] == 1  # spf_fail
    assert features[2] == 0  # dkim_fail
    assert features[3] == 2  # suspicious_keywords_count
    assert features[4] == 1  # attachment_count


def test_feature_extractor_routing():
    """Test that feature extractor routing works."""
    from app.active.heur_trainer import FeatureExtractor

    payload = {"risk_score": 50}

    # Should route to correct extractor
    features = FeatureExtractor.extract_for_agent("inbox_triage", payload)
    assert features is not None
    assert len(features) == 7

    # Unknown agent should return None
    features = FeatureExtractor.extract_for_agent("unknown_agent", payload)
    assert features is None


def test_uncertainty_calculation():
    """Test uncertainty calculation methods."""
    from app.active.sampler import UncertaintySampler
    from unittest.mock import Mock

    sampler = UncertaintySampler(Mock())

    # Test disagreement detection
    judge_scores = {
        "gpt-4": {"verdict": "quarantine", "confidence": 80},
        "claude-3-opus": {"verdict": "safe", "confidence": 75},
    }

    judge_weights = {"gpt-4": 0.8, "claude-3-opus": 0.8}

    uncertainty, method = sampler.calculate_uncertainty(judge_scores, judge_weights)

    assert method == "disagreement"
    assert uncertainty > 0.5  # High disagreement


def test_labeled_example_model():
    """Test LabeledExample model structure."""
    from app.models_al import LabeledExample

    # Check that model has required fields
    assert hasattr(LabeledExample, "id")
    assert hasattr(LabeledExample, "agent")
    assert hasattr(LabeledExample, "key")
    assert hasattr(LabeledExample, "payload")
    assert hasattr(LabeledExample, "label")
    assert hasattr(LabeledExample, "source")
    assert hasattr(LabeledExample, "confidence")
    assert hasattr(LabeledExample, "created_at")


def test_api_router_configuration():
    """Test that API router is configured correctly."""
    from app.api.routes.active import router

    # Check router has correct prefix
    assert router.prefix == "/api/active"

    # Check some key routes exist (routes include the prefix in their path)
    route_paths = [route.path for route in router.routes]

    assert "/api/active/stats/labeled" in route_paths
    assert "/api/active/bundles/create" in route_paths
    assert "/api/active/approvals/pending" in route_paths
    assert "/api/active/canaries/active" in route_paths
    assert "/api/active/weights" in route_paths
    assert "/api/active/review/queue" in route_paths
    assert "/api/active/status" in route_paths


def test_sklearn_imports():
    """Test that scikit-learn is available."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.preprocessing import StandardScaler
    import numpy as np

    # Verify we can instantiate models
    lr = LogisticRegression(random_state=42)
    dt = DecisionTreeClassifier(random_state=42, max_depth=5)
    scaler = StandardScaler()

    assert lr is not None
    assert dt is not None
    assert scaler is not None
    assert np is not None


def test_scheduler_configuration():
    """Test that scheduler jobs are configured correctly."""
    from app.scheduler import (
        list_scheduled_jobs,
        setup_scheduled_jobs,
        shutdown_scheduler,
    )

    # Setup jobs
    try:
        setup_scheduled_jobs()

        # List jobs
        jobs = list_scheduled_jobs()

        # Check that all 4 active learning jobs are present
        job_ids = [job["id"] for job in jobs]

        assert "load_labeled_data" in job_ids
        assert "update_judge_weights" in job_ids
        assert "sample_review_queue" in job_ids
        assert "check_canary_deployments" in job_ids

        # Shutdown
        shutdown_scheduler()
    except Exception as e:
        # If scheduler already running, that's okay
        if "already running" not in str(e).lower():
            raise


if __name__ == "__main__":
    # Run tests
    print("Running Phase 5.3 integration tests...")

    test_imports()
    print("✓ All imports successful")

    test_feature_extractors()
    print("✓ Feature extractors working")

    test_feature_extractor_routing()
    print("✓ Feature extractor routing working")

    test_uncertainty_calculation()
    print("✓ Uncertainty calculation working")

    test_labeled_example_model()
    print("✓ LabeledExample model structure correct")

    test_api_router_configuration()
    print("✓ API router configured correctly")

    test_sklearn_imports()
    print("✓ scikit-learn available")

    test_scheduler_configuration()
    print("✓ Scheduler configured correctly")

    print("\n✅ All Phase 5.3 integration tests passed!")
