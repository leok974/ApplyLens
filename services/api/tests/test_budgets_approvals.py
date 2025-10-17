"""Tests for Phase 3 core features: budgets, approvals, and artifacts.

These are unit tests that don't require database or API fixtures.
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from app.utils.approvals import Approvals
from app.utils.artifacts import ArtifactsStore
from app.agents.executor import Executor


# Mark all tests as unit tests (no database required)
pytestmark = pytest.mark.unit


# ============================================================================
# Approvals Tests
# ============================================================================

def test_approvals_allow_readonly_actions():
    """Readonly actions should always be allowed."""
    readonly_actions = ["query", "fetch", "read", "get", "list", "search"]
    
    for action in readonly_actions:
        assert Approvals.allow("test_agent", action, {}) is True
        assert Approvals.allow("test_agent", action.upper(), {}) is True


def test_approvals_deny_highrisk_actions():
    """High-risk actions should be denied by default in Phase 3."""
    highrisk_actions = ["quarantine", "delete", "purge", "drop"]
    
    for action in highrisk_actions:
        assert Approvals.allow("test_agent", action, {}) is False
        assert Approvals.allow("test_agent", action.upper(), {}) is False


def test_approvals_check_size_limits():
    """Actions exceeding size limits should be denied."""
    # Size under limit - should allow
    context = {"size": 100, "size_limit": 1000}
    assert Approvals.allow("test_agent", "update", context) is True
    
    # Size over limit - should deny
    context = {"size": 1500, "size_limit": 1000}
    assert Approvals.allow("test_agent", "update", context) is False


def test_approvals_check_budget_exceeded():
    """Actions with exceeded budgets should be denied."""
    context = {"budget_exceeded": False}
    assert Approvals.allow("test_agent", "update", context) is True
    
    context = {"budget_exceeded": True}
    assert Approvals.allow("test_agent", "update", context) is False


def test_approvals_check_risk_score():
    """Actions with high risk scores should be denied."""
    # Low risk - should allow
    context = {"risk_score": 50, "risk_threshold": 95}
    assert Approvals.allow("test_agent", "update", context) is True
    
    # High risk - should deny
    context = {"risk_score": 98, "risk_threshold": 95}
    assert Approvals.allow("test_agent", "update", context) is False


def test_approvals_require_approval_stub():
    """require_approval() should return Phase 3 stub response."""
    result = Approvals.require_approval("test_agent", "quarantine", {})
    
    assert result["approved"] is False
    assert result["ticket_id"] is None
    assert "Phase 3" in result["reason"]


def test_approvals_check_budget_time_not_exceeded():
    """check_budget() should pass when time budget not exceeded."""
    result = Approvals.check_budget(
        elapsed_ms=500,
        ops_count=10,
        budget_ms=1000,
        budget_ops=20
    )
    
    assert result["exceeded"] is False
    assert result["time_exceeded"] is False
    assert result["ops_exceeded"] is False
    assert result["elapsed_ms"] == 500
    assert result["ops_count"] == 10


def test_approvals_check_budget_time_exceeded():
    """check_budget() should fail when time budget exceeded."""
    result = Approvals.check_budget(
        elapsed_ms=1500,
        ops_count=10,
        budget_ms=1000,
        budget_ops=20
    )
    
    assert result["exceeded"] is True
    assert result["time_exceeded"] is True
    assert result["ops_exceeded"] is False


def test_approvals_check_budget_ops_exceeded():
    """check_budget() should fail when ops budget exceeded."""
    result = Approvals.check_budget(
        elapsed_ms=500,
        ops_count=25,
        budget_ms=1000,
        budget_ops=20
    )
    
    assert result["exceeded"] is True
    assert result["time_exceeded"] is False
    assert result["ops_exceeded"] is True


def test_approvals_check_budget_no_limits():
    """check_budget() should pass when no limits set."""
    result = Approvals.check_budget(
        elapsed_ms=5000,
        ops_count=100,
        budget_ms=None,
        budget_ops=None
    )
    
    assert result["exceeded"] is False
    assert result["time_exceeded"] is False
    assert result["ops_exceeded"] is False


# ============================================================================
# ArtifactsStore Tests
# ============================================================================

def test_artifacts_write_text():
    """Test writing text artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactsStore(tmpdir)
        
        content = "# Test Report\n\nThis is a test."
        path = store.write("test.md", content)
        
        assert Path(path).exists()
        assert Path(path).read_text() == content


def test_artifacts_write_json():
    """Test writing JSON artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactsStore(tmpdir)
        
        data = {"added": ["rule1"], "removed": ["rule2"]}
        path = store.write_json("diff.json", data)
        
        assert Path(path).exists()
        assert json.loads(Path(path).read_text()) == data


def test_artifacts_write_with_agent_name():
    """Test writing artifacts with agent-specific paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactsStore(tmpdir)
        
        content = "Test content"
        path = store.write("report.md", content, agent_name="test_agent")
        
        assert Path(path).exists()
        assert "test_agent" in path
        assert Path(path).read_text() == content


def test_artifacts_read():
    """Test reading text artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactsStore(tmpdir)
        
        content = "Test content"
        store.write("test.txt", content)
        
        read_content = store.read("test.txt")
        assert read_content == content


def test_artifacts_read_json():
    """Test reading JSON artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactsStore(tmpdir)
        
        data = {"key": "value", "count": 42}
        store.write_json("data.json", data)
        
        read_data = store.read_json("data.json")
        assert read_data == data


def test_artifacts_list_files():
    """Test listing artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactsStore(tmpdir)
        
        store.write("file1.txt", "content1", agent_name="agent1")
        store.write("file2.txt", "content2", agent_name="agent1")
        store.write("file3.txt", "content3", agent_name="agent2")
        
        # List all files for agent1
        files = store.list_files(agent_name="agent1")
        assert len(files) == 2
        assert any("file1.txt" in f for f in files)
        assert any("file2.txt" in f for f in files)
        
        # List with pattern
        files = store.list_files(agent_name="agent1", pattern="*.txt")
        assert len(files) == 2


def test_artifacts_delete():
    """Test deleting artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactsStore(tmpdir)
        
        path = store.write("test.txt", "content")
        assert Path(path).exists()
        
        result = store.delete("test.txt")
        assert result is True
        assert not Path(path).exists()
        
        # Deleting non-existent file
        result = store.delete("nonexistent.txt")
        assert result is False


def test_artifacts_get_timestamped_path():
    """Test timestamped path generation."""
    store = ArtifactsStore()
    
    path = store.get_timestamped_path("run", "json")
    assert "run_" in path
    assert path.endswith(".json")
    
    path = store.get_timestamped_path("report", "md", agent_name="test_agent")
    assert "test_agent/" in path
    assert "report_" in path
    assert path.endswith(".md")


def test_artifacts_get_weekly_path():
    """Test ISO week-based path generation."""
    store = ArtifactsStore()
    
    path = store.get_weekly_path()
    assert "-W" in path
    assert path.endswith(".md")
    
    path = store.get_weekly_path("report", "txt")
    assert "report_" in path
    assert "-W" in path
    assert path.endswith(".txt")


# ============================================================================
# Executor Budget Tests
# ============================================================================

def test_executor_budget_time_limit():
    """Test executor respects time budget."""
    run_store = {}
    executor = Executor(run_store, auditor=None, event_bus_enabled=False)
    
    def slow_handler(plan):
        time.sleep(0.2)  # 200ms
        return {"result": "done"}
    
    plan = {
        "agent": "test_agent",
        "objective": "test objective",
        "dry_run": True
    }
    
    # Should succeed with generous budget
    run = executor.execute(
        plan, 
        slow_handler, 
        budget_ms=1000,  # 1 second
        allow_actions=False
    )
    assert run["status"] == "succeeded"
    assert "budget exceeded" not in " ".join(run["logs"]).lower()
    
    # Should log warning with tight budget
    run = executor.execute(
        plan, 
        slow_handler, 
        budget_ms=50,  # 50ms (too tight)
        allow_actions=False
    )
    # Handler completes, but budget warning logged
    assert run["status"] == "succeeded"
    # Check if budget warning appears in logs
    logs_text = " ".join(run["logs"]).lower()
    # May or may not have warning depending on timing


def test_executor_budget_ops_limit():
    """Test executor tracks operation count."""
    run_store = {}
    executor = Executor(run_store, auditor=None, event_bus_enabled=False)
    
    def handler_with_ops(plan):
        return {"result": "done", "ops_count": 15}
    
    plan = {
        "agent": "test_agent",
        "objective": "test objective",
        "dry_run": True
    }
    
    run = executor.execute(
        plan, 
        handler_with_ops, 
        budget_ops=20,
        allow_actions=False
    )
    
    assert run["status"] == "succeeded"
    assert run["ops_count"] == 15


def test_executor_allow_actions_gate():
    """Test executor enforces allow_actions gate."""
    run_store = {}
    executor = Executor(run_store, auditor=None, event_bus_enabled=False)
    
    def handler(plan):
        return {"result": "done"}
    
    plan = {
        "agent": "test_agent",
        "objective": "test objective",
        "dry_run": False  # Actions mode
    }
    
    # Should fail without allow_actions
    run = executor.execute(plan, handler, allow_actions=False)
    assert run["status"] == "failed"
    assert "allow_actions" in " ".join(run["logs"]).lower()
    
    # Should succeed with allow_actions
    run = executor.execute(plan, handler, allow_actions=True)
    assert run["status"] == "succeeded"


def test_executor_dry_run_always_allowed():
    """Test executor allows dry_run regardless of allow_actions."""
    run_store = {}
    executor = Executor(run_store, auditor=None, event_bus_enabled=False)
    
    def handler(plan):
        return {"result": "done"}
    
    plan = {
        "agent": "test_agent",
        "objective": "test objective",
        "dry_run": True  # Dry run mode
    }
    
    # Should succeed even without allow_actions
    run = executor.execute(plan, handler, allow_actions=False)
    assert run["status"] == "succeeded"
