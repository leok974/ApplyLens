"""
Tests for incident lifecycle - Phase 5.4 PR1

Tests incident creation, state transitions, and watcher logic.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.models_incident import Incident, IncidentAction
from app.intervene.watcher import InvariantWatcher


def test_incident_creation(db_session):
    """Test creating a basic incident."""
    incident = Incident(
        kind="invariant",
        key="INV_PHISHING_001",
        severity="sev2",
        status="open",
        summary="Phishing detection failed",
        details={"agent": "inbox.triage", "task_id": "test_123"},
        playbooks=["rerun_eval"],
    )
    
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)
    
    assert incident.id is not None
    assert incident.kind == "invariant"
    assert incident.status == "open"
    assert incident.created_at is not None


def test_incident_state_transitions(db_session):
    """Test incident lifecycle state machine."""
    incident = Incident(
        kind="budget",
        key="budget.planner.daily",
        severity="sev2",
        status="open",
        summary="Budget exceeded",
        details={"spent": 150, "limit": 100},
    )
    
    db_session.add(incident)
    db_session.commit()
    
    # open → acknowledged
    incident.status = "acknowledged"
    incident.acknowledged_at = datetime.utcnow()
    db_session.commit()
    assert incident.acknowledged_at is not None
    
    # acknowledged → mitigated
    incident.status = "mitigated"
    incident.mitigated_at = datetime.utcnow()
    db_session.commit()
    assert incident.mitigated_at is not None
    
    # mitigated → resolved
    incident.status = "resolved"
    incident.resolved_at = datetime.utcnow()
    db_session.commit()
    assert incident.resolved_at is not None
    
    # resolved → closed
    incident.status = "closed"
    incident.closed_at = datetime.utcnow()
    db_session.commit()
    assert incident.closed_at is not None


def test_incident_to_dict(db_session):
    """Test incident serialization."""
    incident = Incident(
        kind="planner",
        key="planner:v2",
        severity="sev1",
        status="open",
        summary="Planner regression detected",
        details={"version": "v2", "metric_drop": 0.15},
        playbooks=["rollback_planner"],
    )
    
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)
    
    data = incident.to_dict()
    
    assert data["id"] == incident.id
    assert data["kind"] == "planner"
    assert data["severity"] == "sev1"
    assert data["status"] == "open"
    assert data["playbooks"] == ["rollback_planner"]
    assert "version" in data["details"]


def test_incident_action_creation(db_session):
    """Test creating incident actions."""
    # Create incident
    incident = Incident(
        kind="invariant",
        key="INV_TEST",
        severity="sev3",
        status="open",
        summary="Test incident",
        details={},
    )
    db_session.add(incident)
    db_session.commit()
    
    # Create action
    action = IncidentAction(
        incident_id=incident.id,
        action_type="playbook",
        action_name="rerun_dbt",
        parameters={"models": ["inbox_features"]},
        executed_by="admin@example.com",
        dry_run=True,
        status="success",
        result={"affected_rows": 1234},
    )
    
    db_session.add(action)
    db_session.commit()
    db_session.refresh(action)
    
    assert action.id is not None
    assert action.incident_id == incident.id
    assert action.dry_run is True
    assert action.status == "success"


def test_watcher_deduplication(db_session):
    """Test that watcher doesn't create duplicate incidents."""
    watcher = InvariantWatcher(db_session)
    
    # Create existing open incident
    existing = Incident(
        kind="invariant",
        key="INV_TEST_001",
        severity="sev3",
        status="open",
        summary="Test",
        details={},
    )
    db_session.add(existing)
    db_session.commit()
    
    # Check deduplication
    has_open = watcher._has_open_incident("invariant", "INV_TEST_001")
    assert has_open is True
    
    has_open_other = watcher._has_open_incident("invariant", "INV_OTHER")
    assert has_open_other is False


def test_watcher_rate_limiting(db_session):
    """Test that watcher rate limits incident creation."""
    watcher = InvariantWatcher(db_session)
    
    # Create 3 recent incidents (within rate limit window)
    for i in range(3):
        incident = Incident(
            kind="budget",
            key="budget.test",
            severity="sev3",
            status="closed",
            summary=f"Test {i}",
            details={},
            created_at=datetime.utcnow() - timedelta(minutes=30),
        )
        db_session.add(incident)
    db_session.commit()
    
    # Should be rate limited
    is_limited = watcher._is_rate_limited("budget", "budget.test", hours=1)
    assert is_limited is True
    
    # Different key should not be rate limited
    is_limited_other = watcher._is_rate_limited("budget", "budget.other", hours=1)
    assert is_limited_other is False


def test_watcher_check_invariants_no_failures(db_session):
    """Test watcher with no invariant failures."""
    watcher = InvariantWatcher(db_session)
    
    incidents = watcher.check_invariants(lookback_minutes=60)
    
    # Should create no incidents if no failures
    assert len(incidents) == 0


def test_watcher_severity_mapping(db_session):
    """Test that watcher maps invariant priority to incident severity."""
    watcher = InvariantWatcher(db_session)
    
    # Mock eval result with critical invariant failure
    mock_eval_result = Mock()
    mock_eval_result.id = 123
    mock_eval_result.agent = "inbox.triage"
    mock_eval_result.task_id = "test_001"
    mock_eval_result.created_at = datetime.utcnow()
    
    inv_result = {
        "invariant_id": "CRITICAL_TEST",
        "name": "Critical Test Invariant",
        "passed": False,
        "priority": "critical",
        "message": "Test failure",
        "evidence": {},
    }
    
    incident = watcher._create_invariant_incident(mock_eval_result, inv_result)
    
    assert incident.severity == "sev1"  # critical → sev1
    assert incident.kind == "invariant"
    assert "CRITICAL_TEST" in incident.key


def test_watcher_budget_overage(db_session):
    """Test watcher detects budget overages."""
    watcher = InvariantWatcher(db_session)
    
    budget_data = {
        "spent": 150.0,
        "limit": 100.0,
    }
    
    incident = watcher._create_budget_incident("budget.test.daily", budget_data)
    
    assert incident.kind == "budget"
    assert incident.severity == "sev2"
    assert incident.details["overage"] == 50.0
    assert incident.details["overage_pct"] == 50.0
    assert "reduce_traffic" in incident.playbooks


def test_watcher_planner_regression(db_session):
    """Test watcher detects planner regressions."""
    watcher = InvariantWatcher(db_session)
    
    canary_data = {
        "status": "regressed",
        "metrics": {
            "accuracy": 0.85,
            "baseline_accuracy": 0.95,
        },
    }
    
    incident = watcher._create_planner_incident("v2_insights", canary_data)
    
    assert incident.kind == "planner"
    assert incident.key == "planner:v2_insights"
    assert incident.severity == "sev2"
    assert "rollback_planner" in incident.playbooks
    assert incident.details["rollback_available"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
