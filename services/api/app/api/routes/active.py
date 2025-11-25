"""Active Learning API routes.

Endpoints for labeled data, training, bundles, approvals, canaries, and review queue.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db import get_db
from app.active.feeds import FeedLoader, load_all_feeds
from app.active.weights import JudgeWeights, nightly_update_weights
from app.active.sampler import UncertaintySampler
from app.active.bundles import BundleManager
from app.active.guards import OnlineLearningGuard
from app.models import AgentApproval

router = APIRouter(prefix="/api/active", tags=["active_learning"])


# ============================================================================
# Pydantic Models
# ============================================================================


class LabeledStatsResponse(BaseModel):
    total: int
    by_source: dict
    by_agent: dict
    recent_7d: int


class BundleCreateRequest(BaseModel):
    agent: str
    min_examples: int = 50
    model_type: str = "logistic"


class BundleCreateResponse(BaseModel):
    bundle_id: str
    agent: str
    training_count: int
    accuracy: float
    thresholds: dict


class BundleProposeRequest(BaseModel):
    agent: str
    bundle_id: str
    proposer: str = "system"


class BundleProposeResponse(BaseModel):
    approval_id: str


class ApprovalActionRequest(BaseModel):
    approver: str
    rationale: Optional[str] = None


class ApprovalActionResponse(BaseModel):
    status: str
    message: str


class BundleApplyRequest(BaseModel):
    canary_percent: Optional[int] = None


class BundleApplyResponse(BaseModel):
    status: str
    canary_percent: Optional[int] = None


class CanaryPerformanceResponse(BaseModel):
    has_regression: bool
    quality_delta: float
    latency_delta: float
    recommendation: str
    reason: str


class CanaryPromoteRequest(BaseModel):
    target_percent: int = 100


class ReviewQueueStatsResponse(BaseModel):
    total_unlabeled: int
    by_agent: dict
    total_eval_results: int
    total_labeled: int


# ============================================================================
# Labeled Data Endpoints
# ============================================================================


@router.get("/stats/labeled", response_model=LabeledStatsResponse)
def get_labeled_stats(db: Session = Depends(get_db)):
    """Get statistics on labeled training data."""
    loader = FeedLoader(db)
    stats = loader.get_stats()
    return stats


@router.post("/feeds/load")
def load_feeds(db: Session = Depends(get_db)):
    """Manually trigger feed loading from all sources."""
    counts = load_all_feeds(db)
    return {"status": "success", "counts": counts, "total": sum(counts.values())}


# ============================================================================
# Bundle Endpoints
# ============================================================================


@router.post("/bundles/create", response_model=BundleCreateResponse)
def create_bundle(request: BundleCreateRequest, db: Session = Depends(get_db)):
    """Train a new config bundle for an agent."""
    mgr = BundleManager(db)

    bundle = mgr.create_bundle(
        agent=request.agent,
        min_examples=request.min_examples,
        model_type=request.model_type,
    )

    if not bundle:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient training data for {request.agent}. Need at least {request.min_examples} labeled examples.",
        )

    return BundleCreateResponse(
        bundle_id=bundle["bundle_id"],
        agent=bundle["agent"],
        training_count=bundle["training_count"],
        accuracy=bundle["accuracy"],
        thresholds=bundle["thresholds"],
    )


@router.post("/bundles/propose", response_model=BundleProposeResponse)
def propose_bundle(request: BundleProposeRequest, db: Session = Depends(get_db)):
    """Propose a bundle for approval."""
    mgr = BundleManager(db)

    try:
        approval_id = mgr.propose_bundle(
            agent=request.agent, bundle_id=request.bundle_id, proposer=request.proposer
        )
        return BundleProposeResponse(approval_id=approval_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/bundles/{agent}/active")
def get_active_bundle(agent: str, db: Session = Depends(get_db)):
    """Get the currently active bundle for an agent."""
    mgr = BundleManager(db)
    bundle = mgr._load_active_bundle(agent)

    if not bundle:
        raise HTTPException(status_code=404, detail=f"No active bundle for {agent}")

    return bundle


# ============================================================================
# Approval Endpoints
# ============================================================================


@router.get("/approvals/pending")
def list_pending_approvals(db: Session = Depends(get_db)):
    """List all pending bundle approvals."""
    mgr = BundleManager(db)
    return mgr.list_pending_approvals()


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalActionResponse)
def approve_bundle(
    approval_id: str, request: ApprovalActionRequest, db: Session = Depends(get_db)
):
    """Approve a pending bundle."""
    mgr = BundleManager(db)

    try:
        mgr.approve_bundle(
            approval_id=approval_id,
            approver=request.approver,
            rationale=request.rationale,
        )
        return ApprovalActionResponse(
            status="approved",
            message=f"Bundle approval {approval_id} approved by {request.approver}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalActionResponse)
def reject_bundle(
    approval_id: str, request: ApprovalActionRequest, db: Session = Depends(get_db)
):
    """Reject a pending bundle."""
    approval = db.query(AgentApproval).filter_by(id=approval_id).first()

    if not approval:
        raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found")

    if approval.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Approval {approval_id} is not pending (status={approval.status})",
        )

    approval.status = "rejected"
    approval.approved_by = request.approver
    approval.rationale = request.rationale
    approval.approved_at = datetime.utcnow()

    db.commit()

    return ApprovalActionResponse(
        status="rejected",
        message=f"Bundle approval {approval_id} rejected by {request.approver}",
    )


@router.post("/approvals/{approval_id}/apply", response_model=BundleApplyResponse)
def apply_bundle(
    approval_id: str, request: BundleApplyRequest, db: Session = Depends(get_db)
):
    """Apply an approved bundle (with optional canary deployment)."""
    mgr = BundleManager(db)

    try:
        mgr.apply_approved_bundle(
            approval_id=approval_id, canary_percent=request.canary_percent
        )
        return BundleApplyResponse(
            status="deployed", canary_percent=request.canary_percent
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Canary Endpoints
# ============================================================================


@router.get("/canaries/active")
def list_active_canaries(db: Session = Depends(get_db)):
    """List all active canary deployments."""
    from app.models import RuntimeSetting

    canary_settings = (
        db.query(RuntimeSetting)
        .filter(RuntimeSetting.key.like("planner_canary.%.canary_percent"))
        .all()
    )

    active_canaries = []
    for setting in canary_settings:
        if int(setting.value) > 0:
            agent = setting.key.split(".")[1]

            # Get canary bundle
            canary_key = f"bundle.{agent}.canary"
            canary_setting = db.query(RuntimeSetting).filter_by(key=canary_key).first()

            if canary_setting:
                import json

                canary_bundle = json.loads(canary_setting.value)

                active_canaries.append(
                    {
                        "agent": agent,
                        "canary_percent": int(setting.value),
                        "deployed_at": canary_bundle.get("created_at"),
                        "bundle_id": canary_bundle.get("bundle_id"),
                    }
                )

    return active_canaries


@router.get("/canaries/{agent}/performance", response_model=CanaryPerformanceResponse)
def check_canary_performance(
    agent: str,
    lookback_hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """Check canary performance and get recommendation."""
    guard = OnlineLearningGuard(db)

    result = guard.check_canary_performance(agent=agent, lookback_hours=lookback_hours)

    return CanaryPerformanceResponse(**result)


@router.post("/canaries/{agent}/promote")
def promote_canary(
    agent: str, request: CanaryPromoteRequest, db: Session = Depends(get_db)
):
    """Promote canary to higher traffic percentage."""
    guard = OnlineLearningGuard(db)

    guard.promote_canary(agent=agent, target_percent=request.target_percent)

    return {
        "status": "promoted",
        "agent": agent,
        "target_percent": request.target_percent,
    }


@router.post("/canaries/{agent}/rollback")
def rollback_canary(agent: str, db: Session = Depends(get_db)):
    """Rollback canary deployment."""
    guard = OnlineLearningGuard(db)

    guard.rollback_canary(agent=agent)

    return {
        "status": "rolled_back",
        "agent": agent,
        "message": f"Canary for {agent} rolled back to active bundle",
    }


# ============================================================================
# Judge Weights Endpoints
# ============================================================================


@router.get("/weights")
def get_all_judge_weights(db: Session = Depends(get_db)):
    """Get judge weights for all agents."""
    from app.models_al import LabeledExample

    # Get distinct agents
    agents = db.query(LabeledExample.agent).distinct().all()
    agents = [a[0] for a in agents]

    weights_mgr = JudgeWeights(db)
    results = {}

    for agent in agents:
        results[agent] = weights_mgr.get_weights(agent)

    return results


@router.get("/weights/{agent}")
def get_judge_weights(agent: str, db: Session = Depends(get_db)):
    """Get judge weights for a specific agent."""
    weights_mgr = JudgeWeights(db)
    return weights_mgr.get_weights(agent)


@router.post("/weights/update")
def update_judge_weights(
    lookback_days: int = Query(30, ge=7, le=90), db: Session = Depends(get_db)
):
    """Manually trigger judge weight update for all agents."""
    results = nightly_update_weights(db)

    return {"status": "success", "updated_agents": len(results), "weights": results}


# ============================================================================
# Review Queue Endpoints
# ============================================================================


@router.get("/review/queue")
def get_review_queue(
    agent: Optional[str] = None,
    top_n: int = Query(50, ge=1, le=500),
    min_uncertainty: float = Query(0.5, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    """Get uncertain predictions for human review."""
    sampler = UncertaintySampler(db)

    if agent:
        candidates = sampler.sample_for_review(
            agent=agent, top_n=top_n, min_uncertainty=min_uncertainty
        )
        return {"agent": agent, "candidates": candidates}
    else:
        candidates = sampler.sample_all_agents(
            top_n_per_agent=top_n, min_uncertainty=min_uncertainty
        )
        return {"candidates": candidates}


@router.get("/review/stats", response_model=ReviewQueueStatsResponse)
def get_review_queue_stats(db: Session = Depends(get_db)):
    """Get review queue statistics."""
    sampler = UncertaintySampler(db)
    stats = sampler.get_review_queue_stats()
    return stats


# ============================================================================
# Admin Endpoints
# ============================================================================


@router.post("/pause")
def pause_active_learning(
    reason: str = Query(..., description="Reason for pausing"),
    db: Session = Depends(get_db),
):
    """Pause active learning (stops all nightly jobs)."""
    from app.models import RuntimeSetting

    setting = RuntimeSetting(
        key="active_learning.paused", value="true", category="active_learning"
    )

    existing = db.query(RuntimeSetting).filter_by(key="active_learning.paused").first()
    if existing:
        existing.value = "true"
        existing.updated_at = datetime.utcnow()
    else:
        db.add(setting)

    # Store reason
    reason_setting = RuntimeSetting(
        key="active_learning.pause_reason", value=reason, category="active_learning"
    )

    existing_reason = (
        db.query(RuntimeSetting).filter_by(key="active_learning.pause_reason").first()
    )
    if existing_reason:
        existing_reason.value = reason
        existing_reason.updated_at = datetime.utcnow()
    else:
        db.add(reason_setting)

    db.commit()

    return {
        "status": "paused",
        "reason": reason,
        "message": "Active learning paused. Nightly jobs will not run.",
    }


@router.post("/resume")
def resume_active_learning(db: Session = Depends(get_db)):
    """Resume active learning."""
    from app.models import RuntimeSetting

    setting = db.query(RuntimeSetting).filter_by(key="active_learning.paused").first()

    if setting:
        setting.value = "false"
        setting.updated_at = datetime.utcnow()
        db.commit()

    return {
        "status": "resumed",
        "message": "Active learning resumed. Nightly jobs will run.",
    }


@router.get("/status")
def get_active_learning_status(db: Session = Depends(get_db)):
    """Get overall active learning system status."""
    from app.models import RuntimeSetting

    # Check if paused
    paused_setting = (
        db.query(RuntimeSetting).filter_by(key="active_learning.paused").first()
    )
    is_paused = paused_setting and paused_setting.value == "true"

    # Get labeled data stats
    loader = FeedLoader(db)
    labeled_stats = loader.get_stats()

    # Get active canaries
    canary_settings = (
        db.query(RuntimeSetting)
        .filter(RuntimeSetting.key.like("planner_canary.%.canary_percent"))
        .all()
    )
    active_canary_count = sum(1 for s in canary_settings if int(s.value) > 0)

    # Get pending approvals
    mgr = BundleManager(db)
    pending_approvals = len(mgr.list_pending_approvals())

    return {
        "is_paused": is_paused,
        "labeled_examples": labeled_stats["total"],
        "recent_7d_growth": labeled_stats["recent_7d"],
        "active_canaries": active_canary_count,
        "pending_approvals": pending_approvals,
    }
