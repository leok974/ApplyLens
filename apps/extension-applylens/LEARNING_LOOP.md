# ApplyLens Companion - Learning Loop

**Version:** 1.0.0
**Updated:** 2025-11-12
**Summary:** Learning loop for smarter, privacy-aware autofill across Companion + ApplyLens backend.

---

## Goals

### Primary Objectives
- **Improve autofill accuracy and speed** over time per user and per site
- **Reduce user edits** to generated answers while staying safe and on-brand
- **Capture site-specific quirks** (ATS platforms) without storing raw PII

### What Is Learned

#### Field Mapping
- `selector → semantic field` (first_name, email, portfolio, cover_letter, etc.)

#### Value Generation
- **Tone, length, keywords, and phrasing** that work best for a given company/role

#### Success Proxy Signals
- `time_to_fill`
- `edit_rate` (kept vs overwritten)
- `validation_success`
- Later recruitment outcomes (optional/linkable)

#### Per-Site Quirks
- Workday/Greenhouse/Lever/SmartRecruiters field naming patterns
- Validation rules (required, max_length, regex)
- Widget quirks (textarea vs rich text, multi-step forms)

---

## Signals

### Client Extension

**Fields Captured:**
- `field_map_suggestions` - Initial mapping guesses
- `field_map_final` - User-confirmed mappings
- `value_edit_distance` - Levenshtein distance between generated and final
- `fill_duration_ms` - Time from scan to submit
- `tab_switch_count` - User context switches
- `nudge_clicked` - Whether user accepted suggestions
- `site_fingerprint` - Privacy-safe site identifier

**Site Fingerprint Components:**
- `host` - Domain only (no subdomains beyond TLD+1)
- `form_schema_hash` - Hash of field selectors/types
- ⚠️ **Never store raw full URLs; no query params or paths**

**PII Rules:**
- ❌ Do not store raw values (email, phone, address, free text)
- ✅ Store boolean or aggregate flags only
- Example: `email_provided=1` instead of actual email

### Server (ApplyLens API)

**Events:**
- `autofill_event` - Per-run telemetry
- `autofill_outcome` - Success/failure status

**Optional Links:**
- Link `autofill_event` to `application` (company, role)
- Use downstream outcomes later (reply rates, interview, offer)

---

## Data Model

### Tables

#### `form_profiles`
**Purpose:** Per host + schema canonical mappings and performance stats

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `host` | `text` | Domain (e.g., jobs.lever.co) |
| `schema_hash` | `text` | Hash of form structure |
| `fields` | `jsonb` | Canonical selector→semantic mapping w/ confidences |
| `success_rate` | `numeric` | % of successful autofills |
| `avg_edit_chars` | `numeric` | Average characters edited per run |
| `avg_duration_ms` | `integer` | Average time to complete |
| `last_seen_at` | `timestamptz` | Last autofill on this form |
| `created_at` | `timestamptz` | First seen |

#### `autofill_events`
**Purpose:** Per-autofill run telemetry

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Event ID |
| `user_id` | `uuid` | User who triggered autofill |
| `host` | `text` | Domain |
| `schema_hash` | `text` | Form schema hash |
| `suggested_map` | `jsonb` | selector→semantic suggested |
| `final_map` | `jsonb` | selector→semantic actually used |
| `gen_style_id` | `text` | Generation style variant used |
| `edit_stats` | `jsonb` | Per-field edit_distance, chars_added, chars_deleted |
| `duration_ms` | `integer` | Total time from scan to fill |
| `validation_errors` | `jsonb` | Field-level validation failures |
| `status` | `text` | ok, validation_error, cancelled |
| `created_at` | `timestamptz` | Timestamp |
| `application_id` | `uuid` (nullable) | Link to ExtensionApplication |

#### `gen_styles`
**Purpose:** Autofill style variants (prompt presets/features)

| Column | Type | Description |
|--------|------|-------------|
| `id` | `text` | Style ID (e.g., concise_bullets_v1) |
| `name` | `text` | Human-readable name |
| `temperature` | `numeric` | LLM temperature |
| `tone` | `text` | concise, narrative, confident |
| `format` | `text` | bullets, paragraph |
| `length_hint` | `text` | short, medium, long |
| `keywords_json` | `jsonb` | ATS keywords or skills focus |
| `prior_weight` | `numeric` | Bandit prior for selection |
| `created_at` | `timestamptz` | Created |
| `updated_at` | `timestamptz` | Last updated |

**Relations Note:** `ExtensionApplication` and `ExtensionOutreach` tables already exist; `autofill_events` may optionally reference Application rows.

---

## Learning Loops

### Extension (Local)

**Storage:** IndexedDB
**Key:** `FormMemory`
**Index:** `host + schema_hash`

**Value Structure:**
```json
{
  "selector_map": { "input[name='firstName']": "first_name" },
  "style_prefs": { "tone": "concise", "format": "bullets" },
  "stats": { "success_count": 12, "last_used_at": "2025-11-12T..." }
}
```

**Behavior:**
1. **On scan:** Load FormMemory for `host+schema_hash` and rank known mappings first
2. **If mapping missing:** Fall back to heuristics and store new mapping when user confirms
3. **Track per-field edit distance** and durations; adjust local defaults accordingly
4. **Periodically sync** anonymized aggregates to server (if user opt-in is enabled)

### Server (Tenant-Wide)

**Batch Job:** Nightly `AutofillAggregator`

**Inputs:**
- `autofill_events`
- `form_profiles`
- `gen_styles`

**Steps:**
1. Group events by `host + schema_hash`
2. Compute canonical mapping per semantic field (top selectors by support & success)
3. Estimate `success_rate`, `avg_edit_chars`, `avg_duration_ms`
4. Write or update `form_profiles` rows
5. Update `gen_styles` priors based on style performance per host/schema
6. Serve canonical mappings back to clients in shadow mode while logging edits

**Shadow Mode:**
- Provide canonical mapping and style hints, but always log user overrides
- Do not hard-fail if mapping is wrong
- **Goal:** Continuous improvement without blocking the user

---

## Generation

### Inputs
- `company_summary` - From posting or site snippet
- `role_requirements` - Skills, level, location
- `user_profile_highlights` - Resume/ApplyLens profile
- `known_site_constraints` - Max length, required fields
- `style_hint` - From `gen_styles` + host history

### Style Bandit

**Method:** Epsilon-greedy or Thompson sampling
**Arms:** `gen_styles` rows

**Reward Signal:**
- `inverse_edit_distance` - Less editing = higher reward
- `success_flag` - No validation errors
- `time_saved` - vs baseline/no-autofill

### Guardrails
- ✅ Respect max characters per field
- ✅ No unsupported links if field forbids URLs
- ✅ No fabricated employment or degrees
- ✅ Consistently replace company name and role placeholders safely
- ✅ Basic profanity / unsafe content filter

---

## Metrics & Evaluation

### Prometheus Metrics
```
applylens_autofill_runs_total{status}
applylens_autofill_edit_chars_total
applylens_autofill_edit_chars_per_run
applylens_autofill_success_ratio
applylens_autofill_time_ms_bucket
```

### Grafana Panels
- **Autofill runs by status** (stacked) over time
- **Success rate by host** and by ATS vendor
- **Edit distance trend** (p50/p90) overall and per host
- **Time-to-fill distribution** (p50/p90)
- **Style variant win-rates** (which gen_styles are winning)

### Offline Evaluation

**Dataset Size:** 50 curated samples
**Description:** Real ATS schemas and fields across top vendors

**Checks:**
- All required fields populated
- No field exceeds max length
- Pattern/regex constraints respected (e.g., email, phone)
- No obviously unsafe content

---

## Privacy & Safety

### Opt-In Model

**Extension:**
- Toggle in popup: `Improve autofill using my anonymous data`
- Button: `Reset learning` clears local IndexedDB

**Web Settings:**
- Mirror toggle under Settings → Companion
- Show last sync time and ability to revoke

### PII Policies
- ❌ **No raw PII values** stored in telemetry (names, emails, phone, addresses, free-text content)
- ✅ **Store semantic presence flags** and aggregates only (e.g., `has_cover_letter=1`)
- ✅ **Server-side aggregation is per-tenant**; host-level models do not expose individual user traces

### User Controls
- **Reset local learning** - Clear FormMemory in extension
- **Server-side delete** of `autofill_events` for a given user_id (future/optional)

### Security
- Reuse existing CSRF + M2M protections
- Learning endpoints protected via authenticated user context and/or appropriate API keys
- Rate-limits on learning sync endpoints

---

## API Surface

### New Routes

#### `POST /api/extension/learning/sync`
**Purpose:** Ingest anonymized per-run learning signals from extension

**Body Example:**
```json
{
  "host": "example.com",
  "schema_hash": "abc123",
  "events": [
    {
      "suggested_map": { "input[name='q1']": "first_name" },
      "final_map": { "input[name='q1']": "first_name" },
      "gen_style_id": "concise_bullets_v1",
      "edit_stats": {
        "total_chars_added": 12,
        "total_chars_deleted": 4
      },
      "duration_ms": 180000,
      "validation_errors": []
    }
  ]
}
```

#### `GET /api/extension/learning/profile`
**Purpose:** Return canonical mapping + style hints for a given host + schema

**Query Params:**
- `host`
- `schema_hash`

**Response Example:**
```json
{
  "host": "example.com",
  "schema_hash": "abc123",
  "canonical_map": {
    "input[name='firstName']": "first_name",
    "input[name='lastName']": "last_name"
  },
  "style_hint": {
    "gen_style_id": "concise_bullets_v2",
    "confidence": 0.82
  }
}
```

---

## Work Items

### `apps/extension-applylens`
- [ ] Implement FormMemory in IndexedDB keyed by `host+schema_hash`
- [ ] Plug FormMemory into `scanAndSuggest()` ranking logic
- [ ] Track per-field `edit_stats` (edit distance, chars added/removed)
- [ ] Add settings toggles for `Improve autofill` and `Reset learning`
- [ ] Implement periodic `POST /api/extension/learning/sync` with anonymized aggregates

### `services/api`
- [ ] Add tables: `form_profiles`, `autofill_events`, `gen_styles` (Alembic migrations)
- [ ] Implement `POST /api/extension/learning/sync` handler with validation + auth
- [ ] Implement `GET /api/extension/learning/profile` handler backed by `form_profiles`
- [ ] Implement nightly `AutofillAggregator` job (can share pattern with backfill scheduler)
- [ ] Wire Prometheus counters and histograms for new metrics

### `apps/web`
- [ ] Extend Companion Settings page with: opt-in toggle, reset button, last sync time
- [ ] Add host-level view: top sites and success rates (read-only from API)
- [ ] Display a simple `Avg time saved per application` stat based on duration deltas

### Infrastructure
- [ ] Add cron-like container/service for nightly `AutofillAggregator`
- [ ] Expose new metrics to Prometheus scrape configs
- [ ] Add a dedicated `Companion` row in Grafana dashboard for autofill metrics

---

## Fast Wins

1. **Implement local-only FormMemory** in extension (no server calls yet)
2. **Request canonical mapping from server** if available; otherwise fall back to local/heuristics
3. **Start logging `edit_distance` and `validation_errors`** into Prometheus and build a simple `Autofill Quality` panel

---

## Next Steps

1. Review and approve this design with team
2. Create implementation tickets for each work item
3. Start with fast wins (local FormMemory + basic metrics)
4. Iterate in weekly sprints with user feedback
5. Monitor metrics and adjust learning parameters based on real-world performance
