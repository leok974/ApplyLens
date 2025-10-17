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


def record_agent_run(agent: str, status: str, duration_ms: float) -> None:
    """Record metrics for an agent run.
    
    Args:
        agent: Agent name
        status: Run status (succeeded, failed, canceled)
        duration_ms: Execution duration in milliseconds
    """
    agent_runs_total.labels(agent=agent, status=status).inc()
    agent_run_latency_ms.labels(agent=agent).observe(duration_ms)
