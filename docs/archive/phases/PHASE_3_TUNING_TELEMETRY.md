# Phase 3 – Tuning & Telemetry for Companion Autofill

**Goal:**
Prove (with data) that the Companion learning loop actually improves autofill quality and speed, and give myself the tools to tune it safely (feature flags, dashboards, thresholds).

This phase focuses on **metrics, dashboards, and tuning levers**, not new features.

---

## 0. Scope & Assumptions

- Phase 1.x + 2.x are implemented:
  - Extension sends learning events.
  - Backend persists `autofill_events`.
  - Aggregator populates `form_profiles` on a schedule.
  - `/api/extension/learning/profile` returns quality-gated profiles.
  - Extension uses profiles + FormMemory + heuristics.

- Autofill aggregator cron (`applylens-autofill-aggregator`) exists and runs on a 6h loop in prod.

Phase 3 will **not** change core behavior; it will:
- Instrument metrics.
- Add dashboards.
- Introduce safe tuning knobs.
- (Optionally) enable basic experiments.

---

## 1. Metrics to Track

### 1.1 Autofill Run Metrics (Backend)

**New Prometheus metrics (API):**

- `applylens_autofill_runs_total{status, host}`
  - `status` = `ok` | `validation_error` | `cancelled` | `error`
  - Incremented when:
    - A form run completes (ok or error).
    - A validation failure is detected (if/when we log it).
- `applylens_autofill_edit_chars_total{host}`
  - Sum of `(total_chars_added + total_chars_deleted)` per event.
- `applylens_autofill_time_ms_bucket{host, le}`
  - Histogram of `duration_ms` values.

**Derived ratios (Grafana):**

- `autofill_success_ratio = ok / (ok + validation_error)`
- `avg_edit_chars` per run (over time).
- `p50 / p90 duration_ms` per host.

---

### 1.2 Aggregator Metrics (Backend / Cron)

**New Prometheus metrics:**

- `applylens_autofill_agg_runs_total{status}`
  - `status` = `ok` | `err`
  - ✅ **Already implemented** in `services/api/app/autofill_aggregator.py`
- `applylens_autofill_profiles_updated_total`
  - Count of profiles updated per run.
  - ✅ **Already implemented** in `services/api/app/autofill_aggregator.py`
- Optional: `applylens_autofill_profiles_rejected_total`
  - Based on quality guards (low success rate / high edit chars).

---

### 1.3 Profile Usage Metrics (Extension → Backend)

Log per event (in `autofill_events` or a lightweight side metric):

- `profile_used` = `true|false` (was a non-empty canonical_map applied?)
- `source` = `server_only` | `local_only` | `merged` | `heuristics_only`

These will let us compare:

- With profile vs without profile.
- Server-only vs local-only vs merged vs heuristics-only.

---

## 2. Implementation Plan

### 2.1 Backend – Metrics Instrumentation

**Tasks**

- [ ] Add Prometheus counters/histograms in the **extension learning router** and/or wherever you finalize an autofill event:
  - `applylens_autofill_runs_total`
  - `applylens_autofill_edit_chars_total`
  - `applylens_autofill_time_ms_bucket`
- [x] Add counters to **aggregator**:
  - ✅ `applylens_autofill_agg_runs_total{status}` (commit: 831c170)
  - ✅ `applylens_autofill_profiles_updated_total` (commit: 831c170)
- [ ] Add optional counter:
  - `applylens_autofill_profiles_rejected_total` (increment when `/profile` rejects a profile due to quality guards).
- [x] Expose metrics via existing `/metrics` endpoint (same Prometheus registry).
  - ✅ **Already done** - aggregator metrics use same registry

**Copilot hint (backend):**

> Add Prometheus metrics for the Companion learning loop:
> - In the place where AutofillEvent is recorded, increment applylens_autofill_runs_total with labels (status, host), add to applylens_autofill_edit_chars_total, and observe duration in a histogram applylens_autofill_time_ms_bucket.
> - In the aggregator run_aggregator, increment applylens_autofill_agg_runs_total with status and add updated profile count to applylens_autofill_profiles_updated_total. ✅ **DONE**
> - In GET /profile quality guard branch, increment applylens_autofill_profiles_rejected_total when a profile is rejected due to low success_rate or high avg_edit_chars.

---

### 2.2 DB / Event-Level Fields (Optional but Nice)

**Tasks**

- [ ] Ensure `autofill_events` has fields (or a JSON blob) to store:
  - `profile_used`: bool
  - `profile_source`: enum (`server_only`, `local_only`, `merged`, `heuristics_only`)
- [ ] Update learning sync endpoint to accept these flags from extension (or derive on server if easier).

This will allow richer analytics later (dbt, BigQuery, etc.), but is optional for initial Phase 3.

---

### 2.3 Extension – Usage Labels

**Tasks**

- [ ] In content script, when building the effective mapping:
  - Determine `profile_source`:
    - `server_only`: non-empty server canonical map, no local overrides.
    - `local_only`: empty server map, non-empty local map.
    - `merged`: both server and local have entries.
    - `heuristics_only`: no server/local, heuristics used.
  - Attach `profile_used` + `profile_source` to the learning event payload.
- [ ] Ensure this flows through to backend as part of the learning sync event or autofill event.

This does **not** change behavior; it just labels what we did.

---

### 2.4 Grafana – Dashboards

**Create a new dashboard row:** `Companion – Autofill Tuning`

**Panels:**

1. **Autofill Volume (by host):**
   ```promql
   sum(rate(applylens_autofill_runs_total[1h])) by (host, status)
   ```

2. **Success Ratio (by host):**
   ```promql
   sum(rate(applylens_autofill_runs_total{status="ok"}[1h]))
   / sum(rate(applylens_autofill_runs_total[1h]))
   ```

3. **Edit Distance – p50/p90:**
   Use a recording rule or graph:
   ```promql
   avg_over_time(applylens_autofill_edit_chars_total[1h]) / max(autofill_runs_in_that_window)
   ```

4. **Time-to-Fill Histogram (global and per host):**
   Visualize `applylens_autofill_time_ms_bucket`.

5. **Aggregator Health:**
   ```promql
   rate(applylens_autofill_agg_runs_total[1h]) by (status)
   increase(applylens_autofill_profiles_updated_total[24h])
   ```

6. **Optional:**
   **Profile Usage Split:**
   Once `profile_used` and `profile_source` are in metrics or DB → pie/stacked bar for:
   `server_only / local_only / merged / heuristics_only`.

---

### 2.5 Flags & Tuning Levers

**Feature flags / Env:**

1. **`COMPANION_AUTOFILL_AGG_ENABLED`**
   - ✅ **Already present** (commit: 5a7072d); use as master on/off for aggregator.
   - Default: `1`
   - Location: `infra/.env.prod`

2. **`COMPANION_AUTOFILL_PROFILE_ENABLED` (new, optional)**
   - If `0`: extension still sends events, but backend always returns empty profile (full shadow mode).

3. **`COMPANION_AUTOFILL_QUALITY_MIN_SUCCESS` & `COMPANION_AUTOFILL_QUALITY_MAX_EDIT`**
   - Externalize the `0.6` / `500` thresholds.

**Tasks**

- [ ] Move hard-coded quality thresholds to env or a small config object.
- [ ] Add a single place in code that reads them and applies the guard.
- [ ] Document default values and safe ranges in README/PHASE doc.

---

## 3. Acceptance Criteria

Phase 3 is "done" when:

- [x] Metrics are visible in Prometheus:
  - [x] ✅ `applylens_autofill_agg_runs_total` (commit: 831c170)
  - [x] ✅ `applylens_autofill_profiles_updated_total` (commit: 831c170)
  - [ ] `applylens_autofill_runs_total`
  - [ ] `applylens_autofill_time_ms_bucket`
  - [ ] (Optional) `applylens_autofill_profiles_rejected_total`

- [ ] Grafana dashboard row exists with:
  - Autofill volume, success ratio, edit distance, time-to-fill, and aggregator health.

- [ ] Quality thresholds are configurable (env / config), not hard-coded.

- [ ] Flags allow:
  - Full shadow mode for profiles.
  - Easy disable of aggregation without tearing down services. ✅ **Already available**

- [ ] A short Ops note exists:
  - How to tell if Companion is helping (improved success ratio, lower edit chars / time).
  - How to rollback (flip flags) if metrics regress.

---

## 4. Future (Phase 3.x Ideas)

Not in scope for this phase, but worth parking:

- **3.1** – A/B styles (randomly choose between 2 `gen_style_id`s and compare edit distance).
- **3.2** – Host-level tuning (different quality thresholds per host).
- **3.3** – User-facing stats ("Companion saved you ~X keystrokes this week").

---

## 5. Current Implementation Status

### ✅ Completed (as of 2025-11-12)

1. **Aggregator Service** (commit: 5a7072d)
   - Docker service: `applylens-autofill-aggregator`
   - Schedule: Every 6 hours with jitter
   - Feature flag: `COMPANION_AUTOFILL_AGG_ENABLED=1`
   - Configuration: `AGG_EVERY_HOURS=6`, `AGG_LOOKBACK_DAYS=30`
   - Healthcheck: Database connectivity probe
   - Network: `applylens-prod`
   - Restart policy: `unless-stopped`

2. **Aggregator Metrics** (commit: 831c170)
   - `applylens_autofill_agg_runs_total{status="ok|err"}`
   - `applylens_autofill_profiles_updated_total`
   - Metrics exposed via `/metrics` endpoint
   - Error tracking with status labels

3. **Runner Integration** (commit: 831c170)
   - Calls actual `run_aggregator()` function
   - Structured logging: `[autofill-agg] {timestamp} {level} {message}`
   - Error handling with metrics tracking

### 🚧 In Progress

- Event-level metrics (autofill runs, edit distance, duration)
- Grafana dashboard creation
- Quality threshold externalization

### 📋 Next Steps

1. **Add event-level metrics** to learning router:
   - `applylens_autofill_runs_total{status, host}`
   - `applylens_autofill_edit_chars_total{host}`
   - `applylens_autofill_time_ms_bucket{host}`

2. **Create Grafana dashboard** with panels for:
   - Autofill volume by host/status
   - Success ratio trends
   - Edit distance p50/p90
   - Time-to-fill histogram
   - Aggregator health

3. **Externalize quality thresholds:**
   - Move `0.6` success rate threshold to env
   - Move `500` edit chars threshold to env
   - Document safe ranges

4. **Add shadow mode flag:**
   - `COMPANION_AUTOFILL_PROFILE_ENABLED=0` → always return empty profile
   - Allows testing without disrupting event collection

---

## 6. Operations Guide

### Starting the Aggregator

```powershell
docker compose -f docker-compose.prod.yml --env-file infra\.env.prod up -d autofill-aggregator
```

### Checking Metrics

```powershell
# View aggregator metrics
curl http://localhost:8003/metrics | Select-String "autofill_agg"

# Expected output:
# applylens_autofill_agg_runs_total{status="ok"} 5.0
# applylens_autofill_profiles_updated_total 42.0
```

### Viewing Logs

```powershell
docker logs -f applylens-autofill-aggregator

# Expected log format:
# [autofill-agg] 2025-11-12T20:30:00Z START autofill aggregator starting (enabled=True, interval=6h, lookback=30d)
# [autofill-agg] 2025-11-12T20:30:42Z OK aggregation complete: profiles=5 duration=2.34s lookback=30d
```

### Disabling Aggregation

```powershell
# In infra/.env.prod, set:
COMPANION_AUTOFILL_AGG_ENABLED=0

# Restart service
docker compose -f docker-compose.prod.yml --env-file infra\.env.prod restart autofill-aggregator
```

### Manual Aggregation Run

```powershell
# Trigger aggregation manually (for testing)
docker exec applylens-api-prod python -c "from app.autofill_aggregator import run_aggregator; print(run_aggregator(30))"
```

---

## 7. Testing Checklist

- [ ] Aggregator runs successfully every 6 hours
- [ ] Metrics appear in `/metrics` endpoint
- [ ] Metrics increment after each run
- [ ] Error status tracked when aggregation fails
- [ ] Feature flag disables aggregation when set to 0
- [ ] Healthcheck shows (healthy) in `docker ps`
- [ ] Logs show structured output with timestamps
- [ ] Manual run works via docker exec
- [ ] Grafana can query and display metrics
- [ ] Quality thresholds are configurable
