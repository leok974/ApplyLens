"""Machine learning model training for email categorization.

This module trains a lightweight TF-IDF + Logistic Regression classifier
using weak labels generated from high-precision rules.

The model serves as a fallback for emails that don't match any rules,
providing probabilistic predictions with confidence scores.

Usage:
    python train_ml.py /path/to/weak_labels.jsonl /path/to/output_model.joblib

Expected JSONL format:
    {"subject": "...", "body_text": "...", "features": {...}, "weak_label": "promo"}
    {"subject": "...", "body_text": "...", "features": {...}, "weak_label": "newsletter"}
"""

import json
import os
import sys

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Target categories
CATEGORIES = ["promo", "newsletter", "recruiting", "bill", "other"]


def load_training_data(jsonl_path: str) -> tuple[list[dict], list[str]]:
    """Load training data from JSONL file.

    Args:
        jsonl_path: Path to JSONL file with training examples

    Returns:
        Tuple of (feature_dicts, labels) where:
            - feature_dicts: List of dicts with 'text' and numeric features
            - labels: List of category labels

    Raises:
        FileNotFoundError: If JSONL file doesn't exist
        ValueError: If JSONL is malformed or missing required fields
    """
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"Training data not found: {jsonl_path}")

    X, y = [], []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            try:
                doc = json.loads(line)

                # Combine subject and body for text features
                text = f"{doc.get('subject', '')} \n {doc.get('body_text', '')}"

                # Extract numeric features
                features = doc.get("features", {})

                # Build feature dict
                X.append(
                    {
                        "text": text,
                        "url_count": features.get("url_count", 0),
                        "money_hits": features.get("money_hits", 0),
                        "due_date_hit": features.get("due_date_hit", 0),
                        "sender_tf": features.get("sender_tf", 1),
                    }
                )

                # Get label
                label = doc.get("weak_label", "other")
                y.append(label)

            except json.JSONDecodeError as e:
                print(f"⚠️  Warning: Skipping malformed line {line_num}: {e}")
                continue
            except Exception as e:
                print(f"⚠️  Warning: Error processing line {line_num}: {e}")
                continue

    if not X:
        raise ValueError(f"No valid training examples found in {jsonl_path}")

    print(f"✅ Loaded {len(X)} training examples")
    print(f"   Label distribution: {dict(zip(*np.unique(y, return_counts=True)))}")

    return X, y


def build_pipeline() -> Pipeline:
    """Build scikit-learn pipeline for email classification.

    The pipeline consists of:
        1. TF-IDF vectorization of text (subject + body)
        2. Scaling of numeric features (URL count, money hits, etc.)
        3. Logistic regression classifier

    Returns:
        Fitted scikit-learn Pipeline ready for training
    """
    # Text vectorization with TF-IDF
    text_vec = TfidfVectorizer(
        max_features=20000,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,
    )

    # Numeric features to scale
    numeric_cols = ["url_count", "money_hits", "due_date_hit", "sender_tf"]

    # Column transformer to handle both text and numeric features
    preprocessor = ColumnTransformer(
        transformers=[
            ("text", text_vec, "text"),
            ("numeric", StandardScaler(with_mean=False), numeric_cols),
        ],
        remainder="drop",
        sparse_threshold=0.3,
    )

    # Logistic regression classifier
    classifier = LogisticRegression(
        max_iter=1000,
        n_jobs=-1,
        random_state=42,
        class_weight="balanced",  # Handle imbalanced classes
    )

    # Full pipeline
    pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )

    return pipeline


def train_model(
    jsonl_path: str,
    model_output_path: str = "label_model.joblib",
    test_size: float = 0.2,
) -> None:
    """Train email classification model and save to disk.

    Args:
        jsonl_path: Path to training data (JSONL format)
        model_output_path: Where to save the trained model
        test_size: Fraction of data to hold out for evaluation

    Side effects:
        - Writes trained model to model_output_path
        - Prints training metrics to stdout
    """
    print(f"🚀 Starting model training from {jsonl_path}")

    # Load data
    X, y = load_training_data(jsonl_path)

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )

    print(f"📊 Train set: {len(X_train)} examples")
    print(f"📊 Test set: {len(X_test)} examples")

    # Build and train pipeline
    print("🔨 Building pipeline...")
    pipeline = build_pipeline()

    print("🏋️  Training model...")
    pipeline.fit(X_train, y_train)

    # Evaluate on test set
    print("\n📈 Test Set Performance:")
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred, zero_division=0))

    # Confusion matrix
    print("\n🔍 Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred, labels=CATEGORIES)
    print(f"Labels: {CATEGORIES}")
    print(cm)

    # Training set performance (for comparison)
    print("\n📈 Training Set Performance (for reference):")
    y_train_pred = pipeline.predict(X_train)
    print(classification_report(y_train, y_train_pred, zero_division=0))

    # Save model
    print(f"\n💾 Saving model to {model_output_path}")
    joblib.dump(pipeline, model_output_path)

    print("\n✅ Model training complete!")
    print(f"   Model file: {model_output_path}")
    print(f"   File size: {os.path.getsize(model_output_path) / 1024:.1f} KB")


def main():
    """CLI entry point for model training."""
    if len(sys.argv) < 2:
        print("Usage: python train_ml.py <input_jsonl> [output_model]")
        print("\nExample:")
        print("  python train_ml.py /tmp/weak_labels.jsonl label_model.joblib")
        sys.exit(1)

    jsonl_path = sys.argv[1]
    model_path = sys.argv[2] if len(sys.argv) > 2 else "label_model.joblib"

    try:
        train_model(jsonl_path, model_path)
    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
