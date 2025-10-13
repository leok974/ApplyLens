from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import SecurityPolicy
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
