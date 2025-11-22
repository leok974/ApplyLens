# Phase 5.2: Segment-Aware Style Tuning

**Status**: ✅ Implementation Complete
**Date**: 2025-11-14

## Overview

Phase 5.2 adds segment-aware style tuning to the Companion learning system. Different styles may work better for different role levels (e.g., interns vs seniors). This phase introduces a new hierarchical fallback level between form-level and family-level recommendations.

## Key Concepts

### Segments

Segments are job role categories derived from job titles:
- **intern**: Internships, co-ops
- **junior**: Junior, entry-level roles
- **senior**: Senior, lead, principal roles
- **default**: Mid-level or unclear roles

### Hierarchical Selection (Phase 5.2)

1. **Form-level** (most specific): ≥5 runs on exact (host, schema_hash)
2. **Segment-level** (NEW): ≥5 runs for (family, segment) combination
3. **Family-level**: ≥10 runs for entire ATS family
4. **None**: Insufficient data at all levels

### Example Scenario

**New Greenhouse form for Senior Engineer role:**
- Form has 2 autofill runs → too sparse
- Segment ("greenhouse", "senior") has 15 runs with `style_professional` performing well
- **Result**: Use `style_professional` from segment-level stats
- **Benefit**: Cold-start form gets immediate recommendations from similar forms for the same role level

## Implementation

### 1. Data Model Changes

#### AutofillEvent Model
```python
# File: app/models_learning_db.py

class AutofillEvent(Base):
    __tablename__ = "autofill_events"

    # ... existing columns ...

    # Phase 5.2: Segment-aware tuning
    segment_key = Column(
        Text, nullable=True, index=True
    )  # "senior" | "junior" | "intern" | "default"

    __table_args__ = (
        # ... existing indexes ...
        Index("ix_autofill_events_segment_key", "segment_key"),
    )
```

#### Migration
```bash
# File: alembic/versions/a1b2c3d4e5f6_phase_52_segment_key.py

- Adds segment_key VARCHAR(128) column to autofill_events
- Creates index ix_autofill_events_segment_key
- Reversible downgrade removes index then column
```

### 2. Segment Derivation

#### Helper Function
```python
# File: app/autofill_aggregator.py

def derive_segment_key(job: Optional[dict]) -> Optional[str]:
    """
    Derive segment from job title.

    Returns:
        - "intern" if title contains "intern" or "co-op"
        - "junior" if title contains "junior", "jr", or "entry"
        - "senior" if title contains "senior", "sr", "lead", or "principal"
        - "default" for mid-level or unclear roles
        - None if job data is missing
    """
```

#### Learning Sync Integration
```python
# File: app/routers/extension_learning.py

@router.post("/learning/sync")
async def learning_sync(payload: LearningSyncRequest, ...):
    for event in payload.events:
        # Derive segment from job info
        segment_key = derive_segment_key(event.job)

        db_event = AutofillEvent(
            # ... existing fields ...
            segment_key=segment_key,  # Phase 5.2
        )
```

### 3. Segment Stats Aggregation

```python
# File: app/autofill_aggregator.py

def _compute_segment_style_stats(
    db: Session, lookback_days: int
) -> Dict[Tuple[str, str, str], StyleStats]:
    """
    Aggregate AutofillEvent by (host_family, segment_key, style_id).

    Returns:
        {
            ("greenhouse", "senior", "professional_v1"): StyleStats(...),
            ("greenhouse", "intern", "friendly_bullets_v1"): StyleStats(...),
        }
    """
```

**Key characteristics:**
- Filters events with `gen_style_id.isnot(None)` and `segment_key.isnot(None)`
- Groups by (family, segment, style) triple
- Aggregates helpful/unhelpful feedback and edit_chars
- Same structure as StyleStats used elsewhere

### 4. Hierarchical Selection Update

```python
def _pick_style_for_profile(
    host: str,
    schema_hash: str,
    form_stats: Dict[...],
    family_stats: Dict[...],
    segment_stats: Dict[...],  # NEW
    segment_key: Optional[str] = None,  # NEW
) -> Tuple[Optional[StyleStats], Dict[str, any]]:
    """
    Returns: (best_style, metadata)

    metadata = {
        "source": "form" | "segment" | "family" | None,
        "segment_key": segment_key if source=="segment"
    }
    """
```

**Selection logic:**
1. Check form-level: If any style ≥ MIN_FORM_RUNS (5), use form-level best
2. Check segment-level: If family & segment_key set, and any (family, segment, style) ≥ MIN_SEGMENT_RUNS (5), use segment-level best
3. Check family-level: If family set, and any (family, style) ≥ MIN_FAMILY_RUNS (10), use family-level best
4. Return None if all levels too sparse

### 5. Style Hint Enrichment

```python
# File: app/autofill_aggregator.py

def _update_style_hints(db: Session, lookback_days: int = 30) -> int:
    # Compute all three levels
    form_stats = _compute_style_stats(db, lookback_days)
    family_stats = _compute_family_style_stats(db, lookback_days)
    segment_stats = _compute_segment_style_stats(db, lookback_days)  # NEW

    for profile in profiles:
        # Derive segment_key for this profile
        segment_key = (
            db.query(AutofillEvent.segment_key)
            .filter(...)
            .order_by(func.count(...).desc())
            .group_by(AutofillEvent.segment_key)
            .first()
        )

        best, meta = _pick_style_for_profile(
            # ... form, family, segment stats ...
            segment_key=segment_key,
        )

        # Enrich style_hint
        hint["preferred_style_id"] = best.style_id
        hint["source"] = meta["source"]  # NEW: "form"/"segment"/"family"
        if meta["source"] == "segment":
            hint["segment_key"] = segment_key  # NEW
```

**style_hint JSON structure:**
```json
{
  "preferred_style_id": "professional_narrative_v1",
  "source": "segment",
  "segment_key": "senior",
  "style_stats": { ... }
}
```

## Testing

### Test Coverage

**File**: `tests/test_learning_style_tuning.py`

#### 1. Unit Test: Segment Derivation
```python
def test_derive_segment_key():
    # Validates job title classification
    assert derive_segment_key({"title": "Summer Intern"}) == "intern"
    assert derive_segment_key({"title": "Junior Developer"}) == "junior"
    assert derive_segment_key({"title": "Senior Engineer"}) == "senior"
    assert derive_segment_key({"title": "Software Engineer"}) == "default"
```

#### 2. Integration Test: Segment Stats Computation
```python
@pytest.mark.postgres
def test_compute_segment_style_stats(postgresql_db):
    # Creates events across multiple segments
    # Validates aggregation by (family, segment, style)
    # Verifies correct counts and metrics
```

#### 3. Integration Test: Segment Preference
```python
@pytest.mark.postgres
def test_segment_preferred_over_family_when_enough_data(postgresql_db):
    # Setup:
    #   Form: 3 runs (< MIN_FORM_RUNS)
    #   Segment (greenhouse, senior): 15 runs (>= MIN_SEGMENT_RUNS)
    #   Family (greenhouse): 20 runs (>= MIN_FAMILY_RUNS)
    # Expected: Use segment-level recommendation
    # Validates meta["source"] == "segment"
```

#### 4. Integration Test: Family Fallback
```python
@pytest.mark.postgres
def test_family_used_when_segment_too_sparse(postgresql_db):
    # Setup:
    #   Form: 2 runs
    #   Segment: 3 runs (< MIN_SEGMENT_RUNS)
    #   Family: 15 runs (>= MIN_FAMILY_RUNS)
    # Expected: Fall back to family-level
    # Validates meta["source"] == "family"
```

#### 5. Integration Test: No Recommendation
```python
@pytest.mark.postgres
def test_no_segment_no_family_returns_none(postgresql_db):
    # Setup: All levels below thresholds
    # Expected: Return (None, {"source": None})
```

### Running Tests

```bash
# Unit tests (no DB required)
python test_phase51_manual.py  # From Phase 5.1

# All learning tests (requires PostgreSQL)
python -m pytest tests/test_learning_style_tuning.py -v

# Only Phase 5.2 tests
python -m pytest tests/test_learning_style_tuning.py::test_derive_segment_key -v
python -m pytest tests/test_learning_style_tuning.py::test_compute_segment_style_stats -v
python -m pytest tests/test_learning_style_tuning.py::test_segment_preferred_over_family_when_enough_data -v
python -m pytest tests/test_learning_style_tuning.py::test_family_used_when_segment_too_sparse -v
python -m pytest tests/test_learning_style_tuning.py::test_no_segment_no_family_returns_none -v
```

## Deployment

### Migration Steps

1. **Run Migration**
   ```bash
   docker exec applylens-api-prod alembic upgrade head
   # Applies: a1b2c3d4e5f6_phase_52_segment_key
   ```

2. **Verify Schema**
   ```bash
   docker exec applylens-api-prod python -c "
   from app.models_learning_db import AutofillEvent
   from app.db import SessionLocal

   db = SessionLocal()
   result = db.execute('SELECT segment_key FROM autofill_events LIMIT 1')
   print('✅ segment_key column exists')
   "
   ```

3. **Backfill Segment Keys (Optional)**
   ```python
   # If you have existing events with application_id, derive segments retroactively
   from app.autofill_aggregator import derive_segment_key
   from app.models_learning_db import AutofillEvent
   from app.models import Application  # If you have job info linked

   events = db.query(AutofillEvent).filter(
       AutofillEvent.application_id.isnot(None),
       AutofillEvent.segment_key.is_(None)
   ).all()

   for event in events:
       app = db.query(Application).get(event.application_id)
       if app and app.job:
           event.segment_key = derive_segment_key(app.job)

   db.commit()
   print(f"Backfilled {len(events)} events")
   ```

4. **Run Aggregator**
   ```bash
   docker exec applylens-api-prod python -c "
   from app.autofill_aggregator import run_aggregator
   updated = run_aggregator(days=30)
   print(f'Phase 5.2 aggregation: {updated} profiles updated')
   "
   ```

5. **Verify Segment Recommendations**
   ```bash
   docker exec applylens-api-prod python -c "
   from app.db import SessionLocal
   from app.models_learning_db import FormProfile

   db = SessionLocal()

   # Check for segment-based recommendations
   profiles = db.query(FormProfile).filter(
       FormProfile.style_hint.isnot(None)
   ).all()

   segment_count = 0
   for p in profiles:
       hint = p.style_hint or {}
       if hint.get('source') == 'segment':
           segment_count += 1
           print(f'{p.host}/{p.schema_hash}:')
           print(f'  preferred={hint.get(\"preferred_style_id\")}')
           print(f'  segment={hint.get(\"segment_key\")}')

   print(f'\n{segment_count} profiles using segment-level recommendations')
   db.close()
   "
   ```

### Extension Integration (Future - Phase 5.3)

Phase 5.2 is **server-only**. The extension doesn't need changes because:
- Backend derives `segment_key` from job info
- Aggregator uses segment stats internally
- Profile endpoint returns single `preferred_style_id` (same as Phase 5.0/5.1)

**Future enhancement**: Extension could send `segment_key` explicitly, or request segment-specific recommendations per API call.

## Monitoring

### Metrics to Track

1. **Segment Distribution**
   ```sql
   SELECT
     segment_key,
     COUNT(*) as events,
     ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as pct
   FROM autofill_events
   WHERE segment_key IS NOT NULL
   GROUP BY segment_key
   ORDER BY events DESC;
   ```

   Expected distribution:
   - senior: 30-40%
   - default: 30-40%
   - junior: 15-25%
   - intern: 5-10%

2. **Recommendation Sources**
   ```sql
   SELECT
     style_hint->>'source' as source,
     COUNT(*) as profiles,
     ROUND(100.0 * COUNT(*) / SUM(COUNT(*) OVER(), 1) as pct
   FROM form_profiles
   WHERE style_hint IS NOT NULL
   GROUP BY 1
   ORDER BY profiles DESC;
   ```

   Target after Phase 5.2:
   - form: 30-40%
   - segment: 25-35% (NEW!)
   - family: 20-30%
   - Total coverage: ~85-95%

3. **Segment Performance**
   ```sql
   SELECT
     segment_key,
     COUNT(*) as total_runs,
     SUM(CASE WHEN feedback_status = 'helpful' THEN 1 ELSE 0 END) as helpful,
     ROUND(100.0 * SUM(CASE WHEN feedback_status = 'helpful' THEN 1 ELSE 0 END) / COUNT(*), 1) as helpful_pct
   FROM autofill_events
   WHERE segment_key IS NOT NULL
     AND feedback_status IS NOT NULL
   GROUP BY segment_key
   ORDER BY helpful_pct DESC;
   ```

### Prometheus Metrics

Add to `app/autofill_aggregator.py`:
```python
autofill_segment_stats_total = PrometheusCounter(
    "applylens_autofill_segment_stats_total",
    "Segment-level style stats computed",
    ["family", "segment"],
)

# In _compute_segment_style_stats:
for (family, segment, style_id), stats in segment_stats.items():
    autofill_segment_stats_total.labels(
        family=family, segment=segment
    ).inc(stats.total_runs)
```

### Grafana Dashboards

**Panel: Recommendation Source Breakdown**
```promql
sum by (source) (
  rate(applylens_autofill_profiles_updated_total[5m])
)
```

**Panel: Segment Coverage**
```promql
sum by (segment) (
  rate(applylens_autofill_segment_stats_total[5m])
)
```

## Validation Checklist

Before declaring Phase 5.2 complete:

- [x] **Data Model**
  - [x] `segment_key` column added to AutofillEvent
  - [x] Index created on `segment_key`
  - [x] Migration file created (a1b2c3d4e5f6)

- [x] **Segment Derivation**
  - [x] `derive_segment_key()` function implemented
  - [x] Handles intern/junior/senior/default cases
  - [x] Returns None for missing data

- [x] **Learning Sync**
  - [x] `/api/extension/learning/sync` derives and persists `segment_key`
  - [x] `job` field added to AutofillLearningEvent schema
  - [x] Backward compatible (job optional)

- [x] **Aggregation**
  - [x] `_compute_segment_style_stats()` implemented
  - [x] Aggregates by (family, segment, style)
  - [x] Filters events with segment_key set

- [x] **Selection Logic**
  - [x] `_pick_style_for_profile()` updated with segment fallback
  - [x] Returns (StyleStats, metadata) tuple
  - [x] Metadata includes source and segment_key
  - [x] MIN_SEGMENT_RUNS threshold added (5)

- [x] **Style Hints**
  - [x] `_update_style_hints()` computes segment_stats
  - [x] Derives segment_key for each profile
  - [x] Enriches hint with source and segment_key

- [x] **Tests**
  - [x] Unit test for derive_segment_key
  - [x] Integration test for segment stats computation
  - [x] Integration test for segment preference
  - [x] Integration test for family fallback
  - [x] Integration test for no recommendation

- [ ] **Deployment** (Pending)
  - [ ] Migration run in production
  - [ ] Aggregator executed with Phase 5.2 logic
  - [ ] Segment-level recommendations verified
  - [ ] Metrics collected

- [ ] **Monitoring** (Pending)
  - [ ] Segment distribution tracked
  - [ ] Recommendation source breakdown monitored
  - [ ] Segment performance analyzed

## Known Limitations

1. **Segment Derivation**: Simple keyword matching in job titles
   - May misclassify some roles
   - Doesn't account for discipline (e.g., ML vs frontend)
   - Future: Add more sophisticated NLP or use normalized_title from job processing

2. **Segment Stability**: Uses most common segment for a profile
   - If a form gets applications across multiple segments, recommendation may oscillate
   - Future: Track segment per event, not per profile

3. **Cold Start**: New segments still need MIN_SEGMENT_RUNS (5) samples
   - First few applications for a new segment still use family fallback
   - Future: Lower threshold for new segments, or use Bayesian priors

4. **Extension Integration**: Server-only for Phase 5.2
   - Extension doesn't explicitly send segment_key
   - Future: Extension derives segment client-side for consistency

## Future Enhancements (Phase 5.3+)

1. **Discipline-Aware Segments**
   - Segment key: `(seniority, discipline)`
   - Examples: `"senior_ml"`, `"junior_frontend"`, `"intern_data"`
   - Requires job processing to extract discipline

2. **Multi-Dimensional Tuning**
   - Segment by company type (startup vs enterprise)
   - Segment by role function (IC vs manager)
   - Hierarchical fallback across multiple dimensions

3. **Per-Segment Style Maps**
   - Instead of single `preferred_style_id`, return map:
     ```json
     {
       "segment_styles": {
         "senior": "professional_narrative_v1",
         "junior": "friendly_bullets_v1",
         "intern": "concise_bullets_v1"
       }
     }
     ```
   - Extension picks style based on current application's segment

4. **Adaptive Thresholds**
   - MIN_SEGMENT_RUNS varies by segment popularity
   - Popular segments (senior, default): higher threshold (10)
   - Rare segments (intern): lower threshold (3)

## Summary

Phase 5.2 adds a powerful new dimension to the Companion learning system. By segmenting recommendations by role level, we can:

✅ **Improve cold-start performance**: New forms get recommendations from similar forms for the same segment
✅ **Increase coverage**: ~25-35% of profiles will use segment-level recommendations
✅ **Better personalization**: Interns get different styles than seniors
✅ **Maintain simplicity**: Extension doesn't need changes; server-only feature

**Next Steps**:
1. Run migration in production
2. Execute aggregator to populate segment recommendations
3. Monitor recommendation source distribution
4. Validate segment performance vs form/family levels
5. Consider Phase 5.3 enhancements based on production data
