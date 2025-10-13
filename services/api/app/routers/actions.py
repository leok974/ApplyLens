"""
Actions Router - Phase 4 Agentic Actions & Approval Loop

Endpoints:
- POST /actions/propose - Create action proposals for emails
- POST /actions/{id}/approve - Approve and execute an action
- POST /actions/{id}/reject - Reject an action
- POST /actions/{id}/execute - Direct execution (admin)
- GET /actions/tray - List pending actions for UI
- GET /actions/policies - List all policies
- POST /actions/policies - Create new policy
- PUT /actions/policies/{id} - Update policy
- DELETE /actions/policies/{id} - Delete policy
- POST /actions/policies/{id}/test - Test policy against emails
"""

import base64
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.executors import execute_action
from ..core.learner import score_ctx_with_user, update_user_weights
from ..core.yardstick import evaluate_policy, validate_condition
from ..db import get_db
from ..models import ActionType, AuditAction, Email, Policy, PolicyStats, ProposedAction
from ..telemetry.metrics import METRICS

router = APIRouter(prefix="/actions", tags=["actions"])


# ===== Request/Response Models =====


class ProposeRequest(BaseModel):
    """Request to propose actions for emails."""

    email_ids: List[int] = Field(default_factory=list, description="Specific email IDs")
    query: Optional[str] = Field(None, description="ES query to find candidate emails")
    limit: int = Field(100, ge=1, le=1000, description="Max emails to process")


class ApproveRequest(BaseModel):
    """Request to approve an action with optional screenshot."""

    screenshot_data_url: Optional[str] = Field(
        None, description="Base64 data URL of screenshot"
    )


class PolicyCreate(BaseModel):
    """Request to create a new policy."""

    name: str = Field(..., min_length=1, max_length=255)
    enabled: bool = Field(True)
    priority: int = Field(100, ge=1, le=1000)
    condition: Dict[str, Any] = Field(..., description="Yardstick DSL condition")
    action: ActionType
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0)


class PolicyUpdate(BaseModel):
    """Request to update an existing policy."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=1000)
    condition: Optional[Dict[str, Any]] = None
    action: Optional[ActionType] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class PolicyTestRequest(BaseModel):
    """Request to test a policy against emails."""

    email_ids: List[int] = Field(default_factory=list)
    limit: int = Field(10, ge=1, le=100)


# ===== Helper Functions =====


def build_email_ctx(email: Email) -> Dict[str, Any]:
    """
    Build email context for policy evaluation.

    Returns dict with all relevant fields for Yardstick DSL.
    """
    ctx = {
        "category": email.category,
        "risk_score": email.risk_score or 0.0,
        "quarantined": email.quarantined,
        "sender": email.sender,
        "sender_domain": extract_domain(email.sender) if email.sender else None,
        "subject": email.subject,
        "received_at": email.received_at.isoformat() if email.received_at else None,
        "expires_at": email.expires_at.isoformat() if email.expires_at else None,
        "labels": email.labels or [],
    }

    # Compute age_days
    if email.received_at:
        age = datetime.utcnow() - email.received_at.replace(tzinfo=None)
        ctx["age_days"] = age.days

    # Compute expired_days
    if email.expires_at:
        expired = datetime.utcnow() - email.expires_at.replace(tzinfo=None)
        ctx["expired_days"] = max(0, expired.days)

    return ctx


def extract_domain(email_address: str) -> Optional[str]:
    """Extract domain from email address."""
    if not email_address or "@" not in email_address:
        return None
    return email_address.split("@")[-1].lower()


def estimate_confidence(
    policy: Policy,
    feats: Dict[str, Any],
    aggs: Dict[str, Any],
    neighbors: List[Any],
    db: Optional[Session] = None,
    user: Optional[Any] = None,
    email: Optional[Email] = None,
) -> float:
    """
    Estimate confidence score for a policy match with personalized learning bump.

    Args:
        policy: Matched policy
        feats: Email features dict
        aggs: Aggregation features (promo_ratio, etc.)
        neighbors: KNN neighbors (for future use)
        db: Database session (for user weight lookup)
        user: User object with email attribute
        email: Email object being evaluated

    Returns:
        Confidence score (0.01 - 0.99)
    """
    # Base confidence from policy
    base = policy.confidence_threshold if policy else 0.7

    # Simple heuristics
    if feats.get("category") == "promo" and aggs.get("promo_ratio", 0) > 0.6:
        base += 0.1
    if feats.get("risk_score", 0) >= 80:
        base = 0.95

    # User-personalized bump: +/- up to ~0.15
    if db and user and email:
        f = []
        if getattr(email, "category", None):
            f.append(f"category:{email.category}")
        if getattr(email, "sender_domain", None):
            f.append(f"sender_domain:{email.sender_domain}")
        subj = (getattr(email, "subject", "") or "").lower()
        for tok in ("invoice", "receipt", "meetup", "interview", "newsletter", "offer"):
            if tok in subj:
                f.append(f"contains:{tok}")

        bump = max(-0.15, min(0.15, 0.05 * score_ctx_with_user(db, user.email, f)))
        base += bump

    return max(0.01, min(0.99, base))


def build_rationale(
    email: Email,
    policy: Policy,
    db: Optional[Session] = None,
    user: Optional[Any] = None,
) -> tuple[float, Dict[str, Any]]:
    """
    Build confidence score and rationale for an action proposal.

    Returns:
        (confidence: float, rationale: dict)

    Rationale schema:
    {
        "features": {...},
        "narrative": {
            "summary": "..."
        },
        "policy": {
            "id": 1,
            "name": "...",
            "priority": 50
        }
    }
    """
    # Gather features for confidence estimation
    features = {
        "category": email.category,
        "risk_score": email.risk_score,
        "quarantined": email.quarantined,
        "expired_days": 0,
    }

    if email.expires_at:
        expired = datetime.utcnow() - email.expires_at.replace(tzinfo=None)
        features["expired_days"] = max(0, expired.days)

    # Estimate confidence with personalized learning bump
    aggs = {}  # TODO: Add ES aggregations in Phase 4.1
    neighbors = []  # TODO: Add KNN neighbors in Phase 4.1
    confidence = estimate_confidence(
        policy, features, aggs, neighbors, db=db, user=user, email=email
    )

    # Build narrative
    narrative = {"summary": f"Policy '{policy.name}' matched this email."}

    if (
        policy.action == ActionType.archive_email
        and features.get("expired_days", 0) > 0
    ):
        narrative["summary"] = (
            f"Email expired {features['expired_days']} days ago; auto-archiving per policy."
        )
    elif (
        policy.action == ActionType.quarantine_attachment
        and features.get("risk_score", 0) >= 80
    ):
        narrative["summary"] = (
            f"High risk score ({features['risk_score']:.1f}); quarantining per policy."
        )

    rationale = {
        "features": features,
        "narrative": narrative,
        "policy": {
            "id": policy.id,
            "name": policy.name,
            "priority": policy.priority,
        },
    }

    return confidence, rationale


def derive_action_params(email: Email, policy: Policy) -> Dict[str, Any]:
    """
    Derive action-specific parameters from email and policy.

    Examples:
    - label_email -> {"label": "auto-archived"}
    - create_calendar_event -> {"title": ..., "start_time": ...}
    """
    params = {}

    if policy.action == ActionType.label_email:
        params["label"] = "auto-" + policy.name.lower().replace(" ", "-")

    elif policy.action == ActionType.move_to_folder:
        params["folder"] = "Archive"

    elif policy.action == ActionType.create_calendar_event and email.event_start_at:
        params["title"] = email.subject or "Event"
        params["start_time"] = email.event_start_at.isoformat()
        if email.event_location:
            params["location"] = email.event_location

    elif policy.action == ActionType.create_task:
        params["title"] = email.subject or "Task"
        if email.expires_at:
            params["due_date"] = email.expires_at.isoformat()

    elif policy.action == ActionType.block_sender:
        params["sender"] = email.sender

    return params


def save_screenshot(data_url: Optional[str]) -> Optional[str]:
    """
    Save screenshot data URL to disk.

    Returns:
        Path to saved file, or None
    """
    if not data_url:
        return None

    try:
        # Parse data URL: data:image/png;base64,iVBORw0KG...
        if not data_url.startswith("data:image/"):
            return None

        header, encoded = data_url.split(",", 1)
        image_data = base64.b64decode(encoded)

        # Create directory structure
        now = datetime.utcnow()
        dir_path = f"/data/audit/{now.year}-{now.month:02d}"
        os.makedirs(dir_path, exist_ok=True)

        # Save file
        filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}.png"
        file_path = os.path.join(dir_path, filename)

        with open(file_path, "wb") as f:
            f.write(image_data)

        return file_path

    except Exception as e:
        print(f"Failed to save screenshot: {e}")
        return None


def _touch_policy_stats(
    db: Session,
    user_email: str,
    policy_id: int,
    fired: int = 0,
    approved: int = 0,
    rejected: int = 0,
) -> None:
    """
    Update policy statistics for personalization.

    Increments counters and recomputes precision.

    Args:
        db: Database session
        user_email: User identifier
        policy_id: Policy ID that fired/was approved/rejected
        fired: Increment fired counter by this amount
        approved: Increment approved counter by this amount
        rejected: Increment rejected counter by this amount
    """
    ps = (
        db.query(PolicyStats)
        .filter_by(policy_id=policy_id, user_id=user_email)
        .one_or_none()
    )

    if not ps:
        ps = PolicyStats(policy_id=policy_id, user_id=user_email)
        db.add(ps)

    # Increment counters
    ps.fired += fired
    ps.approved += approved
    ps.rejected += rejected

    # Recompute precision: approved / fired
    denom = max(1, ps.fired)
    ps.precision = ps.approved / denom
    ps.updated_at = datetime.utcnow()

    db.commit()


def get_current_user():
    """
    Get current user (stub - replace with actual auth).

    In production, this would extract user from JWT/session.
    """
    # TODO: Implement real authentication
    return type("User", (), {"email": "user@example.com"})()


# ===== Endpoints =====


@router.post("/propose")
def propose_actions(
    req: ProposeRequest, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    """
    Propose actions for a set of emails based on enabled policies.

    Process:
    1. Load emails (by IDs or query)
    2. Load enabled policies (ordered by priority)
    3. For each email:
        - Evaluate policies in priority order
        - Create ProposedAction for first matching policy
        - Stop at first match (short-circuit)

    Returns:
        {"created": [action_ids], "count": N}
    """
    # Load emails
    if req.email_ids:
        emails = db.query(Email).filter(Email.id.in_(req.email_ids)).all()
    else:
        # TODO: Implement ES query search in Phase 4.1
        # For now, just get recent emails
        emails = (
            db.query(Email).order_by(Email.received_at.desc()).limit(req.limit).all()
        )

    # Load enabled policies (priority order)
    policies = (
        db.query(Policy).filter(Policy.enabled).order_by(Policy.priority.asc()).all()
    )

    if not policies:
        raise HTTPException(400, "No enabled policies found")

    created = []

    for email in emails:
        ctx = build_email_ctx(email)

        # Try each policy (stop at first match)
        for policy in policies:
            if evaluate_policy({"condition": policy.condition}, ctx):
                confidence, rationale = build_rationale(email, policy, db=db, user=user)

                if confidence >= policy.confidence_threshold:
                    pa = ProposedAction(
                        email_id=email.id,
                        action=policy.action,
                        confidence=confidence,
                        params=derive_action_params(email, policy),
                        rationale=rationale,
                        policy_id=policy.id,
                        status="pending",
                    )
                    db.add(pa)
                    created.append(pa)

                    # Track metric
                    METRICS["actions_proposed"].labels(policy_name=policy.name).inc()

                    # Phase 6: Track policy fired
                    _touch_policy_stats(db, user.email, policy.id, fired=1)
                    METRICS["policy_fired_total"].labels(
                        policy_id=str(policy.id), user=user.email
                    ).inc()

                    break  # Stop at first matching policy

    db.commit()

    return {"created": [pa.id for pa in created], "count": len(created)}


@router.post("/{action_id}/approve")
def approve_action(
    action_id: int,
    req: ApproveRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Approve and execute a proposed action.

    Process:
    1. Validate action is pending
    2. Mark as approved
    3. Execute the action
    4. Write audit trail
    5. Update status (executed/failed)

    Returns:
        {"ok": bool, "outcome": str}
    """
    pa = db.get(ProposedAction, action_id)

    if not pa:
        raise HTTPException(404, "Action not found")

    if pa.status != "pending":
        raise HTTPException(400, f"Action is not pending (status={pa.status})")

    # Mark as approved
    pa.status = "approved"
    pa.reviewed_by = user.email
    pa.reviewed_at = datetime.utcnow()
    db.commit()

    # Execute action
    success, error = execute_action(pa, user)

    # Save screenshot
    screenshot_path = save_screenshot(req.screenshot_data_url)

    # Write audit trail
    audit = AuditAction(
        email_id=pa.email_id,
        action=pa.action,
        params=pa.params,
        actor=user.email,
        outcome="success" if success else "fail",
        error=error,
        why=pa.rationale,
        screenshot_path=screenshot_path,
    )
    db.add(audit)

    # Update proposed action status
    pa.status = "executed" if success else "failed"
    db.commit()

    # Phase 6: Learn from approve feedback
    email = db.get(Email, pa.email_id)
    if email:
        update_user_weights(db, user.email, email, label=+1)  # +1 for approve
        METRICS["user_weight_updates"].labels(user=user.email, sign="plus").inc()

    # Phase 6: Update policy stats
    if hasattr(pa, "policy_id") and pa.policy_id:
        _touch_policy_stats(db, user.email, pa.policy_id, approved=1)
        METRICS["policy_approved_total"].labels(
            policy_id=str(pa.policy_id), user=user.email
        ).inc()

    # Track metrics
    if success:
        METRICS["actions_executed"].labels(
            action_type=pa.action.value, outcome="success"
        ).inc()
    else:
        METRICS["actions_failed"].labels(
            action_type=pa.action.value, error_type=error[:50] if error else "unknown"
        ).inc()

    return {"ok": success, "outcome": "success" if success else "fail", "error": error}


@router.post("/{action_id}/reject")
def reject_action(
    action_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    """
    Reject a proposed action.

    Process:
    1. Validate action is pending
    2. Mark as rejected
    3. Write audit trail (outcome=noop)

    Returns:
        {"ok": true}
    """
    pa = db.get(ProposedAction, action_id)

    if not pa:
        raise HTTPException(404, "Action not found")

    if pa.status != "pending":
        raise HTTPException(400, f"Action is not pending (status={pa.status})")

    # Mark as rejected
    pa.status = "rejected"
    pa.reviewed_by = user.email
    pa.reviewed_at = datetime.utcnow()

    # Write audit trail
    audit = AuditAction(
        email_id=pa.email_id,
        action=pa.action,
        params=pa.params,
        actor=user.email,
        outcome="noop",
        error=None,
        why={"reason": "rejected_by_user"},
    )
    db.add(audit)
    db.commit()

    # Phase 6: Learn from reject feedback
    email = db.get(Email, pa.email_id)
    if email:
        update_user_weights(db, user.email, email, label=-1)  # -1 for reject
        METRICS["user_weight_updates"].labels(user=user.email, sign="minus").inc()

    # Phase 6: Update policy stats
    if hasattr(pa, "policy_id") and pa.policy_id:
        _touch_policy_stats(db, user.email, pa.policy_id, rejected=1)
        METRICS["policy_rejected_total"].labels(
            policy_id=str(pa.policy_id), user=user.email
        ).inc()

    return {"ok": True}


class AlwaysRequest(BaseModel):
    """Request to create a policy from this action (Always do this)."""

    rationale_features: Dict[str, Any] = Field(default_factory=dict)


@router.post("/{action_id}/always")
def always_do_this(
    action_id: int,
    req: AlwaysRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Create a policy based on this action ("Always do this" button).

    Process:
    1. Load the proposed action
    2. Extract stable features from rationale
    3. Create a new policy with learned condition
    4. Set appropriate priority and confidence threshold

    Returns:
        {"ok": true, "policy_id": N}
    """
    pa = db.get(ProposedAction, action_id)

    if not pa:
        raise HTTPException(404, "Action not found")

    # Extract features from rationale
    feats = req.rationale_features or (pa.rationale or {}).get("features", {})

    # Build condition from stable features
    cond_all = []

    for k in ("category", "sender_domain"):
        if feats.get(k) is not None:
            cond_all.append({"eq": [k, feats[k]]})

    if not cond_all:
        raise HTTPException(400, "No stable features to learn policy from")

    # Create learned policy
    policy = Policy(
        name=f"Learned: {pa.action.value} for {feats.get('sender_domain', 'generic')}",
        enabled=True,
        priority=40,  # Medium priority for learned policies
        action=pa.action,
        confidence_threshold=max(0.7, float(pa.confidence) - 0.05),
        condition={"all": cond_all},
    )

    db.add(policy)
    db.commit()

    return {"ok": True, "policy_id": policy.id}


@router.get("/tray")
def get_tray(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Get pending actions for UI tray.

    Returns list of proposed actions with email details.
    """
    actions = (
        db.query(ProposedAction)
        .filter(ProposedAction.status == "pending")
        .order_by(ProposedAction.created_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for pa in actions:
        email = db.get(Email, pa.email_id)
        if not email:
            continue

        result.append(
            {
                "id": pa.id,
                "action": pa.action.value,
                "confidence": pa.confidence,
                "rationale": pa.rationale,
                "created_at": pa.created_at.isoformat(),
                "email": {
                    "id": email.id,
                    "subject": email.subject,
                    "sender": email.sender,
                    "received_at": (
                        email.received_at.isoformat() if email.received_at else None
                    ),
                },
            }
        )

    return result


# ===== Policy CRUD =====


@router.get("/policies")
def list_policies(enabled_only: bool = Query(False), db: Session = Depends(get_db)):
    """List all policies."""
    query = db.query(Policy)

    if enabled_only:
        query = query.filter(Policy.enabled)

    policies = query.order_by(Policy.priority.asc()).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "enabled": p.enabled,
            "priority": p.priority,
            "condition": p.condition,
            "action": p.action.value,
            "confidence_threshold": p.confidence_threshold,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        }
        for p in policies
    ]


@router.post("/policies")
def create_policy(req: PolicyCreate, db: Session = Depends(get_db)):
    """Create a new policy."""
    # Validate condition syntax
    valid, error = validate_condition(req.condition)
    if not valid:
        raise HTTPException(400, f"Invalid condition: {error}")

    # Check for duplicate name
    existing = db.query(Policy).filter(Policy.name == req.name).first()
    if existing:
        raise HTTPException(400, f"Policy with name '{req.name}' already exists")

    policy = Policy(
        name=req.name,
        enabled=req.enabled,
        priority=req.priority,
        condition=req.condition,
        action=req.action,
        confidence_threshold=req.confidence_threshold,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    return {
        "id": policy.id,
        "name": policy.name,
        "enabled": policy.enabled,
        "priority": policy.priority,
        "condition": policy.condition,
        "action": policy.action.value,
        "confidence_threshold": policy.confidence_threshold,
    }


@router.put("/policies/{policy_id}")
def update_policy(policy_id: int, req: PolicyUpdate, db: Session = Depends(get_db)):
    """Update an existing policy."""
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(404, "Policy not found")

    # Validate condition if provided
    if req.condition is not None:
        valid, error = validate_condition(req.condition)
        if not valid:
            raise HTTPException(400, f"Invalid condition: {error}")
        policy.condition = req.condition

    # Update fields
    if req.name is not None:
        # Check for duplicate name
        existing = (
            db.query(Policy)
            .filter(Policy.name == req.name, Policy.id != policy_id)
            .first()
        )
        if existing:
            raise HTTPException(400, f"Policy with name '{req.name}' already exists")
        policy.name = req.name

    if req.enabled is not None:
        policy.enabled = req.enabled

    if req.priority is not None:
        policy.priority = req.priority

    if req.action is not None:
        policy.action = req.action

    if req.confidence_threshold is not None:
        policy.confidence_threshold = req.confidence_threshold

    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)

    return {
        "id": policy.id,
        "name": policy.name,
        "enabled": policy.enabled,
        "priority": policy.priority,
        "condition": policy.condition,
        "action": policy.action.value,
        "confidence_threshold": policy.confidence_threshold,
    }


@router.delete("/policies/{policy_id}")
def delete_policy(policy_id: int, db: Session = Depends(get_db)):
    """Delete a policy."""
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(404, "Policy not found")

    db.delete(policy)
    db.commit()

    return {"ok": True}


@router.post("/policies/{policy_id}/test")
def test_policy(policy_id: int, req: PolicyTestRequest, db: Session = Depends(get_db)):
    """
    Test a policy against emails without creating proposals.

    Returns:
        {"matches": [email_ids], "count": N}
    """
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(404, "Policy not found")

    # Load emails
    if req.email_ids:
        emails = db.query(Email).filter(Email.id.in_(req.email_ids)).all()
    else:
        emails = (
            db.query(Email).order_by(Email.received_at.desc()).limit(req.limit).all()
        )

    matches = []
    for email in emails:
        ctx = build_email_ctx(email)
        if evaluate_policy({"condition": policy.condition}, ctx):
            matches.append(email.id)

    return {
        "matches": matches,
        "count": len(matches),
        "policy": {
            "id": policy.id,
            "name": policy.name,
            "action": policy.action.value,
        },
    }
