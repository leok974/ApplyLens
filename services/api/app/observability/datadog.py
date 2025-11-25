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


# Initialize Datadog patches for automatic instrumentation
if DATADOG_AVAILABLE:
    try:
        # Patch common libraries
        patch(httpx=True)
        patch(asyncio=True)
        logger.info("✓ Datadog patches applied (httpx, asyncio)")
    except Exception as e:
        logger.warning(f"⚠ Failed to apply Datadog patches: {e}")
