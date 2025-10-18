"""
Tests for policy bundle activation, canary, and rollback.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from httpx import AsyncClient

from app.models_policy import PolicyBundle
from app.models import Incident
from app.policy.activate import (
    activate_bundle,
    check_canary_gates,
    promote_canary,
    rollback_bundle,
    get_canary_status,
    ActivationError,
    CanaryGate
)


# Unit Tests - Activation Logic

class TestActivationLogic:
    """Test activation engine logic."""
    
    def test_activate_bundle_success(self, db: Session):
        """Test successful bundle activation."""
        # Create draft bundle
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "quarantine", "effect": "allow"}],
            notes="Test bundle",
            created_by="alice"
        )
        db.add(bundle)
        db.commit()
        
        # Activate
        activated = activate_bundle(
            db=db,
            bundle_id=bundle.id,
            approval_id=123,
            activated_by="bob",
            canary_pct=10
        )
        
        assert activated.active is True
        assert activated.canary_pct == 10
        assert activated.approval_id == 123
        assert activated.activated_by == "bob"
        assert activated.activated_at is not None
    
    def test_activate_deactivates_previous(self, db: Session):
        """Test activating new bundle deactivates previous."""
        # Create and activate first bundle
        bundle1 = PolicyBundle(
            version="1.0.0",
            rules=[{"id": "old", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=100
        )
        db.add(bundle1)
        db.commit()
        
        # Create and activate second bundle
        bundle2 = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "new", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice"
        )
        db.add(bundle2)
        db.commit()
        
        activate_bundle(
            db=db,
            bundle_id=bundle2.id,
            approval_id=456,
            activated_by="bob",
            canary_pct=10
        )
        
        # Refresh and check
        db.refresh(bundle1)
        assert bundle1.active is False
        assert bundle1.canary_pct == 0
    
    def test_activate_requires_approval(self, db: Session):
        """Test activation requires approval ID."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice"
        )
        db.add(bundle)
        db.commit()
        
        with pytest.raises(ActivationError, match="Approval required"):
            activate_bundle(
                db=db,
                bundle_id=bundle.id,
                approval_id=None,
                activated_by="bob"
            )
    
    def test_activate_nonexistent_bundle(self, db: Session):
        """Test activating non-existent bundle fails."""
        with pytest.raises(ActivationError, match="not found"):
            activate_bundle(
                db=db,
                bundle_id=99999,
                approval_id=123,
                activated_by="bob"
            )


class TestCanaryGates:
    """Test quality gate checks."""
    
    def test_gates_pass_with_good_metrics(self, db: Session):
        """Test gates pass with healthy metrics."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=10
        )
        db.add(bundle)
        db.commit()
        
        metrics = {
            "total_decisions": 200,
            "error_count": 5,      # 2.5% error rate
            "deny_count": 40,      # 20% deny rate
            "baseline_avg_cost": 10.0,
            "canary_avg_cost": 11.0  # 10% increase
        }
        
        passed, failures = check_canary_gates(db=db, bundle_id=bundle.id, metrics=metrics)
        
        assert passed is True
        assert len(failures) == 0
    
    def test_gates_fail_high_error_rate(self, db: Session):
        """Test gates fail with high error rate."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=10
        )
        db.add(bundle)
        db.commit()
        
        metrics = {
            "total_decisions": 200,
            "error_count": 15,     # 7.5% error rate (exceeds 5%)
            "deny_count": 40,
            "baseline_avg_cost": 10.0,
            "canary_avg_cost": 11.0
        }
        
        passed, failures = check_canary_gates(db=db, bundle_id=bundle.id, metrics=metrics)
        
        assert passed is False
        assert any("Error rate" in f for f in failures)
    
    def test_gates_fail_high_deny_rate(self, db: Session):
        """Test gates fail with high deny rate."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=10
        )
        db.add(bundle)
        db.commit()
        
        metrics = {
            "total_decisions": 200,
            "error_count": 5,
            "deny_count": 80,      # 40% deny rate (exceeds 30%)
            "baseline_avg_cost": 10.0,
            "canary_avg_cost": 11.0
        }
        
        passed, failures = check_canary_gates(db=db, bundle_id=bundle.id, metrics=metrics)
        
        assert passed is False
        assert any("Deny rate" in f for f in failures)
    
    def test_gates_fail_high_cost_increase(self, db: Session):
        """Test gates fail with high cost increase."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=10
        )
        db.add(bundle)
        db.commit()
        
        metrics = {
            "total_decisions": 200,
            "error_count": 5,
            "deny_count": 40,
            "baseline_avg_cost": 10.0,
            "canary_avg_cost": 15.0  # 50% increase (exceeds 20%)
        }
        
        passed, failures = check_canary_gates(db=db, bundle_id=bundle.id, metrics=metrics)
        
        assert passed is False
        assert any("Cost increase" in f for f in failures)
    
    def test_gates_fail_insufficient_samples(self, db: Session):
        """Test gates fail with insufficient sample size."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=10
        )
        db.add(bundle)
        db.commit()
        
        metrics = {
            "total_decisions": 50,  # Less than 100
            "error_count": 2,
            "deny_count": 10,
            "baseline_avg_cost": 10.0,
            "canary_avg_cost": 11.0
        }
        
        passed, failures = check_canary_gates(db=db, bundle_id=bundle.id, metrics=metrics)
        
        assert passed is False
        assert any("Insufficient samples" in f for f in failures)


class TestPromotion:
    """Test canary promotion."""
    
    def test_promote_canary_success(self, db: Session):
        """Test successful canary promotion."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=10
        )
        db.add(bundle)
        db.commit()
        
        promoted = promote_canary(db=db, bundle_id=bundle.id, target_pct=50)
        
        assert promoted.canary_pct == 50
    
    def test_promote_to_100_percent(self, db: Session):
        """Test full promotion to 100%."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=50
        )
        db.add(bundle)
        db.commit()
        
        promoted = promote_canary(db=db, bundle_id=bundle.id, target_pct=100)
        
        assert promoted.canary_pct == 100
    
    def test_promote_inactive_bundle_fails(self, db: Session):
        """Test promoting inactive bundle fails."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=False,
            canary_pct=10
        )
        db.add(bundle)
        db.commit()
        
        with pytest.raises(ActivationError, match="not active"):
            promote_canary(db=db, bundle_id=bundle.id, target_pct=50)
    
    def test_promote_already_at_target_fails(self, db: Session):
        """Test promoting to current percentage fails."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=100
        )
        db.add(bundle)
        db.commit()
        
        with pytest.raises(ActivationError, match="already at"):
            promote_canary(db=db, bundle_id=bundle.id, target_pct=100)


class TestRollback:
    """Test rollback functionality."""
    
    def test_rollback_success(self, db: Session):
        """Test successful rollback to previous version."""
        # Create and activate first bundle
        bundle1 = PolicyBundle(
            version="1.0.0",
            rules=[{"id": "old", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=False,
            canary_pct=0,
            activated_at=datetime.utcnow() - timedelta(days=1),
            activated_by="alice"
        )
        db.add(bundle1)
        db.commit()
        
        # Create and activate second bundle
        bundle2 = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "new", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="bob",
            active=True,
            canary_pct=10,
            activated_at=datetime.utcnow(),
            activated_by="bob"
        )
        db.add(bundle2)
        db.commit()
        
        # Rollback
        previous = rollback_bundle(
            db=db,
            bundle_id=bundle2.id,
            reason="High error rate detected",
            rolled_back_by="charlie",
            create_incident=False
        )
        
        # Check rollback succeeded
        assert previous.id == bundle1.id
        assert previous.active is True
        assert previous.canary_pct == 100
        
        # Check current bundle deactivated
        db.refresh(bundle2)
        assert bundle2.active is False
        assert bundle2.canary_pct == 0
        
        # Check rollback metadata
        assert "rollback" in previous.metadata
        assert previous.metadata["rollback"]["from_version"] == "2.0.0"
        assert previous.metadata["rollback"]["reason"] == "High error rate detected"
    
    def test_rollback_creates_incident(self, db: Session):
        """Test rollback creates incident."""
        # Create previous and current bundles
        bundle1 = PolicyBundle(
            version="1.0.0",
            rules=[{"id": "old", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=False,
            activated_at=datetime.utcnow() - timedelta(days=1),
            activated_by="alice"
        )
        db.add(bundle1)
        
        bundle2 = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "new", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="bob",
            active=True,
            canary_pct=10,
            activated_at=datetime.utcnow(),
            activated_by="bob"
        )
        db.add(bundle2)
        db.commit()
        
        # Rollback with incident creation
        rollback_bundle(
            db=db,
            bundle_id=bundle2.id,
            reason="Quality gates failed",
            rolled_back_by="charlie",
            create_incident=True
        )
        
        # Check incident created
        incident = db.query(Incident).filter(
            Incident.agent == "policy.activate",
            Incident.action == "rollback"
        ).first()
        
        assert incident is not None
        assert "rollback" in incident.title.lower()
        assert incident.severity.value == "high"
        assert incident.context["from_version"] == "2.0.0"
        assert incident.context["to_version"] == "1.0.0"
    
    def test_rollback_inactive_bundle_fails(self, db: Session):
        """Test rolling back inactive bundle fails."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=False
        )
        db.add(bundle)
        db.commit()
        
        with pytest.raises(ActivationError, match="not currently active"):
            rollback_bundle(
                db=db,
                bundle_id=bundle.id,
                reason="Test",
                rolled_back_by="bob"
            )
    
    def test_rollback_no_previous_version_fails(self, db: Session):
        """Test rollback fails with no previous version."""
        bundle = PolicyBundle(
            version="1.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=100
        )
        db.add(bundle)
        db.commit()
        
        with pytest.raises(ActivationError, match="No previous version"):
            rollback_bundle(
                db=db,
                bundle_id=bundle.id,
                reason="Test",
                rolled_back_by="bob"
            )


class TestCanaryStatus:
    """Test canary status monitoring."""
    
    def test_get_canary_status(self, db: Session):
        """Test getting canary status."""
        activated_at = datetime.utcnow() - timedelta(hours=12)
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=10,
            activated_at=activated_at,
            activated_by="bob"
        )
        db.add(bundle)
        db.commit()
        
        status = get_canary_status(db=db, bundle_id=bundle.id)
        
        assert status["bundle_id"] == bundle.id
        assert status["version"] == "2.0.0"
        assert status["active"] is True
        assert status["canary_pct"] == 10
        assert status["activated_by"] == "bob"
        assert status["fully_promoted"] is False
        assert status["promotion_eligible"] is False  # Only 12h, need 24h
    
    def test_canary_status_promotion_eligible(self, db: Session):
        """Test canary eligible for promotion after 24h."""
        activated_at = datetime.utcnow() - timedelta(hours=25)
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=10,
            activated_at=activated_at,
            activated_by="bob"
        )
        db.add(bundle)
        db.commit()
        
        status = get_canary_status(db=db, bundle_id=bundle.id)
        
        assert status["promotion_eligible"] is True
    
    def test_canary_status_fully_promoted(self, db: Session):
        """Test fully promoted bundle status."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=100,
            activated_at=datetime.utcnow(),
            activated_by="bob"
        )
        db.add(bundle)
        db.commit()
        
        status = get_canary_status(db=db, bundle_id=bundle.id)
        
        assert status["fully_promoted"] is True
        assert status["promotion_eligible"] is False  # Already at 100%


# API Tests

@pytest.mark.asyncio
class TestActivationEndpoints:
    """Test activation REST API."""
    
    async def test_activate_bundle(self, async_client: AsyncClient, db: Session):
        """Test POST /policy/bundles/{id}/activate."""
        # Create draft bundle
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "quarantine", "effect": "allow"}],
            created_by="alice"
        )
        db.add(bundle)
        db.commit()
        
        response = await async_client.post(
            f"/policy/bundles/{bundle.id}/activate",
            json={
                "approval_id": 123,
                "activated_by": "bob",
                "canary_pct": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"
        assert data["active"] is True
        assert data["canary_pct"] == 10
        assert data["approval_id"] == 123
    
    async def test_check_gates(self, async_client: AsyncClient, db: Session):
        """Test POST /policy/bundles/{id}/check-gates."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=10
        )
        db.add(bundle)
        db.commit()
        
        response = await async_client.post(
            f"/policy/bundles/{bundle.id}/check-gates",
            json={
                "metrics": {
                    "total_decisions": 200,
                    "error_count": 5,
                    "deny_count": 40,
                    "baseline_avg_cost": 10.0,
                    "canary_avg_cost": 11.0
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["passed"] is True
        assert len(data["failures"]) == 0
    
    async def test_promote_bundle(self, async_client: AsyncClient, db: Session):
        """Test POST /policy/bundles/{id}/promote."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=10
        )
        db.add(bundle)
        db.commit()
        
        response = await async_client.post(
            f"/policy/bundles/{bundle.id}/promote",
            json={"target_pct": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["canary_pct"] == 50
    
    async def test_rollback_bundle(self, async_client: AsyncClient, db: Session):
        """Test POST /policy/bundles/{id}/rollback."""
        # Create previous and current bundles
        bundle1 = PolicyBundle(
            version="1.0.0",
            rules=[{"id": "old", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=False,
            activated_at=datetime.utcnow() - timedelta(days=1),
            activated_by="alice"
        )
        db.add(bundle1)
        
        bundle2 = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "new", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="bob",
            active=True,
            canary_pct=10,
            activated_at=datetime.utcnow(),
            activated_by="bob"
        )
        db.add(bundle2)
        db.commit()
        
        response = await async_client.post(
            f"/policy/bundles/{bundle2.id}/rollback",
            json={
                "reason": "High error rate detected during canary",
                "rolled_back_by": "charlie",
                "create_incident": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0.0"
        assert data["rolled_back_from"] == "2.0.0"
        assert data["incident_created"] is True
    
    async def test_get_canary_status(self, async_client: AsyncClient, db: Session):
        """Test GET /policy/bundles/{id}/canary-status."""
        bundle = PolicyBundle(
            version="2.0.0",
            rules=[{"id": "test", "agent": "inbox.triage", "action": "allow", "effect": "allow"}],
            created_by="alice",
            active=True,
            canary_pct=10,
            activated_at=datetime.utcnow(),
            activated_by="bob"
        )
        db.add(bundle)
        db.commit()
        
        response = await async_client.get(f"/policy/bundles/{bundle.id}/canary-status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["bundle_id"] == bundle.id
        assert data["version"] == "2.0.0"
        assert data["canary_pct"] == 10
        assert data["activated_by"] == "bob"
