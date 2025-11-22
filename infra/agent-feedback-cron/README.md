# Agent Feedback Aggregation Cron

Scheduled job that periodically calls `/api/v2/agent/feedback/aggregate` to aggregate user feedback from companion usage and update agent learning models.

## Overview

This container runs a simple Python script that:
1. Calls the feedback aggregation endpoint on a schedule
2. Logs results for monitoring
3. Provides health check for Docker orchestration

## Configuration

Set these environment variables in `.env.prod`:

```bash
# Agent Feedback Cron Configuration
AGENT_FEEDBACK_EVERY_HOURS=6    # Run every 6 hours (default)
AGENT_FEEDBACK_TIMEOUT=120      # Timeout in seconds (default: 2 minutes)
BACKFILL_API_KEY=<your-api-key> # API key for authentication
```

## Schedule

- **Default**: Every 6 hours
- **Configurable**: Set `AGENT_FEEDBACK_EVERY_HOURS` to adjust frequency
- **First run**: Immediately on container start
- **Subsequent runs**: Every N hours on the hour

## Monitoring

### Logs

View aggregation logs:
```bash
docker logs applylens-agent-feedback-cron -f
```

Expected output:
```
2025-11-20 14:00:00 [INFO] 🚀 Agent Feedback Aggregator starting
2025-11-20 14:00:00 [INFO]    API URL: http://applylens-api-prod:8003/api/v2/agent/feedback/aggregate
2025-11-20 14:00:00 [INFO]    Interval: Every 6 hour(s)
2025-11-20 14:00:00 [INFO] ⏰ Running initial aggregation...
2025-11-20 14:00:00 [INFO] 🔄 Calling http://applylens-api-prod:8003/api/v2/agent/feedback/aggregate
2025-11-20 14:00:05 [INFO] ✅ Aggregation completed successfully
2025-11-20 14:00:05 [INFO]    Response: {...}
2025-11-20 14:00:05 [INFO] ⏰ Next run scheduled for 2025-11-20 20:00:00
```

### Health Check

Docker automatically monitors container health:
```bash
docker ps --filter "name=agent-feedback-cron" --format "table {{.Names}}\t{{.Status}}"
```

Expected: `Up X hours (healthy)`

### Manual Run

Trigger immediate aggregation:
```bash
docker exec applylens-agent-feedback-cron python /app/runner.py --once
```

## Troubleshooting

### Aggregation Fails

**Check API connectivity:**
```bash
docker exec applylens-agent-feedback-cron curl -f http://applylens-api-prod:8003/api/healthz
```

**Check API key:**
```bash
# View environment variables
docker exec applylens-agent-feedback-cron printenv | grep BACKFILL_API_KEY
```

### Container Not Running

**Check dependencies:**
```bash
# API must be healthy
docker ps --filter "name=applylens-api-prod" --format "table {{.Names}}\t{{.Status}}"
```

**Restart container:**
```bash
docker-compose -f docker-compose.prod.yml restart agent-feedback-cron
```

## Architecture

```
┌──────────────────────────────┐
│ agent-feedback-cron          │
│  (Python 3.11-slim)          │
│                              │
│  Every 6 hours:              │
│  ├─ Call /api/v2/agent/      │
│  │  feedback/aggregate       │
│  ├─ Log results              │
│  └─ Sleep until next run     │
└──────────────────────────────┘
           │
           │ HTTP POST
           ▼
┌──────────────────────────────┐
│ applylens-api-prod           │
│  (FastAPI)                   │
│                              │
│  /api/v2/agent/feedback/     │
│  aggregate                   │
│  ├─ Aggregate feedback       │
│  ├─ Update models            │
│  └─ Return summary           │
└──────────────────────────────┘
```

## Security

- **API Key**: Uses same `BACKFILL_API_KEY` as backfill service
- **Network**: Isolated on `applylens-prod` network (no external access)
- **Read-only volumes**: Application code mounted read-only

## Deployment

The service is automatically started with:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

To deploy updates:
```bash
# Restart to pick up new code (volume is read-only, so edit files first)
docker-compose -f docker-compose.prod.yml restart agent-feedback-cron
```

## Development

Test locally:
```bash
# Set environment variables
export API_URL=http://localhost:8003/api/v2/agent/feedback/aggregate
export EVERY_HOURS=1
export TIMEOUT=30

# Run directly
python infra/agent-feedback-cron/runner.py
```
