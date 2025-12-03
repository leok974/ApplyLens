"""
Evaluate the email classifier on the golden set.

Usage (from services/api/):

    python -m scripts.eval_email_classifier_on_golden

This script:
    - Loads emails from email_golden_labels (hand-labeled ground truth)
    - Uses the trained ML model to predict categories
    - Computes precision, recall, F1 for is_real_opportunity
    - Prints detailed classification report
"""

from __future__ import annotations

import sys

from sklearn.metrics import classification_report, confusion_matrix
from sqlalchemy.orm import Session

from app.classification.email_classifier import get_classifier
from app.db import SessionLocal
from app.models import Email, EmailGoldenLabel


def evaluate_on_golden_set() -> None:
    """
    Evaluate classifier on golden labels and print metrics.
    """
    db: Session = SessionLocal()

    try:
        # Load golden labels with their emails
        golden_labels = (
            db.query(EmailGoldenLabel)
            .join(Email, EmailGoldenLabel.email_id == Email.id)
            .all()
        )

        if not golden_labels:
            print("❌ No golden labels found in email_golden_labels table")
            print("\nTo create golden labels, manually label emails:")
            print("  INSERT INTO email_golden_labels")
            print(
                "    (email_id, golden_category, golden_is_real_opportunity, labeler)"
            )
            print("  VALUES")
            print("    (123, 'interview_invite', TRUE, 'your_name');")
            sys.exit(1)

        print(f"✓ Found {len(golden_labels)} golden labels\n")

        # Get classifier
        classifier = get_classifier()
        print(
            f"✓ Loaded classifier: mode={classifier.mode}, version={classifier.version}\n"
        )

        # Collect predictions and ground truth
        y_true = []
        y_pred = []
        category_true = []
        category_pred = []

        for golden in golden_labels:
            email = db.query(Email).filter(Email.id == golden.email_id).first()
            if not email:
                continue

            # Predict
            result = classifier.classify(email)

            # Binary classification (is_real_opportunity)
            y_true.append(golden.golden_is_real_opportunity)
            y_pred.append(result.is_real_opportunity)

            # Category classification
            category_true.append(golden.golden_category)
            category_pred.append(result.category)

        if not y_true:
            print("❌ No valid predictions generated")
            sys.exit(1)

        print("=" * 60)
        print("BINARY CLASSIFICATION: is_real_opportunity")
        print("=" * 60)
        print(
            classification_report(
                y_true,
                y_pred,
                target_names=["Not Opportunity", "Opportunity"],
                digits=3,
            )
        )

        print("\nConfusion Matrix (is_real_opportunity):")
        cm = confusion_matrix(y_true, y_pred)
        print("                  Predicted")
        print("                  False  True")
        print(f"Actual False      {cm[0][0]:5d}  {cm[0][1]:4d}")
        print(f"       True       {cm[1][0]:5d}  {cm[1][1]:4d}")

        print("\n" + "=" * 60)
        print("CATEGORY CLASSIFICATION")
        print("=" * 60)
        print(
            classification_report(
                category_true, category_pred, digits=3, zero_division=0
            )
        )

        # Summary stats
        binary_accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
        category_accuracy = sum(
            1 for t, p in zip(category_true, category_pred) if t == p
        ) / len(category_true)

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Golden set size:           {len(golden_labels)}")
        print(f"Binary accuracy:           {binary_accuracy:.3f}")
        print(f"Category accuracy:         {category_accuracy:.3f}")
        print(f"Classifier mode:           {classifier.mode}")
        print(f"Model version:             {classifier.version}")

        # Breakdown by category
        print("\n" + "=" * 60)
        print("PREDICTIONS BY CATEGORY")
        print("=" * 60)
        from collections import Counter

        pred_counter = Counter(category_pred)
        true_counter = Counter(category_true)

        all_categories = sorted(set(category_true) | set(category_pred))
        print(f"{'Category':<30} {'True':>6} {'Pred':>6}")
        print("-" * 60)
        for cat in all_categories:
            print(f"{cat:<30} {true_counter[cat]:>6} {pred_counter[cat]:>6}")

    finally:
        db.close()


def main() -> None:
    print("\n=== Email Classifier Golden Set Evaluation ===\n")
    evaluate_on_golden_set()
    print("\n✅ Evaluation complete!\n")


if __name__ == "__main__":
    main()
