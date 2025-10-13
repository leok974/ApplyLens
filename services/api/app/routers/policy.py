from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db import get_db
from app.models import SecurityPolicy
from app.models.actions import Policy
from app.models.personalization import PolicyStats
from app.schemas import SecurityPoliciesIn, SecurityPoliciesOut

router = APIRouter(prefix="/policy", tags=["policy"])


def _coerce_out(p: SecurityPolicy) -> SecurityPoliciesOut:
    """Convert database model to API output format."""
    return SecurityPoliciesOut(
        autoQuarantineHighRisk=p.auto_quarantine_high_risk,
        autoArchiveExpiredPromos=p.auto_archive_expired_promos,
        autoUnsubscribeInactive={
            "enabled": p.auto_unsubscribe_enabled,
            "threshold": p.auto_unsubscribe_threshold,
        },
    )


@router.get("/security", response_model=SecurityPoliciesOut)
def get_security_policy(db: Session = Depends(get_db)):
    """
    Get security policy configuration.
    Creates default policy if none exists.
    """
    p = db.query(SecurityPolicy).first()
    if not p:
        # Create default policy
        p = SecurityPolicy()
        db.add(p)
        db.commit()
        db.refresh(p)
    return _coerce_out(p)


@router.put("/security", response_model=SecurityPoliciesOut)
def put_security_policy(payload: SecurityPoliciesIn, db: Session = Depends(get_db)):
    """
    Update security policy configuration.
    Creates policy if none exists.
    """
    p = db.query(SecurityPolicy).first()
    if not p:
        p = SecurityPolicy()
        db.add(p)
    
    # Update policy fields
    p.auto_quarantine_high_risk = bool(payload.auto_quarantine_high_risk)
    p.auto_archive_expired_promos = bool(payload.auto_archive_expired_promos)
    
    # Handle auto_unsubscribe_inactive dict
    au = payload.auto_unsubscribe_inactive
    if au:
        p.auto_unsubscribe_enabled = bool(au.enabled)
        p.auto_unsubscribe_threshold = int(au.threshold)
    else:
        p.auto_unsubscribe_enabled = False
        p.auto_unsubscribe_threshold = 10
    
    db.commit()
    db.refresh(p)
    return _coerce_out(p)


def get_current_user():
    """Get current user (stub - replace with actual auth)."""
    return type("User", (), {"email": "user@example.com"})()


@router.get("/stats")
def policy_stats(db: Session = Depends(get_db), user=Depends(get_current_user)) -> List[Dict[str, Any]]:
    """
    Get policy performance statistics for the current user.
    
    Returns list of policies with their performance metrics:
    - policy_id: Policy ID
    - name: Policy name
    - precision: Ratio of approved to fired proposals
    - approved: Total approved proposals
    - rejected: Total rejected proposals
    - fired: Total times policy proposed an action
    
    Sorted by fired count (most active first).
    """
    rows = db.query(PolicyStats).filter_by(user_id=user.email).all()
    
    out = []
    for r in rows:
        pol = db.query(Policy).get(r.policy_id)
        out.append({
            "policy_id": r.policy_id,
            "name": getattr(pol, "name", "Unknown Policy"),
            "precision": round(r.precision, 3),
            "approved": r.approved,
            "rejected": r.rejected,
            "fired": r.fired,
            "recall": round(r.recall, 3),
            "window_days": r.window_days,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None
        })
    
    # Sort by fired count (most active first)
    out.sort(key=lambda x: x["fired"], reverse=True)
    
    return out
