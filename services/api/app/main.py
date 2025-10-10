import os
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import Elasticsearch
from sqlalchemy import text
from starlette_exporter import PrometheusMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from .settings import settings
from .db import Base, engine, SessionLocal
from .routers import emails, health, search, suggest
from . import auth_google, routes_gmail, oauth_google, routes_extract
from .es import ensure_index
from .metrics import DB_UP, ES_UP

Base.metadata.create_all(bind=engine)

# CORS allowlist from environment (comma-separated)
ALLOWED_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5175").split(",")

app = FastAPI(title="ApplyLens API")

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

@app.get("/healthz")
def healthz():
    """Simple health check endpoint"""
    return {"ok": True}

@app.get("/readiness")
def readiness():
    """Readiness check - verifies DB and ES connectivity"""
    ok = True
    
    # DB ping
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        DB_UP.set(1)
    except Exception:
        DB_UP.set(0)
        ok = False
    finally:
        db.close()
    
    # ES ping
    try:
        es_url = os.getenv("ES_URL", "http://es:9200")
        es = Elasticsearch(es_url)
        if es.ping():
            ES_UP.set(1)
        else:
            ES_UP.set(0)
            ok = False
    except Exception:
        ES_UP.set(0)
        ok = False
    
    return {"ok": ok, "db": "up" if DB_UP._value.get() == 1 else "down", "es": "up" if ES_UP._value.get() == 1 else "down"}

@app.get("/debug/500")
def debug_500():
    """Debug endpoint to test 5xx error alerting (dev/testing only)"""
    raise HTTPException(status_code=500, detail="Debug error for alert testing")

app.include_router(health.router)
app.include_router(emails.router)
app.include_router(search.router)
app.include_router(suggest.router)
app.include_router(auth_google.router)
app.include_router(routes_gmail.router)
app.include_router(oauth_google.router)
app.include_router(routes_extract.router)

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
