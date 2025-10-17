"""Prometheus metrics for agent system.

Tracks agent execution counts, latencies, and status distribution.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram


# Counter: Total agent runs by agent name and status
agent_runs_total = Counter(
    "agent_runs_total",
    "Total number of agent runs",
    ["agent", "status"]
)

# Histogram: Agent run latency in milliseconds
agent_run_latency_ms = Histogram(
    "agent_run_latency_ms",
    "Agent run execution latency in milliseconds",
    ["agent"],
    buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000)
)

# Phase 5.1: Planner canary metrics
planner_selection = Counter(
    "planner_selection_total",
    "Planner version selected for execution",
    ["planner", "reason"]  # planner=v1|v2, reason=default|canary|kill_switch
)

planner_diff = Counter(
    "planner_decision_diff_total",
    "Planner V1 vs V2 decision differences",
    ["agent_v1", "agent_v2", "changed"]  # changed=True|False
)


def record_agent_run(agent: str, status: str, duration_ms: float) -> None:
    """Record metrics for an agent run.
    
    Args:
        agent: Agent name
        status: Run status (succeeded, failed, canceled)
        duration_ms: Execution duration in milliseconds
    """
    agent_runs_total.labels(agent=agent, status=status).inc()
    agent_run_latency_ms.labels(agent=agent).observe(duration_ms)
