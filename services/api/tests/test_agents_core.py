"""Golden tests for agents core components (planner, executor, registry)."""

import pytest

from app.agents.executor import Executor
from app.agents.planner import Planner
from app.agents.registry import AgentRegistry


def test_planner_deterministic():
    """Test that planner creates consistent plans."""
    planner = Planner()
    
    plan = planner.plan(
        "warehouse.health",
        "check parity",
        {"dry_run": True, "tools": ["es", "bq"]}
    )
    
    assert plan["agent"] == "warehouse.health"
    assert plan["objective"] == "check parity"
    assert plan["dry_run"] is True
    assert plan["steps"] == ["validate", "prepare_tools", "act", "summarize"]
    assert plan["tools"] == ["es", "bq"]


def test_planner_default_dry_run():
    """Test that planner defaults to dry_run=True."""
    planner = Planner()
    
    plan = planner.plan("test.agent", "test objective", {})
    
    assert plan["dry_run"] is True


def test_executor_success():
    """Test successful execution."""
    store = {}
    executor = Executor(store)
    
    plan = {"agent": "test", "objective": "succeed"}
    
    def success_handler(p):
        return {"result": "success", "data": 42}
    
    run = executor.execute(plan, success_handler)
    
    assert run["status"] == "succeeded"
    assert run["artifacts"]["result"] == "success"
    assert run["artifacts"]["data"] == 42
    assert run["run_id"] in store
    assert "start agent=test" in run["logs"][0]


def test_executor_failure():
    """Test execution failure handling."""
    store = {}
    executor = Executor(store)
    
    plan = {"agent": "test", "objective": "fail"}
    
    def failing_handler(p):
        raise ValueError("Intentional test failure")
    
    run = executor.execute(plan, failing_handler)
    
    assert run["status"] == "failed"
    assert "error:" in run["logs"][1]
    assert "ValueError" in run["logs"][1]


def test_executor_stores_run():
    """Test that executor stores run in run_store."""
    store = {}
    executor = Executor(store)
    
    plan = {"agent": "test", "objective": "store"}
    run = executor.execute(plan, lambda p: {})
    
    assert run["run_id"] in store
    assert store[run["run_id"]] == run


def test_registry_register_and_get():
    """Test agent registration and retrieval."""
    registry = AgentRegistry()
    
    def test_handler(plan):
        return {"test": True}
    
    registry.register("test.agent", test_handler)
    
    handler = registry.get("test.agent")
    assert handler == test_handler
    assert handler({})["test"] is True


def test_registry_list():
    """Test listing registered agents."""
    registry = AgentRegistry()
    
    registry.register("agent.one", lambda p: {})
    registry.register("agent.two", lambda p: {})
    registry.register("agent.three", lambda p: {})
    
    agents = registry.list()
    
    assert agents == ["agent.one", "agent.three", "agent.two"]  # Sorted
    assert len(agents) == 3


def test_registry_get_unknown_agent():
    """Test that getting unknown agent raises KeyError."""
    registry = AgentRegistry()
    
    with pytest.raises(KeyError, match="unknown agent: nonexistent"):
        registry.get("nonexistent")


def test_registry_empty_list():
    """Test listing when no agents registered."""
    registry = AgentRegistry()
    
    assert registry.list() == []
