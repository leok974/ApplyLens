# Phase 5.0 Backend Implementation Guide

## Overview
Phase 5.0 adds feedback-aware style tuning to the ApplyLens system. The extension-side changes are complete. This guide provides the backend implementation requirements.

## Extension Changes (✅ Complete)

### 1. Profile Client Updates
**Files Modified:**
- `src/learning/profileClient.ts`
- `learning.profileClient.js`

**Changes:**
- Now maps both `preferred_style_id` and `gen_style_id` from backend response
- Uses `preferred_style_id` if available, falls back to `gen_style_id`
- Stored in `styleHint.genStyleId` property

### 2. Learning Event Tracking
**Files Modified:**
- `content.js` (added `currentProfile` module variable)
- Learning events now include `genStyleId` field

**Changes:**
- Profile stored in module-level `currentProfile` variable
- Learning sync events include: `genStyleId: currentProfile?.styleHint?.genStyleId || null`
- Backend receives `gen_style_id` in learning sync payload

### 3. E2E Test Coverage
**New Test:** `e2e/autofill-style-tuning.spec.ts`
- Validates `preferred_style_id` flows from profile → styleHint → generation request
- Tagged with `@companion @styletuning`
- Passes with all other companion tests (9/9 passing)

## Backend Requirements (TODO)

### 1. Database Schema Changes

#### AutofillEvent Model
**File:** `services/api/app/models_learning_db.py`

Add columns:
```python
class AutofillEvent(Base):
    __tablename__ = "autofill_events"

    # ... existing columns ...

    # Phase 5.0: Style tracking
    gen_style_id = Column(String, nullable=True, index=True)
    feedback_status = Column(String, nullable=True)  # "helpful" | "unhelpful" | None
    edit_chars = Column(Integer, nullable=True)
```

**Migration Notes:**
- `gen_style_id`: Comes from learning sync events
- `feedback_status`: From feedback endpoint (already implemented in extension)
- `edit_chars`: Total characters edited in autofill run

#### FormProfile Model
**File:** `services/api/app/models_learning_db.py`

Extend `style_hint` JSONB field:
```python
class FormProfile(Base):
    __tablename__ = "form_profiles"

    # ... existing columns ...

    style_hint = Column(JSONB, nullable=True)
    # Now contains:
    # {
    #   "gen_style_id": "...",           # current style (if known)
    #   "confidence": 0.85,               # current confidence
    #   "preferred_style_id": "bullets_v1",  # PHASE 5.0: best performing style
    #   "style_stats": {                  # PHASE 5.0: per-style metrics
    #     "bullets_v1": {
    #       "helpful": 8,
    #       "unhelpful": 1,
    #       "total_runs": 10,
    #       "helpful_ratio": 0.8,
    #       "avg_edit_chars": 120
    #     },
    #     "narrative_v1": { ... }
    #   }
    # }
```

### 2. Aggregator Logic

#### File: `services/api/app/autofill_aggregator.py`

**New Components:**

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from collections import defaultdict

@dataclass
class StyleStats:
    style_id: str
    helpful: int = 0
    unhelpful: int = 0
    total_runs: int = 0
    avg_edit_chars: float = 0.0

    @property
    def helpful_ratio(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.helpful / self.total_runs


def compute_style_stats(session: Session, lookback_days: int) -> Dict[tuple, Dict[str, StyleStats]]:
    """
    Aggregate AutofillEvent by (host, schema_hash, gen_style_id).

    Returns:
        { (host, schema_hash): { style_id: StyleStats } }
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    q = (
        session.query(
            AutofillEvent.host,
            AutofillEvent.schema_hash,
            AutofillEvent.gen_style_id,
            AutofillEvent.feedback_status,
            AutofillEvent.edit_chars,
        )
        .filter(AutofillEvent.created_at >= cutoff)
        .filter(AutofillEvent.gen_style_id.isnot(None))
    )

    by_profile: Dict[tuple, Dict[str, StyleStats]] = defaultdict(dict)

    for host, schema_hash, style_id, feedback_status, edit_chars in q:
        key = (host, schema_hash)
        if style_id not in by_profile[key]:
            by_profile[key][style_id] = StyleStats(style_id=style_id)

        st = by_profile[key][style_id]
        st.total_runs += 1

        if feedback_status == "helpful":
            st.helpful += 1
        elif feedback_status == "unhelpful":
            st.unhelpful += 1

        if edit_chars is not None:
            # Running average
            n = st.total_runs
            st.avg_edit_chars = ((st.avg_edit_chars * (n - 1)) + edit_chars) / n

    return by_profile


def pick_best_style(styles: Dict[str, StyleStats]) -> Optional[StyleStats]:
    """
    Select best style by:
    1. Highest helpful_ratio
    2. Tie-breaker: lowest avg_edit_chars
    3. Tie-breaker: most total_runs
    """
    if not styles:
        return None

    return max(
        styles.values(),
        key=lambda s: (
            s.helpful_ratio,
            -s.avg_edit_chars,
            s.total_runs,
        ),
    )


def run_aggregator(days: int = 30) -> int:
    """
    Update FormProfile.style_hint with preferred_style_id based on feedback.

    Returns:
        Number of profiles updated
    """
    session = next(get_db())
    updated = 0

    style_map = compute_style_stats(session, lookback_days=days)

    profiles = (
        session.query(FormProfile)
        .filter(FormProfile.host.isnot(None))
        .all()
    )

    for profile in profiles:
        key = (profile.host, profile.schema_hash)
        styles_for_profile = style_map.get(key, {})

        if not styles_for_profile:
            continue

        best = pick_best_style(styles_for_profile)
        if not best:
            continue

        hint = (profile.style_hint or {}).copy()
        hint["preferred_style_id"] = best.style_id
        hint["style_stats"] = {
            sid: {
                "helpful": s.helpful,
                "unhelpful": s.unhelpful,
                "total_runs": s.total_runs,
                "helpful_ratio": s.helpful_ratio,
                "avg_edit_chars": s.avg_edit_chars,
            }
            for sid, s in styles_for_profile.items()
        }

        profile.style_hint = hint
        updated += 1

    session.commit()
    return updated
```

### 3. Backend Tests

#### File: `services/api/tests/test_learning_style_tuning.py`

```python
import pytest
from datetime import datetime, timedelta

from app.autofill_aggregator import run_aggregator
from app.models_learning_db import AutofillEvent, FormProfile
from app.db import get_db

pytestmark = pytest.mark.postgresql


def seed_events(session):
    """Create test data with two styles - one good, one bad."""
    now = datetime.utcnow()

    # Create profile
    profile = FormProfile(
        host="example-ats.com",
        schema_hash="schema-1",
        style_hint={"gen_style_id": "bullets_v1"},
    )
    session.add(profile)
    session.flush()

    # Good style: bullets_v1
    for _ in range(8):
        session.add(
            AutofillEvent(
                host="example-ats.com",
                schema_hash="schema-1",
                gen_style_id="bullets_v1",
                feedback_status="helpful",
                edit_chars=100,
                created_at=now,
            )
        )

    # Add 1 unhelpful for bullets
    session.add(
        AutofillEvent(
            host="example-ats.com",
            schema_hash="schema-1",
            gen_style_id="bullets_v1",
            feedback_status="unhelpful",
            edit_chars=150,
            created_at=now,
        )
    )

    # Bad style: narrative_v1
    for _ in range(5):
        session.add(
            AutofillEvent(
                host="example-ats.com",
                schema_hash="schema-1",
                gen_style_id="narrative_v1",
                feedback_status="unhelpful",
                edit_chars=700,
                created_at=now,
            )
        )

    # Add 2 helpful for narrative
    for _ in range(2):
        session.add(
            AutofillEvent(
                host="example-ats.com",
                schema_hash="schema-1",
                gen_style_id="narrative_v1",
                feedback_status="helpful",
                edit_chars=400,
                created_at=now,
            )
        )

    session.commit()


def test_style_tuning_picks_best_style(postgresql_session):
    """Aggregator should select style with highest helpful_ratio."""
    session = postgresql_session
    seed_events(session)

    updated = run_aggregator(days=30)
    assert updated == 1

    profile = (
        session.query(FormProfile)
        .filter_by(host="example-ats.com", schema_hash="schema-1")
        .one()
    )

    hint = profile.style_hint or {}

    # Should prefer bullets_v1 (8/9 helpful = 88.9%) over narrative_v1 (2/7 = 28.6%)
    assert hint.get("preferred_style_id") == "bullets_v1"

    # Validate stats are included
    stats = hint.get("style_stats", {})
    assert "bullets_v1" in stats
    assert "narrative_v1" in stats

    # bullets_v1: 8 helpful, 1 unhelpful, 9 total
    bullets = stats["bullets_v1"]
    assert bullets["helpful"] == 8
    assert bullets["unhelpful"] == 1
    assert bullets["total_runs"] == 9
    assert 0.88 < bullets["helpful_ratio"] < 0.89
    assert 100 <= bullets["avg_edit_chars"] <= 120

    # narrative_v1: 2 helpful, 5 unhelpful, 7 total
    narrative = stats["narrative_v1"]
    assert narrative["helpful"] == 2
    assert narrative["unhelpful"] == 5
    assert narrative["total_runs"] == 7
    assert 0.28 < narrative["helpful_ratio"] < 0.29


def test_style_tuning_handles_no_feedback():
    """If no feedback data exists, profile should not be updated."""
    session = next(get_db())

    profile = FormProfile(
        host="no-data.com",
        schema_hash="schema-empty",
        style_hint={"gen_style_id": "default"},
    )
    session.add(profile)
    session.commit()

    updated = run_aggregator(days=30)
    assert updated == 0

    # Profile unchanged
    profile = (
        session.query(FormProfile)
        .filter_by(host="no-data.com", schema_hash="schema-empty")
        .one()
    )
    assert "preferred_style_id" not in (profile.style_hint or {})
```

### 4. API Endpoints (Already Implemented)

Extension already sends data to these endpoints:

1. **Learning Sync:** `POST /api/extension/learning/sync`
   - Receives `gen_style_id` in event payload
   - Should store in `AutofillEvent.gen_style_id`

2. **Feedback:** `POST /api/extension/feedback/autofill`
   - Receives `{host, schema_hash, status: "helpful"|"unhelpful"}`
   - Should update corresponding `AutofillEvent.feedback_status`

3. **Profile:** `GET /api/extension/learning/profile`
   - Should return `style_hint.preferred_style_id` if available
   - Extension prefers `preferred_style_id` over `gen_style_id`

### 5. Deployment Checklist

- [ ] Run database migration to add columns to `AutofillEvent`
- [ ] Implement `compute_style_stats()` and `pick_best_style()`
- [ ] Update `run_aggregator()` to compute preferred styles
- [ ] Add backend tests for style tuning logic
- [ ] Update learning sync endpoint to store `gen_style_id`
- [ ] Update feedback endpoint to store `feedback_status` and `edit_chars`
- [ ] Schedule aggregator to run nightly/hourly
- [ ] Verify profile endpoint returns `preferred_style_id` in response

## Data Flow

```
User autofills form
    ↓
Learning event includes: genStyleId (from profile)
    ↓
Backend stores: AutofillEvent.gen_style_id
    ↓
User clicks thumbs up/down
    ↓
Feedback endpoint updates: AutofillEvent.feedback_status
    ↓
Aggregator runs (scheduled job)
    ↓
Computes StyleStats per (host, schema_hash, style_id)
    ↓
Selects best style by helpful_ratio
    ↓
Updates FormProfile.style_hint.preferred_style_id
    ↓
Next autofill request includes preferred_style_id
    ↓
Extension uses it as genStyleId for generation
```

## Testing

### Extension Tests (✅ All Passing)
- 9/9 companion tests passing
- New test: `autofill-style-tuning.spec.ts` validates end-to-end flow
- All existing tests updated to handle new `genStyleId` field

### Backend Tests (TODO)
See test examples in section 3 above.

## Notes

- Extension uses `genStyleId` (camelCase) internally
- Backend uses `gen_style_id` (snake_case) in API/DB
- Extension automatically transforms between conventions
- Fallback behavior: if no `preferred_style_id`, uses `gen_style_id`
- All learning events now include `genStyleId: null` when no style hint provided
