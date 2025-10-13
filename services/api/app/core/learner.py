"""
Phase 6: Online learner for per-user personalization.

Learns feature weights from user approve/reject feedback using online gradient descent.
"""
from sqlalchemy.orm import Session
from ..models.personalization import UserWeight
from datetime import datetime
from typing import List, Dict, Any

# Learning rate for online gradient descent
ETA = 0.2


def featureize(email: Any) -> List[str]:
    """
    Extract features from an email for personalization.
    
    Features include:
    - category:<cat> (e.g., category:promo, category:event)
    - sender_domain:<domain> (e.g., sender_domain:bestbuy.com)
    - listid:<list_id> (e.g., listid:github-notifications)
    - contains:<token> (e.g., contains:invoice, contains:meetup)
    
    Args:
        email: Email object or dict with category, sender_domain, list_id, subject
        
    Returns:
        List of feature strings
    """
    feats = []
    
    # Category feature
    category = getattr(email, "category", None) or (email.get("category") if isinstance(email, dict) else None)
    if category:
        feats.append(f"category:{category}")
    
    # Sender domain feature
    sender_domain = getattr(email, "sender_domain", None) or (email.get("sender_domain") if isinstance(email, dict) else None)
    if sender_domain:
        feats.append(f"sender_domain:{sender_domain}")
    
    # List ID feature
    list_id = getattr(email, "list_id", None) or (email.get("list_id") if isinstance(email, dict) else None)
    if list_id:
        feats.append(f"listid:{list_id}")
    
    # Lightweight token features from subject
    subject = getattr(email, "subject", "") or (email.get("subject", "") if isinstance(email, dict) else "")
    subj_lower = (subject or "").lower()
    
    # Common tokens that indicate email type
    tokens = [
        "invoice", "receipt", "meetup", "interview", "newsletter", 
        "offer", "promotion", "discount", "sale", "deal", "conference",
        "webinar", "event", "reminder", "payment", "order", "shipping"
    ]
    
    for tok in tokens:
        if tok in subj_lower:
            feats.append(f"contains:{tok}")
    
    return feats


def update_user_weights(db: Session, user_id: str, email: Any, label: int) -> None:
    """
    Update user feature weights using online gradient descent.
    
    Update rule: w ← w + η * y * x
    where:
    - η (ETA) = learning rate (0.2)
    - y (label) = +1 for approve (good), -1 for reject (bad)
    - x = 1 for feature presence (binary features)
    
    Args:
        db: Database session
        user_id: User identifier (email)
        email: Email object or dict
        label: +1 for approve, -1 for reject
    """
    feats = featureize(email)
    
    for f in feats:
        # Get or create weight entry
        row = db.query(UserWeight).filter_by(user_id=user_id, feature=f).one_or_none()
        if not row:
            row = UserWeight(user_id=user_id, feature=f, weight=0.0)
            db.add(row)
        
        # Apply gradient update: w ← w + η * y * x (where x=1)
        row.weight = row.weight + ETA * label * 1.0
        row.updated_at = datetime.utcnow()
    
    db.commit()


def score_ctx_with_user(db: Session, user_id: str, feats: List[str]) -> float:
    """
    Score a context (set of features) using learned user weights.
    
    Args:
        db: Database session
        user_id: User identifier (email)
        feats: List of feature strings (from featureize())
        
    Returns:
        Sum of weights for all features present
    """
    tot = 0.0
    for f in feats:
        w = db.query(UserWeight).filter_by(user_id=user_id, feature=f).one_or_none()
        if w:
            tot += w.weight
    return tot


def get_user_preferences(db: Session, user_id: str, top_k: int = 20) -> List[Dict[str, Any]]:
    """
    Get top learned preferences for a user (highest absolute weights).
    
    Args:
        db: Database session
        user_id: User identifier
        top_k: Number of top features to return
        
    Returns:
        List of dicts with feature, weight, and preference type (like/dislike)
    """
    weights = (
        db.query(UserWeight)
        .filter_by(user_id=user_id)
        .order_by(UserWeight.weight.desc())
        .limit(top_k)
        .all()
    )
    
    result = []
    for w in weights:
        result.append({
            "feature": w.feature,
            "weight": w.weight,
            "preference": "like" if w.weight > 0 else "dislike",
            "strength": abs(w.weight),
            "updated_at": w.updated_at.isoformat() if w.updated_at else None
        })
    
    return result
