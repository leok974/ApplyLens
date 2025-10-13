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
    ["policy_name"],
)

# Action execution counter
actions_executed = Counter(
    "actions_executed_total",
    "Total number of successfully executed actions",
    ["action_type", "outcome"],
)

# Action failure counter
actions_failed = Counter(
    "actions_failed_total",
    "Total number of failed action executions",
    ["action_type", "error_type"],
)

# Policy evaluation counter
policy_evaluations = Counter(
    "policy_evaluations_total",
    "Total number of policy evaluations",
    ["policy_name", "matched"],
)

# Phase 6: Personalization metrics
policy_fired_total = Counter(
    "policy_fired_total",
    "Total times a policy fired (created proposal)",
    ["policy_id", "user"],
)

policy_approved_total = Counter(
    "policy_approved_total",
    "Total times a policy proposal was approved",
    ["policy_id", "user"],
)

policy_rejected_total = Counter(
    "policy_rejected_total",
    "Total times a policy proposal was rejected",
    ["policy_id", "user"],
)

user_weight_updates = Counter(
    "user_weight_updates_total",
    "Total user weight updates from learning",
    ["user", "sign"],  # sign = "plus" or "minus"
)

ats_enriched_total = Counter(
    "ats_enriched_total", "Total emails enriched with ATS data"
)

# Export all metrics in a dictionary for easy access
METRICS = {
    "actions_proposed": actions_proposed,
    "actions_executed": actions_executed,
    "actions_failed": actions_failed,
    "policy_evaluations": policy_evaluations,
    # Phase 6
    "policy_fired_total": policy_fired_total,
    "policy_approved_total": policy_approved_total,
    "policy_rejected_total": policy_rejected_total,
    "user_weight_updates": user_weight_updates,
    "ats_enriched_total": ats_enriched_total,
}
