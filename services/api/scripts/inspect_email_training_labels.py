"""
Inspect email training labels to verify data quality before training ml_v1.

Usage (from services/api/):

    python -m scripts.inspect_email_training_labels

This script:
    - Connects to the database and queries email_training_labels
    - Prints summary statistics:
        * Total label count
        * Distribution by category
        * Distribution by is_real_opportunity
        * Confidence statistics (min/avg/max)
    - Helps validate training data quality before running train_email_classifier
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import EmailTrainingLabel


def inspect_training_labels(db: Session) -> None:
    """Print summary statistics for email training labels."""

    print("=" * 70)
    print("EMAIL TRAINING LABELS - DATA QUALITY REPORT")
    print("=" * 70)
    print()

    # Total count
    total_count = db.query(EmailTrainingLabel).count()
    print(f"📊 Total Labels: {total_count}")
    print()

    if total_count == 0:
        print("⚠️  No training labels found!")
        print("   Run bootstrap_email_training_labels.py to generate labels.")
        return

    # Distribution by category
    print("📁 Distribution by Category:")
    print("-" * 70)
    category_counts = (
        db.query(
            EmailTrainingLabel.label_category,
            func.count(EmailTrainingLabel.id).label("count"),
        )
        .group_by(EmailTrainingLabel.label_category)
        .order_by(func.count(EmailTrainingLabel.id).desc())
        .all()
    )

    for category, count in category_counts:
        pct = (count / total_count) * 100
        bar = "█" * int(pct / 2)  # Visual bar (max 50 chars)
        print(f"  {category:30s} {count:5d} ({pct:5.1f}%) {bar}")
    print()

    # Distribution by is_real_opportunity
    print("🎯 Distribution by is_real_opportunity:")
    print("-" * 70)
    opp_counts = (
        db.query(
            EmailTrainingLabel.label_is_real_opportunity,
            func.count(EmailTrainingLabel.id).label("count"),
        )
        .group_by(EmailTrainingLabel.label_is_real_opportunity)
        .all()
    )

    for is_opp, count in opp_counts:
        label = "TRUE (Opportunity)" if is_opp else "FALSE (Not Opportunity)"
        if is_opp is None:
            label = "NULL (Unknown)"
        pct = (count / total_count) * 100
        print(f"  {label:30s} {count:5d} ({pct:5.1f}%)")
    print()

    # Class balance check
    true_count = (
        db.query(EmailTrainingLabel)
        .filter(EmailTrainingLabel.label_is_real_opportunity == True)  # noqa: E712
        .count()
    )
    false_count = (
        db.query(EmailTrainingLabel)
        .filter(EmailTrainingLabel.label_is_real_opportunity == False)  # noqa: E712
        .count()
    )

    if true_count > 0 and false_count > 0:
        balance_ratio = min(true_count, false_count) / max(true_count, false_count)
        print(f"⚖️  Class Balance Ratio: {balance_ratio:.3f}")
        if balance_ratio < 0.3:
            print(
                "   ⚠️  WARNING: Classes are imbalanced (ratio < 0.3). "
                "Consider rebalancing."
            )
        elif balance_ratio < 0.5:
            print("   ⚠️  Classes are somewhat imbalanced. Monitor training metrics.")
        else:
            print("   ✓ Classes are reasonably balanced.")
        print()

    # Confidence statistics
    print("📈 Confidence Statistics:")
    print("-" * 70)
    confidence_stats = db.query(
        func.min(EmailTrainingLabel.confidence).label("min_conf"),
        func.avg(EmailTrainingLabel.confidence).label("avg_conf"),
        func.max(EmailTrainingLabel.confidence).label("max_conf"),
    ).first()

    if confidence_stats:
        min_conf, avg_conf, max_conf = confidence_stats
        print(f"  Minimum: {min_conf:.3f}")
        print(f"  Average: {avg_conf:.3f}")
        print(f"  Maximum: {max_conf:.3f}")
    print()

    # High-confidence labels (>= 0.8)
    high_conf_count = (
        db.query(EmailTrainingLabel)
        .filter(EmailTrainingLabel.confidence >= 0.8)
        .count()
    )
    high_conf_pct = (high_conf_count / total_count) * 100
    print(
        f"✨ High-Confidence Labels (>= 0.8): {high_conf_count} ({high_conf_pct:.1f}%)"
    )
    print()

    # Label sources
    print("🔍 Label Sources:")
    print("-" * 70)
    source_counts = (
        db.query(
            EmailTrainingLabel.label_source,
            func.count(EmailTrainingLabel.id).label("count"),
        )
        .group_by(EmailTrainingLabel.label_source)
        .order_by(func.count(EmailTrainingLabel.id).desc())
        .all()
    )

    for source, count in source_counts:
        pct = (count / total_count) * 100
        print(f"  {source:40s} {count:5d} ({pct:5.1f}%)")
    print()

    # Recommendations
    print("=" * 70)
    print("💡 RECOMMENDATIONS:")
    print("=" * 70)

    if total_count < 300:
        print("  ⚠️  Low label count (<300). Recommend generating more labels.")
    elif total_count < 1000:
        print(
            "  ⚠️  Moderate label count (300-1000). Training possible but more data helps."
        )
    else:
        print(f"  ✓ Good label count ({total_count}). Ready for training.")

    if high_conf_count < 200:
        print(
            "  ⚠️  Low high-confidence labels (<200). Consider adding more high-confidence examples."
        )
    else:
        print(f"  ✓ Sufficient high-confidence labels ({high_conf_count}).")

    if true_count > 0 and false_count > 0:
        if balance_ratio >= 0.5:
            print("  ✓ Class balance is acceptable.")
        else:
            print("  ⚠️  Consider addressing class imbalance before training.")
    else:
        print(
            "  ❌ Missing examples for one or both classes. Cannot train binary classifier."
        )

    print("=" * 70)


def main() -> None:
    """CLI entry point for inspection script."""
    db: Session = SessionLocal()
    try:
        inspect_training_labels(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
