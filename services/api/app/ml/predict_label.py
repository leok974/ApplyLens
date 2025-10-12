"""
ML-based email classification with rule-based overrides.

This module loads the trained model and scores emails, combining
ML predictions with high-precision rule matches for best results.
"""
from joblib import load
import numpy as np
from scipy.sparse import hstack
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging

from app.ml.rules import match_rules


logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "label_v1.joblib"
_MODEL_CACHE: Optional[Dict] = None


def get_model() -> Dict:
    """Load model from disk (cached)."""
    global _MODEL_CACHE
    
    if _MODEL_CACHE is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. "
                "Run `python -m app.ml.train_label_model` first."
            )
        
        logger.info(f"Loading model from {MODEL_PATH}")
        _MODEL_CACHE = load(MODEL_PATH)
        logger.info(f"Model loaded: version={_MODEL_CACHE.get('version')}, "
                   f"categories={_MODEL_CACHE.get('categories')}")
    
    return _MODEL_CACHE


def score_email(email: Dict[str, any]) -> Tuple[str, Dict[str, float], Dict[str, any]]:
    """
    Score an email and return predicted category with confidence scores.
    
    Args:
        email: Dict with keys: subject, body_text, sender_domain, headers
        
    Returns:
        Tuple of (predicted_category, scores_dict, features_dict)
    """
    model = get_model()
    
    # Extract text
    text = (email.get("subject", "") or "") + "\n" + (email.get("body_text", "") or "")[:5000]
    
    # Build features
    tfidf = model["tfidf"]
    scaler = model["scaler"]
    clf = model["clf"]
    
    # Text features
    X_text = tfidf.transform([text])
    
    # Numeric features
    url_count = (email.get("body_text") or "").count("http")
    money_hits = 1 if "$" in (email.get("body_text") or "") else 0
    has_unsub = 1 if "list-unsubscribe" in str(email.get("headers", {})).lower() else 0
    X_numeric = np.array([[url_count, money_hits, has_unsub]], dtype=float)
    X_numeric = scaler.transform(X_numeric)
    
    # Combine
    X = hstack([X_text, X_numeric])
    
    # Get ML predictions
    proba = clf.predict_proba(X)[0]
    classes = list(clf.classes_)
    scores = dict(zip(classes, proba.astype(float).tolist()))
    
    # Apply high-precision rule overrides
    rule_matches = match_rules(email)
    for category, matched in rule_matches.items():
        if matched and category in scores:
            # Rule match gives very high confidence
            scores[category] = max(scores.get(category, 0), 0.95)
    
    # Pick best category
    predicted_category = max(scores.items(), key=lambda x: x[1])[0]
    
    # Build feature dict for debugging/analysis
    features = {
        "url_count": url_count,
        "has_money": money_hits > 0,
        "has_unsubscribe": has_unsub > 0,
        "text_length": len(text),
        "rule_matches": {k: v for k, v in rule_matches.items() if v},
    }
    
    logger.debug(f"Scored email: category={predicted_category}, "
                f"top_scores={dict(sorted(scores.items(), key=lambda x: -x[1])[:3])}")
    
    return predicted_category, scores, features


def reload_model():
    """Force reload of model from disk."""
    global _MODEL_CACHE
    _MODEL_CACHE = None
    get_model()
