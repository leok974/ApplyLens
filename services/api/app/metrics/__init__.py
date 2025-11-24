"""Metrics module for warehouse and analytics queries."""

from .warehouse import (
    mq_activity_daily,
    mq_categories_30d,
    mq_messages_last_24h,
    mq_top_senders_30d,
)

# Re-export Prometheus metrics from app/metrics.py file to avoid import conflicts
# The metrics.py file exists at the same level as this metrics/ folder
# We need to import from the parent app package
import sys
from pathlib import Path

# Add parent directory to path temporarily for import
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    import metrics as metrics_module

    DB_UP = metrics_module.DB_UP
    ES_UP = metrics_module.ES_UP
    BACKFILL_INSERTED = metrics_module.BACKFILL_INSERTED
    BACKFILL_REQUESTS = metrics_module.BACKFILL_REQUESTS
    GMAIL_CONNECTED = metrics_module.GMAIL_CONNECTED
    risk_recompute_requests = metrics_module.risk_recompute_requests
    risk_recompute_duration = metrics_module.risk_recompute_duration
    risk_emails_scored_total = metrics_module.risk_emails_scored_total
    risk_score_avg = metrics_module.risk_score_avg
    tool_queries_total = metrics_module.tool_queries_total
    record_tool = metrics_module.record_tool
    parity_checks_total = metrics_module.parity_checks_total
    parity_mismatches_total = metrics_module.parity_mismatches_total
    AGENT_TODAY_DURATION_SECONDS = metrics_module.AGENT_TODAY_DURATION_SECONDS
except (ImportError, AttributeError):
    # Fallback - create empty placeholders
    from prometheus_client import Counter, Gauge, Histogram, Summary

    DB_UP = Gauge("applylens_db_up", "Database ping successful (1=up, 0=down)")
    ES_UP = Gauge("applylens_es_up", "Elasticsearch ping successful (1=up, 0=down)")
    BACKFILL_INSERTED = Counter(
        "applylens_backfill_inserted_total", "Total emails inserted during backfill"
    )
    BACKFILL_REQUESTS = Counter(
        "applylens_backfill_requests_total", "Backfill requests", ["result"]
    )
    GMAIL_CONNECTED = Gauge(
        "applylens_gmail_connected", "Gmail connection status", ["user_email"]
    )
    risk_recompute_requests = Counter(
        "applylens_risk_recompute_requests_total", "Risk recomputation requests"
    )
    risk_recompute_duration = Summary(
        "applylens_risk_recompute_duration_seconds", "Risk recomputation duration"
    )
    risk_emails_scored_total = Counter(
        "applylens_risk_emails_scored_total", "Emails scored"
    )
    risk_score_avg = Gauge("applylens_risk_score_avg", "Average risk score")
    tool_queries_total = Counter(
        "assistant_tool_queries_total",
        "Tool queries",
        ["tool", "has_hits", "window_bucket"],
    )
    parity_checks_total = Counter("applylens_parity_checks_total", "Parity checks")
    parity_mismatches_total = Counter(
        "applylens_parity_mismatches_total", "Parity mismatches"
    )
    AGENT_TODAY_DURATION_SECONDS = Histogram(
        "applylens_agent_today_duration_seconds", "Today endpoint duration"
    )

    def record_tool(tool_name: str, hits: int, window_days: int = 30) -> None:
        """Fallback record_tool function"""
        pass
finally:
    # Remove from path
    if str(parent_dir) in sys.path:
        sys.path.remove(str(parent_dir))

__all__ = [
    "mq_activity_daily",
    "mq_categories_30d",
    "mq_messages_last_24h",
    "mq_top_senders_30d",
    # Prometheus metrics
    "DB_UP",
    "ES_UP",
    "BACKFILL_INSERTED",
    "BACKFILL_REQUESTS",
    "GMAIL_CONNECTED",
    "risk_recompute_requests",
    "risk_recompute_duration",
    "risk_emails_scored_total",
    "risk_score_avg",
    "tool_queries_total",
    "record_tool",
    "parity_checks_total",
    "parity_mismatches_total",
    "AGENT_TODAY_DURATION_SECONDS",
]
