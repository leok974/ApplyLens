# Style Tuning Operations Runbook

**Purpose**: This runbook provides operational procedures for verifying and debugging the Phase 5.0 feedback-aware style tuning system in ApplyLens Companion.

**Audience**: DevOps, SREs, Backend Engineers

**Last Updated**: November 14, 2025

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Verification in Staging](#verification-in-staging)
3. [Database Queries](#database-queries)
4. [Common Issues](#common-issues)
5. [Monitoring & Alerts](#monitoring--alerts)
6. [Rollback Procedures](#rollback-procedures)

---

## System Overview

### What is Style Tuning?

Phase 5.0 implements a feedback loop that automatically selects the best-performing autofill generation style for each ATS form:

1. **User autofills form** → Event logged with `gen_style_id`
2. **User provides feedback** → Thumbs up/down stored as `feedback_status`
3. **Aggregator runs** → Computes best style per (host, schema)
4. **Profile returns preferred style** → Extension uses it for next autofill
5. **Cycle repeats** → System improves over time

### Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **Backend API** | Returns `preferred_style_id` in profile | `/api/extension/learning/profile` |
| **Aggregator** | Computes style performance stats | `app/autofill_aggregator.py` |
| **Database** | Stores events and profiles | Tables: `autofill_events`, `form_profiles` |
| **Extension** | Uses preferred style in generation | `content.js`, `profileClient.ts` |

### Data Flow

```
AutofillEvent (gen_style_id, feedback_status, edit_chars)
    ↓
Aggregator (_compute_style_stats, _pick_best_style)
    ↓
FormProfile.style_hint (preferred_style_id, style_stats)
    ↓
GET /api/extension/learning/profile
    ↓
Extension (styleHint.preferredStyleId)
    ↓
POST /api/extension/generate-form-answers (style_hint.style_id)
    ↓
LLM Generation (uses preferred style)
```

---

## Verification in Staging

### Prerequisites

- Staging environment running with PostgreSQL
- Migration `75310f8e88d7` applied
- At least 5-10 autofill events with feedback

### Step-by-Step Verification

#### 1. Verify Migration Applied

```bash
# SSH into staging API container
docker exec -it applylens-api-staging bash

# Check alembic current revision
python -m alembic current

# Expected output should include:
# 75310f8e88d7 (head)
```

**Alternative**: Check database directly

```sql
SELECT version_num FROM alembic_version;
-- Should return: 75310f8e88d7 (or later)
```

#### 2. Generate Test Autofill Events

**Via Extension** (recommended):

1. Load extension in Chrome
2. Navigate to a test ATS form (e.g., `https://jobs.lever.co/example`)
3. Click ApplyLens icon → Scan & Autofill
4. Fill form (this creates an `AutofillEvent` with `gen_style_id`)
5. Repeat 3-5 times with different style presets

**Via API** (for bulk testing):

```bash
# POST to learning sync endpoint
curl -X POST https://staging-api.applylens.io/api/extension/learning/sync \
  -H "Content-Type: application/json" \
  -d '{
    "host": "jobs.lever.co",
    "schema_hash": "test-schema-001",
    "events": [
      {
        "event_type": "autofill",
        "gen_style_id": "friendly_bullets_v1",
        "timestamp": "2025-11-14T10:00:00Z",
        "fields_filled": 5,
        "time_saved_seconds": 45
      }
    ]
  }'
```

#### 3. Submit Feedback

**Via Extension UI**:

1. After autofill, click thumbs up 👍 or thumbs down 👎
2. This updates `AutofillEvent.feedback_status`

**Via API** (for testing):

```bash
# Update event with feedback
curl -X POST https://staging-api.applylens.io/api/extension/learning/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "EVENT_UUID_HERE",
    "feedback_status": "helpful",
    "edit_chars": 50
  }'
```

#### 4. Trigger Aggregator

**Scheduled** (production):

```bash
# Aggregator runs on cron schedule (default: every 6 hours)
# Check logs for:
docker logs applylens-autofill-aggregator | grep "Updated.*profiles with style hints"
```

**Manual** (staging/testing):

```bash
# Execute aggregator manually
docker exec applylens-api-staging python -c "
from app.autofill_aggregator import run_aggregator
updated = run_aggregator(days=30)
print(f'✅ Updated {updated} profiles with style hints')
"

# Expected output:
# ✅ Updated 3 profiles with style hints
```

**Verify Aggregator Environment Variables**:

```bash
docker exec applylens-api-staging env | grep COMPANION

# Should see:
# COMPANION_AUTOFILL_AGG_ENABLED=1
# COMPANION_AUTOFILL_AGG_LOOKBACK_DAYS=30
```

#### 5. Verify Profile Endpoint

**Test with curl**:

```bash
curl -s "https://staging-api.applylens.io/api/extension/learning/profile?host=jobs.lever.co&schema_hash=test-schema-001" | jq .

# Expected response:
{
  "host": "jobs.lever.co",
  "schema_hash": "test-schema-001",
  "canonical_map": { ... },
  "style_hint": {
    "preferred_style_id": "friendly_bullets_v1",  # ← Phase 5.0
    "summary_style": "bullets",
    "max_length": 500,
    "tone": "friendly",
    "style_stats": {
      "friendly_bullets_v1": {
        "helpful": 8,
        "unhelpful": 1,
        "total_runs": 10,
        "helpful_ratio": 0.8,
        "avg_edit_chars": 120,
        "last_seen": "2025-11-14T10:30:00Z"
      }
    }
  }
}
```

**Check for Phase 5.0 fields**:

```bash
# Should return the preferred_style_id
curl -s "https://staging-api.applylens.io/api/extension/learning/profile?host=jobs.lever.co&schema_hash=test-schema-001" \
  | jq -r '.style_hint.preferred_style_id'

# Example output:
# friendly_bullets_v1
```

#### 6. Verify Extension Integration

**Chrome DevTools Console**:

1. Open extension on a form
2. Open DevTools (F12) → Console tab
3. Trigger autofill
4. Look for log:

```
📊 Using tuned style: friendly_bullets_v1 (based on 3 style comparisons)
```

**Network Tab**:

1. DevTools → Network tab
2. Filter: `generate-form-answers`
3. Click autofill
4. Inspect request payload:

```json
{
  "job": { ... },
  "fields": [ ... ],
  "style_hint": {
    "style_id": "friendly_bullets_v1",  // ← Phase 5.0
    "summary_style": "bullets",
    "max_length": 500,
    "tone": "friendly"
  }
}
```

---

## Database Queries

### Inspect Recent Autofill Events

```sql
-- Show last 50 autofill events with feedback
SELECT 
  id,
  host,
  schema_hash,
  gen_style_id,
  feedback_status,
  edit_chars,
  created_at
FROM autofill_events
WHERE gen_style_id IS NOT NULL
ORDER BY created_at DESC
LIMIT 50;
```

**Expected output**:

```
id                  | host           | schema_hash    | gen_style_id          | feedback_status | edit_chars | created_at
--------------------|----------------|----------------|-----------------------|-----------------|------------|-------------------
uuid-1              | jobs.lever.co  | test-schema-1  | friendly_bullets_v1   | helpful         | 50         | 2025-11-14 10:30
uuid-2              | jobs.lever.co  | test-schema-1  | professional_para_v1  | unhelpful       | 300        | 2025-11-14 10:25
...
```

### Inspect Style Hints on Profiles

```sql
-- Show profiles with style hints
SELECT 
  host,
  schema_hash,
  style_hint->>'preferred_style_id' AS preferred_style,
  jsonb_object_keys(style_hint->'style_stats') AS styles_tested,
  updated_at
FROM form_profiles
WHERE style_hint IS NOT NULL
ORDER BY updated_at DESC
LIMIT 20;
```

**Expected output**:

```
host              | schema_hash    | preferred_style      | styles_tested           | updated_at
------------------|----------------|----------------------|-------------------------|-------------------
jobs.lever.co     | test-schema-1  | friendly_bullets_v1  | friendly_bullets_v1     | 2025-11-14 11:00
jobs.lever.co     | test-schema-1  | NULL                 | professional_para_v1    | 2025-11-14 11:00
greenhouse.io     | schema-abc     | concise_bullets_v2   | concise_bullets_v2      | 2025-11-14 10:45
...
```

### Count Events by Style

```sql
-- Aggregate events by style and feedback
SELECT 
  gen_style_id,
  feedback_status,
  COUNT(*) AS event_count,
  AVG(edit_chars) AS avg_edit_chars
FROM autofill_events
WHERE gen_style_id IS NOT NULL
  AND created_at > NOW() - INTERVAL '30 days'
GROUP BY gen_style_id, feedback_status
ORDER BY gen_style_id, feedback_status;
```

**Expected output**:

```
gen_style_id          | feedback_status | event_count | avg_edit_chars
----------------------|-----------------|-------------|---------------
friendly_bullets_v1   | helpful         | 12          | 120.5
friendly_bullets_v1   | unhelpful       | 2           | 350.0
professional_para_v1  | helpful         | 3           | 80.0
professional_para_v1  | unhelpful       | 9           | 450.2
```

### Find Forms Without Preferred Style

```sql
-- Find profiles that don't have a preferred style yet
SELECT 
  host,
  schema_hash,
  (SELECT COUNT(*) 
   FROM autofill_events ae 
   WHERE ae.host = fp.host 
     AND ae.schema_hash = fp.schema_hash) AS total_events,
  updated_at
FROM form_profiles fp
WHERE style_hint IS NULL
   OR style_hint->>'preferred_style_id' IS NULL
ORDER BY total_events DESC
LIMIT 10;
```

**Use case**: Find forms with autofill events but no style tuning (aggregator hasn't run yet)

### Detailed Style Stats for a Profile

```sql
-- Deep dive into style performance for a specific form
SELECT 
  host,
  schema_hash,
  style_hint->>'preferred_style_id' AS preferred,
  jsonb_pretty(style_hint->'style_stats') AS stats
FROM form_profiles
WHERE host = 'jobs.lever.co'
  AND schema_hash = 'test-schema-1';
```

**Expected output**:

```
host           | schema_hash    | preferred           | stats
---------------|----------------|---------------------|--------------------------------------------------
jobs.lever.co  | test-schema-1  | friendly_bullets_v1 | {
                                                        "friendly_bullets_v1": {
                                                            "helpful": 12,
                                                            "unhelpful": 2,
                                                            "total_runs": 14,
                                                            "helpful_ratio": 0.857,
                                                            "avg_edit_chars": 120.5,
                                                            "last_seen": "2025-11-14T10:30:00Z"
                                                        },
                                                        "professional_para_v1": {
                                                            "helpful": 3,
                                                            "unhelpful": 9,
                                                            "total_runs": 12,
                                                            "helpful_ratio": 0.25,
                                                            "avg_edit_chars": 450.0,
                                                            "last_seen": "2025-11-13T15:20:00Z"
                                                        }
                                                      }
```

---

## Common Issues

### Issue 1: No preferred_style_id in Profile

**Symptoms**:
- Profile endpoint returns `style_hint: null` or `preferred_style_id: null`
- Extension logs show "No preferred style available"

**Diagnosis**:

```sql
-- Check if events exist for this form
SELECT 
  COUNT(*) AS total_events,
  COUNT(CASE WHEN feedback_status IS NOT NULL THEN 1 END) AS events_with_feedback,
  COUNT(CASE WHEN gen_style_id IS NOT NULL THEN 1 END) AS events_with_style
FROM autofill_events
WHERE host = 'TARGET_HOST'
  AND schema_hash = 'TARGET_SCHEMA'
  AND created_at > NOW() - INTERVAL '30 days';
```

**Common Causes**:

1. **Not enough events**: Aggregator requires at least 3-5 events with `gen_style_id`
   - **Solution**: Generate more test events or wait for real user activity

2. **No feedback provided**: All events have `feedback_status = NULL`
   - **Solution**: Extension must send feedback updates

3. **Aggregator hasn't run**: Events exist but profile not updated
   - **Solution**: Trigger aggregator manually (see Step 4 above)

4. **Events outside lookback window**: All events older than 30 days
   - **Solution**: Increase `COMPANION_AUTOFILL_AGG_LOOKBACK_DAYS` or generate new events

**Fix**:

```bash
# Force aggregator run with longer lookback
docker exec applylens-api-staging python -c "
from app.autofill_aggregator import run_aggregator
updated = run_aggregator(days=90)  # Increase window
print(f'Updated {updated} profiles')
"
```

### Issue 2: Extension Not Sending style_id

**Symptoms**:
- Profile returns `preferred_style_id` correctly
- Generation request payload missing `style_hint.style_id`
- DevTools console shows no "Using tuned style" log

**Diagnosis**:

```javascript
// Check browser DevTools Console
// Extension should log:
console.log("📊 Using tuned style: ...");

// If missing, check Network tab:
// POST /api/extension/generate-form-answers
// Request Payload should have:
{
  "style_hint": {
    "style_id": "friendly_bullets_v1"  // ← Should be present
  }
}
```

**Common Causes**:

1. **Old extension version**: content.js doesn't have Phase 5.0 code
   - **Solution**: Rebuild extension with Phase 5.0 content.js

2. **Profile client not mapping**: `preferred_style_id` not converted to `preferredStyleId`
   - **Solution**: Check `src/learning/profileClient.ts` has Phase 5.0 mapping

3. **Content script not using preferredStyleId**: Logic not integrated
   - **Solution**: Verify content.js has `effectiveStyleHint` logic

**Fix**:

```bash
# Rebuild extension
cd apps/extension-applylens
npm run build

# Reload in Chrome
# chrome://extensions → ApplyLens → Reload button
```

### Issue 3: Aggregator Not Running

**Symptoms**:
- Many events in database with feedback
- No profiles have `preferred_style_id`
- Logs show no aggregator activity

**Diagnosis**:

```bash
# Check aggregator service status
docker ps | grep aggregator

# If not running:
# CONTAINER ID   IMAGE                         STATUS
# <none>         applylens-autofill-aggregator  Exited (1) 2 hours ago

# Check environment variable
docker exec applylens-api-staging env | grep COMPANION_AUTOFILL_AGG_ENABLED

# If empty or "0", aggregator is disabled
```

**Common Causes**:

1. **Aggregator disabled**: `COMPANION_AUTOFILL_AGG_ENABLED=0`
   - **Solution**: Set to `1` and restart

2. **Cron schedule misconfigured**: Job not triggering
   - **Solution**: Check cron logs or run manually

3. **Database connection error**: Aggregator can't connect
   - **Solution**: Check `DATABASE_URL` and PostgreSQL status

**Fix**:

```bash
# Enable aggregator
docker exec applylens-api-staging sh -c 'export COMPANION_AUTOFILL_AGG_ENABLED=1'

# Restart container
docker restart applylens-api-staging

# Manually trigger (for immediate results)
docker exec applylens-api-staging python -c "
from app.autofill_aggregator import run_aggregator
run_aggregator(30)
"
```

### Issue 4: Wrong Style Selected

**Symptoms**:
- Profile returns `preferred_style_id = "style_A"`
- Expected `style_B` based on feedback
- Style selection seems incorrect

**Diagnosis**:

```sql
-- Check actual stats for this form
SELECT 
  jsonb_pretty(style_hint->'style_stats') AS stats
FROM form_profiles
WHERE host = 'TARGET_HOST'
  AND schema_hash = 'TARGET_SCHEMA';
```

**Review Selection Algorithm**:

The aggregator selects best style by:
1. **Helpful ratio** (primary) - `helpful / total_runs`
2. **Avg edit chars** (tiebreaker) - Lower is better
3. **Total runs** (confidence) - Higher is better (min 3)

**Example Debug**:

```
Style A: 8/10 helpful (0.80), 120 avg_edit_chars, 10 runs → Chosen
Style B: 7/10 helpful (0.70), 50 avg_edit_chars, 10 runs  → Not chosen

Why? Style A has higher helpful_ratio (0.80 > 0.70)
```

**Fix**:

If the algorithm is working as designed but results seem suboptimal:
- Collect more feedback (increase sample size)
- Adjust ranking criteria in `_pick_best_style()` if needed
- Consider adding recency weighting (Phase 5.1 enhancement)

---

## Monitoring & Alerts

### Prometheus Metrics

**Existing Metrics** (reused from Phase 4):

```promql
# Aggregator runs
applylens_autofill_aggregator_runs_total

# Profiles updated
applylens_autofill_aggregator_profiles_updated_total

# Learning events
applylens_learning_events_total{event_type="autofill"}
applylens_learning_events_total{event_type="feedback"}
```

**Custom Queries**:

```promql
# Profile coverage (% with style hints)
count(form_profiles{style_hint != ""}) / count(form_profiles) * 100

# Average helpful ratio across all styles
sum(autofill_events{feedback_status="helpful"}) 
/ (sum(autofill_events{feedback_status="helpful"}) 
   + sum(autofill_events{feedback_status="unhelpful"}))

# Events with feedback in last 24h
increase(applylens_learning_events_total{event_type="feedback"}[24h])
```

### Grafana Dashboard

**Suggested Panels**:

1. **Style Tuning Coverage**
   - Query: `count(form_profiles{style_hint != ""}) / count(form_profiles)`
   - Type: Gauge
   - Threshold: Warn if < 50%, Critical if < 25%

2. **Aggregator Success Rate**
   - Query: `rate(applylens_autofill_aggregator_runs_total[5m])`
   - Type: Graph
   - Alert: If no runs in last 6 hours (scheduled interval)

3. **Feedback Volume**
   - Query: `sum by (feedback_status) (rate(autofill_events[5m]))`
   - Type: Stacked bar chart
   - Shows: helpful vs unhelpful ratio over time

4. **Top Performing Styles**
   - Query: Custom SQL → Top 10 styles by helpful_ratio
   - Type: Table
   - Refresh: Every 15 minutes

### Recommended Alerts

```yaml
# Grafana Alert: Aggregator Stalled
- alert: AggregatorNotRunning
  expr: time() - applylens_autofill_aggregator_last_run_timestamp > 21600  # 6 hours
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Autofill aggregator hasn't run in 6+ hours"
    description: "Check COMPANION_AUTOFILL_AGG_ENABLED and cron schedule"

# Grafana Alert: Low Feedback Rate
- alert: LowFeedbackRate
  expr: rate(applylens_learning_events_total{event_type="feedback"}[24h]) < 0.1
  for: 1h
  labels:
    severity: info
  annotations:
    summary: "Very low feedback volume in last 24h"
    description: "Users may not be providing feedback on autofills"

# Grafana Alert: Style Tuning Coverage Dropped
- alert: StyleTuningCoverageLow
  expr: (count(form_profiles{style_hint != ""}) / count(form_profiles)) < 0.3
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "Less than 30% of profiles have style hints"
    description: "Aggregator may be failing or disabled"
```

### Log Analysis

**Aggregator Success**:

```bash
# Look for successful runs
docker logs applylens-autofill-aggregator | grep "Updated.*profiles"

# Example output:
# 2025-11-14 11:00:00 INFO Updated 15 profiles with style hints
```

**Extension Usage**:

```bash
# Search for style_id in API logs
docker logs applylens-api-staging | grep "style_hint.style_id"

# Should see generation requests with tuned styles
```

---

## Rollback Procedures

### Emergency Rollback (Extension Only)

If Phase 5.0 extension causes issues:

```bash
# 1. Revert to previous extension version
cd apps/extension-applylens
git checkout PREVIOUS_TAG  # e.g., v1.4.0

# 2. Rebuild
npm run build

# 3. Deploy to Chrome Web Store
# OR distribute .zip to users
```

**Impact**: Extension will ignore `preferred_style_id`, use base `styleHint` or template defaults

**Backend**: No changes needed, continues working

### Database Rollback (Backend)

If Phase 5.0 backend migration causes issues:

```bash
# 1. SSH into production DB container
docker exec -it applylens-db-prod bash

# 2. Run downgrade migration
python -m alembic downgrade 75310f8e88d7^

# This removes:
# - autofill_events.feedback_status
# - autofill_events.edit_chars
# - form_profiles.style_hint
```

**Impact**: 
- Existing events and profiles remain intact
- Aggregator will fail if run (expects columns)
- API endpoint returns profiles without `preferred_style_id`
- Extension falls back gracefully (tested)

**Recovery**:

```bash
# To re-apply migration later:
python -m alembic upgrade head
```

### Disable Aggregator (Soft Rollback)

If aggregator is causing issues but want to keep data:

```bash
# Stop aggregator without removing data
docker exec applylens-api-staging sh -c 'export COMPANION_AUTOFILL_AGG_ENABLED=0'

# Restart container
docker restart applylens-api-staging
```

**Impact**:
- Stops new `preferred_style_id` updates
- Existing style hints remain in database
- Extension continues using cached preferred styles
- Can re-enable later without data loss

---

## Appendix: Quick Reference

### Environment Variables

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `COMPANION_AUTOFILL_AGG_ENABLED` | Enable aggregator | `0` | `1` |
| `COMPANION_AUTOFILL_AGG_LOOKBACK_DAYS` | Event lookback window | `30` | `90` |
| `DATABASE_URL` | PostgreSQL connection | - | `postgresql://user:pass@localhost/applylens` |

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/extension/learning/profile` | GET | Fetch profile with `preferred_style_id` |
| `/api/extension/learning/sync` | POST | Submit autofill events |
| `/api/extension/learning/feedback` | POST | Update feedback on events |
| `/api/extension/generate-form-answers` | POST | Generate autofill (uses `style_id`) |

### Key Files

| File | Purpose |
|------|---------|
| `app/autofill_aggregator.py` | Style stats computation and selection |
| `app/models_learning_db.py` | Database models |
| `alembic/versions/75310f8e88d7_*.py` | Phase 5.0 migration |
| `tests/test_learning_style_tuning.py` | Backend tests |
| `apps/extension-applylens/content.js` | Extension autofill logic |
| `apps/extension-applylens/e2e/autofill-style-tuning.spec.ts` | E2E tests |

### Support Contacts

| Issue Type | Contact |
|------------|---------|
| Database/Infrastructure | DevOps team |
| Backend Logic | Backend engineers |
| Extension Issues | Frontend/Extension team |
| Data Analysis | Analytics team |

---

**End of Runbook**

For detailed Phase 5.0 documentation, see `services/api/PHASE_5_COMPLETE.md`.
