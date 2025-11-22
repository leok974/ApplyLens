"""
Agent V2 - Prometheus Metrics

Tracks Agent V2 orchestration health, performance, and usage patterns.
Integrates with Grafana dashboards for real-time monitoring.

Metrics:
- agent_v2_runs_total: Counter by intent and status (done/error)
- agent_v2_latency_seconds: Histogram of end-to-end latency by intent
- agent_v2_tool_calls_total: Counter of tool invocations by tool name
- agent_v2_llm_tokens_total: Counter of LLM token usage

Usage in orchestrator:
    from app.metrics_agent import (
        agent_v2_runs_total,
        agent_v2_latency_seconds,
        track_agent_run,
    )

    with track_agent_run(intent="suspicious"):
        # ... orchestration logic ...
        pass
"""

import time
import logging
from contextlib import contextmanager
from typing import Generator, Optional

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# ============================================================================
# Core Metrics
# ============================================================================

agent_v2_runs_total = Counter(
    "agent_v2_runs_total",
    "Total Agent V2 runs completed",
    ["intent", "status"],
)

agent_v2_latency_seconds = Histogram(
    "agent_v2_latency_seconds",
    "Agent V2 end-to-end latency in seconds",
    ["intent"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

agent_v2_tool_calls_total = Counter(
    "agent_v2_tool_calls_total",
    "Total tool invocations by Agent V2",
    ["tool_name", "status"],
)

agent_v2_llm_tokens_total = Counter(
    "agent_v2_llm_tokens_total",
    "Total LLM tokens consumed by Agent V2",
    ["llm_provider", "token_type"],  # token_type: prompt, completion
)

agent_v2_errors_total = Counter(
    "agent_v2_errors_total",
    "Total Agent V2 errors by type",
    ["error_type"],  # tool_timeout, llm_error, validation_error, etc.
)

agent_v2_feedback_total = Counter(
    "agent_v2_feedback_total",
    "Total Agent V2 feedback events from users",
    ["intent", "label"],  # label: helpful, not_helpful, hide, done
)

# ============================================================================
# Helper Functions
# ============================================================================


@contextmanager
def track_agent_run(
    intent: str, status_ref: Optional[dict] = None
) -> Generator[None, None, None]:
    """
    Context manager to track Agent V2 run metrics.

    Args:
        intent: Detected user intent (suspicious, bills, followups, etc.)
        status_ref: Optional dict to capture final status (done/error)

    Usage:
        status = {"value": "done"}
        with track_agent_run(intent="suspicious", status_ref=status):
            # ... orchestration logic ...
            status["value"] = "error"  # update if error occurs
    """
    start = time.perf_counter()
    final_status = "done"

    try:
        yield
    except Exception as exc:
        final_status = "error"
        logger.exception(f"Agent V2 run failed for intent={intent}: {exc}")
        raise
    finally:
        # Check if caller updated status via status_ref
        if status_ref and "value" in status_ref:
            final_status = status_ref["value"]

        duration = time.perf_counter() - start

        # Record metrics
        agent_v2_runs_total.labels(intent=intent, status=final_status).inc()
        agent_v2_latency_seconds.labels(intent=intent).observe(duration)

        logger.info(
            f"Agent V2 run completed: intent={intent}, status={final_status}, duration={duration:.2f}s"
        )


def track_tool_call(tool_name: str, status: str = "success") -> None:
    """
    Track a single tool invocation.

    Args:
        tool_name: Name of the tool (email_search, security_scan, etc.)
        status: success, error, or timeout
    """
    agent_v2_tool_calls_total.labels(tool_name=tool_name, status=status).inc()


def track_llm_tokens(
    llm_provider: str, prompt_tokens: int, completion_tokens: int
) -> None:
    """
    Track LLM token usage.

    Args:
        llm_provider: ollama, openai, anthropic, etc.
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
    """
    agent_v2_llm_tokens_total.labels(
        llm_provider=llm_provider, token_type="prompt"
    ).inc(prompt_tokens)
    agent_v2_llm_tokens_total.labels(
        llm_provider=llm_provider, token_type="completion"
    ).inc(completion_tokens)


def track_error(error_type: str) -> None:
    """
    Track an Agent V2 error by type.

    Args:
        error_type: tool_timeout, llm_error, validation_error, etc.
    """
    agent_v2_errors_total.labels(error_type=error_type).inc()
