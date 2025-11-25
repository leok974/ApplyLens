"""
Prometheus metrics for ApplyLens API.
Centralized metrics definitions to avoid circular imports.
"""

from prometheus_client import Counter, Gauge, Histogram, Summary

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

# --- Assistant Tool Metrics ---

tool_queries_total = Counter(
    "assistant_tool_queries_total",
    "Total assistant tool queries",
    [
        "tool",
        "has_hits",
        "window_bucket",
    ],  # tool: summarize, find, clean, etc.; has_hits: 0 or 1; window_bucket: 7, 30, 60, 90+
)


def window_bucket(days: int) -> str:
    """
    Categorize window_days into buckets for metrics.

    Args:
        days: Number of days in the window

    Returns:
        Bucket label: "7", "30", "60", or "90+"
    """
    if days <= 7:
        return "7"
    elif days <= 30:
        return "30"
    elif days <= 60:
        return "60"
    else:
        return "90+"


def record_tool(tool_name: str, hits: int, window_days: int = 30) -> None:
    """
    Record assistant tool usage.

    Args:
        tool_name: Name of the tool (summarize, find, clean, etc.)
        hits: Number of results/hits returned
        window_days: Time window in days for bucket tracking
    """
    try:
        tool_queries_total.labels(
            tool=tool_name,
            has_hits="1" if hits > 0 else "0",
            window_bucket=window_bucket(window_days),
        ).inc()
    except Exception:
        # Metrics are optional - don't fail requests
        pass


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

# --- Phase 3.1: LLM Generation Metrics ---

llm_generation_requests = Counter(
    "applylens_llm_generation_requests_total",
    "Total LLM generation requests",
    [
        "provider",
        "model",
        "status",
    ],  # provider: openai|ollama, model: gpt-4o-mini, status: success|error
)

llm_generation_duration = Histogram(
    "applylens_llm_generation_duration_seconds",
    "LLM generation latency in seconds",
    ["provider"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

llm_guardrail_triggers = Counter(
    "applylens_llm_guardrail_triggers_total",
    "Guardrail violations detected",
    ["guardrail_type"],  # url, forbidden_phrase, length, email
)

llm_template_fallbacks = Counter(
    "applylens_llm_template_fallbacks_total",
    "LLM failures resulting in template fallback",
    ["reason"],  # disabled, error, timeout
)

autofill_field_acceptance = Counter(
    "applylens_autofill_field_acceptance_total",
    "Fields accepted vs rejected by users",
    ["accepted"],  # true | false
)

autofill_manual_edits = Counter(
    "applylens_autofill_manual_edits_total",
    "Fields manually edited by users",
)

# --- Agent Today Endpoint Metrics ---

AGENT_TODAY_DURATION_SECONDS = Histogram(
    "applylens_agent_today_duration_seconds",
    "Wall-clock time spent building /v2/agent/today responses.",
    buckets=(
        0.1,  # super fast
        0.25,
        0.5,
        0.75,
        1.0,
        1.5,
        2.0,
        3.0,
        5.0,
        7.5,
        10.0,  # very slow
    ),
)

# --- Follow-up Draft Metrics ---

FOLLOWUP_DRAFT_REQUESTS = Counter(
    "applylens_followup_draft_requested_total",
    "Number of follow-up drafts requested",
    ["source"],  # thread_viewer, etc.
)

# --- Follow-up Queue Metrics ---

FOLLOWUP_QUEUE_REQUESTS = Counter(
    "applylens_followup_queue_requested_total",
    "Number of follow-up queue requests",
)

FOLLOWUP_QUEUE_ITEM_DONE = Counter(
    "applylens_followup_queue_item_done_total",
    "Number of follow-up queue items marked as done",
)

INTERVIEW_PREP_REQUESTS = Counter(
    "applylens_interview_prep_requested_total",
    "Number of interview prep requests",
    ["source"],
)

ROLE_MATCH_REQUESTS = Counter(
    "applylens_role_match_requested_total",
    "Number of role match requests",
    ["match_bucket"],
)

ROLE_MATCH_BATCH_REQUESTS = Counter(
    "applylens_role_match_batch_requests_total",
    "Number of batch role-match requests",
)
