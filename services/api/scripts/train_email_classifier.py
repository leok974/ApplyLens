"""
Train baseline email opportunity classifier.

Usage (from services/api/):
    python -m scripts.train_email_classifier

This will:
    - Connect to the DB
    - Build a dataset from email_training_labels (or heuristic bootstrap)
    - Train a binary classifier for is_real_opportunity
    - Save model + vectorizer under models/
"""

from __future__ import annotations

import os
import sys
from typing import List, Tuple

from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from app.models import Email, EmailTrainingLabel
from app.classification.email_classifier import build_email_text
from app.config import get_agent_settings


# Default paths (can be overridden by settings)
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, "email_opp_model.joblib")
DEFAULT_VEC_PATH = os.path.join(MODEL_DIR, "email_opp_vectorizer.joblib")


def _ensure_model_dir() -> None:
    """Create models directory if it doesn't exist."""
    os.makedirs(MODEL_DIR, exist_ok=True)


def load_training_data(
    db: Session, min_confidence: float = 0.8
) -> Tuple[List[str], List[int]]:
    """
    Load training dataset from email_training_labels.

    Label: 1 = real opportunity, 0 = not opportunity.
    Only use high-confidence labels for v1 to ensure quality.

    Args:
        db: Database session
        min_confidence: Minimum confidence threshold (default 0.8)

    Returns:
        Tuple of (texts, labels)
    """
    q = (
        db.query(EmailTrainingLabel, Email)
        .join(Email, EmailTrainingLabel.email_id == Email.id)
        .filter(EmailTrainingLabel.confidence >= min_confidence)
    )

    texts: List[str] = []
    labels: List[int] = []

    for tl, email in q:
        if tl.label_is_real_opportunity is None:
            continue

        y = 1 if tl.label_is_real_opportunity else 0
        x = build_email_text(email)

        if not x.strip():
            continue

        texts.append(x)
        labels.append(y)

    return texts, labels


def main() -> None:
    """Main training pipeline."""
    print("=== Email Opportunity Classifier Training ===\n")

    # Get settings for model paths
    settings = get_agent_settings()
    model_path = settings.EMAIL_CLASSIFIER_MODEL_PATH or DEFAULT_MODEL_PATH
    vec_path = settings.EMAIL_CLASSIFIER_VECTORIZER_PATH or DEFAULT_VEC_PATH

    # Ensure output directory exists
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    os.makedirs(os.path.dirname(vec_path), exist_ok=True)

    # Connect to database
    print("Connecting to database...")
    db: Session = SessionLocal()

    try:
        # Load training data
        print("Loading training data from email_training_labels...")
        texts, labels = load_training_data(db, min_confidence=0.8)
    finally:
        db.close()

    if not texts:
        print("\n❌ ERROR: No training data found in email_training_labels table.")
        print("   Make sure you have:")
        print("   1. Run the migration: alembic upgrade head")
        print("   2. Populated training labels from heuristics or rules")
        print("   3. Set confidence >= 0.8 for training examples")
        sys.exit(1)

    print(f"✓ Loaded {len(texts)} training examples")

    # Check class balance
    pos_count = sum(labels)
    neg_count = len(labels) - pos_count
    print(
        f"  - Positive (opportunities): {pos_count} ({pos_count/len(labels)*100:.1f}%)"
    )
    print(
        f"  - Negative (not opportunities): {neg_count} ({neg_count/len(labels)*100:.1f}%)"
    )

    # Import ML libraries (only when actually training)
    print("\nImporting ML libraries...")
    try:
        import joblib
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import (
            classification_report,
            precision_recall_fscore_support,
        )
    except ImportError as e:
        print(f"\n❌ ERROR: Required ML library not found: {e}")
        print("   Install with: pip install scikit-learn joblib")
        sys.exit(1)

    # Split data
    print("\nSplitting data (80/20 train/validation)...")
    X_train, X_val, y_train, y_val = train_test_split(
        texts,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )
    print(f"  - Training set: {len(X_train)} examples")
    print(f"  - Validation set: {len(X_val)} examples")

    # Build TF-IDF features
    print("\nBuilding TF-IDF features...")
    vectorizer = TfidfVectorizer(
        max_features=50000,
        ngram_range=(1, 2),
        lowercase=True,
        strip_accents="unicode",
        min_df=2,  # Ignore very rare terms
    )

    X_train_vec = vectorizer.fit_transform(X_train)
    X_val_vec = vectorizer.transform(X_val)
    print(f"✓ Feature matrix shape: {X_train_vec.shape}")
    print(f"  - Vocabulary size: {len(vectorizer.vocabulary_)}")

    # Train logistic regression
    print("\nTraining Logistic Regression classifier...")
    clf = LogisticRegression(
        max_iter=200,
        n_jobs=-1,
        class_weight="balanced",  # Handle class imbalance
        solver="lbfgs",
        random_state=42,
    )

    clf.fit(X_train_vec, y_train)
    print("✓ Training complete")

    # Evaluate on validation set
    print("\n=== Validation Results ===")
    y_pred = clf.predict(X_val_vec)

    print(
        classification_report(
            y_val, y_pred, digits=3, target_names=["Not Opp", "Opportunity"]
        )
    )

    # Additional metrics
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_val, y_pred, average="binary", pos_label=1
    )
    print("\n📊 Binary Metrics (Opportunity class):")
    print(f"   Precision: {precision:.3f}")
    print(f"   Recall:    {recall:.3f}")
    print(f"   F1-Score:  {f1:.3f}")

    # Save artifacts
    print("\n💾 Saving model artifacts...")
    joblib.dump(clf, model_path)
    joblib.dump(vectorizer, vec_path)
    print(f"✓ Saved model to: {model_path}")
    print(f"✓ Saved vectorizer to: {vec_path}")

    print("\n✅ Training complete! Model is ready to use.")
    print("\nNext steps:")
    print("  1. Test the classifier: python -m scripts.test_classifier")
    print("  2. Update settings.EMAIL_CLASSIFIER_MODE = 'ml_shadow'")
    print("  3. Monitor shadow mode predictions vs heuristics")
    print("  4. When confident, switch to 'ml_live'")


if __name__ == "__main__":
    main()
