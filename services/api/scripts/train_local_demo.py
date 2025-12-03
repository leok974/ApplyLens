"""Local Email Opportunity Classifier Training Demo 🧪

PURPOSE
-------
This script demonstrates the complete ML training pipeline for email classification
WITHOUT requiring access to the production database. It's an "offline lab" for:

1. **Testing Infrastructure** - Verify ML loading, inference, and diagnostics work
2. **Local Development** - Experiment with model changes without prod DB access
3. **Teaching Tool** - Understand how the ApplyLens classifier works under the hood
4. **CI/CD Validation** - Run training as part of automated testing

WHAT IT DOES
------------
1. Generates 60 synthetic email examples (25 opportunities + 35 non-opportunities)
2. Trains a TF-IDF vectorizer + LogisticRegression classifier
3. Evaluates performance on a validation split
4. Saves model artifacts as .joblib files

USAGE
-----
    python -m scripts.train_local_demo

OUTPUT
------
    models/email_classifier_v1.joblib    (~25KB)
    models/email_vectorizer_v1.joblib    (~120KB)

See docs/LOCAL_ML_DEMO.md for complete usage guide.

⚠️  NOT FOR PRODUCTION - Synthetic data only, intentionally overfit for testing.
"""

from __future__ import annotations

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_synthetic_training_data():
    """Generate synthetic training data without database."""

    # Synthetic examples mimicking real job search emails
    texts = [
        # True opportunities (is_real_opportunity=True)
        "Hi, I'm a recruiter at Google. We'd like to discuss the Senior Software Engineer role with you. Are you available for a call next week?",
        "Your application for the Product Manager position has been received. We'll review and get back to you within 5 business days.",
        "Congratulations! We'd like to invite you to interview for the Data Scientist role at Meta. Please select a time that works for you.",
        "Thank you for interviewing with us. We're pleased to extend an offer for the Engineering Manager position. Offer letter attached.",
        "We're interested in your profile for our Tech Lead opening. Can we schedule a phone screen to discuss the opportunity?",
        "Interview confirmation: Your technical interview is scheduled for Tuesday at 2pm PST. Meeting link: zoom.us/j/123",
        "Following up on your application - we'd like to move forward with the next round. Are you still interested in the role?",
        "Your profile matches our Machine Learning Engineer opening. Let's connect to discuss the position and team.",
        "We received your application for Software Engineer. Based on your experience, we think you'd be a great fit.",
        "Exciting news! After reviewing your interviews, we'd like to make you an offer. Compensation details below.",
        # More true opportunities
        "Hi there! I'm reaching out about an open position on our engineering team. Would love to chat about your background.",
        "Thanks for applying! We're impressed with your resume and would like to schedule a technical assessment.",
        "Your interview for the Backend Engineer role is confirmed. We'll send calendar invites shortly.",
        "Great speaking with you yesterday! As discussed, here's the formal offer letter for the Senior Developer position.",
        "We're moving forward with your candidacy. Next step is a behavioral interview with the hiring manager.",
        "Your application stood out to us. Let's hop on a call to discuss the Staff Engineer opportunity.",
        "Offer update: We've increased the compensation package based on your feedback. New details attached.",
        "Following up on our conversation - are you available for an onsite interview next month?",
        "We'd like to extend an invitation to our final round interviews. This will be an all-day session.",
        "Congratulations on passing the technical rounds! HR will reach out regarding next steps.",
        # Even more opportunities for better training
        "I'm a technical recruiter at Amazon. Your background in distributed systems is exactly what we're looking for.",
        "We're impressed by your open source contributions. Would you be interested in joining our team?",
        "Your skills match our Principal Engineer opening. Compensation range: $200k-$300k + equity.",
        "Thanks for the great interview! We'd like to schedule you for the final round with our CTO.",
        "We're pleased to inform you that you've been selected for the Software Architect position.",
        # False - not real opportunities (is_real_opportunity=False)
        "Your verification code is 482937. This code expires in 10 minutes. Do not share with anyone.",
        "Your order #45829 has shipped! Track your package here: tracking.example.com",
        "Weekly newsletter: Top 10 programming tips for developers. Click here to read more.",
        "Your LinkedIn security alert: New sign-in detected from Chrome on Windows in Seattle, WA.",
        "Receipt for your $49.99 purchase at Amazon.com. Order date: Dec 1, 2025.",
        "Join us for our upcoming webinar on Cloud Architecture Best Practices. Register now!",
        "Your GitHub pull request #1234 has been merged into main branch.",
        "Monthly digest: 15 new job postings matching 'software engineer' in your area.",
        "Your Spotify Premium subscription will renew on Dec 15 for $9.99.",
        "Security code for your bank account login: 739284. Valid for 5 minutes.",
        # More false examples
        "You've been added as a collaborator on the project 'awesome-repo'.",
        "Your password reset request for example.com. Click here to reset within 1 hour.",
        "Reminder: Your cloud hosting bill of $127.50 is due on Dec 10.",
        "New comment on your Stack Overflow answer: 'This solution worked perfectly, thanks!'",
        "Your flight confirmation AA1234 from SFO to NYC on Dec 20. Boarding at 6:45am.",
        "Weekly summary: You have 3 new followers and 12 profile views on LinkedIn.",
        "Alert: Unusual activity detected on your credit card ending in 4892.",
        "Your package has been delivered. Left at front door. See photo.",
        "Zoom meeting reminder: Team standup in 15 minutes. Join: zoom.us/j/9876",
        "Monthly report: Your GitHub stats - 42 commits, 8 PRs merged this month.",
        # More non-opportunities
        "Your domain registration for example.com will expire in 30 days. Renew now.",
        "Slack notification: @john mentioned you in #engineering channel.",
        "Your Docker Hub automated build completed successfully. View logs.",
        "Calendar event: All-hands meeting tomorrow at 10am PT.",
        "Your AWS bill for November: $234.67. View detailed breakdown.",
        "New connection request from Jane Smith on LinkedIn.",
        "Your email storage is 85% full. Upgrade to get more space.",
        "Reminder: Performance review self-assessment due Friday.",
        "Your certificate of completion for 'Advanced Python' course is ready.",
        "System notification: Server maintenance scheduled for this weekend.",
        # Additional non-opportunities for balance
        "Your tweet received 50+ likes! See who liked it.",
        "Medium digest: Top stories in Software Development this week.",
        "Your npm package 'awesome-lib' has 1000+ downloads!",
        "Jira notification: Issue DEV-123 assigned to you.",
        "Your conference ticket purchase confirmed. Event: PyCon 2025.",
    ]

    # Labels corresponding to each text (1 = opportunity, 0 = not opportunity)
    labels = [
        # True opportunities (25 examples)
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        # False - not opportunities (35 examples)
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]

    return texts, labels


def main() -> None:
    """Main training pipeline using synthetic data."""
    print("=== Email Opportunity Classifier Training (Local Demo) ===\n")

    # Get model paths from config or use defaults
    from app.config import get_agent_settings

    settings = get_agent_settings()

    MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
    DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, "email_classifier_v1.joblib")
    DEFAULT_VEC_PATH = os.path.join(MODEL_DIR, "email_vectorizer_v1.joblib")

    model_path = settings.EMAIL_CLASSIFIER_MODEL_PATH or DEFAULT_MODEL_PATH
    vec_path = settings.EMAIL_CLASSIFIER_VECTORIZER_PATH or DEFAULT_VEC_PATH

    # Ensure output directory exists
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    os.makedirs(os.path.dirname(vec_path), exist_ok=True)

    # Generate synthetic training data
    print("Generating synthetic training data...")
    texts, labels = generate_synthetic_training_data()
    print(f"✓ Generated {len(texts)} training examples")

    # Check class balance
    pos_count = sum(labels)
    neg_count = len(labels) - pos_count
    print(
        f"  - Positive (opportunities): {pos_count} ({pos_count/len(labels)*100:.1f}%)"
    )
    print(
        f"  - Negative (not opportunities): {neg_count} ({neg_count/len(labels)*100:.1f}%)"
    )

    # Import ML libraries
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
    # TF-IDF (Term Frequency-Inverse Document Frequency) converts text to numerical features
    # Parameters match production for consistency:
    # - max_features=50000: Keep top 50K most informative words (prevents memory bloat)
    # - ngram_range=(1,2): Use both single words and 2-word phrases ("senior engineer")
    # - min_df=2: Ignore words that appear in fewer than 2 documents (reduces noise)
    # - sublinear_tf=True: Use log scaling for term frequency (reduces impact of word spam)
    print("\nBuilding TF-IDF features...")
    vectorizer = TfidfVectorizer(
        max_features=50000,
        ngram_range=(1, 2),
        lowercase=True,
        strip_accents="unicode",
        min_df=1,  # Lower for small dataset
    )

    X_train_vec = vectorizer.fit_transform(X_train)
    X_val_vec = vectorizer.transform(X_val)
    print(f"✓ Feature matrix shape: {X_train_vec.shape}")
    print(f"  - Vocabulary size: {len(vectorizer.vocabulary_)}")

    # Train logistic regression
    # Logistic Regression is a simple, interpretable binary classifier
    # Parameters:
    # - max_iter=200: Maximum training iterations (usually converges much faster)
    # - n_jobs=-1: Use all CPU cores for faster training
    # - class_weight="balanced": Automatically adjust for imbalanced classes (more non-opps)
    # - solver="lbfgs": Optimization algorithm (fast, works well for small datasets)
    # - random_state=42: Reproducible results (same model every run)
    print("\nTraining Logistic Regression classifier...")
    clf = LogisticRegression(
        max_iter=200,
        n_jobs=-1,
        class_weight="balanced",  # Handle 25 opps vs 35 non-opps imbalance
        solver="lbfgs",
        random_state=42,
    )

    clf.fit(X_train_vec, y_train)  # Learn from vectorized training data
    print("✓ Training complete")

    # Evaluate on validation set
    # Classification report shows:
    # - Precision: Of predictions labeled "opportunity", how many were correct?
    # - Recall: Of actual opportunities, how many did we catch?
    # - F1-score: Harmonic mean of precision and recall (balanced metric)
    # - Support: Number of examples in each class
    #
    # Expected: 100% on all metrics (tiny dataset, intentional overfit for demo)
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
    # joblib serializes Python objects to disk efficiently (better than pickle for numpy)
    # Both artifacts are required for inference:
    # 1. vectorizer: Transforms new email text into feature vectors (same vocabulary)
    # 2. clf: Makes predictions from feature vectors
    # These files can be loaded directly by app/classification/email_classifier.py
    print("\n💾 Saving model artifacts...")
    joblib.dump(clf, model_path)  # Save trained classifier (~25KB)
    joblib.dump(vectorizer, vec_path)  # Save fitted vectorizer (~120KB)
    print(f"✓ Saved model to: {model_path}")
    print(f"✓ Saved vectorizer to: {vec_path}")

    print("\n✅ Training complete! Model is ready to use.")
    print("\n📝 Note: This model was trained on synthetic data for demonstration.")
    print("   For production use, train on real labeled emails from the database.")
    print("\nNext steps:")
    print("  1. Test the classifier with the diagnostic endpoint")
    print("  2. Update EMAIL_CLASSIFIER_MODE to 'ml_shadow' to enable shadow mode")
    print("  3. Monitor predictions and compare with heuristic baseline")


if __name__ == "__main__":
    main()
