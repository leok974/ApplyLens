# Companion Learning v1 - Quick Reference

**Date:** 2025-12-03
**Version:** v0.3 + Learning v1
**Status:** ✅ Complete

---

## What Was Built

### New Tables (PostgreSQL)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `form_profiles` | Aggregated form statistics per (host, schema_hash) | `canonical_map`, `style_hint`, `success_rate`, `avg_edit_chars` |
| `autofill_events` | Raw user events with timing and edit metrics | `suggested_map`, `final_map`, `edit_stats`, `duration_ms`, `policy` |
| `gen_styles` | Style variants for A/B testing | `tone`, `format`, `prior_weight` |

### New Endpoints

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| `POST` | `/api/extension/learning/sync` | Ingest batch of learning events | 202 Accepted |
| `GET` | `/api/extension/learning/profile` | Retrieve learned canonical mappings | 200 OK with `canonical_map` + `style_hint` |

### Extension Learning Flow

1. **Scan Form** → Build schema hash from field selectors
2. **Load Memory** (v0.3) → Instant suggestions from IndexedDB
3. **Generate AI** (if needed) → Fill gaps in memory
4. **User Reviews** → Edits suggestions in panel
5. **Apply to Page** → Fill form fields
   - Save to `memoryV3` (client-side IndexedDB)
   - Build learning event:
     - `suggestedMap`: {canonical → selector} from AI/memory
     - `finalMap`: {canonical → selector} after user edits
     - `editStats`: {charsAdded, charsDeleted}
     - `durationMs`: Time from scan to apply
     - `policy`: "exploit" (v0.3 always uses memory/AI, no exploration)
   - Queue event via `learning/client.js`
   - Flush to `/api/extension/learning/sync`

### Privacy Guarantees

**What Gets Sent:**
- ✅ Field selectors (CSS, XPath)
- ✅ Canonical field types (email, phone, cover_letter)
- ✅ Edit distance (numeric)
- ✅ Timing (milliseconds)
- ✅ Status codes

**What NEVER Gets Sent:**
- ❌ Raw field values (emails, names, phone numbers)
- ❌ Free-text answers
- ❌ Cover letter content
- ❌ Personal information

---

## How to Run

### Manual Aggregation

```bash
cd services/api
python scripts/aggregate_autofill_events.py --days 30
```

**Dry-run (preview changes):**
```bash
python scripts/aggregate_autofill_events.py --days 30 --dry-run
```

### Cron Setup (Nightly)

**Add to crontab:**
```bash
0 2 * * * cd /opt/applylens/services/api && venv/bin/python scripts/aggregate_autofill_events.py --days 30 >> logs/aggregator.log 2>&1
```

**Or via GitHub Actions:**
```yaml
name: Companion Learning Aggregator
on:
  schedule:
    - cron: '0 2 * * *'
jobs:
  aggregate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run aggregator
        run: |
          cd services/api
          python scripts/aggregate_autofill_events.py --days 30
```

---

## Testing

### Backend Tests

```bash
cd services/api

# Learning endpoint tests
pytest tests/test_learning_endpoints.py -v

# Phase 2 persistence tests
pytest tests/test_learning_phase2.py -v

# Aggregator tests
pytest tests/test_learning_style_tuning.py -v
```

**Expected:** All tests passing (PostgreSQL required for Phase 2+)

### Extension E2E Tests

```bash
cd apps/extension-applylens

# Learning sync tests
npx playwright test e2e/learning-sync.spec.ts

# Profile integration tests
npx playwright test e2e/learning-profile.spec.ts
```

---

## Metrics

### Check Prometheus Metrics

```bash
curl http://localhost:8003/metrics | grep applylens_autofill
```

**Key Metrics:**
```
applylens_autofill_runs_total{status="persisted"} 42
applylens_autofill_runs_total{status="error"} 0
applylens_autofill_policy_total{policy="exploit",host_family="lever",segment_key="default"} 15
```

### Database Queries

**Check recent events:**
```sql
SELECT host, schema_hash, status, created_at
FROM autofill_events
ORDER BY created_at DESC
LIMIT 10;
```

**Check profiles:**
```sql
SELECT host, schema_hash, success_rate, avg_edit_chars, last_seen_at
FROM form_profiles
ORDER BY last_seen_at DESC
LIMIT 10;
```

**Count events per host:**
```sql
SELECT host, COUNT(*) as event_count
FROM autofill_events
GROUP BY host
ORDER BY event_count DESC;
```

---

## Files Modified/Created

### Extension

**Modified:**
- `contentV2.js` - Added learning event tracking in Apply button
- `manifest.json` - Added `learning/utils.js` and `learning/client.js` to content scripts

**Existing (Reused):**
- `learning/client.js` - Event batching and API sync (Phase 1.5)
- `learning/utils.js` - simpleHash, editDistance (Phase 1.5)
- `learning/formMemory.js` - IndexedDB wrapper (Phase 1.5, separate from memoryV3)

### Backend

**Created:**
- `scripts/aggregate_autofill_events.py` - CLI for nightly aggregation

**Existing (Reused):**
- `app/models_learning_db.py` - SQLAlchemy models (Phases 1-5)
- `app/routers/extension_learning.py` - API endpoints (Phases 1-5)
- `app/autofill_aggregator.py` - Aggregation logic (Phases 2-5)
- `alembic/versions/0024_companion_learning_tables.py` - Migration (Phase 2)
- `alembic/versions/75310f8e88d7_phase_5_style_feedback_tracking.py` - Phase 5 columns

### Documentation

**Created:**
- `LEARNING_V1_COMPLETE.md` - Full implementation guide (this summary's parent doc)
- `LEARNING_V1_QUICKREF.md` - This file

**Existing:**
- `LEARNING_IMPLEMENTATION.md` - Phase 1.5 summary
- `LEARNING_LOOP.md` - Original design doc
- `V03_RELEASE_NOTES.md` - v0.3 memory system

---

## Next Steps

### Deployment

1. **Run migration** (if not already done):
   ```bash
   cd services/api
   alembic upgrade head
   ```

2. **Test locally**:
   - Load extension in Chrome
   - Fill a job form
   - Check console: `[Learning v1] Queued learning event`
   - Verify POST request to `/api/extension/learning/sync`

3. **Set up cron job** for nightly aggregation

4. **Monitor metrics** via Prometheus/Grafana

### Future Phases

**Phase 2: Profile Fetching (Planned)**
- Extension fetches `/api/extension/learning/profile` before scanning
- Uses `canonical_map` to guide field detection
- Applies `style_hint.preferred_style_id` for generation

**Phase 3: Style Bandit (Planned)**
- Epsilon-greedy exploration (90% exploit, 10% explore)
- Thompson sampling for advanced users
- Track `policy` in autofill_events

**Phase 4: Segment-Aware Tuning (Partial - Phase 5.2)**
- Backend already tracks `segment_key` (seniority level)
- Extension TODO: Pass job context to learning events

**Phase 5: User Feedback (Partial - Phase 5.0)**
- Backend already has `feedback_status` column
- Extension TODO: Add 👍/👎 buttons in panel

---

## Troubleshooting

### Learning events not syncing

1. Check console for errors: `[LearningClient] Sync failed: 401`
2. Verify `APPLYLENS_DEV=1` is set (for dev endpoints)
3. Check backend logs: `tail -f services/api/logs/uvicorn.log`
4. Test endpoint manually:
   ```bash
   curl -X POST http://localhost:8003/api/extension/learning/sync \
     -H "Content-Type: application/json" \
     -d '{"host":"test.com","schema_hash":"abc123","events":[]}'
   ```

### Aggregator fails

1. Check database connection:
   ```bash
   cd services/api
   python -c "from app.db import SessionLocal; db = SessionLocal(); print('OK')"
   ```
2. Verify migration applied:
   ```bash
   alembic current
   # Should show: 75310f8e88d7 (head)
   ```
3. Run with `--dry-run` to see errors without committing
4. Check for missing indexes: `\d autofill_events` in psql

### No profiles returned

1. Check if events exist:
   ```sql
   SELECT COUNT(*) FROM autofill_events WHERE host = 'jobs.lever.co';
   ```
2. Run aggregator manually:
   ```bash
   python scripts/aggregate_autofill_events.py --days 30
   ```
3. Verify profile created:
   ```sql
   SELECT * FROM form_profiles WHERE host = 'jobs.lever.co';
   ```
4. Check safety guards: `success_rate >= 0.6 AND avg_edit_chars <= 500`

---

## Related Docs

- **Full Guide:** `LEARNING_V1_COMPLETE.md`
- **v0.3 Memory:** `V03_RELEASE_NOTES.md`
- **Original Design:** `LEARNING_LOOP.md`
- **Style Tuning:** `docs/core/runbooks/STYLE_TUNING.md`
- **Phase 5 Details:** `services/api/PHASE_5_COMPLETE.md`
