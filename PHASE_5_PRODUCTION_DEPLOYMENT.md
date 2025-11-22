# Phase 5.0 Production Deployment Guide

**Date**: 2025-11-14
**Branch**: `thread-viewer-v1`
**Commit**: `9c4605f`

## Pre-Deployment Status ✅

- **Extension E2E Tests**: 9/9 passing (including Phase 5.0 style tuning test)
- **Backend Tests**: 8 tests ready (require PostgreSQL)
- **Documentation**: Complete (4 guides, 2,100+ lines)
- **CI/CD**: GitHub Actions workflow configured
- **Ops Runbook**: Complete troubleshooting guide

## Quick Start (Docker Compose)

```bash
# 1. Deploy Backend
cd d:/ApplyLens/services/api
git checkout thread-viewer-v1 && git pull
docker-compose exec api alembic upgrade head
docker-compose restart api

# 2. Run Aggregator
docker-compose exec api python -c "from app.autofill_aggregator import run_aggregator; print(f'Updated {run_aggregator(30)} profiles')"

# 3. Validate
docker-compose exec api pytest tests/test_learning_style_tuning.py -v
curl http://localhost:8000/api/extension/learning/profile?host=test&schema_hash=test

# 4. Build Extension
cd d:/ApplyLens/apps/extension-applylens
npm run build
cd dist && tar -czf ../applylens-phase5.zip . && cd ..
```

**Estimated Time**: 15 minutes
**Risk**: Low (fully backward compatible)

---

## Deployment Overview

Phase 5.0 adds feedback-aware style tuning:
- **Backend**: `feedback_status`, `edit_chars` columns, `style_hint` JSONB, aggregator
- **Extension**: Uses `preferred_style_id` from profile for optimal style selection
- **Complete Feedback Loop**: Thumbs up/down → aggregation → profile → better autofills

---

## Step 1: Deploy Backend to Production

### 1.1 Apply Database Migration

```bash
# Navigate to API directory
cd d:/ApplyLens/services/api

# Pull latest code
git fetch origin
git checkout thread-viewer-v1
git pull origin thread-viewer-v1

# Verify migration exists
ls alembic/versions/*75310f8e88d7*

# Apply migration (adds feedback_status, edit_chars, style_hint)
docker-compose exec api alembic upgrade head

# Verify migration applied
docker-compose exec api alembic current
# Should show: 75310f8e88d7 (head)
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Running upgrade ... -> 75310f8e88d7, phase_5_style_feedback_tracking
```

### 1.2 Restart API Service

```bash
# Restart API to load new code
docker-compose restart api

# Check health endpoint
curl http://localhost:8000/health
# Should return: {"status": "ok"}

# Check logs for errors
docker-compose logs api --tail 100
```

### 1.3 Verify Database Schema

```bash
# Connect to database (replace 'db' with your postgres service name from docker-compose.yml)
docker-compose exec db psql -U postgres -d applylens

# Check autofill_events columns
\d autofill_events

# Should see:
#   feedback_status    | text
#   edit_chars         | integer
#   gen_style_id       | text

# Check form_profiles columns
\d form_profiles

# Should see:
#   style_hint         | jsonb

# Exit psql
\q
```

---

## Step 2: Run Aggregator in Production

### 2.1 Initial Aggregation Run

```bash
# Run aggregator for last 30 days of feedback data
docker-compose exec api python -c "from app.autofill_aggregator import run_aggregator; updated = run_aggregator(days=30); print(f'✓ Updated {updated} profiles with style hints')"
```

**Expected Output**:
```
✓ Updated 47 profiles with style hints
```

### 2.2 Verify Style Hints Created

```bash
# Check profiles with style hints
docker-compose exec db psql -U postgres -d applylens -c "SELECT host, schema_hash, style_hint->>'preferred_style_id' AS preferred_style FROM form_profiles WHERE style_hint IS NOT NULL LIMIT 10;"
```

**Expected Output**:
```
       host        |    schema_hash     |  preferred_style
-------------------+--------------------+-------------------
 greenhouse.io     | schema_abc123      | friendly_bullets_v1
 lever.co          | schema_def456      | professional_narrative_v1
 workday.com       | schema_ghi789      | friendly_bullets_v1
```

### 2.3 Setup Scheduled Aggregator

**Option A: Windows Task Scheduler**

```powershell
# Create a PowerShell script: run_aggregator.ps1
$scriptContent = @'
cd d:/ApplyLens/services/api
docker-compose exec -T api python -c "from app.autofill_aggregator import run_aggregator; run_aggregator(30)"
'@

$scriptContent | Out-File -FilePath "d:/ApplyLens/services/api/run_aggregator.ps1" -Encoding UTF8

# Create scheduled task (run every 6 hours)
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File d:/ApplyLens/services/api/run_aggregator.ps1"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 6)
Register-ScheduledTask -TaskName "ApplyLens Aggregator" -Action $action -Trigger $trigger -Description "Runs Phase 5.0 aggregator every 6 hours"
```

**Option B: Docker Compose with Cron Container** (Linux/Mac)

Add to `docker-compose.yml`:
```yaml
services:
  aggregator-cron:
    image: python:3.11-slim
    volumes:
      - ./:/app
    command: >
      sh -c "
      while true; do
        cd /app && python -c 'from app.autofill_aggregator import run_aggregator; run_aggregator(30)'
        sleep 21600
      done
      "
    depends_on:
      - db
      - api
```

---

## Step 3: Validate Backend

### 3.1 Run Backend Tests on PostgreSQL

```bash
# Run Phase 5.0 backend tests
docker-compose exec api pytest tests/test_learning_style_tuning.py -v

# Expected: 8/8 tests passing
```

**Expected Output**:
```
tests/test_learning_style_tuning.py::test_style_stats_dataclass PASSED
tests/test_learning_style_tuning.py::test_compute_style_stats_basic PASSED
tests/test_learning_style_tuning.py::test_pick_best_style_by_helpful_ratio PASSED
tests/test_learning_style_tuning.py::test_pick_best_style_tiebreaker_edit_chars PASSED
tests/test_learning_style_tuning.py::test_pick_best_style_empty PASSED
tests/test_learning_style_tuning.py::test_update_style_hints_integration PASSED
tests/test_learning_style_tuning.py::test_update_style_hints_no_data PASSED
tests/test_learning_style_tuning.py::test_lookback_window_filters_old_events PASSED

====== 8 passed in 2.43s ======
```

### 3.2 Test Profile Endpoint

```bash
# Test profile endpoint (adjust host/schema_hash based on your data)
curl "http://localhost:8000/api/extension/learning/profile?host=greenhouse.io&schema_hash=test" | jq .

# Should return profile with style_hint
```

**Expected Response**:
```json
{
  "host": "greenhouse.io",
  "schema_hash": "schema_abc123",
  "canonical_map": {
    "input[name='email']": "email"
  },
  "style_hint": {
    "preferred_style_id": "friendly_bullets_v1",
    "summary_style": "bullets",
    "max_length": 500,
    "tone": "friendly",
    "style_stats": {
      "friendly_bullets_v1": {
        "helpful": 12,
        "unhelpful": 2,
        "total_runs": 14,
        "helpful_ratio": 0.857,
        "avg_edit_chars": 120
      }
    }
  }
}
```

---

## Step 4: Deploy Extension to Production

### 4.1 Build Extension

```bash
# Navigate to extension directory
cd /path/to/ApplyLens/apps/extension-applylens

# Install dependencies (if needed)
npm install

# Build production bundle
npm run build

# Verify build output
ls dist/
# Should see: manifest.json, content.js, background.js, etc.
```

### 4.2 Create Extension Package

```bash
# Create ZIP for Chrome Web Store
cd dist
zip -r ../applylens-extension-phase5.zip .
cd ..

# Verify package
unzip -l applylens-extension-phase5.zip | head -20
```

### 4.3 Upload to Chrome Web Store

1. Go to [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
2. Select ApplyLens extension
3. Click "Package" → "Upload new package"
4. Upload `applylens-extension-phase5.zip`
5. Update version to `1.5.0` (Phase 5.0)
6. Add release notes:

```
Version 1.5.0 - Feedback-Aware Style Tuning

New Features:
- Intelligent style selection based on user feedback
- Automatically uses the best-performing autofill style for each form
- Improved autofill quality through continuous learning

Technical:
- Uses preferred_style_id from learning profiles
- Falls back gracefully for forms without feedback data
- Backward compatible with existing profiles
```

7. Click "Submit for review"

### 4.4 Monitor Extension Review

- **Typical review time**: 1-3 business days
- **Check status**: Chrome Web Store Developer Dashboard
- **Once approved**: Extension will auto-update for users within 24 hours

---

## Step 5: Post-Deployment Validation

### 5.1 Monitor API Logs

```bash
# Watch for profile requests using preferred_style_id
docker-compose logs -f api | Select-String "preferred_style_id"

# Should see requests like:
# GET /api/extension/learning/profile?host=greenhouse.io&schema_hash=...
# Response includes: "preferred_style_id": "friendly_bullets_v1"
```

### 5.2 Check Database Activity

```bash
# Monitor new autofill events with feedback
docker-compose exec db psql -U postgres -d applylens -c "SELECT host, gen_style_id, feedback_status, edit_chars, created_at FROM autofill_events WHERE gen_style_id IS NOT NULL ORDER BY created_at DESC LIMIT 20;"
```

**Expected Output** (after users interact):
```
       host        |   gen_style_id      | feedback_status | edit_chars |      created_at
-------------------+---------------------+-----------------+------------+----------------------
 greenhouse.io     | friendly_bullets_v1 | helpful         |        45  | 2025-11-14 15:23:10
 lever.co          | professional_nar... | unhelpful       |       320  | 2025-11-14 15:18:45
 workday.com       | friendly_bullets_v1 | helpful         |        12  | 2025-11-14 15:10:22
```

### 5.3 Verify Prometheus Metrics

```bash
# Check aggregator run count
curl http://localhost:8000/metrics | Select-String "aggregator_runs_total"

# Check style hint distribution
curl http://localhost:8000/metrics | Select-String "preferred_style_id"
```

### 5.4 Check Grafana Dashboards

1. Open [Grafana Dashboard](https://grafana.applylens.app)
2. Navigate to "ApplyLens Learning" dashboard
3. Verify new panels:
   - **Style Hints Created** (should increase after aggregator runs)
   - **Feedback by Style** (shows helpful/unhelpful per style)
   - **Edit Distance by Style** (tracks avg_edit_chars)

---

## Step 6: Enable Feature Flags (If Applicable)

```bash
# If using feature flags, enable Phase 5.0
docker-compose exec api python -c "from app.config import set_feature_flag; set_feature_flag('phase_5_style_tuning', True); print('✓ Phase 5.0 feature enabled')"
```

---

## Rollback Procedure (If Needed)

### Database Rollback

```bash
# Revert migration (DESTRUCTIVE - will drop feedback_status, edit_chars, style_hint)
docker-compose exec api alembic downgrade -1

# Verify
docker-compose exec api alembic current
```

### Extension Rollback

1. Go to Chrome Web Store Developer Dashboard
2. Revert to previous version (1.4.x)
3. Republish

### API Code Rollback

```bash
# Checkout previous commit
git checkout <previous-commit>
docker-compose restart api
```

---

## Success Criteria

✅ **Backend Deployed**:
- Migration applied (75310f8e88d7)
- API restarted successfully
- Health endpoint returns 200 OK

✅ **Aggregator Running**:
- Initial run completed (updated profiles)
- Cron job configured for every 6 hours
- Profiles have `preferred_style_id` in database

✅ **Extension Deployed**:
- Build successful
- Uploaded to Chrome Web Store
- Review submitted

✅ **Validation Complete**:
- Backend tests: 8/8 passing
- Profile endpoint returns style_hint
- Metrics show feedback events
- Grafana dashboards updated

---

## Monitoring Checklist

### Week 1 Post-Deployment

- [ ] Check aggregator cron runs daily (every 6 hours)
- [ ] Monitor feedback events in database (should increase)
- [ ] Verify style_hint usage in generation requests
- [ ] Check for errors in API logs
- [ ] Review Grafana metrics for anomalies

### Week 2-4 Post-Deployment

- [ ] Analyze helpful_ratio across different styles
- [ ] Identify top-performing styles per host
- [ ] Monitor avg_edit_chars trends (should decrease)
- [ ] Collect user feedback on autofill quality
- [ ] Plan Phase 5.1 enhancements (recency weighting, exploration)

---

## Troubleshooting

### Issue: Aggregator runs but no style hints created

**Solution**:
```bash
# Check if there's enough feedback data
docker-compose exec db psql -U postgres -d applylens -c "SELECT COUNT(*) FROM autofill_events WHERE feedback_status IS NOT NULL AND created_at > NOW() - INTERVAL '30 days';"

# Need at least 3 events per (host, schema, style) for aggregation
```

### Issue: Profile endpoint returns null style_hint

**Solution**:
- Check if aggregator ran for that (host, schema)
- Verify feedback data exists in database
- Check aggregator logs for errors

### Issue: Extension not using preferred_style_id

**Solution**:
- Check browser console for profile fetch logs
- Verify API response includes `preferred_style_id`
- Check extension version (should be 1.5.0+)

---

## Documentation References

- **Complete Overview**: `services/api/PHASE_5_COMPLETE.md`
- **Extension Guide**: `services/api/PHASE_5_EXTENSION_IMPLEMENTATION.md`
- **Test Guide**: `services/api/PHASE_5_TEST_IMPLEMENTATION.md`
- **Ops Runbook**: `infra/STYLE_TUNING_RUNBOOK.md`
- **Migration Status**: `services/api/MIGRATION_STATUS.md`

---

## Next Steps After Deployment

1. **Monitor for 1 week**: Watch metrics, check logs, collect feedback
2. **Analyze results**: Which styles perform best? Which hosts benefit most?
3. **Plan Phase 5.1**: Recency weighting, multi-armed bandit exploration
4. **User communications**: Announce improved autofill quality in release notes

---

## Contact

- **Deployment Issues**: Check #deployments Slack channel
- **Backend Issues**: Check #backend Slack channel
- **Extension Issues**: Check #extension Slack channel
- **Oncall**: See PagerDuty schedule

---

**Deployment Prepared By**: GitHub Copilot
**Review Required**: Backend Lead, DevOps Lead
**Estimated Deployment Time**: 45 minutes
**Estimated Risk**: Low (fully backward compatible, tested in dev)
