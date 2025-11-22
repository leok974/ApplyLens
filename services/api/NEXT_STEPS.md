# ApplyLens - Next Steps (Nov 14, 2024)

## ✅ Completed Work

### Phase 5.2: Segment-Aware Style Tuning (Backend)
- ✅ **Commit 3ef4ef6**: Core implementation (data model, derivation, selection)
- ✅ **Commit 1273426**: Initial metrics attempt
- ✅ **Commit 06d6c20**: Complete metrics + documentation + cleanup

**Status**: Backend implementation complete and pushed to `thread-viewer-v1` branch

---

## 🔄 Next Steps (In Priority Order)

### Step 1: Resolve Phase 5.0 Migration Blocker
**Priority**: High (blocks all DB migrations)  
**Issue**: `user_id` type mismatch (UUID vs VARCHAR)  
**Location**: `alembic/versions/75310f8e88d7_phase_50_user_id.py`

**Action**:
```bash
# Check current state
docker exec applylens-db-prod psql -U postgres -d applylens_prod -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'autofill_events' AND column_name = 'user_id';
"

# If VARCHAR, manually fix or create corrective migration
# Then proceed with Phase 5.2 migration
```

**Files to review**:
- `services/api/alembic/versions/75310f8e88d7_phase_50_user_id.py`
- `services/api/manual_phase52_migration.sql` (backup option)

---

### Step 2: Run Phase 5.2 Database Migration
**Priority**: High (required before metrics work)  
**File**: `alembic/versions/a1b2c3d4e5f6_phase_52_segment_key.py`

**Action**:
```bash
# Option A: Alembic (if Phase 5.0 is fixed)
cd d:\ApplyLens\services\api
docker exec applylens-api-prod alembic upgrade head

# Option B: Manual SQL (if Alembic blocked)
docker exec -i applylens-db-prod psql -U postgres -d applylens_prod < manual_phase52_migration.sql
```

**Validation**:
```bash
# Verify segment_key column exists
docker exec applylens-db-prod psql -U postgres -d applylens_prod -c "
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'autofill_events' AND column_name = 'segment_key';
"
# Expected: segment_key | text | YES
```

---

### Step 3: Run Aggregator to Populate Metrics
**Priority**: High (generates first metrics)  
**Location**: Running in container

**Action**:
```bash
# Run aggregator for last 30 days
docker exec applylens-api-prod python -c "
from app.autofill_aggregator import run_aggregator
updated = run_aggregator(days=30)
print(f'✅ Updated {updated} profiles with style hints')
"
```

**Expected output**:
```
INFO:app.autofill_aggregator:Updated style hint for boards.greenhouse.io/schema-abc: preferred=friendly_bullets_v1 (source=segment, helpful_ratio=85.7%, avg_edit_chars=120.5)
...
✅ Updated 42 profiles with style hints
```

**Validation**:
```bash
# Check metrics endpoint
curl http://localhost:8003/metrics | grep applylens_autofill_style_choice_total

# Expected result (non-zero counts):
# applylens_autofill_style_choice_total{source="form",host_family="greenhouse",segment_key=""} 15
# applylens_autofill_style_choice_total{source="segment",host_family="greenhouse",segment_key="senior"} 8
```

---

### Step 4: Import Grafana Dashboard
**Priority**: Medium (visualization for monitoring)  
**File**: `grafana/dashboards/applylens-style-tuning-phase5.json`

**Action**:
1. Open Grafana: `http://localhost:3000`
2. Navigate: **Dashboards** → **Import**
3. Click **Upload JSON file**
4. Select `grafana/dashboards/applylens-style-tuning-phase5.json`
5. Configure:
   - **Datasource**: Select "Prometheus"
   - **UID**: Keep as `applylens-style-tuning`
6. Click **Import**

**Panels to verify** (10 total):
1. Style Choice Source (timeseries)
2. Segment-based Recommendations by ATS (bar chart)
3. Senior/Junior/Intern Segment Mix (3 pie charts)
4. Coverage stats (4 stat panels: total, segment %, form %, no-rec %)
5. Detailed Breakdown (table)

---

### Step 5: Set Up Prometheus Alerts (Optional)
**Priority**: Low (production monitoring)

**File**: Create `prometheus/alerts/applylens-style-tuning.yml`

```yaml
groups:
  - name: applylens_style_tuning
    interval: 5m
    rules:
      - alert: HighNoRecommendationRate
        expr: |
          100 * sum(increase(applylens_autofill_style_choice_total{source="none"}[1h]))
              / sum(increase(applylens_autofill_style_choice_total[1h]))
          > 30
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "High percentage of forms have no style recommendation"
          description: "{{ $value }}% of profiles lack sufficient data for style tuning"

      - alert: LowSegmentCoverage
        expr: |
          100 * sum(increase(applylens_autofill_style_choice_total{source="segment"}[6h]))
              / sum(increase(applylens_autofill_style_choice_total[6h]))
          < 20
        for: 1h
        labels:
          severity: info
        annotations:
          summary: "Segment-level recommendations below target"
          description: "Only {{ $value }}% using segment-level stats (target: 25-35%)"
```

---

### Step 6: Monitor & Validate Phase 5.2 Behavior
**Priority**: Medium (1-2 weeks after deployment)

**Daily checks**:
```bash
# Check segment distribution
docker exec applylens-api-prod python -c "
from app.db import SessionLocal
from app.models_learning_db import FormProfile

db = SessionLocal()
profiles = db.query(FormProfile).filter(FormProfile.style_hint.isnot(None)).all()

sources = {}
for p in profiles:
    hint = p.style_hint or {}
    source = hint.get('source', 'none')
    sources[source] = sources.get(source, 0) + 1

total = len(profiles)
print(f'📊 Style Source Distribution (n={total}):')
for source in ['form', 'segment', 'family', 'none']:
    count = sources.get(source, 0)
    pct = 100 * count / total if total > 0 else 0
    print(f'  {source:8s}: {count:4d} ({pct:5.1f}%)')
"
```

**Expected results** (after stabilization):
- Form: 30-40% ✅
- Segment: 25-35% ✅ (Phase 5.2 benefit)
- Family: 15-25% ✅
- None: <20% ✅

**Weekly checks**:
- Review Grafana dashboard for trends
- Check for new ATS families with low coverage
- Identify forms needing manual intervention

---

## 🚀 Future Work (Phase 5.x Extensions)

### Phase 5.0: Extension Implementation
**Document**: `PHASE_5_EXTENSION_IMPLEMENTATION.md` (current file)  
**Status**: Backend complete, extension work pending  
**Tasks**:
1. Update `src/learning/types.ts` - Add `preferredStyleId` to StyleHint
2. Update `src/learning/profileClient.ts` - Map `preferred_style_id` → `preferredStyleId`
3. Update `content.js` - Use `preferredStyleId` in generation request
4. Add unit tests: `tests/profileClient.test.ts`
5. Add E2E tests: `e2e/autofill-style-tuning.spec.ts`

**See**: Full guide in `PHASE_5_EXTENSION_IMPLEMENTATION.md`

---

### Phase 5.3: Advanced Segment Features (Future)
**Ideas**:
- Discipline-based segments (e.g., "software-senior", "marketing-junior")
- Geographic segments (different styles for different regions)
- Company size segments (startup vs enterprise)
- Dynamic segment discovery from job data

---

### Phase 5.4: A/B Testing Infrastructure (Future)
**Ideas**:
- Randomized style assignment per user cohort
- Statistical significance testing
- Multi-armed bandit optimization
- Automated threshold tuning

---

## 📋 Immediate Action Items

**Today (Nov 14, 2024)**:
1. ✅ Commit and push Phase 5.2 metrics
2. ⏳ Investigate Phase 5.0 migration blocker
3. ⏳ Run Phase 5.2 migration (manual or Alembic)
4. ⏳ Run aggregator to generate first metrics

**This week**:
5. Import Grafana dashboard
6. Validate metric data in Prometheus
7. Monitor segment distribution for 3-5 days
8. Begin extension work (Phase 5.0 client-side)

**Next week**:
9. Set up Prometheus alerts
10. Review Phase 5.2 coverage metrics
11. Tune thresholds if needed (MIN_SEGMENT_RUNS, MIN_FAMILY_RUNS)
12. Document any issues or improvements

---

## 📚 Reference Documentation

**Phase 5.2 Docs** (all created):
- `PHASE_5.2_IMPLEMENTATION.md` - Technical implementation guide
- `PHASE_5.2_DEPLOYMENT_SUMMARY.md` - Deployment checklist
- `PHASE_5.2_METRICS_GUIDE.md` - Prometheus/Grafana setup
- `PHASE_5.2_COMPLETE_SUMMARY.md` - Comprehensive overview

**Phase 5.0 Extension**:
- `PHASE_5_EXTENSION_IMPLEMENTATION.md` - Client-side guide

**Helper Scripts**:
- `test_phase52_manual.py` - Standalone validation
- `manual_phase52_migration.sql` - Backup migration
- `deploy_phase5.ps1` - Deployment automation (if needed)

---

## 🎯 Success Criteria

Phase 5.2 is **production-ready** when:

- ✅ Code complete and tested
- ✅ Committed to `thread-viewer-v1` branch
- ✅ Pushed to GitHub
- ⏳ Database migration applied
- ⏳ Aggregator run with metrics generated
- ⏳ Grafana dashboard imported and showing data
- ⏳ Segment coverage 25-35%
- ⏳ Form coverage 30-40%
- ⏳ No-recommendation rate <20%

**Current status**: 3/8 complete (code done, deployment pending)
