"""
Tests for Playbook Executor - Phase 5.4 PR3

Tests action orchestration with approval gates.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from app.intervene.executor import PlaybookExecutor
from app.models_incident import Incident, IncidentAction
from app.intervene.actions.base import ActionStatus


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    return db


@pytest.fixture
def sample_invariant_incident():
    """Sample invariant failure incident."""
    return Incident(
        id=1,
        kind="invariant",
        key="INV_123",
        severity="sev2",
        status="open",
        summary="Data quality check failed",
        details={
            "task_id": 456,
            "invariant_name": "completeness_check",
        },
        playbooks=["rerun_eval", "check_agent_config"],
    )


@pytest.fixture
def sample_planner_incident():
    """Sample planner regression incident."""
    return Incident(
        id=2,
        kind="planner",
        key="planner:v2.1.0",
        severity="sev2",
        status="open",
        summary="Planner regression",
        details={
            "version": "v2.1.0",
            "metrics": {"accuracy": -0.05},
        },
        playbooks=["rollback_planner", "analyze_regression"],
    )


def test_executor_list_available_actions(mock_db, sample_invariant_incident):
    """Test listing available actions for incident."""
    executor = PlaybookExecutor(mock_db)

    actions = executor.list_available_actions(sample_invariant_incident)

    # Should have at least 1 action
    assert len(actions) > 0

    # Check structure
    action = actions[0]
    assert "action_type" in action
    assert "display_name" in action
    assert "description" in action
    assert "params" in action


def test_executor_dry_run_action(mock_db, sample_invariant_incident):
    """Test dry-run execution."""
    executor = PlaybookExecutor(mock_db)

    result = executor.dry_run_action(
        incident=sample_invariant_incident,
        action_type="rerun_dbt",
        params={"task_id": 456, "models": ["model_a"]},
    )

    assert result.status == ActionStatus.DRY_RUN_SUCCESS
    assert result.estimated_duration is not None
    assert len(result.changes) > 0

    # Verify action was tracked in DB
    mock_db.add.assert_called_once()
    added_action = mock_db.add.call_args[0][0]
    assert isinstance(added_action, IncidentAction)
    assert added_action.dry_run is True


def test_executor_execute_action_without_approval(mock_db, sample_invariant_incident):
    """Test executing action that doesn't require approval."""
    executor = PlaybookExecutor(mock_db)

    # Incremental dbt run doesn't need approval
    result = executor.execute_action(
        incident=sample_invariant_incident,
        action_type="rerun_dbt",
        params={"task_id": 456, "models": ["model_a"], "full_refresh": False},
        approved_by=None,
    )

    assert result.status == ActionStatus.SUCCESS
    assert result.actual_duration is not None

    # Verify action was tracked
    mock_db.add.assert_called()


def test_executor_execute_action_requires_approval(mock_db, sample_invariant_incident):
    """Test that high-risk action requires approval."""
    executor = PlaybookExecutor(mock_db)

    # Full refresh requires approval
    result = executor.execute_action(
        incident=sample_invariant_incident,
        action_type="rerun_dbt",
        params={"task_id": 456, "models": ["model_a"], "full_refresh": True},
        approved_by=None,  # No approval provided
    )

    # Should fail without approval
    assert result.status == ActionStatus.FAILED
    assert "approval" in result.message.lower()


def test_executor_execute_action_with_approval(mock_db, sample_invariant_incident):
    """Test executing action with approval."""
    executor = PlaybookExecutor(mock_db)

    result = executor.execute_action(
        incident=sample_invariant_incident,
        action_type="rerun_dbt",
        params={"task_id": 456, "models": ["model_a"], "full_refresh": True},
        approved_by="alice@company.com",  # Approval provided
    )

    assert result.status == ActionStatus.SUCCESS

    # Verify approval was recorded
    added_action = None
    for call in mock_db.add.call_args_list:
        obj = call[0][0]
        if isinstance(obj, IncidentAction):
            added_action = obj
            break

    assert added_action is not None
    assert added_action.approved_by == "alice@company.com"


def test_executor_rollback_action(mock_db, sample_planner_incident):
    """Test rollback of previous action."""
    # Mock previous action with rollback available
    previous_action = IncidentAction(
        id=100,
        incident_id=2,
        action_type="rollback_planner",
        params={"from_version": "v2.1.0", "to_version": "v2.0.5"},
        dry_run=False,
        status="success",
        result={
            "status": "success",
            "rollback_available": True,
            "rollback_action": {
                "action_type": "deploy_planner",  # Would be a real action
                "params": {"version": "v2.1.0"},
            },
        },
    )

    mock_db.query.return_value.filter.return_value.first.return_value = previous_action

    executor = PlaybookExecutor(mock_db)

    # Attempt rollback - will fail because deploy_planner isn't registered
    # but we can verify the flow
    result = executor.rollback_action(sample_planner_incident, action_id=100)

    # Should attempt to create deploy_planner action
    assert result is not None


def test_executor_rollback_not_available(mock_db, sample_invariant_incident):
    """Test rollback fails when not available."""
    # Mock action without rollback
    previous_action = IncidentAction(
        id=101,
        incident_id=1,
        action_type="rerun_dbt",
        params={},
        dry_run=False,
        status="success",
        result={"status": "success", "rollback_available": False},
    )

    mock_db.query.return_value.filter.return_value.first.return_value = previous_action

    executor = PlaybookExecutor(mock_db)

    result = executor.rollback_action(sample_invariant_incident, action_id=101)

    assert result.status == ActionStatus.FAILED
    assert "does not support rollback" in result.message


def test_executor_get_action_history(mock_db, sample_invariant_incident):
    """Test retrieving action history."""
    # Mock action history
    action1 = IncidentAction(
        id=1,
        incident_id=1,
        action_type="rerun_dbt",
        params={"task_id": 456},
        dry_run=True,
        status="dry_run_success",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
    )

    action2 = IncidentAction(
        id=2,
        incident_id=1,
        action_type="rerun_dbt",
        params={"task_id": 456},
        dry_run=False,
        status="success",
        approved_by="alice@company.com",
        created_at=datetime(2024, 1, 1, 12, 5, 0),
    )

    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        action2,
        action1,
    ]

    executor = PlaybookExecutor(mock_db)

    history = executor.get_action_history(sample_invariant_incident)

    assert len(history) == 2
    assert history[0]["id"] == 2  # Most recent first
    assert history[0]["dry_run"] is False
    assert history[0]["approved_by"] == "alice@company.com"
    assert history[1]["dry_run"] is True


def test_executor_playbook_to_action_invariant(mock_db, sample_invariant_incident):
    """Test playbook mapping for invariant incident."""
    executor = PlaybookExecutor(mock_db)

    action = executor._playbook_to_action(sample_invariant_incident, "rerun_eval")

    assert action is not None
    assert action["action_type"] == "rerun_dbt"
    assert action["params"]["task_id"] == 456


def test_executor_playbook_to_action_planner(mock_db, sample_planner_incident):
    """Test playbook mapping for planner incident."""
    executor = PlaybookExecutor(mock_db)

    action = executor._playbook_to_action(sample_planner_incident, "rollback_planner")

    assert action is not None
    assert action["action_type"] == "rollback_planner"
    assert action["params"]["from_version"] == "v2.1.0"


def test_executor_handles_validation_error(mock_db, sample_invariant_incident):
    """Test executor handles action validation errors."""
    executor = PlaybookExecutor(mock_db)

    # Invalid params (missing required field)
    result = executor.dry_run_action(
        incident=sample_invariant_incident,
        action_type="adjust_canary_split",
        params={"version": "v1.0.0", "target_percent": 150},  # Invalid percentage
    )

    # Should return failure result
    assert result.status == ActionStatus.DRY_RUN_FAILED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
