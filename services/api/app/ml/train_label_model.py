"""
Weak-label ML training for email categorization.

This module trains a simple LogisticRegression model on TF-IDF features
using weak labels from rule-based matching. The model learns to generalize
beyond the explicit rules.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
from joblib import dump, load
import numpy as np
from scipy.sparse import hstack
from pathlib import Path
from typing import List, Tuple
import logging

from app.ml.rules import match_rules
from app.db import SessionLocal
from app.models import Email


logger = logging.getLogger(__name__)

CATEGORIES = ["promotions", "ats", "bills", "banks", "events", "other"]
MODELS_DIR = Path(__file__).parent.parent.parent / "models"


def build_features(rows: List[Email]) -> Tuple[any, np.ndarray, List[str]]:
    """
    Build feature matrix from email rows.
    
    Args:
        rows: List of Email ORM objects
        
    Returns:
        Tuple of (X_features, y_labels, feature_names)
    """
    logger.info(f"Building features from {len(rows)} emails...")
    
    # Extract text content
    texts = [
        (r.subject or "") + "\n" + (r.body_text or "")[:5000]
        for r in rows
    ]
    
    # Extract simple numeric features
    sender_domains = [(r.sender or "").split("@")[-1] for r in rows]
    url_counts = [(r.body_text or "").count("http") for r in rows]
    money_mentions = [1 if "$" in (r.body_text or "") else 0 for r in rows]
    has_unsubscribe = [
        1 if r.raw and "list-unsubscribe" in str((r.raw.get("payload", {}) or {}).get("headers", [])).lower()
        else 0
        for r in rows
    ]
    
    # Generate weak labels from rules
    y_labels = []
    for r in rows:
        try:
            headers_dict = {}
            if r.raw and isinstance(r.raw, dict):
                headers_list = r.raw.get("payload", {}).get("headers", [])
                if isinstance(headers_list, list):
                    headers_dict = {h.get("name", ""): h.get("value", "") for h in headers_list}
            
            matches = match_rules({
                "headers": headers_dict,
                "sender_domain": (r.sender or "").split("@")[-1],
                "body_text": r.body_text or "",
                "subject": r.subject or "",
            })
            
            # Pick strongest match (priority order)
            label = "other"
            for category in ["ats", "bills", "banks", "events", "promotions"]:
                if matches.get(category):
                    label = category
                    break
            
            y_labels.append(label)
        except Exception as e:
            logger.warning(f"Error generating label for email {r.id}: {e}")
            y_labels.append("other")
    
    # Build TF-IDF features
    logger.info("Vectorizing text with TF-IDF...")
    tfidf = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=3,
        max_features=6000,
        stop_words='english'
    )
    X_text = tfidf.fit_transform(texts)
    
    # Build numeric features
    X_numeric = np.vstack([url_counts, money_mentions, has_unsubscribe]).T.astype(float)
    scaler = StandardScaler()
    X_numeric = scaler.fit_transform(X_numeric)
    
    # Combine features (convert to CSR for efficient slicing)
    X = hstack([X_text, X_numeric]).tocsr()
    
    logger.info(f"Feature matrix shape: {X.shape}")
    logger.info(f"Label distribution: {dict(zip(*np.unique(y_labels, return_counts=True)))}")
    
    return X, np.array(y_labels), tfidf, scaler


def train_model(limit: int = 5000, test_split: float = 0.2) -> dict:
    """
    Train weak-label classification model.
    
    Args:
        limit: Number of recent emails to use for training
        test_split: Fraction of data to use for testing
        
    Returns:
        Dict with model metrics and info
    """
    logger.info(f"Starting training with limit={limit}, test_split={test_split}")
    
    # Fetch recent emails
    db = SessionLocal()
    try:
        rows = (
            db.query(Email)
            .filter(Email.body_text.isnot(None))
            .order_by(Email.received_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()
    
    if len(rows) < 100:
        raise ValueError(f"Not enough emails for training (found {len(rows)}, need at least 100)")
    
    logger.info(f"Loaded {len(rows)} emails from database")
    
    # Build features
    X, y, tfidf, scaler = build_features(rows)
    
    # Split train/test
    n_samples = X.shape[0]
    split_idx = int(n_samples * (1 - test_split))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # Train logistic regression (one-vs-rest)
    logger.info("Training LogisticRegression model...")
    clf = LogisticRegression(
        max_iter=1000,
        n_jobs=-1,
        class_weight='balanced',
        random_state=42
    )
    clf.fit(X_train, y_train)
    
    # Evaluate
    y_pred = clf.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True)
    
    logger.info("Classification Report:")
    logger.info(classification_report(y_test, y_pred))
    
    # Save model
    MODELS_DIR.mkdir(exist_ok=True, parents=True)
    model_path = MODELS_DIR / "label_v1.joblib"
    
    model_bundle = {
        "tfidf": tfidf,
        "scaler": scaler,
        "clf": clf,
        "categories": list(clf.classes_),
        "version": "1.0",
    }
    
    dump(model_bundle, model_path)
    logger.info(f"Model saved to {model_path}")
    
    return {
        "model_path": str(model_path),
        "train_size": X_train.shape[0],
        "test_size": X_test.shape[0],
        "accuracy": report["accuracy"],
        "categories": list(clf.classes_),
        "report": report,
    }


if __name__ == "__main__":
    # CLI usage: python -m app.ml.train_label_model
    logging.basicConfig(level=logging.INFO)
    result = train_model(limit=5000)
    print(f"\nTraining complete!")
    print(f"Model: {result['model_path']}")
    print(f"Accuracy: {result['accuracy']:.3f}")
    print(f"Categories: {result['categories']}")
