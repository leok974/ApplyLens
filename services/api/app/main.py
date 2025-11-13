import logging
import os

# Load .env early (dev only) - ensures environment variables are available
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette_exporter import PrometheusMiddleware

# Copilot: Ensure routers include gmail/backfill at /api/gmail/backfill and health/live endpoint.
# Copilot: All routers should use proper prefixes and error logging with exc_info=True.
from . import auth_google, health, oauth_google, routes_extract, routes_gmail
from .db import Base, engine
from .es import ensure_index
from .routers import applications, emails, search, suggest, search_debug
from .settings import settings
from .tracing import init_tracing
from .config import agent_settings
from .core.csrf import CSRFMiddleware
from .core.limiter import RateLimitMiddleware
from .core.metrics import metrics_router

# CORS allowlist from environment (comma-separated)
ALLOWED_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5175").split(",")

# Add chrome extension support for dev mode
if os.getenv("APPLYLENS_DEV") == "1":
    # Support chrome extensions and any localhost port for development
    ALLOWED_ORIGINS.extend(
        [
            "chrome-extension://*",
            "http://localhost",
            "http://localhost:*",
            "http://127.0.0.1:*",
        ]
    )

app = FastAPI(title="ApplyLens API")

# Prometheus middleware for HTTP metrics (outermost layer)
app.add_middleware(
    PrometheusMiddleware,
    app_name="applylens_api",
    group_paths=True,  # coalesce dynamic paths
    prefix="applylens_http",  # e.g. applylens_http_requests_total
)

# CORS middleware (must be before CSRF to handle preflight OPTIONS requests)
if os.getenv("APPLYLENS_DEV") == "1":
    # Dev mode: Use regex to support wildcards (chrome-extension://* and localhost:*)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"(chrome-extension://.*|http://localhost(:\d+)?|http://127\.0\.0\.1(:\d+)?)",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
else:
    # Production: Use explicit allowlist
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

# Rate limiting middleware (after CORS, before CSRF)
app.add_middleware(
    RateLimitMiddleware,
    capacity=agent_settings.RATE_LIMIT_MAX_REQ,
    window=agent_settings.RATE_LIMIT_WINDOW_SEC,
)

# CSRF protection middleware (after CORS, before session)
app.add_middleware(CSRFMiddleware)

# Add session middleware for OAuth state management
app.add_middleware(
    SessionMiddleware,
    secret_key=agent_settings.SESSION_SECRET,
    max_age=3600,  # 1 hour for OAuth state
    same_site="lax",
    https_only=agent_settings.COOKIE_SECURE == "1",
)


@app.on_event("startup")
async def _maybe_create_tables():
    """Create database tables on startup if enabled.

    Prefer Alembic migrations in real environments; this is only for local/dev if enabled.
    Disabled in test environment to avoid DB connection at import time.
    """
    # Log critical environment variables for debugging
    log = logging.getLogger("uvicorn")
    log.info(
        f"🔧 Runtime config: APPLYLENS_DEV={os.getenv('APPLYLENS_DEV')}, "
        f"DATABASE_URL={settings.DATABASE_URL[:50]}..., "
        f"DEVDIAG_BASE={os.getenv('DEVDIAG_BASE')}, "
        f"DEVDIAG_ENABLED={os.getenv('DEVDIAG_ENABLED')}"
    )

    if settings.CREATE_TABLES_ON_STARTUP:
        Base.metadata.create_all(bind=engine)


# Initialize OpenTelemetry tracing (optional, controlled by OTEL_ENABLED)
init_tracing(app)


@app.on_event("startup")
def _startup():
    # Log key environment variables for troubleshooting
    logger.info(
        f"🔧 Runtime config: APPLYLENS_DEV={os.getenv('APPLYLENS_DEV')}, "
        f"DATABASE_URL={settings.DATABASE_URL[:30]}..., "
        f"ES_ENABLED={os.getenv('ES_ENABLED', 'true')}, "
        f"DEVDIAG_BASE={os.getenv('DEVDIAG_BASE')}, "
        f"DEVDIAG_ENABLED={os.getenv('DEVDIAG_ENABLED')}"
    )

    # Make sure ES index exists (no‑op if disabled)
    ensure_index()

    # Initialize health metrics (DB_UP, ES_UP) on startup
    try:
        from .health import initialize_health_metrics

        initialize_health_metrics()
    except Exception as e:
        print(f"Warning: Could not initialize health metrics: {e}")

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


# Runtime config endpoint - Frontend feature flags
@app.get("/config")
def get_runtime_config():
    """
    Get runtime configuration for frontend feature flags.

    Returns:
        - readOnly: Whether destructive actions (mute/delete/archive) are disabled
        - version: Current API version (e.g., "v0.4.35")
    """
    allow_mutations = os.getenv("ALLOW_ACTION_MUTATIONS", "true").lower() == "true"
    return {
        "readOnly": not allow_mutations,
        "version": settings.APP_VERSION,
    }


# Health endpoints (include new enhanced module)
app.include_router(health.router)

# Metrics endpoints (security events + Prometheus)
app.include_router(metrics_router)


@app.get("/debug/500")
def debug_500():
    """Debug endpoint to test 5xx error alerting (dev/testing only)"""
    raise HTTPException(status_code=500, detail="Debug error for alert testing")


# Dev routers FIRST - Must be before production routers to win path matches
# Dev seed router - Test data seeding (dev only)
from .routers import dev_seed  # noqa: E402

app.include_router(dev_seed.router)

# Dev risk router - Email risk assessment stubs (dev only)
# MUST BE BEFORE emails.router to win /emails/{id}/risk-advice
from .routers import dev_risk  # noqa: E402

app.include_router(dev_risk.router)
app.include_router(dev_risk.emails_risk_router)  # /emails/* paths (no prefix)

# Dev backfill router - Gmail backfill stubs (dev only)
from .routers import dev_backfill  # noqa: E402

app.include_router(dev_backfill.router)

# Include production routers
app.include_router(emails.router)
app.include_router(search.router)
app.include_router(search_debug.router)  # Debug diagnostics for search
app.include_router(suggest.router)
app.include_router(applications.router)

# Auth router - Google OAuth and demo mode
from .routers import auth as auth_router  # noqa: E402

app.include_router(auth_router.router)

# Admin router - System maintenance
from .routers import admin as admin_router  # noqa: E402

app.include_router(admin_router.router)

app.include_router(auth_google.router)
app.include_router(routes_gmail.router)
app.include_router(oauth_google.router)
app.include_router(routes_extract.router)

# Companion learning loop
from .routers import extension_learning  # noqa: E402

app.include_router(extension_learning.router)

# Async Gmail backfill with job tracking (v0.4.17)
from .routers import gmail_backfill  # noqa: E402

app.include_router(gmail_backfill.router)  # /gmail/backfill/* (no /api prefix needed)

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

app.include_router(security.router, prefix="/api")  # /api/security/*
app.include_router(policy.router)

# Phase 4 - Agentic Actions & Approval Loop
from .routers import actions  # noqa: E402
from .routers import inbox_actions  # noqa: E402
from .routers import senders  # noqa: E402
from .routers import tracker  # noqa: E402

app.include_router(actions.router)
app.include_router(inbox_actions.router)
app.include_router(senders.router)  # /settings/senders
app.include_router(tracker.router)  # /tracker

# Browser Extension API (dev-only)
from .routers import extension  # noqa: E402

app.include_router(extension.router)  # /api/extension/* + /api/profile/*

# DevDiag Proxy (ops diagnostics)
from .routers import devdiag_proxy  # noqa: E402

app.include_router(devdiag_proxy.router, prefix="/api")  # /api/ops/diag/*

# Phase 5 - Chat Assistant
from .routers import chat  # noqa: E402
from .routers import assistant  # noqa: E402

app.include_router(chat.router)
app.include_router(assistant.router)  # /assistant/query

# Email Statistics (with Redis caching)
from .routers import emails_stats  # noqa: E402

app.include_router(emails_stats.router)

# Feature Flags Management (Email Risk v3.1 rollout)
from .routers import flags  # noqa: E402

app.include_router(flags.router)

# Phase 6 - Money Mode (Receipt tracking)
from .routers import money  # noqa: E402

app.include_router(money.router)

# Fivetran & BigQuery Warehouse Metrics
from .routers import metrics_profile  # noqa: E402

app.include_router(metrics_profile.router)

# BigQuery Warehouse Profile Metrics (feature-flagged)
try:
    from .routers.warehouse import router as warehouse_router

    app.include_router(warehouse_router)
except ImportError:
    pass  # Warehouse module not available (requires google-cloud-bigquery)

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
    from .routers.policy_lint import router as policy_lint_router
    from .routers.policy_sim import router as policy_sim_router
    from .routers.policy_bundle_io import router as policy_bundle_io_router
    from .routers.policy_activate import router as policy_activate_router

    app.include_router(policy_bundles_router)
    app.include_router(policy_lint_router)
    app.include_router(policy_sim_router)
    app.include_router(policy_bundle_io_router)
    app.include_router(policy_activate_router)
except ImportError:
    pass  # Policy bundles module not available yet

# Phase 4 AI Features - Email Summarizer, Risk Badge, RAG Search
logger = logging.getLogger(__name__)

try:
    logger.info("Attempting to load AI and RAG routers...")
    from .routers import ai, rag

    logger.info(f"AI router loaded: {ai.router}")
    logger.info(f"RAG router loaded: {rag.router}")

    app.include_router(ai.router)
    logger.info("[OK] AI router registered")

    # RAG router: Register twice for backwards compatibility
    app.include_router(rag.router)  # /rag/...
    app.include_router(rag.router, prefix="/api")  # /api/rag/... (backwards compat)
    logger.info("[OK] RAG router registered at /rag/* and /api/rag/*")

    print("[OK] Phase 4 AI routers registered successfully")
except ImportError as e:
    logger.error(f"[WARN] AI features module import failed: {e}")
    print(f"[WARN] AI features module not available: {e}")
except Exception as e:
    logger.error(f"[ERROR] Error loading AI features: {e}", exc_info=True)
    print(f"[ERROR] Error loading AI features: {e}")
    import traceback

    traceback.print_exc()

# Dev-only routes for E2E testing (seed data, etc.)
# Only available when ALLOW_DEV_ROUTES=1 environment variable is set
if os.getenv("ALLOW_DEV_ROUTES") == "1":
    try:
        from .routers import dev_seed

        app.include_router(dev_seed.router)
        logger.info("[OK] Dev seed router registered at /api/dev/*")
    except ImportError as e:
        logger.error(f"[WARN] Dev seed module import failed: {e}")
    except Exception as e:
        logger.error(f"[ERROR] Error loading dev seed router: {e}", exc_info=True)
