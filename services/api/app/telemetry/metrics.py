"""
Telemetry metrics for Phase 4 Agentic Actions.

Prometheus counters for tracking action proposals, executions, and failures.
These will automatically appear in the /metrics endpoint.
"""
from prometheus_client import Counter

# Action proposal counter
actions_proposed = Counter(
    "actions_proposed_total",
    "Total number of action proposals created",
    ["policy_name"]
)

# Action execution counter
actions_executed = Counter(
    "actions_executed_total",
    "Total number of successfully executed actions",
    ["action_type", "outcome"]
)

# Action failure counter
actions_failed = Counter(
    "actions_failed_total",
    "Total number of failed action executions",
    ["action_type", "error_type"]
)

# Policy evaluation counter
policy_evaluations = Counter(
    "policy_evaluations_total",
    "Total number of policy evaluations",
    ["policy_name", "matched"]
)

# Export all metrics in a dictionary for easy access
METRICS = {
    "actions_proposed": actions_proposed,
    "actions_executed": actions_executed,
    "actions_failed": actions_failed,
    "policy_evaluations": policy_evaluations,
}
