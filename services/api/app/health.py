"""Enhanced health and readiness endpoints for production monitoring.

These endpoints follow Kubernetes best practices:
- /healthz: Liveness probe (app is running)
- /live: Alias for liveness
- /ready: Readiness probe (app can serve traffic - DB & ES healthy)
"""

import os
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from elasticsearch import Elasticsearch

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

    Returns 200 with details if ready, 503 if not ready.
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
        "status": "ready" if is_ready else "not_ready",
        "db": db_status,
        "es": es_status,
        "migration": migration_version,
    }

    if errors:
        response["errors"] = errors

    if not is_ready:
        raise HTTPException(status_code=503, detail=response)

    return response
