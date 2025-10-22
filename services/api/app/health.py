"""Enhanced health and readiness endpoints for production monitoring.

These endpoints follow Kubernetes best practices:
- /healthz: Liveness probe (app is running)
- /live: Alias for liveness
- /ready: Readiness probe (app can serve traffic - DB & ES healthy)
"""

import os

from elasticsearch import Elasticsearch
from fastapi import APIRouter
from sqlalchemy import text

from .db import SessionLocal
from .metrics import DB_UP, ES_UP

# Import migration helper
try:
    from .utils.schema_guard import get_current_migration
except ImportError:

    def get_current_migration():
        return "unknown"


router = APIRouter(prefix="", tags=["health"])  # Root scope for K8s probes


@router.get("/healthz")
def healthz():
    """Liveness probe - basic health check.

    Returns 200 if the application is running.
    This should NOT check external dependencies.
    """
    return {"status": "ok"}


@router.get("/live")
def live():
    """Alias for liveness probe (alternative naming convention)."""
    return {"status": "alive"}


@router.get("/ready")
def ready():
    """Readiness probe - checks if app can serve traffic.

    Verifies:
    - Database connectivity
    - Elasticsearch connectivity
    - Current migration version

    NEVER returns 5xx - always returns 200 with structured state.
    This prevents frontend reload loops on 502/503 errors.

    Returns 200 with {"status": "ready"} if ready,
    or 200 with {"status": "degraded", "errors": [...]} if dependencies are down.
    """
    errors = []
    db_status = "unknown"
    es_status = "unknown"
    migration_version = "unknown"

    # Check DB connectivity
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
        DB_UP.set(1)
    except Exception as e:
        db_status = "down"
        DB_UP.set(0)
        errors.append(f"Database: {str(e)}")
    finally:
        db.close()

    # Check ES connectivity
    try:
        es_url = os.getenv("ES_URL", "http://es:9200")
        es = Elasticsearch(es_url)
        if es.ping():
            es_status = "ok"
            ES_UP.set(1)
        else:
            es_status = "down"
            ES_UP.set(0)
            errors.append("Elasticsearch: ping failed")
    except Exception as e:
        es_status = "down"
        ES_UP.set(0)
        errors.append(f"Elasticsearch: {str(e)}")

    # Get migration version
    try:
        migration_version = get_current_migration() or "none"
    except Exception as e:
        migration_version = "error"
        errors.append(f"Migration check: {str(e)}")

    # Determine overall readiness
    is_ready = db_status == "ok" and es_status == "ok"

    response = {
        "status": "ready" if is_ready else "degraded",
        "db": db_status,
        "es": es_status,
        "migration": migration_version,
    }

    if errors:
        response["errors"] = errors

    # ALWAYS return 200 - frontend will check status field
    return response


@router.get("/status")
def status():
    """Application status endpoint (alias for /ready with simpler response).

    NEVER returns 5xx - always returns 200 with structured state.
    This prevents frontend reload loops on 502/503 errors.

    Returns:
        - {"ok": true, "gmail": "ok"} when healthy
        - {"ok": false, "gmail": "degraded", "message": "..."} when degraded
    """
    errors = []
    db_status = "unknown"
    es_status = "unknown"

    # Check DB connectivity
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
        DB_UP.set(1)
    except Exception as e:
        db_status = "down"
        DB_UP.set(0)
        errors.append(f"Database: {str(e)}")
    finally:
        db.close()

    # Check ES connectivity
    try:
        es_url = os.getenv("ES_URL", "http://es:9200")
        es = Elasticsearch(es_url)
        if es.ping():
            es_status = "ok"
            ES_UP.set(1)
        else:
            es_status = "down"
            ES_UP.set(0)
            errors.append("Elasticsearch: ping failed")
    except Exception as e:
        es_status = "down"
        ES_UP.set(0)
        errors.append(f"Elasticsearch: {str(e)}")

    # Determine overall status
    is_healthy = db_status == "ok" and es_status == "ok"

    # Frontend-friendly response format
    if is_healthy:
        return {"ok": True, "gmail": "ok"}

    message = "; ".join(errors) if errors else "Services degraded"
    return {"ok": False, "gmail": "degraded", "message": message}
