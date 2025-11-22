# Autofill Aggregator Service

**Purpose:** Companion learning loop that aggregates application tracking data to improve form autofill suggestions.

## Overview

This service runs on a schedule (default: every 6 hours) to:
1. Analyze application tracking data from the last 30 days
2. Extract domain patterns and common form fields
3. Update user profiles with autofill suggestions
4. Log summary statistics (hosts processed, profiles updated, duration)

## Configuration

**Environment Variables:**

- `COMPANION_AUTOFILL_AGG_ENABLED` - Feature flag (default: 1)
  - Set to `0` to disable aggregation (service will no-op)
- `AGG_EVERY_HOURS` - Run interval in hours (default: 6)
- `AGG_LOOKBACK_DAYS` - Historical window in days (default: 30)
- `DATABASE_URL` - PostgreSQL connection string (shared with API)
- `TZ` - Timezone (default: America/New_York)

**From `.env.prod`:**
```bash
COMPANION_AUTOFILL_AGG_ENABLED=1
AGG_EVERY_HOURS=6
AGG_LOOKBACK_DAYS=30
```

## Service Details

**Container:** `applylens-autofill-aggregator`
**Image:** `python:3.11-slim`
**Network:** `applylens-prod`
**Restart Policy:** `unless-stopped`

**Dependencies:**
- PostgreSQL database (healthy)
- API service (healthy, for shared models/code)

**Healthcheck:**
- **Test:** Database connectivity check (`SELECT 1`)
- **Interval:** 10 minutes
- **Timeout:** 30 seconds
- **Retries:** 2
- **Start Period:** 120 seconds

## Files

- `runner.py` - Main scheduler loop with aggregation logic
- `healthcheck.py` - Database connectivity test
- `README.md` - This file

## Operations

### Start Service

```powershell
docker compose -f docker-compose.prod.yml --env-file infra\.env.prod up -d autofill-aggregator
```

### Check Status

```powershell
docker ps --filter "name=applylens-autofill-aggregator" --format "table {{.Names}}\t{{.Status}}"
```

### View Logs

```powershell
docker logs -f applylens-autofill-aggregator
```

### Restart Service

```powershell
docker compose -f docker-compose.prod.yml --env-file infra\.env.prod restart autofill-aggregator
```

### Disable Aggregation

To disable without stopping the container:

```powershell
# In .env.prod, set:
COMPANION_AUTOFILL_AGG_ENABLED=0

# Restart service
docker compose -f docker-compose.prod.yml --env-file infra\.env.prod restart autofill-aggregator
```

## Expected Log Output

```
[autofill-agg] 2025-11-12T20:30:00Z START autofill aggregator starting (enabled=True, interval=6h, lookback=30d)
[autofill-agg] 2025-11-12T20:30:00Z SLEEP initial_jitter=42s
[autofill-agg] 2025-11-12T20:30:42Z OK aggregation complete: hosts=127 profiles=5 duration=2.34s lookback=30d
[autofill-agg] 2025-11-12T20:30:42Z SLEEP next_run_in=21720s (6h) stats={'profiles_updated': 5, 'hosts_processed': 127, 'duration_s': 2.34}
```

**When disabled:**
```
[autofill-agg] 2025-11-12T20:30:42Z SKIP aggregator disabled (COMPANION_AUTOFILL_AGG_ENABLED=0)
[autofill-agg] 2025-11-12T20:30:42Z SLEEP next_run_in=21650s (6h) stats={'profiles_updated': 0, 'hosts_processed': 0, 'duration_s': 0}
```

## Metrics

The aggregator tracks the following Prometheus metrics (to be implemented):

- `applylens_autofill_agg_runs_total{status="ok|err"}` - Total aggregation runs
- `applylens_autofill_profiles_updated_total` - Total profiles updated

## Implementation Status

**✅ Completed:**
- Docker service configuration
- Feature flag support
- Database healthcheck
- Scheduler loop with jitter
- Structured logging
- Error handling

**🚧 TODO:**
- Implement actual aggregation logic in `run_aggregator()`
- Add Prometheus metrics
- Add metrics dashboard in Grafana
- Implement profile autofill update logic

## Notes

- The service shares the API codebase via volume mount (`./services/api:/api:ro`)
- Python imports use `PYTHONPATH=/api` to access `app.models` and `app.db`
- Initial jitter (10-60s) prevents thundering herd on container restart
- Run jitter (+0-5min) prevents exact synchronization across restarts
- Healthcheck runs every 10 minutes (less frequent than backfill since aggregation is less critical)
