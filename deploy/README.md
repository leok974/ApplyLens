# ApplyLens Release & Deployment

This directory contains scripts and workflows for promoting ApplyLens releases through environments.

## Release Channels

ApplyLens uses four deployment environments:

1. **Dev** - Local development and testing
2. **Staging** - Pre-production validation
3. **Canary** - Production with limited traffic (10-50%)
4. **Prod** - Full production deployment

## Promotion Path

```
dev → staging → canary (10%) → canary (50%) → prod (100%)
```

Each promotion includes:
- ✅ Automated test suite
- ✅ Database backup (for prod deployments)
- ✅ Smoke tests
- ✅ Monitoring (canary deployments)
- ✅ Automatic rollback on failure

## Usage

### Manual Promotion (CLI)

```bash
# Promote to staging
python deploy/scripts/promote_release.py staging

# Promote specific commit to canary with 10% traffic
python deploy/scripts/promote_release.py canary \
  --from-commit abc123 \
  --canary-pct 10

# Promote to prod (requires canary validation)
python deploy/scripts/promote_release.py prod

# Rollback production
python deploy/scripts/promote_release.py prod --rollback

# Dry run (no actual changes)
python deploy/scripts/promote_release.py staging --dry-run
```

### GitHub Actions (Automated)

Use the `release-promote` workflow:

1. Go to Actions → Release Promotion
2. Click "Run workflow"
3. Select target environment
4. (Optional) Specify commit SHA
5. (Optional) Set canary percentage
6. Run workflow

The workflow will:
- Run full test suite
- Execute database migrations
- Deploy to target environment
- Run smoke tests
- Monitor metrics (for canary)
- Notify via Slack
- Automatic rollback on failure

## Environment Configuration

Each environment uses separate configuration:

### Dev
- Database: `applylens_dev`
- Rate limit: 1000/min (relaxed)
- Features: All enabled
- Secrets: Dev placeholders

### Staging
- Database: `applylens_staging`
- Rate limit: 300/min
- Features: All enabled
- Secrets: Staging-specific

### Canary
- Database: `applylens_prod` (shared with prod)
- Rate limit: 60/min
- Traffic: 10-50% (configurable)
- Features: All enabled
- Secrets: Production secrets

### Prod
- Database: `applylens_prod`
- Rate limit: 60/min
- Traffic: 100%
- Features: All enabled
- Secrets: Production secrets

## Environment Variables

### Required

```bash
# Environment identifier
APPLYLENS_ENV=prod

# Database connection
DATABASE_URL=postgresql://user:pass@host/db

# Security secrets (MUST be different per environment)
APPLYLENS_HMAC_SECRET=your-hmac-secret-here
APPLYLENS_JWT_SECRET=your-jwt-secret-here
```

### Optional

```bash
# Redis cache
REDIS_URL=redis://localhost:6379/0

# Canary traffic percentage (canary env only)
APPLYLENS_CANARY_PERCENTAGE=25

# External service credentials
GMAIL_CREDENTIALS_PATH=/path/to/gmail.json
BIGQUERY_CREDENTIALS_PATH=/path/to/bigquery.json
ELASTICSEARCH_URL=https://es.example.com

# Feature flags
ENABLE_TELEMETRY=true
ENABLE_INCIDENTS=true
ENABLE_APPROVALS=true
ENABLE_POLICIES=true

# Rate limiting
MAX_CONCURRENT_REQUESTS=100

# Timeouts
REQUEST_TIMEOUT_SECONDS=30
AGENT_TIMEOUT_SECONDS=60
```

## Canary Deployments

Canary deployments allow safe validation in production with limited traffic:

### Phase 1: Initial Canary (10%)
```bash
python deploy/scripts/promote_release.py canary --canary-pct 10
```

- Deploy to production infrastructure
- Route 10% of traffic to new version
- Monitor for 24-48 hours
- Check error rates, latency, cost

### Phase 2: Expand Canary (50%)
```bash
python deploy/scripts/promote_release.py canary --canary-pct 50
```

- Increase to 50% traffic
- Monitor for 12-24 hours
- Validate stability at scale

### Phase 3: Full Production
```bash
python deploy/scripts/promote_release.py prod
```

- Deploy to 100% traffic
- Tag release (v1.0.0)
- Send notifications

### Rollback

If issues detected:
```bash
python deploy/scripts/promote_release.py canary --rollback
```

Automatic rollback triggers:
- Error rate > 5%
- Latency p95 > 2x baseline
- Cost increase > 50%
- Failed health checks

## Monitoring

### Health Checks

Each environment exposes `/health` endpoint:

```bash
curl https://staging.applylens.io/health
```

Returns:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "staging",
  "database": "connected",
  "redis": "connected"
}
```

### Canary Metrics

Monitor these metrics during canary:

- **Error Rate**: Should be < 1%
- **Latency p95**: Should be within 20% of baseline
- **Latency p99**: Should be within 50% of baseline
- **Cost**: Should be within 30% of baseline
- **Throughput**: Should match traffic percentage

### Dashboards

- **Grafana**: https://grafana.applylens.io/d/release-health
- **Prometheus**: https://prometheus.applylens.io

## Database Migrations

Migrations run automatically during promotion:

```bash
cd services/api
alembic upgrade head
```

For rollback:
```bash
alembic downgrade -1
```

## Rollback Procedures

### Automatic Rollback

Triggers on:
- Failed smoke tests
- High error rates (>5%)
- Failed health checks
- Deployment timeout

### Manual Rollback

```bash
# Rollback to previous deployment
python deploy/scripts/promote_release.py prod --rollback

# Rollback to specific commit
python deploy/scripts/promote_release.py prod \
  --rollback \
  --from-commit abc123
```

### Post-Rollback

1. Investigate root cause
2. Create incident record
3. Fix issue in dev/staging
4. Re-promote when ready

## Security

### Secrets Management

- **Never commit secrets to git**
- Use GitHub Secrets for CI/CD
- Rotate secrets quarterly
- Different secrets per environment

### Access Control

- Staging: All developers
- Canary: Team leads only
- Prod: On-call engineers only

### Audit Trail

All deployments are logged with:
- Commit SHA
- Deployed by (user)
- Timestamp
- Environment
- Canary percentage (if applicable)

## Troubleshooting

### Promotion Failed

Check:
1. Test suite passed?
2. Database migrations successful?
3. Secrets configured correctly?
4. Health check passing?

### Canary Issues

Monitor:
1. Error logs (CloudWatch/DataDog)
2. Grafana dashboards
3. Slack #ops-alerts channel

### Database Connection Errors

Verify:
1. `DATABASE_URL` is correct
2. Database is accessible from environment
3. Migrations are up to date

### Smoke Tests Failing

Check:
1. Service is fully started (wait 30s)
2. Health endpoint is accessible
3. No blocking migrations

## Support

- **Slack**: #ops-deploys
- **On-Call**: PagerDuty rotation
- **Runbook**: docs/PRODUCTION_HANDBOOK.md
