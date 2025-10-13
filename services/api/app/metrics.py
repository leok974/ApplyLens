"""
Prometheus metrics for ApplyLens API.
Centralized metrics definitions to avoid circular imports.
"""

from prometheus_client import Counter, Gauge, Summary, Histogram

# --- Custom Prometheus Metrics ---

BACKFILL_REQUESTS = Counter(
    "applylens_backfill_requests_total",
    "Backfill requests by result",
    ["result"],  # ok, error, rate_limited, bad_request
)

BACKFILL_INSERTED = Counter(
    "applylens_backfill_inserted_total",
    "Total emails inserted during backfill operations",
)

GMAIL_CONNECTED = Gauge(
    "applylens_gmail_connected",
    "Gmail connection status (1=connected, 0=disconnected)",
    ["user_email"],
)

DB_UP = Gauge("applylens_db_up", "Database ping successful (1=up, 0=down)")

ES_UP = Gauge("applylens_es_up", "Elasticsearch ping successful (1=up, 0=down)")

# --- Risk Scoring Metrics ---

risk_recompute_requests = Counter(
    "applylens_risk_recompute_requests_total", "Total risk recomputation requests"
)

risk_recompute_duration = Summary(
    "applylens_risk_recompute_duration_seconds",
    "Risk recomputation duration in seconds",
)

risk_emails_scored_total = Counter(
    "applylens_risk_emails_scored_total", "Total number of emails scored"
)

risk_score_avg = Gauge(
    "applylens_risk_score_avg", "Average current risk score across all emails"
)

# Parity Check Metrics
parity_checks_total = Counter(
    "applylens_parity_checks_total", "Total number of parity checks performed"
)

parity_mismatches_total = Counter(
    "applylens_parity_mismatches_total", "Total number of mismatches detected"
)

parity_mismatch_ratio = Gauge(
    "applylens_parity_mismatch_ratio",
    "Current parity mismatch ratio (mismatches / total checked)",
)

parity_last_check_timestamp = Gauge(
    "applylens_parity_last_check_timestamp", "Unix timestamp of last parity check"
)

# --- Backfill Performance Metrics ---

backfill_duration_seconds = Histogram(
    "applylens_backfill_duration_seconds",
    "Duration of backfill jobs in seconds",
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600],  # 10s to 1h
)

risk_batch_duration_seconds = Histogram(
    "applylens_risk_batch_duration_seconds",
    "Duration of risk scoring batches in seconds",
    buckets=[1, 5, 10, 30, 60, 120, 300],  # 1s to 5m
)

risk_requests_total = Counter(
    "applylens_risk_requests_total",
    "Total risk computation requests by outcome",
    ["outcome"],  # success, failure
)
