"""Tests for local ML demo training script.

Verifies that synthetic training data is valid and model training works.
"""

from collections import Counter

from scripts.train_local_demo import get_mock_training_data, train_demo_model_in_memory


def test_mock_training_data_has_both_classes():
    """Verify synthetic dataset has both opportunities and non-opportunities."""
    texts, labels = get_mock_training_data()

    # Sanity check: non-trivial demo set
    assert len(texts) >= 20, "Training set should have at least 20 examples"
    assert len(texts) == len(labels), "Texts and labels must have same length"

    # Count class distribution
    counts = Counter(labels)

    # Ensure we have both positives and negatives
    assert counts[1] > 0, "Should have at least one opportunity example"
    assert counts[0] > 0, "Should have at least one non-opportunity example"

    # Verify class balance is reasonable (not too skewed)
    total = len(labels)
    minority_pct = min(counts[0], counts[1]) / total
    assert (
        minority_pct >= 0.2
    ), f"Classes too imbalanced: {counts} (minority class < 20%)"


def test_train_demo_model_in_memory_produces_predictions():
    """Verify in-memory training produces a working classifier."""
    clf, vec = train_demo_model_in_memory()

    # Get first 5 examples for smoke test
    texts, labels = get_mock_training_data()
    test_texts = texts[:5]

    # Transform and predict
    X = vec.transform(test_texts)
    preds = clf.predict(X)

    # Verify predictions
    assert len(preds) == len(test_texts), "Should predict for all test examples"
    assert set(preds).issubset({0, 1}), "Predictions should be binary (0 or 1)"

    # Verify predict_proba works
    probas = clf.predict_proba(X)
    assert probas.shape == (
        len(test_texts),
        2,
    ), "Should return probabilities for both classes"
    assert all(
        0 <= p <= 1 for row in probas for p in row
    ), "Probabilities should be in [0, 1]"


def test_vectorizer_vocabulary_is_reasonable():
    """Verify TF-IDF vectorizer learns a reasonable vocabulary."""
    _, vec = train_demo_model_in_memory()

    vocab_size = len(vec.vocabulary_)

    # Should have a decent vocabulary but not too large
    assert vocab_size > 50, "Vocabulary too small - may not capture enough features"
    assert vocab_size < 5000, "Vocabulary unexpectedly large for tiny training set"

    # Check for some expected keywords in vocabulary
    expected_terms = ["recruiter", "interview", "position", "engineer"]
    vocab = set(vec.vocabulary_.keys())

    found = [term for term in expected_terms if term in vocab]
    assert (
        len(found) >= 2
    ), f"Should find common job-related terms in vocabulary. Found: {found}"


def test_classifier_has_reasonable_coefficients():
    """Verify classifier learns meaningful feature weights."""
    clf, vec = train_demo_model_in_memory()

    # Get feature names and coefficients
    feature_names = vec.get_feature_names_out()
    coefficients = clf.coef_[0]

    # Should have as many coefficients as features
    assert len(coefficients) == len(
        feature_names
    ), "Coefficient count should match vocabulary size"

    # Some coefficients should be non-zero (model actually learned something)
    non_zero = sum(1 for c in coefficients if abs(c) > 0.01)
    assert non_zero > 10, "Too few non-zero coefficients - model may not be learning"

    # Check that some job-related terms have high positive weight
    coef_dict = dict(zip(feature_names, coefficients))
    job_terms = [t for t in ["recruiter", "interview", "position"] if t in coef_dict]

    if job_terms:
        avg_job_weight = sum(coef_dict[t] for t in job_terms) / len(job_terms)
        assert (
            avg_job_weight > 0
        ), "Job-related terms should have positive weight for opportunities"
