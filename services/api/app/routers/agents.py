"""Agent API endpoints."""

from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, HTTPException

from ..agents.audit import get_auditor
from ..agents.executor import Executor
from ..agents.planner import Planner
from ..agents.registry import AgentRegistry
from ..schemas.agents import AgentRunRequest

router = APIRouter(prefix="/agents", tags=["agents"])

# Module-level storage and components
_run_store: Dict[str, dict] = {}
_registry = AgentRegistry()
_planner = Planner()
_auditor = get_auditor()
_executor = Executor(_run_store, _auditor)


@router.get("")
def list_agents():
    """List all registered agents.
    
    Returns:
        Dictionary with list of agent names
    """
    return {"agents": _registry.list()}


@router.post("/{name}/run")
def run_agent(name: str, body: AgentRunRequest):
    """Run an agent with the given objective.
    
    Args:
        name: Agent name
        body: Run request with objective and parameters
        
    Returns:
        Run result with status, logs, and artifacts
        
    Raises:
        HTTPException: If agent not found (404)
    """
    try:
        handler = _registry.get(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"agent not found: {name}")
    
    plan = _planner.plan(name, body.objective, body.model_dump())
    run = _executor.execute(
        plan, 
        handler,
        budget_ms=body.budget_ms,
        budget_ops=body.budget_ops,
        budget_cost_cents=body.budget_cost_cents,
        allow_actions=body.allow_actions
    )
    return run


@router.get("/{name}/runs")
def list_runs(name: str):
    """List all runs for a specific agent.
    
    Args:
        name: Agent name
        
    Returns:
        Dictionary with list of runs for this agent
    """
    # Filter runs by agent name (extracted from first log entry)
    agent_runs = [
        r for r in _run_store.values() 
        if r["logs"] and r["logs"][0].startswith(f"start agent={name}")
    ]
    return {"runs": agent_runs}


# Expose registry for agent registration
def get_registry() -> AgentRegistry:
    """Get the global agent registry.
    
    Returns:
        The agent registry instance
    """
    return _registry
