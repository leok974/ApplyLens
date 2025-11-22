"""
Agent v2 - Prometheus Metrics

Metrics for agent runs, tool calls, and performance.
"""

from prometheus_client import Counter, Histogram
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Metrics Definitions
# ============================================================================

# Agent runs (mailbox agent v2)
mailbox_agent_runs_total = Counter(
    "mailbox_agent_runs_total",
    "Mailbox agent runs",
    labelnames=("intent", "mode", "status"),
)

mailbox_agent_run_duration_seconds = Histogram(
    "mailbox_agent_run_duration_seconds",
    "Agent run duration in seconds",
    labelnames=("intent", "mode"),
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# Tool calls
mailbox_agent_tool_calls_total = Counter(
    "mailbox_agent_tool_calls_total",
    "Mailbox agent tool calls",
    labelnames=("tool", "status"),
)

mailbox_agent_tool_latency_seconds = Histogram(
    "mailbox_agent_tool_latency_seconds",
    "Latency of mailbox agent tools",
    labelnames=("tool",),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)

# RAG
mailbox_agent_rag_context_count = Counter(
    "mailbox_agent_rag_context_count",
    "Number of RAG contexts attached to runs",
    labelnames=("source",),  # emails | kb
)

# Redis
mailbox_agent_redis_hits_total = Counter(
    "mailbox_agent_redis_hits_total",
    "Redis hits/misses for agent caches",
    labelnames=("kind", "result"),  # kind=get/set, result=hit|miss
)

mailbox_agent_redis_errors_total = Counter(
    "mailbox_agent_redis_errors_total",
    "Redis errors for agent caches",
    labelnames=("kind",),  # get|set
)

mailbox_agent_redis_latency_seconds = Histogram(
    "mailbox_agent_redis_latency_seconds",
    "Redis latency for agent caches",
    labelnames=("kind",),
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1),
)


# ============================================================================
# Helper Functions
# ============================================================================


def record_agent_run(intent: str, mode: str, status: str, duration_ms: int):
    """Record an agent run completion."""
    try:
        mailbox_agent_runs_total.labels(intent=intent, mode=mode, status=status).inc()
        mailbox_agent_run_duration_seconds.labels(intent=intent, mode=mode).observe(
            duration_ms / 1000.0
        )
    except Exception as e:
        logger.error(f"Failed to record agent run metric: {e}")


def record_tool_call(tool: str, status: str, duration_ms: int):
    """Record a tool call."""
    try:
        mailbox_agent_tool_calls_total.labels(tool=tool, status=status).inc()
        mailbox_agent_tool_latency_seconds.labels(tool=tool).observe(
            duration_ms / 1000.0
        )
    except Exception as e:
        logger.error(f"Failed to record tool call metric: {e}")


def record_rag_contexts(source: str, count: int):
    """Record RAG context retrieval."""
    try:
        mailbox_agent_rag_context_count.labels(source=source).observe(count)
    except Exception as e:
        logger.error(f"Failed to record RAG context metric: {e}")


def record_redis_hit(cache_type: str, hit: bool):
    """Record Redis cache hit/miss."""
    try:
        result = "hit" if hit else "miss"
        mailbox_agent_redis_hits_total.labels(type=cache_type, result=result).inc()
    except Exception as e:
        logger.error(f"Failed to record Redis metric: {e}")


def record_security_check(result: str):
    """Record security check result (unused - for future use)."""
    # TODO: Add security_checks_total metric definition above
    logger.debug(f"Security check recorded: {result}")
