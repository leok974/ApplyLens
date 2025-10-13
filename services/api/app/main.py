import os
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette_exporter import PrometheusMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from .settings import settings
from .db import Base, engine
from .routers import emails, search, suggest, applications
from . import auth_google, routes_gmail, oauth_google, routes_extract, health
from .es import ensure_index
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
    group_paths=True,          # coalesce dynamic paths
    prefix="applylens_http",   # e.g. applylens_http_requests_total
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
app.include_router(emails.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(suggest.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
app.include_router(auth_google.router)
app.include_router(routes_gmail.router, prefix="/api")
app.include_router(oauth_google.router)
app.include_router(routes_extract.router)

# Phase 2 - Category labeling and profile analytics
from .routers import labels, profile, labeling  # noqa: E402
app.include_router(labels.router)
app.include_router(profile.router)
app.include_router(labeling.router, prefix="/api")

# Security analysis
from .routers import security, policy  # noqa: E402
app.include_router(security.router, prefix="/api")
app.include_router(policy.router, prefix="/api")

# Phase 4 - Agentic Actions & Approval Loop
from .routers import actions  # noqa: E402
app.include_router(actions.router, prefix="/api")

# Phase 5 - Chat Assistant
from .routers import chat  # noqa: E402
app.include_router(chat.router, prefix="/api")

# Phase 6 - Money Mode (Receipt tracking)
from .routers import money  # noqa: E402
app.include_router(money.router, prefix="/api")

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

