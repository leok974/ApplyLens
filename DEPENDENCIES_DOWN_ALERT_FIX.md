# DependenciesDown Alert False Positive Fix

## Problem

**Alert**: `DependenciesDown` firing immediately on API startup
**Expression**: `(min(applylens_db_up) == 0) or (min(applylens_es_up) == 0)`
**Symptom**: Alert shows "firing" for 2+ minutes after restart, even when DB and ES are healthy

## Root Cause

**Prometheus Gauge metrics default to 0 if never set.**

The `DB_UP` and `ES_UP` metrics were only initialized when:
- `/ready` endpoint was called manually
- `/status` endpoint was queried
- A health check probe ran

Between API startup and the first health check call, Prometheus scraped metrics showing:
```
applylens_db_up 0.0
applylens_es_up 0.0
```

This triggered the `DependenciesDown` alert for 2+ minutes until the first `/ready` call.

## Fix Applied

### Code Changes

**services/api/app/health.py**:
```python
def initialize_health_metrics():
    """Initialize health metrics on startup to avoid 0 values in Prometheus.

    This ensures DB_UP and ES_UP are set immediately when the app starts,
    preventing false alerts in Prometheus before the first /ready call.
    """
    # Check DB connectivity
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        DB_UP.set(1)
    except Exception:
        DB_UP.set(0)
    finally:
        db.close()

    # Check ES connectivity
    try:
        es_url = os.getenv("ES_URL", "http://es:9200")
        es = Elasticsearch(es_url)
        if es.ping():
            ES_UP.set(1)
        else:
            ES_UP.set(0)
    except Exception:
        ES_UP.set(0)
```

**services/api/app/main.py**:
```python
@app.on_event("startup")
def _startup():
    # Make sure ES index exists (no‑op if disabled)
    ensure_index()

    # Initialize health metrics (DB_UP, ES_UP) on startup
    try:
        from .health import initialize_health_metrics
        initialize_health_metrics()
    except Exception as e:
        print(f"Warning: Could not initialize health metrics: {e}")

    # Start scheduled jobs...
```

## Verification

After restart, metrics show correct values immediately:
```bash
docker exec applylens-prometheus-prod wget -qO- http://api:8003/metrics | grep "applylens_db_up\|applylens_es_up"
```

**Output**:
```
# HELP applylens_db_up Database ping successful (1=up, 0=down)
# TYPE applylens_db_up gauge
applylens_db_up 1.0
# HELP applylens_es_up Elasticsearch ping successful (1=up, 0=down)
# TYPE applylens_es_up gauge
applylens_es_up 1.0
```

✅ **Metrics show 1.0 within seconds of startup**, before first `/ready` call

## Alert Behavior

- **Before Fix**: Alert fires for ~2 minutes on every API restart
- **After Fix**: Alert only fires if DB or ES actually fail

The alert will auto-resolve within 2 minutes (the `for: 2m` duration) after the fix is deployed.

## Best Practices

**Prometheus Gauge Initialization**:
- Always initialize gauges to a known state on startup
- Don't rely on endpoint calls to set initial metric values
- Use startup events for dependency health checks

**Health Check Design**:
- Startup initialization: Set initial state
- Periodic updates: Keep state current (via `/ready` calls or background probes)
- Separate concerns: Liveness vs. readiness vs. metrics

## Related Changes

- Commit: "Initialize health metrics on startup to prevent false DependenciesDown alerts"
- Image: `leoklemet/applylens-api:latest` (digest sha256:7227f7c...)
- Deployed: October 22, 2025, ~4:02 PM

---

**Impact**: Eliminates false positive alerts, improves monitoring reliability
**Status**: ✅ Deployed and verified working
