"""
Tests for Remediation Actions - Phase 5.4 PR3

Tests typed actions with dry-run and execution.
"""
import pytest
from app.intervene.actions.base import ActionRegistry, ActionStatus
from app.intervene.actions.dbt import RerunDbtAction, RefreshDbtDependenciesAction
from app.intervene.actions.elastic import RefreshSynonymsAction, ClearCacheAction
from app.intervene.actions.planner import RollbackPlannerAction, AdjustCanarySplitAction


def test_action_registry():
    """Test action registry contains all actions."""
    actions = ActionRegistry.list_actions()
    
    assert "rerun_dbt" in actions
    assert "refresh_synonyms" in actions
    assert "rollback_planner" in actions
    assert "adjust_canary_split" in actions


def test_rerun_dbt_action_dry_run():
    """Test dbt rerun dry-run."""
    action = RerunDbtAction(
        task_id=123,
        models=["model_a", "model_b"],
        full_refresh=False,
    )
    
    # Note: validation will fail without DB, but dry_run should work
    result = action.dry_run()
    
    assert result.status == ActionStatus.DRY_RUN_SUCCESS
    assert "model_a" in str(result.details)
    assert result.estimated_duration is not None
    assert result.estimated_cost is not None
    assert len(result.changes) > 0
    assert not result.rollback_available


def test_rerun_dbt_full_refresh_requires_approval():
    """Test that full refresh requires approval."""
    action = RerunDbtAction(
        task_id=123,
        models=["model_a"],
        full_refresh=True,
    )
    
    assert action.get_approval_required() is True
    
    # Incremental doesn't require approval
    action2 = RerunDbtAction(
        task_id=123,
        models=["model_a"],
        full_refresh=False,
    )
    
    assert action2.get_approval_required() is False


def test_refresh_dbt_dependencies():
    """Test dbt dependency refresh."""
    action = RefreshDbtDependenciesAction(project_path="/opt/dbt")
    
    result = action.dry_run()
    
    assert result.status == ActionStatus.DRY_RUN_SUCCESS
    assert "dbt deps" in str(result.changes)
    assert action.get_approval_required() is False


def test_refresh_synonyms_action():
    """Test Elasticsearch synonym refresh."""
    action = RefreshSynonymsAction(
        index_name="applications",
        synonym_filter="job_title_synonyms",
        reindex=False,
    )
    
    result = action.dry_run()
    
    assert result.status == ActionStatus.DRY_RUN_SUCCESS
    assert "applications" in result.message
    assert result.estimated_duration == "30s"
    
    # Without reindex, no approval needed
    assert action.get_approval_required() is False


def test_refresh_synonyms_with_reindex_requires_approval():
    """Test that reindex requires approval."""
    action = RefreshSynonymsAction(
        index_name="applications",
        reindex=True,
    )
    
    result = action.dry_run()
    
    assert result.status == ActionStatus.DRY_RUN_SUCCESS
    assert "reindex" in str(result.changes).lower()
    assert result.estimated_cost > 0
    assert action.get_approval_required() is True


def test_clear_cache_action():
    """Test cache clear action."""
    action = ClearCacheAction(
        index_name="applications",
        cache_types=["query", "request"],
    )
    
    result = action.dry_run()
    
    assert result.status == ActionStatus.DRY_RUN_SUCCESS
    assert "query" in str(result.details)
    assert action.get_approval_required() is False


def test_rollback_planner_action():
    """Test planner rollback."""
    action = RollbackPlannerAction(
        from_version="v2.1.0",
        to_version="v2.0.5",
        immediate=False,
    )
    
    result = action.dry_run()
    
    assert result.status == ActionStatus.DRY_RUN_SUCCESS
    assert "v2.1.0" in result.message
    assert "v2.0.5" in result.message
    assert result.rollback_available is True
    assert result.rollback_action is not None
    
    # Gradual rollback doesn't require approval
    assert action.get_approval_required() is False


def test_rollback_planner_immediate_requires_approval():
    """Test immediate rollback requires approval."""
    action = RollbackPlannerAction(
        from_version="v2.1.0",
        immediate=True,
    )
    
    assert action.get_approval_required() is True


def test_adjust_canary_split():
    """Test canary split adjustment."""
    action = AdjustCanarySplitAction(
        version="v2.1.0",
        target_percent=5,
        gradual=True,
    )
    
    result = action.dry_run()
    
    assert result.status == ActionStatus.DRY_RUN_SUCCESS
    assert "5%" in result.message or "5" in str(result.details)
    assert result.rollback_available is True


def test_adjust_canary_split_validation():
    """Test canary split validates percentage."""
    # Invalid percentage
    with pytest.raises(ValueError, match="between 0 and 100"):
        action = AdjustCanarySplitAction(
            version="v2.1.0",
            target_percent=150,
        )
        action.validate()


def test_action_to_dict():
    """Test action serialization."""
    action = RerunDbtAction(
        task_id=123,
        models=["model_a"],
    )
    
    data = action.to_dict()
    
    assert data["action_type"] == "RerunDbtAction"
    assert data["params"]["task_id"] == 123
    assert "model_a" in data["params"]["models"]


def test_action_from_dict():
    """Test action deserialization."""
    data = {
        "action_type": "RerunDbtAction",
        "params": {
            "task_id": 123,
            "models": ["model_a"],
            "full_refresh": False,
        }
    }
    
    action = RerunDbtAction.from_dict(data)
    
    assert action.task_id == 123
    assert action.models == ["model_a"]
    assert action.full_refresh is False


def test_action_result_to_dict():
    """Test ActionResult serialization."""
    from app.intervene.actions.base import ActionResult
    
    result = ActionResult(
        status=ActionStatus.DRY_RUN_SUCCESS,
        message="Test result",
        details={"key": "value"},
        estimated_duration="5m",
        estimated_cost=1.50,
        changes=["change1", "change2"],
    )
    
    data = result.to_dict()
    
    assert data["status"] == "dry_run_success"
    assert data["message"] == "Test result"
    assert data["estimated_cost"] == 1.50
    assert len(data["changes"]) == 2


def test_action_impact_assessment():
    """Test impact assessment for approval UI."""
    action = RerunDbtAction(
        task_id=123,
        models=["model_a"],
        full_refresh=True,
    )
    
    impact = action.get_estimated_impact()
    
    assert impact["risk_level"] == "high"
    assert "dbt" in impact["affected_systems"]
    assert impact["models_affected"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
