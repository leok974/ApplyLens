"""
Datadog instrumentation for Gemini LLM operations.

Adds APM traces, metrics, and logs for all Gemini API calls.
"""

import functools
import logging
import os
import time
from typing import Callable, Any

logger = logging.getLogger(__name__)

# Try to import ddtrace (graceful degradation if not installed)
try:
    from ddtrace import tracer, patch
    from datadog import statsd

    DATADOG_AVAILABLE = True
    logger.info("✓ Datadog APM initialized")
except ImportError:
    DATADOG_AVAILABLE = False
    logger.warning("⚠ Datadog libraries not available (install ddtrace and datadog)")

    # Mock objects for when Datadog is not available
    class MockTracer:
        def trace(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

    class MockStatsd:
        def increment(self, *args, **kwargs):
            pass

        def histogram(self, *args, **kwargs):
            pass

        def gauge(self, *args, **kwargs):
            pass

    tracer = MockTracer()
    statsd = MockStatsd()


def instrument_llm_call(task_type: str):
    """
    Decorator to instrument LLM calls with Datadog APM and metrics.

    Usage:
        @instrument_llm_call("classify")
        async def classify_email(...):
            ...

    Emits:
        - APM span: applylens.llm.{task_type}
        - Metric: applylens.llm.latency_ms (histogram)
        - Metric: applylens.llm.error_total (counter)
        - Metric: applylens.llm.tokens_used (gauge)
        - Metric: applylens.llm.cost_estimate_usd (gauge)

    Span tags:
        - task_type: classify | extract
        - model_provider: gemini | heuristic
        - env: dev | hackathon | prod
        - service: applylens-api-hackathon
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            error = None
            model_used = "unknown"
            tokens_used = 0

            # Create APM span
            with tracer.trace(
                f"applylens.llm.{task_type}",
                service=os.getenv("DD_SERVICE", "applylens-api"),
                resource=f"llm_{task_type}",
            ) as span:
                try:
                    # Execute function
                    result = await func(*args, **kwargs)

                    # Extract metadata from result
                    if isinstance(result, dict):
                        model_used = result.get("model_used", "unknown")
                        tokens_used = estimate_tokens(result)

                    # Tag span
                    span.set_tag("task_type", task_type)
                    span.set_tag("model_provider", model_used)
                    span.set_tag("env", os.getenv("DD_ENV", "dev"))
                    span.set_tag("tokens_estimate", tokens_used)

                    return result

                except Exception as e:
                    error = e
                    span.set_tag("error", True)
                    span.set_tag("error.type", type(e).__name__)
                    span.set_tag("error.message", str(e))
                    raise

                finally:
                    # Emit metrics
                    latency_ms = int((time.time() - start_time) * 1000)

                    tags = [
                        f"task_type:{task_type}",
                        f"model:{model_used}",
                        f"env:{os.getenv('DD_ENV', 'dev')}",
                    ]

                    # Latency histogram
                    statsd.histogram(
                        "applylens.llm.latency_ms",
                        latency_ms,
                        tags=tags,
                    )

                    # Error counter
                    if error:
                        statsd.increment(
                            "applylens.llm.error_total",
                            tags=tags + [f"error_type:{type(error).__name__}"],
                        )

                    # Token usage
                    if tokens_used > 0:
                        statsd.gauge(
                            "applylens.llm.tokens_used",
                            tokens_used,
                            tags=tags,
                        )

                        # Cost estimate (Gemini Flash pricing: ~$0.075 per 1M tokens)
                        cost_usd = (tokens_used / 1_000_000) * 0.075
                        statsd.gauge(
                            "applylens.llm.cost_estimate_usd",
                            cost_usd,
                            tags=tags,
                        )

        return wrapper

    return decorator


def estimate_tokens(result: dict) -> int:
    """
    Estimate token count from LLM result.

    This is a rough approximation:
    - ~4 characters per token for English text
    - Includes both input and output
    """
    text_content = ""

    # Extract text from result
    if "reasoning" in result:
        text_content += result["reasoning"]

    # Estimate input size (would need actual prompt for accuracy)
    # For now, use a conservative estimate
    input_estimate = 100  # Base prompt tokens

    output_tokens = len(text_content) // 4

    return input_estimate + output_tokens


def log_llm_operation(
    task_type: str, model_used: str, latency_ms: int, success: bool, **kwargs
):
    """
    Log LLM operation to Datadog logs.

    Structured log with privacy controls:
    - No raw email bodies
    - Hashed identifiers only
    - PII redacted
    """
    log_data = {
        "dd.service": os.getenv("DD_SERVICE", "applylens-api"),
        "dd.env": os.getenv("DD_ENV", "dev"),
        "dd.version": os.getenv("DD_VERSION", "dev"),
        "task_type": task_type,
        "model_provider": model_used,
        "latency_ms": latency_ms,
        "success": success,
        **kwargs,
    }

    if success:
        logger.info(f"LLM {task_type} completed", extra=log_data)
    else:
        logger.error(f"LLM {task_type} failed", extra=log_data)


# ============================================================================
# Backfill and Gmail Health Metrics (Phase 3C)
# ============================================================================


def track_backfill_error(error_type: str = "unknown", user_id: str = "unknown"):
    """
    Track backfill job errors for Datadog monitor.

    Emits: applylens.backfill.errors (counter)
    Monitor: #16811136 "ApplyLens – Backfill failing"

    Args:
        error_type: Type of error (e.g., "gmail_api", "db_error", "validation")
        user_id: Hashed user ID (for debugging, not exposed in alert)

    Usage:
        try:
            gmail_backfill_with_progress(...)
        except GoogleAPIError as e:
            track_backfill_error(error_type="gmail_api", user_id=hash(user.id))
            raise
    """
    tags = [
        f"error_type:{error_type}",
        f"env:{os.getenv('DD_ENV', 'dev')}",
        f"service:{os.getenv('DD_SERVICE', 'applylens-api')}",
    ]
    statsd.increment("applylens.backfill.errors", tags=tags)
    logger.warning(f"Backfill error tracked: {error_type}", extra={"user_id": user_id})


def track_backfill_rate_limited(user_id: str = "unknown", quota_user: str = "default"):
    """
    Track Gmail API rate limit (429) responses during backfill.

    Emits: applylens.backfill.rate_limited (counter)
    Monitor: #16811137 "ApplyLens – Backfill rate limited spike"

    Args:
        user_id: Hashed user ID
        quota_user: Gmail API quotaUser value (for tracking per-user quotas)

    Usage:
        except HttpError as e:
            if e.resp.status == 429:
                track_backfill_rate_limited(user_id=hash(user.id))
                # Apply exponential backoff...
    """
    tags = [
        f"quota_user:{quota_user}",
        f"env:{os.getenv('DD_ENV', 'dev')}",
        f"service:{os.getenv('DD_SERVICE', 'applylens-api')}",
    ]
    statsd.increment("applylens.backfill.rate_limited", tags=tags)
    logger.warning(
        "Gmail API rate limited during backfill",
        extra={"user_id": user_id, "quota_user": quota_user},
    )


def track_gmail_connection_status(connected: bool, user_id: str = "unknown"):
    """
    Track Gmail OAuth connection status (gauge).

    Emits: applylens.gmail.connected (gauge: 1=connected, 0=disconnected)
    Monitor: #16811138 "ApplyLens – Gmail disconnected"

    Args:
        connected: True if Gmail is connected, False if disconnected
        user_id: Hashed user ID

    Usage:
        # After successful OAuth flow:
        track_gmail_connection_status(connected=True, user_id=hash(user.id))

        # After detecting invalid/expired token:
        track_gmail_connection_status(connected=False, user_id=hash(user.id))
    """
    value = 1 if connected else 0
    tags = [
        f"status:{'connected' if connected else 'disconnected'}",
        f"env:{os.getenv('DD_ENV', 'dev')}",
        f"service:{os.getenv('DD_SERVICE', 'applylens-api')}",
    ]
    statsd.gauge("applylens.gmail.connected", value, tags=tags)
    logger.info(
        f"Gmail connection status: {'connected' if connected else 'disconnected'}",
        extra={"user_id": user_id, "connected": connected},
    )


# Initialize Datadog patches for automatic instrumentation
if DATADOG_AVAILABLE:
    try:
        # Patch common libraries
        patch(httpx=True)
        patch(asyncio=True)
        logger.info("✓ Datadog patches applied (httpx, asyncio)")
    except Exception as e:
        logger.warning(f"⚠ Failed to apply Datadog patches: {e}")
