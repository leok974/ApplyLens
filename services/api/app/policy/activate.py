"""
Policy bundle activation logic with canary rollout and rollback.

Handles:
- Activation with approval gate
- Canary rollout (10% -> 100%)
- Quality gate monitoring
- Auto-promotion on success
- Auto-rollback on breach
- Incident creation for policy issues
"""

from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models_policy import PolicyBundle
from ..models import Incident, IncidentSeverity


class ActivationError(Exception):
    """Raised when activation fails validation."""

    pass


class CanaryGate:
    """Quality gates for canary promotion."""

    def __init__(
        self,
        max_error_rate: float = 0.05,  # 5% error rate
        max_deny_rate: float = 0.30,  # 30% deny rate
        max_cost_increase: float = 0.20,  # 20% cost increase
        min_sample_size: int = 100,  # Minimum decisions
    ):
        self.max_error_rate = max_error_rate
        self.max_deny_rate = max_deny_rate
        self.max_cost_increase = max_cost_increase
        self.min_sample_size = min_sample_size

    def check(self, metrics: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if canary meets quality gates.

        Returns:
            (passed, failures) tuple
        """
        failures = []

        # Check sample size
        total = metrics.get("total_decisions", 0)
        if total < self.min_sample_size:
            failures.append(f"Insufficient samples: {total} < {self.min_sample_size}")

        # Check error rate
        errors = metrics.get("error_count", 0)
        error_rate = errors / total if total > 0 else 0
        if error_rate > self.max_error_rate:
            failures.append(
                f"Error rate too high: {error_rate:.2%} > {self.max_error_rate:.2%}"
            )

        # Check deny rate
        denies = metrics.get("deny_count", 0)
        deny_rate = denies / total if total > 0 else 0
        if deny_rate > self.max_deny_rate:
            failures.append(
                f"Deny rate too high: {deny_rate:.2%} > {self.max_deny_rate:.2%}"
            )

        # Check cost increase vs baseline
        baseline_cost = metrics.get("baseline_avg_cost", 0)
        canary_cost = metrics.get("canary_avg_cost", 0)
        if baseline_cost > 0:
            cost_increase = (canary_cost - baseline_cost) / baseline_cost
            if cost_increase > self.max_cost_increase:
                failures.append(
                    f"Cost increase too high: {cost_increase:.2%} > {self.max_cost_increase:.2%}"
                )

        passed = len(failures) == 0
        return passed, failures


def activate_bundle(
    db: Session,
    bundle_id: int,
    approval_id: int,
    activated_by: str,
    canary_pct: int = 10,
) -> PolicyBundle:
    """
    Activate a policy bundle with canary rollout.

    Args:
        db: Database session
        bundle_id: ID of bundle to activate
        approval_id: Required approval ID from Phase 5.4
        activated_by: Username of activator
        canary_pct: Initial canary percentage (default 10%)

    Returns:
        Activated PolicyBundle

    Raises:
        ActivationError: If validation fails
    """
    # Get bundle
    bundle = db.query(PolicyBundle).filter(PolicyBundle.id == bundle_id).first()
    if not bundle:
        raise ActivationError(f"Bundle {bundle_id} not found")

    # Validate approval exists
    # In real implementation, would check Phase 5.4 approval status
    # For now, just check approval_id is provided
    if not approval_id:
        raise ActivationError("Approval required for activation")

    # Deactivate current active bundle
    current_active = db.query(PolicyBundle).filter(PolicyBundle.active).first()

    if current_active:
        current_active.active = False
        current_active.canary_pct = 0

    # Activate new bundle with canary
    bundle.active = True
    bundle.canary_pct = canary_pct
    bundle.activated_at = datetime.utcnow()
    bundle.activated_by = activated_by
    bundle.approval_id = approval_id

    db.commit()
    db.refresh(bundle)

    return bundle


def check_canary_gates(
    db: Session,
    bundle_id: int,
    metrics: Dict[str, Any],
    gate: Optional[CanaryGate] = None,
) -> Tuple[bool, List[str]]:
    """
    Check if canary should be promoted.

    Args:
        db: Database session
        bundle_id: ID of canary bundle
        metrics: Performance metrics from monitoring
        gate: Custom quality gate (uses default if None)

    Returns:
        (passed, failures) tuple
    """
    if gate is None:
        gate = CanaryGate()

    bundle = db.query(PolicyBundle).filter(PolicyBundle.id == bundle_id).first()
    if not bundle or not bundle.active:
        return False, ["Bundle not found or not active"]

    if bundle.canary_pct >= 100:
        return True, []  # Already fully promoted

    # Check quality gates
    passed, failures = gate.check(metrics)

    return passed, failures


def promote_canary(db: Session, bundle_id: int, target_pct: int = 100) -> PolicyBundle:
    """
    Promote canary to higher percentage.

    Args:
        db: Database session
        bundle_id: ID of bundle to promote
        target_pct: Target percentage (default 100%)

    Returns:
        Updated PolicyBundle

    Raises:
        ActivationError: If bundle not eligible for promotion
    """
    bundle = db.query(PolicyBundle).filter(PolicyBundle.id == bundle_id).first()
    if not bundle:
        raise ActivationError(f"Bundle {bundle_id} not found")

    if not bundle.active:
        raise ActivationError("Bundle not active")

    if bundle.canary_pct >= target_pct:
        raise ActivationError(f"Bundle already at {bundle.canary_pct}%")

    bundle.canary_pct = target_pct
    db.commit()
    db.refresh(bundle)

    return bundle


def rollback_bundle(
    db: Session,
    bundle_id: int,
    reason: str,
    rolled_back_by: str,
    create_incident: bool = True,
) -> PolicyBundle:
    """
    Rollback a bundle to previous version.

    Args:
        db: Database session
        bundle_id: ID of bundle to rollback
        reason: Reason for rollback
        rolled_back_by: Username initiating rollback
        create_incident: Whether to create incident

    Returns:
        Previous active bundle (now re-activated)

    Raises:
        ActivationError: If rollback fails
    """
    # Get current active bundle
    current = db.query(PolicyBundle).filter(PolicyBundle.id == bundle_id).first()
    if not current or not current.active:
        raise ActivationError("Bundle not currently active")

    # Find previous active version
    previous = (
        db.query(PolicyBundle)
        .filter(PolicyBundle.id != bundle_id, PolicyBundle.activated_at.isnot(None))
        .order_by(desc(PolicyBundle.activated_at))
        .first()
    )

    if not previous:
        raise ActivationError("No previous version to rollback to")

    # Deactivate current
    current.active = False
    current.canary_pct = 0

    # Reactivate previous
    previous.active = True
    previous.canary_pct = 100

    # Update metadata
    if previous.metadata is None:
        previous.metadata = {}

    previous.metadata["rollback"] = {
        "from_version": current.version,
        "reason": reason,
        "rolled_back_by": rolled_back_by,
        "rolled_back_at": datetime.utcnow().isoformat(),
    }

    db.commit()
    db.refresh(previous)

    # Create incident if requested
    if create_incident:
        incident = Incident(
            title=f"Policy rollback: {current.version} → {previous.version}",
            description=f"Reason: {reason}",
            severity=IncidentSeverity.HIGH,
            agent="policy.activate",
            action="rollback",
            context={
                "from_bundle_id": current.id,
                "from_version": current.version,
                "to_bundle_id": previous.id,
                "to_version": previous.version,
                "reason": reason,
                "rolled_back_by": rolled_back_by,
            },
            status="open",
            created_at=datetime.utcnow(),
        )
        db.add(incident)
        db.commit()

    return previous


def get_canary_status(db: Session, bundle_id: int) -> Dict[str, Any]:
    """
    Get current canary status for a bundle.

    Args:
        db: Database session
        bundle_id: ID of bundle

    Returns:
        Status dictionary with canary info
    """
    bundle = db.query(PolicyBundle).filter(PolicyBundle.id == bundle_id).first()
    if not bundle:
        return {"error": "Bundle not found"}

    if not bundle.active:
        return {"error": "Bundle not active"}

    # Calculate time since activation
    time_active = None
    if bundle.activated_at:
        time_active = (datetime.utcnow() - bundle.activated_at).total_seconds()

    # Determine if promotion eligible (24h minimum canary)
    promotion_eligible = False
    if time_active and time_active >= 24 * 3600:  # 24 hours
        promotion_eligible = bundle.canary_pct < 100

    return {
        "bundle_id": bundle.id,
        "version": bundle.version,
        "active": bundle.active,
        "canary_pct": bundle.canary_pct,
        "activated_at": bundle.activated_at.isoformat()
        if bundle.activated_at
        else None,
        "activated_by": bundle.activated_by,
        "time_active_seconds": time_active,
        "promotion_eligible": promotion_eligible,
        "fully_promoted": bundle.canary_pct >= 100,
    }
