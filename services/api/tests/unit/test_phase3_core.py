"""Unit tests for Phase 3 core features (budgets, approvals, artifacts).

These tests run standalone without database or conftest fixtures.
Run with: python -m pytest tests/unit/test_phase3_core.py -v
"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.utils.approvals import Approvals
from app.utils.artifacts import ArtifactsStore
from app.agents.executor import Executor


def test_approvals_allow_readonly_actions():
    """Readonly actions should always be allowed."""
    readonly_actions = ["query", "fetch", "read", "get", "list", "search"]

    for action in readonly_actions:
        assert Approvals.allow("test_agent", action, {}) is True
        assert Approvals.allow("test_agent", action.upper(), {}) is True
    print(" Readonly actions test PASSED")


def test_approvals_deny_highrisk_actions():
    """High-risk actions should be denied by default in Phase 3."""
    highrisk_actions = ["quarantine", "delete", "purge", "drop"]

    for action in highrisk_actions:
        assert Approvals.allow("test_agent", action, {}) is False
        assert Approvals.allow("test_agent", action.upper(), {}) is False
    print("✓ High-risk actions test PASSED")


def test_approvals_check_size_limits():
    """Actions exceeding size limits should be denied."""
    # Size under limit - should allow
    context = {"size": 100, "size_limit": 1000}
    assert Approvals.allow("test_agent", "update", context) is True

    # Size over limit - should deny
    context = {"size": 1500, "size_limit": 1000}
    assert Approvals.allow("test_agent", "update", context) is False
    print("✓ Size limits test PASSED")


def test_approvals_check_budget():
    """Test budget checking logic."""
    # Time budget not exceeded
    result = Approvals.check_budget(500, 10, 1000, 20)
    assert result["exceeded"] is False
    assert result["time_exceeded"] is False
    assert result["ops_exceeded"] is False

    # Time budget exceeded
    result = Approvals.check_budget(1500, 10, 1000, 20)
    assert result["exceeded"] is True
    assert result["time_exceeded"] is True

    # Ops budget exceeded
    result = Approvals.check_budget(500, 25, 1000, 20)
    assert result["exceeded"] is True
    assert result["ops_exceeded"] is True
    print("✓ Budget checking test PASSED")


def test_artifacts_write_and_read():
    """Test writing and reading artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactsStore(tmpdir)

        # Write text
        content = "# Test Report\n\nThis is a test."
        path = store.write("test.md", content)
        assert Path(path).exists()

        # Read back
        read_content = store.read("test.md")
        assert read_content == content
    print("✓ Artifacts write/read test PASSED")


def test_artifacts_json():
    """Test JSON artifact handling."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactsStore(tmpdir)

        # Write JSON
        data = {"added": ["rule1"], "removed": ["rule2"]}
        path = store.write_json("diff.json", data)
        assert Path(path).exists()

        # Read back
        read_data = store.read_json("diff.json")
        assert read_data == data
    print("✓ Artifacts JSON test PASSED")


def test_artifacts_with_agent_name():
    """Test agent-specific artifact paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactsStore(tmpdir)

        content = "Test content"
        path = store.write("report.md", content, agent_name="test_agent")

        assert Path(path).exists()
        assert "test_agent" in path
    print("✓ Artifacts agent naming test PASSED")


def test_artifacts_list_files():
    """Test listing artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactsStore(tmpdir)

        store.write("file1.txt", "content1", agent_name="agent1")
        store.write("file2.txt", "content2", agent_name="agent1")

        files = store.list_files(agent_name="agent1")
        assert len(files) == 2
    print("✓ Artifacts listing test PASSED")


def test_executor_allow_actions_gate():
    """Test executor enforces allow_actions gate."""
    run_store = {}
    executor = Executor(run_store, auditor=None, event_bus_enabled=False)

    def handler(plan):
        return {"result": "done"}

    plan = {
        "agent": "test_agent",
        "objective": "test objective",
        "dry_run": False,  # Actions mode
    }

    # Should fail without allow_actions
    run = executor.execute(plan, handler, allow_actions=False)
    assert run["status"] == "failed"
    assert "allow_actions" in " ".join(run["logs"]).lower()

    # Should succeed with allow_actions
    run = executor.execute(plan, handler, allow_actions=True)
    assert run["status"] == "succeeded"
    print("✓ Executor allow_actions gate test PASSED")


def test_executor_dry_run_always_allowed():
    """Test executor allows dry_run regardless of allow_actions."""
    run_store = {}
    executor = Executor(run_store, auditor=None, event_bus_enabled=False)

    def handler(plan):
        return {"result": "done"}

    plan = {"agent": "test_agent", "objective": "test objective", "dry_run": True}

    # Should succeed even without allow_actions
    run = executor.execute(plan, handler, allow_actions=False)
    assert run["status"] == "succeeded"
    print("✓ Executor dry_run test PASSED")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Phase 3 Core Features - Unit Tests")
    print("=" * 70 + "\n")

    print("Testing Approvals...")
    test_approvals_allow_readonly_actions()
    test_approvals_deny_highrisk_actions()
    test_approvals_check_size_limits()
    test_approvals_check_budget()

    print("\nTesting ArtifactsStore...")
    test_artifacts_write_and_read()
    test_artifacts_json()
    test_artifacts_with_agent_name()
    test_artifacts_list_files()

    print("\nTesting Executor...")
    test_executor_allow_actions_gate()
    test_executor_dry_run_always_allowed()

    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED")
    print("=" * 70 + "\n")
