import os

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette_exporter import PrometheusMiddleware

from . import auth_google, health, oauth_google, routes_extract, routes_gmail
from .db import Base, engine
from .es import ensure_index
from .routers import applications, emails, search, suggest
from .settings import settings
from .tracing import init_tracing

# CORS allowlist from environment (comma-separated)
ALLOWED_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5175").split(",")

app = FastAPI(title="ApplyLens API")


@app.on_event("startup")
async def _maybe_create_tables():
    """Create database tables on startup if enabled.

    Prefer Alembic migrations in real environments; this is only for local/dev if enabled.
    Disabled in test environment to avoid DB connection at import time.
    """
    if settings.CREATE_TABLES_ON_STARTUP:
        Base.metadata.create_all(bind=engine)


# Initialize OpenTelemetry tracing (optional, controlled by OTEL_ENABLED)
init_tracing(app)

# Prometheus middleware for HTTP metrics
app.add_middleware(
    PrometheusMiddleware,
    app_name="applylens_api",
    group_paths=True,  # coalesce dynamic paths
    prefix="applylens_http",  # e.g. applylens_http_requests_total
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    # Make sure ES index exists (no‑op if disabled)
    ensure_index()
    
    # Start scheduled jobs (Phase 5.3 active learning)
    try:
        from .scheduler import setup_scheduled_jobs
        setup_scheduled_jobs()
    except Exception as e:
        print(f"Warning: Could not start scheduler: {e}")


@app.on_event("shutdown")
def _shutdown():
    # Gracefully shutdown scheduler
    try:
        from .scheduler import shutdown_scheduler
        shutdown_scheduler()
    except Exception:
        pass


# Metrics endpoint (Prometheus text format)
@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics in Prometheus text format"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Health endpoints (include new enhanced module)
app.include_router(health.router)


@app.get("/debug/500")
def debug_500():
    """Debug endpoint to test 5xx error alerting (dev/testing only)"""
    raise HTTPException(status_code=500, detail="Debug error for alert testing")


# Include routers
app.include_router(emails.router)
app.include_router(search.router)
app.include_router(suggest.router)
app.include_router(applications.router)
app.include_router(auth_google.router)
app.include_router(routes_gmail.router)
app.include_router(oauth_google.router)
app.include_router(routes_extract.router)

# Phase 2 - Category labeling and profile analytics
from .routers import labeling, labels, profile  # noqa: E402

app.include_router(labels.router)
app.include_router(profile.router)
app.include_router(labeling.router)

# UX metrics (lightweight client telemetry)
from .routers import ux_metrics  # noqa: E402

app.include_router(ux_metrics.router)

# Security analysis
from .routers import policy, security  # noqa: E402

app.include_router(security.router)
app.include_router(policy.router)

# Phase 4 - Agentic Actions & Approval Loop
from .routers import actions  # noqa: E402

app.include_router(actions.router)

# Phase 5 - Chat Assistant
from .routers import chat  # noqa: E402

app.include_router(chat.router)

# Email Statistics (with Redis caching)
from .routers import emails_stats  # noqa: E402

app.include_router(emails_stats.router)

# Phase 6 - Money Mode (Receipt tracking)
from .routers import money  # noqa: E402

app.include_router(money.router)

# Fivetran & BigQuery Warehouse Metrics
from .routers import metrics_profile  # noqa: E402

app.include_router(metrics_profile.router)

# Phase 5 - Agent Telemetry & Online Evaluation
from .routers import agents_telemetry  # noqa: E402

app.include_router(agents_telemetry.router)

# Phase 5 - Budget Gates & Quality Thresholds
from .routers import budgets  # noqa: E402

app.include_router(budgets.router)

# Phase 5 - Intelligence Reports & Weekly Quality Analysis
from .routers import intelligence  # noqa: E402

app.include_router(intelligence.router)

# Phase 5 - Evaluation Metrics & Dashboard Integration
from .routers import metrics_eval  # noqa: E402

app.include_router(metrics_eval.router)

# Phase 5.3 - Active Learning & Judge Reliability
try:
    from .api.routes.active import router as active_router

    app.include_router(active_router)
except ImportError:
    pass  # Active learning module not available yet

# Email automation system
try:
    from .routers.mail_tools import router as mail_tools_router

    app.include_router(mail_tools_router)
except ImportError:
    pass  # Mail tools module not available yet

# Unsubscribe automation
try:
    from .routers.unsubscribe import router as unsubscribe_router

    app.include_router(unsubscribe_router)
except ImportError:
    pass  # Unsubscribe module not available yet

# Natural language agent
try:
    from .routers.nl_agent import router as nl_router

    app.include_router(nl_router)
except ImportError:
    pass  # NL agent module not available yet

# Policy execution (approvals tray)
try:
    from .routers.policy_exec import router as policy_exec_router

    app.include_router(policy_exec_router)
except ImportError:
    pass  # Policy exec module not available yet

# Approvals Tray API (Postgres + ES write-through)
try:
    from .routers.approvals import router as approvals_router

    app.include_router(approvals_router)
except ImportError:
    pass  # Approvals module not available yet

# Agent Approvals API (Phase 4)
try:
    from .routers.approvals_agent import router as agent_approvals_router

    app.include_router(agent_approvals_router)
except ImportError:
    pass  # Agent approvals module not available yet

# Grouped unsubscribe
try:
    from .routers.unsubscribe_group import router as unsubscribe_group_router

    app.include_router(unsubscribe_group_router)
except ImportError:
    pass  # Grouped unsubscribe module not available yet

# Productivity tools (reminders, calendar)
try:
    from .routers.productivity import router as productivity_router

    app.include_router(productivity_router)
except ImportError:
    pass  # Productivity module not available yet

# Phase 51.2 — Analytics endpoints (optional, gated)
try:
    from .routers.analytics import router as analytics_router

    app.include_router(analytics_router)
except ImportError:
    pass  # Analytics module not available

# Backfill health metrics (Prometheus)
try:
    from .routers.metrics import router as backfill_metrics_router

    app.include_router(backfill_metrics_router)
except ImportError:
    pass  # Backfill metrics module not available

# Automation (risk scoring, etc.)
try:
    from .routers.automation import router as automation_router

    app.include_router(automation_router)
except ImportError:
    pass  # Automation module not available

# Phase 1 Agentic System - Agents core infrastructure
try:
    from .routers.agents import router as agents_router, get_registry
    from .routers.agents_events import router as agents_events_router
    from .agents.warehouse import register as register_warehouse
    from .agents.inbox_triage import register as register_inbox_triage
    from .agents.knowledge_update import register as register_knowledge_update
    from .agents.insights_writer import register as register_insights_writer

    app.include_router(agents_router)
    app.include_router(agents_events_router)
    
    # Register agents
    registry = get_registry()
    register_warehouse(registry)
    register_inbox_triage(registry)
    register_knowledge_update(registry)
    register_insights_writer(registry)
except ImportError:
    pass  # Agents module not available

# Phase 5.4 Interventions - Incident tracking and remediation
try:
    from .routers.incidents import router as incidents_router
    from .routers.playbooks import router as playbooks_router
    from .routers.sse import router as sse_router
    
    app.include_router(incidents_router)
    app.include_router(playbooks_router)
    app.include_router(sse_router)
except ImportError:
    pass  # Interventions module not available yet

# Phase 5.5 Policy UI Editor - Policy bundles with versioning
try:
    from .routers.policy_bundles import router as policy_bundles_router
    
    app.include_router(policy_bundles_router)
except ImportError:
    pass  # Policy bundles module not available yet
