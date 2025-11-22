"""
Prometheus metrics for ApplyLens security events.

This module provides counters and gauges for monitoring:
- CSRF validation failures
- Token decryption errors
- Rate limiting events
- Authentication failures

Metrics are exposed via /metrics endpoint for Prometheus scraping.
"""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response
import time

# CSRF Protection Metrics
csrf_fail_total = Counter(
    "applylens_csrf_fail_total",
    "Total number of CSRF validation failures",
    ["path", "method"],
)

csrf_success_total = Counter(
    "applylens_csrf_success_total",
    "Total number of successful CSRF validations",
    ["path", "method"],
)

# Token Encryption Metrics
crypto_decrypt_error_total = Counter(
    "applylens_crypto_decrypt_error_total",
    "Total number of token decryption errors",
    ["error_type"],
)

crypto_encrypt_total = Counter(
    "applylens_crypto_encrypt_total", "Total number of tokens encrypted"
)

crypto_decrypt_total = Counter(
    "applylens_crypto_decrypt_total", "Total number of tokens decrypted successfully"
)

crypto_operation_duration = Histogram(
    "applylens_crypto_operation_duration_seconds",
    "Duration of crypto operations",
    ["operation"],
)

# Rate Limiting Metrics
rate_limit_exceeded_total = Counter(
    "applylens_rate_limit_exceeded_total",
    "Total number of rate limit exceeded events",
    ["path", "ip_prefix"],
)

rate_limit_allowed_total = Counter(
    "applylens_rate_limit_allowed_total",
    "Total number of requests allowed by rate limiter",
    ["path"],
)

# Authentication Metrics
auth_attempt_total = Counter(
    "applylens_auth_attempt_total",
    "Total number of authentication attempts",
    ["method", "status"],  # method: google, demo; status: success, failure
)

oauth_token_refresh_total = Counter(
    "applylens_oauth_token_refresh_total",
    "Total number of OAuth token refresh attempts",
    ["status"],  # success, failure
)

# reCAPTCHA Metrics
recaptcha_verify_total = Counter(
    "applylens_recaptcha_verify_total",
    "Total number of reCAPTCHA verification attempts",
    ["status"],  # success, failure, low_score, disabled
)

recaptcha_score = Histogram(
    "applylens_recaptcha_score",
    "reCAPTCHA v3 scores",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

# Session Metrics
session_created_total = Counter(
    "applylens_session_created_total",
    "Total number of sessions created",
    ["auth_method"],
)

session_destroyed_total = Counter(
    "applylens_session_destroyed_total", "Total number of sessions destroyed (logout)"
)

# Backfill Metrics
backfill_runs_total = Counter(
    "applylens_backfill_runs_total",
    "Gmail backfill job runs",
    ["status"],  # ok, err
)

backfill_emails_synced = Counter(
    "applylens_backfill_emails_synced_total", "Total emails synced via backfill"
)

# Learning Loop Metrics (Companion extension)
learning_sync_counter = Counter(
    "applylens_autofill_runs_total",
    "Total number of Companion autofill learning sync events",
    labelnames=["status"],
)

learning_time_histogram = Histogram(
    "applylens_autofill_time_ms_bucket",
    "Distribution of autofill completion times in milliseconds",
    buckets=(
        1_000,
        5_000,
        10_000,
        30_000,
        60_000,
        120_000,
        300_000,
    ),
)

# Application Tracking Metrics
applications_created_from_thread_total = Counter(
    "applylens_applications_created_from_thread_total",
    "Total number of applications created from mailbox threads",
)


# Helper Functions
def track_crypto_operation(operation: str):
    """Context manager to track crypto operation duration."""

    class CryptoTimer:
        def __enter__(self):
            self.start = time.time()
            return self

        def __exit__(self, *args):
            duration = time.time() - self.start
            crypto_operation_duration.labels(operation=operation).observe(duration)

    return CryptoTimer()


# Metrics Router
metrics_router = APIRouter(tags=["metrics"])


@metrics_router.get("/metrics")
def prometheus_metrics():
    """
    Expose Prometheus metrics endpoint.

    Returns all registered metrics in Prometheus text format.
    This endpoint should be scraped by Prometheus server.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@metrics_router.get("/metrics/health")
def metrics_health():
    """
    Health check for metrics system.

    Returns basic status information.
    """
    return {"status": "healthy", "metrics_available": True, "endpoint": "/metrics"}
