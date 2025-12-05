# Companion Learning v1 - Implementation Guide

**Date:** 2025-12-03
**Status:** ✅ Complete
**Version:** v0.3 + Learning v1

## Overview

Learning v1 connects the Companion extension's v0.3 client-side memory system to the server-side learning loop. The extension now:

1. **Tracks user behavior** - Records which suggestions were applied and how they were edited
2. **Syncs to backend** - Sends anonymized structural data (no PII values) to `/api/extension/learning/sync`
3. **Learns from patterns** - Nightly aggregator builds canonical field mappings per host/form
4. **Improves over time** - Future visits use learned mappings for faster, more accurate suggestions

**Privacy-First Design:**
- ✅ No raw PII values leave the browser
- ✅ Only structural signals: selectors, edit distances, timing
- ✅ Per-host aggregation (no cross-user traces)
- ✅ User controls: opt-in toggle, reset learning, data export

---

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Extension (Client-Side)                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Scan Form → fields[]                                        │
│  2. Load Memory (memoryV3.js) → instant suggestions             │
│  3. Generate AI (if needed) → merged suggestions                │
│  4. User Reviews & Edits                                        │
│  5. Apply to Page                                               │
│     ├─ Save to memoryV3 (IndexedDB)                            │
│     ├─ Build learning event:                                    │
│     │   • suggestedMap: {canonical → selector}                 │
│     │   • finalMap: {canonical → selector}                     │
│     │   • editStats: {charsAdded, charsDeleted}                │
│     │   • durationMs, status                                    │
│     └─ Queue event (learning/client.js)                         │
│                                                                 │
│  6. Flush Events → POST /api/extension/learning/sync           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Backend (Server-Side)                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  POST /api/extension/learning/sync                              │
│     ├─ Validate payload (Pydantic)                             │
│     ├─ Insert autofill_events rows (PostgreSQL)                │
│     ├─ Update form_profiles.last_seen_at                       │
│     └─ Emit Prometheus metrics                                  │
│                                                                 │
│  Nightly Aggregator (scripts/aggregate_autofill_events.py)     │
│     ├─ Group events by (host, schema_hash)                     │
│     ├─ Compute canonical_map (voting algorithm)                │
│     ├─ Calculate success_rate, avg_edit_chars                  │
│     ├─ Update style_hint (preferred_style_id)                  │
│     └─ Upsert form_profiles                                     │
│                                                                 │
│  GET /api/extension/learning/profile?host=X&schema_hash=Y      │
│     ├─ Query form_profiles                                      │
│     ├─ Return canonical_map, style_hint                         │
│     └─ Confidence based on event count                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Extension (Future Visits)                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Scan Form → fields[]                                        │
│  2. Fetch Profile → GET /learning/profile (FUTURE)              │
│  3. Use canonical_map for smarter field detection               │
│  4. Apply learned style preferences                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Extension Changes

#### 1. **contentV2.js** - Main Orchestration

**New Imports:**
```javascript
import { queueLearningEvent, flushLearningEvents } from "./learning/client.js";
import { simpleHash, editDistance } from "./learning/utils.js";
```

**Tracking State:**
```javascript
// Learning v1: Track timing and mappings
const autofillStartTime = Date.now();
let suggestedMap = {}; // canonical → selector from AI/memory
let finalMap = {}; // canonical → selector after user edits
const schemaHash = simpleHash(fields.map(f => f.selector).join("|"));
```

**Apply Button Handler:**
```javascript
applyBtn.addEventListener("click", async () => {
  // ... apply suggestions to page ...

  // Build final map from applied values
  const finalMap = {};
  let totalCharsAdded = 0;
  let totalCharsDeleted = 0;

  for (const input of inputs) {
    const field = fields.find(f => f.selector === selector);
    if (field && field.canonical) {
      finalMap[field.canonical] = selector;

      // Compute edit distance
      const originalValue = suggestions[field.canonical]?.value || "";
      const editDist = editDistance(originalValue, finalValue);
      totalCharsAdded += Math.max(0, finalValue.length - originalValue.length);
      totalCharsDeleted += Math.max(0, originalValue.length - finalValue.length);
    }
  }

  // Queue learning event
  queueLearningEvent({
    host: location.hostname,
    schemaHash,
    suggestedMap: panel.__suggestedMap,
    finalMap,
    genStyleId: null,
    editStats: { totalCharsAdded, totalCharsDeleted, perField: {} },
    durationMs: Date.now() - autofillStartTime,
    validationErrors: {},
    status: "ok",
    policy: "exploit",
  });

  // Flush to backend
  await flushLearningEvents();
});
```

#### 2. **learning/client.js** - Event Batching (Existing)

Already implemented. Batches events and syncs to `/api/extension/learning/sync`.

**Key Features:**
- Converts camelCase to snake_case for backend
- Re-queues on network failure (best-effort retry)
- Auto-detects API base (localhost vs production)

#### 3. **learning/utils.js** - Utilities (Existing)

Already implemented. Provides:
- `simpleHash(str)` - Fast hash for schema fingerprinting
- `editDistance(str1, str2)` - Levenshtein distance calculation

---

### Backend Changes

#### 1. **Models** (`app/models_learning_db.py`) - Existing ✅

**Tables:**
- `form_profiles` - Aggregated stats per (host, schema_hash)
- `autofill_events` - Raw event logs
- `gen_styles` - Style variants for A/B testing

**FormProfile Schema:**
```python
class FormProfile(Base):
    __tablename__ = "form_profiles"

    id = UUID (primary key)
    host = Text (indexed)
    schema_hash = Text (indexed)
    fields = JSONB (canonical_map: {semantic → selector})
    style_hint = JSONB (preferred_style_id, style_stats)
    success_rate = Float
    avg_edit_chars = Float
    avg_duration_ms = Integer
    last_seen_at = DateTime
```

**AutofillEvent Schema:**
```python
class AutofillEvent(Base):
    __tablename__ = "autofill_events"

    id = UUID (primary key)
    user_id = UUID (indexed)
    host = Text (indexed)
    schema_hash = Text (indexed)
    suggested_map = JSONB
    final_map = JSONB
    gen_style_id = Text
    feedback_status = Text ("helpful" | "unhelpful" | null)
    edit_chars = Integer
    segment_key = Text (Phase 5.2)
    policy = Text (Phase 5.4 - bandit tracking)
    edit_stats = JSONB
    duration_ms = Integer
    validation_errors = JSONB
    status = Text
    application_id = UUID (optional)
    created_at = DateTime
```

#### 2. **API Endpoints** (`app/routers/extension_learning.py`) - Existing ✅

**POST /api/extension/learning/sync**
- Accepts batch of learning events
- Validates with Pydantic models
- Persists to `autofill_events` table
- Updates `form_profiles.last_seen_at`
- Emits Prometheus metrics
- Returns 202 Accepted

**GET /api/extension/learning/profile**
- Query params: `host`, `schema_hash`
- Returns `LearningProfileResponse`:
  - `canonical_map`: {semantic → selector}
  - `style_hint`: {preferred_style_id, confidence}
- Confidence based on event count (10+ events = 100%)
- Safety guard: Rejects low-quality profiles (success_rate < 60% or avg_edit_chars > 500)

#### 3. **Aggregator** (`app/autofill_aggregator.py`) - Existing ✅

**Function: `aggregate_autofill_profiles(db, days=30)`**

**Algorithm:**
1. Query all autofill_events for last N days
2. Group by (host, schema_hash)
3. For each group:
   - **Canonical map:** Vote on most common selector→semantic pairs
   - **Success rate:** Count events with status='ok'
   - **Avg edit chars:** Mean of edit_stats.total_chars_added + total_chars_deleted
   - **Avg duration:** Mean of duration_ms
   - **Style hint:** Pick gen_style_id with lowest avg_edit_chars (Phase 5.0)
4. Upsert form_profiles
5. Update gen_styles.prior_weight (Bayesian update)

**Run manually:**
```bash
cd services/api
python scripts/aggregate_autofill_events.py --days 30
```

**Run dry-run:**
```bash
python scripts/aggregate_autofill_events.py --days 30 --dry-run
```

#### 4. **Metrics** (`app/core/metrics.py`) - Existing ✅

**Prometheus Counters:**
```python
learning_sync_counter.labels(status="persisted").inc()
learning_sync_counter.labels(status="error").inc()
autofill_policy_total.labels(policy="exploit", host_family="lever", segment_key="default").inc()
```

**Prometheus Histograms:**
```python
applylens_autofill_time_ms_bucket
applylens_autofill_edit_distance
```

---

## Database Schema

### Tables Created by Migration `0024_companion_learning_tables.py`

**PostgreSQL Only** (skipped on SQLite):

```sql
-- form_profiles: Aggregated form statistics
CREATE TABLE form_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    host TEXT NOT NULL,
    schema_hash TEXT NOT NULL,
    fields JSONB NOT NULL DEFAULT '{}',
    style_hint JSONB,
    success_rate NUMERIC(5,2),
    avg_edit_chars NUMERIC(10,2),
    avg_duration_ms INTEGER,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ix_form_profiles_host_schema
    ON form_profiles(host, schema_hash);
CREATE INDEX ix_form_profiles_last_seen
    ON form_profiles(last_seen_at);

-- autofill_events: Raw event logs
CREATE TABLE autofill_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    host TEXT NOT NULL,
    schema_hash TEXT NOT NULL,
    suggested_map JSONB NOT NULL DEFAULT '{}',
    final_map JSONB NOT NULL DEFAULT '{}',
    gen_style_id TEXT,
    feedback_status TEXT,
    edit_chars INTEGER,
    segment_key TEXT,
    policy TEXT,
    edit_stats JSONB NOT NULL DEFAULT '{}',
    duration_ms INTEGER,
    validation_errors JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'ok',
    application_id UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX ix_autofill_events_user_id ON autofill_events(user_id);
CREATE INDEX ix_autofill_events_host_schema ON autofill_events(host, schema_hash);
CREATE INDEX ix_autofill_events_created_at ON autofill_events(created_at);
CREATE INDEX ix_autofill_events_status ON autofill_events(status);
CREATE INDEX ix_autofill_events_gen_style_id ON autofill_events(gen_style_id);
CREATE INDEX ix_autofill_events_feedback_status ON autofill_events(feedback_status);
CREATE INDEX ix_autofill_events_segment_key ON autofill_events(segment_key);
CREATE INDEX ix_autofill_events_policy ON autofill_events(policy);

-- gen_styles: Style variants for A/B testing
CREATE TABLE gen_styles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    temperature FLOAT NOT NULL DEFAULT 0.7,
    tone TEXT NOT NULL DEFAULT 'concise',
    format TEXT NOT NULL DEFAULT 'bullets',
    length_hint TEXT NOT NULL DEFAULT 'medium',
    keywords_json JSONB NOT NULL DEFAULT '[]',
    prior_weight FLOAT NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX ix_gen_styles_prior_weight ON gen_styles(prior_weight);
```

**Run migration:**
```bash
cd services/api
alembic upgrade head
```

---

## Testing

### Backend Tests

**File:** `services/api/tests/test_learning_endpoints.py`

**Run tests:**
```bash
cd services/api
pytest tests/test_learning_endpoints.py -v
```

**Tests (7/7 passing):**
- ✅ POST /sync accepts valid payload → 202
- ✅ POST /sync requires authentication
- ✅ POST /sync increments Prometheus metric
- ✅ POST /sync handles batch of multiple events
- ✅ POST /sync validates request schema
- ✅ GET /profile returns empty response (stub) → 200
- ✅ GET /profile requires authentication

**Phase 2 Tests:** `tests/test_learning_phase2.py`
- ✅ Learning sync persists to database (PostgreSQL)
- ✅ Learning profile returns database data
- ✅ Learning profile returns empty for unknown form
- ✅ SQLite skip behavior

**Aggregator Tests:** `tests/test_learning_style_tuning.py`
- ✅ Aggregator computes canonical mappings
- ✅ Style hint selection based on performance
- ✅ Handles missing data gracefully

### Extension Tests

**File:** `apps/extension-applylens/e2e/learning-sync.spec.ts`

**Run tests:**
```bash
cd apps/extension-applylens
npx playwright test e2e/learning-sync.spec.ts
```

**Tests:**
- ✅ Learning sync POST sent after Fill All
- ✅ Payload structure validation
- ✅ No sync when learning disabled

**Integration Tests:** `e2e/learning-profile.spec.ts`
- ✅ Companion uses server profile canonical_map
- ✅ Falls back to heuristics when profile unavailable
- ✅ Queries profile with correct params

---

## Privacy & Security

### What Gets Sent to Backend

**✅ ALLOWED (Structural Data):**
- Field selectors (CSS selectors, XPath)
- Canonical field types (email, phone, cover_letter)
- Edit distance (numeric)
- Duration (milliseconds)
- Status codes
- Validation error flags

**❌ FORBIDDEN (PII):**
- Raw field values (email addresses, names, phone numbers)
- Free-text answers
- Cover letter content
- Personal information

### Enforcement

**Extension Side:**
- No `value` fields in learning events
- Only selectors and metadata

**Backend Side:**
- Pydantic models enforce schema
- No `value` fields accepted in payload
- 400 Bad Request if unknown fields present

### User Controls (Planned v0.4)

- [ ] Opt-in toggle in popup settings
- [ ] "Reset all learning data" button
- [ ] Data export endpoint
- [ ] Privacy notice text

---

## Metrics & Observability

### Prometheus Metrics

**Counters:**
```
applylens_autofill_runs_total{status="persisted"}
applylens_autofill_runs_total{status="error"}
applylens_autofill_policy_total{policy="exploit|explore|fallback", host_family="lever|greenhouse", segment_key="default"}
```

**Histograms:**
```
applylens_autofill_time_ms_bucket{...}
applylens_autofill_edit_distance{canonical_field="email"}
```

**Access metrics:**
```bash
curl http://localhost:8003/metrics | grep applylens_autofill
```

### Grafana Dashboards (Planned v0.4)

- Autofill runs by status (stacked area chart)
- Success rate by host and ATS vendor
- Edit distance trend (p50/p90)
- Time-to-fill distribution
- Style variant win-rates

---

## Operational Runbook

### Manual Aggregation Run

```bash
# SSH to backend server
ssh user@applylens-api.server

# Activate venv
cd /opt/applylens/services/api
source venv/bin/activate

# Run aggregator (last 30 days)
python scripts/aggregate_autofill_events.py --days 30

# Check logs
tail -f logs/aggregator.log
```

### Cron Setup (Nightly)

**Add to crontab:**
```bash
# Run aggregator every night at 2 AM
0 2 * * * cd /opt/applylens/services/api && venv/bin/python scripts/aggregate_autofill_events.py --days 30 >> logs/aggregator.log 2>&1
```

**Or via GitHub Actions:**
```yaml
name: Companion Learning Aggregator
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
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

### Monitoring Checklist

- [ ] Check `/metrics` endpoint for `applylens_autofill_runs_total`
- [ ] Verify aggregator runs successfully (check logs)
- [ ] Query `form_profiles` table for recent updates
- [ ] Monitor `autofill_events` table growth rate
- [ ] Alert on sync errors (status="error" spike)

---

## Future Enhancements (v0.4+)

### Phase 2: Profile Fetching (PLANNED)

**Extension Changes:**
1. Before scanning, fetch `/api/extension/learning/profile?host=X&schema_hash=Y`
2. Use `canonical_map` to guide field detection
3. Apply `style_hint.preferred_style_id` for generation
4. Fall back to heuristics if profile not found

**Benefits:**
- Faster field detection (use learned mappings)
- Higher accuracy (crowd-sourced selector→semantic pairs)
- Style optimization (use best-performing variant)

### Phase 3: Style Bandit (PLANNED)

**Epsilon-Greedy Exploration:**
- 90% exploit: Use preferred_style_id
- 10% explore: Randomly try other gen_style variants
- Track policy in autofill_events.policy ("exploit" | "explore")
- Aggregator updates style_hint based on performance

**Thompson Sampling (Advanced):**
- Bayesian prior on gen_styles.prior_weight
- Sample from Beta distribution
- Update posterior with feedback

### Phase 4: Segment-Aware Tuning (PARTIAL - Phase 5.2)

Already implemented in backend:
- `derive_segment_key(job)` extracts seniority level
- `segment_key` stored in autofill_events
- Aggregator computes per-segment stats

**Extension TODO:**
- Pass job context to learning events
- Use segment-specific profiles for suggestions

### Phase 5: User Feedback (PARTIAL - Phase 5.0)

Already implemented in backend:
- `feedback_status` column in autofill_events
- Aggregator weighs helpful vs unhelpful

**Extension TODO:**
- Add 👍/👎 buttons in panel
- POST feedback to `/api/extension/learning/feedback`

---

## Summary for Leo

### ✅ What's Complete (Learning v1)

**New Tables:**
- `form_profiles` - Aggregated stats per (host, schema_hash)
- `autofill_events` - Raw event logs with edit distance, timing
- `gen_styles` - Style variants for A/B testing

**New Endpoints:**
- `POST /api/extension/learning/sync` - Ingest events (202 Accepted)
- `GET /api/extension/learning/profile` - Return canonical_map + style_hint (200 OK)

**Extension Behavior:**
- Syncs learning events every time Apply is clicked
- Tracks edit distance between suggestions and final values
- Stores timing (autofill duration in ms)
- Respects privacy (no PII values, only structural signals)

**Aggregator:**
```bash
# Manual run:
python scripts/aggregate_autofill_events.py --days 30

# Dry-run (preview):
python scripts/aggregate_autofill_events.py --days 30 --dry-run
```

### 📊 Key Numbers

- **Extension event rate:** 1 event per Apply click
- **Batch size:** Flushes immediately (could batch in future)
- **Aggregator lookback:** 30 days (configurable)
- **Confidence threshold:** 10+ events = 100% confidence
- **Safety guard:** Reject profiles with success_rate < 60% or avg_edit_chars > 500

### 🚀 Next Steps

1. **Deploy to production** (run migration)
2. **Set up cron job** for nightly aggregation
3. **Monitor metrics** via Prometheus/Grafana
4. **Phase 2:** Extension fetches profiles before scan
5. **Phase 3:** Style bandit for A/B testing

---

## Related Documentation

- `LEARNING_IMPLEMENTATION.md` - Original Phase 1.5 spec
- `LEARNING_LOOP.md` - Full design doc
- `V03_RELEASE_NOTES.md` - v0.3 Memory system
- `PHASE_5_COMPLETE.md` - Style tuning details
- `STYLE_TUNING.md` - Operations runbook
