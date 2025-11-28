# Phase 5.2 Metrics & Monitoring Deployment Guide

**Date**: November 14, 2025  
**Component**: Prometheus metrics + Grafana dashboard for segment-aware style tuning

---

## Overview

Phase 5.2 adds comprehensive observability for the segment-aware style tuning system through:

1. **Prometheus Counter**: `applylens_autofill_style_choice_total` with 3 labels
2. **Grafana Dashboard**: 10 panels showing source distribution, segment coverage, and ATS family breakdowns
3. **Smoke Test**: Validates metric labels work correctly

---

## 1. Prometheus Metric

### Metric Definition

```python
autofill_style_choice_total = Counter(
    "applylens_autofill_style_choice_total",
    "Total style recommendations chosen per profile aggregation",
    ["source", "host_family", "segment_key"],
)
```

### Labels

- **source**: `"form"` | `"segment"` | `"family"` | `"none"`
  - **form**: Form-specific recommendation (≥5 runs on exact form)
  - **segment**: Segment-level recommendation (≥5 runs for family+segment)
  - **family**: ATS family fallback (≥10 runs for family)
  - **none**: Insufficient data at all levels

- **host_family**: `"greenhouse"` | `"lever"` | `"workday"` | `"ashby"` | `"bamboohr"` | `"other"`
  - Derived via `get_host_family(host)`
  - Maps domains to ATS platform families

- **segment_key**: `"senior"` | `"junior"` | `"intern"` | `"default"` | `""`
  - Empty string when no segment (e.g., source="form" without segment data)
  - Derived from job title via `derive_segment_key(job)`

### When Incremented

- Once per `FormProfile` update in `_update_style_hints()`
- After `_pick_style_for_profile()` selects best style
- Before saving `profile.style_hint`

### Example Metrics

```promql
# All profiles updated with segment-based recommendations for senior roles at Greenhouse
applylens_autofill_style_choice_total{
  source="segment",
  host_family="greenhouse",
  segment_key="senior"
} = 42

# Profiles without sufficient data for any recommendation
applylens_autofill_style_choice_total{
  source="none",
  host_family="other",
  segment_key=""
} = 15
```

---

## 2. Deployment Steps

### 2.1 Update API Code

**Files Changed:**
- `app/autofill_aggregator.py` (metric definition + increment)
- `tests/test_learning_style_tuning.py` (smoke test)

```bash
# Copy updated files to production container
docker cp app/autofill_aggregator.py applylens-api-prod:/app/app/
docker cp tests/test_learning_style_tuning.py applylens-api-prod:/app/tests/

# Restart API to pick up new metric
docker restart applylens-api-prod
```

### 2.2 Verify Metric Exposed

```bash
# Check /metrics endpoint
curl http://localhost:8000/metrics | grep applylens_autofill_style_choice_total

# Expected output (initially 0 until aggregator runs):
# HELP applylens_autofill_style_choice_total Total style recommendations chosen per profile aggregation
# TYPE applylens_autofill_style_choice_total counter
applylens_autofill_style_choice_total{host_family="greenhouse",segment_key="senior",source="segment"} 0.0
```

### 2.3 Run Aggregator

```bash
# Trigger aggregation to populate metrics
docker exec applylens-api-prod python -c "
from app.autofill_aggregator import run_aggregator
updated = run_aggregator(days=30)
print(f'Updated {updated} profiles')
"
```

### 2.4 Verify Metrics Populated

```bash
curl http://localhost:8000/metrics | grep applylens_autofill_style_choice_total

# Expected output with real data:
applylens_autofill_style_choice_total{host_family="greenhouse",segment_key="senior",source="segment"} 23.0
applylens_autofill_style_choice_total{host_family="greenhouse",segment_key="",source="form"} 45.0
applylens_autofill_style_choice_total{host_family="lever",segment_key="junior",source="family"} 12.0
applylens_autofill_style_choice_total{host_family="other",segment_key="",source="none"} 8.0
```

---

## 3. Prometheus Configuration

### 3.1 Verify Scrape Config

Ensure Prometheus is scraping the API `/metrics` endpoint:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'applylens-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['applylens-api-prod:8000']
```

### 3.2 Query Metrics in Prometheus UI

Navigate to `http://localhost:9090/graph` and run:

```promql
# Total profile updates by source
sum by (source) (applylens_autofill_style_choice_total)

# Segment coverage percentage
100 * sum(applylens_autofill_style_choice_total{source="segment"}) 
    / sum(applylens_autofill_style_choice_total)

# Breakdown by family and segment
sum by (host_family, segment_key) (
  applylens_autofill_style_choice_total{source="segment"}
)
```

---

## 4. Grafana Dashboard

### 4.1 Import Dashboard

**Option 1: Via UI**

1. Navigate to Grafana (e.g., `http://localhost:3000`)
2. Click **Dashboards** → **Import**
3. Upload `grafana/dashboards/applylens-style-tuning-phase5.json`
4. Select Prometheus datasource
5. Click **Import**

**Option 2: Via Provisioning**

```bash
# Copy dashboard JSON to Grafana provisioning directory
docker cp grafana/dashboards/applylens-style-tuning-phase5.json \
  grafana:/etc/grafana/provisioning/dashboards/

# Restart Grafana to pick up dashboard
docker restart grafana
```

### 4.2 Dashboard Panels

**Panel 1: Style Choice Source (Timeseries)**
- Shows rate of recommendations by source (form/segment/family/none)
- Green = form (best), Blue = segment (Phase 5.2), Orange = family, Red = none

**Panel 2: Segment-based Recommendations by ATS Family (Bar Chart)**
- Horizontal bar chart showing segment usage across ATS families
- Only includes `source="segment"` choices

**Panel 3-5: Source Mix Pie Charts**
- Separate pies for senior, junior, intern segments
- Shows fallback patterns per role level

**Panel 6-9: Coverage Stats**
- Total profiles updated
- Segment coverage % (target: 25-35%)
- Form-level coverage % (target: 30-40%)
- No recommendation % (target: <20%)

**Panel 10: Detailed Table**
- Comprehensive breakdown of all (family, segment, source) combinations
- Sortable by count

### 4.3 Expected Metrics Distribution

After Phase 5.2 deployment with sufficient data:

| Source   | Expected % | Description                        |
|----------|------------|------------------------------------|
| form     | 30-40%     | Mature forms with ≥5 runs          |
| segment  | 25-35%     | **NEW** - Segment-based choices    |
| family   | 20-30%     | Fallback for sparse forms          |
| none     | 10-20%     | Very sparse forms, no data         |

---

## 5. Validation Checklist

### API Metrics

- [ ] Metric definition added to `autofill_aggregator.py`
- [ ] Metric incremented in `_update_style_hints()`
- [ ] Smoke test passes: `test_style_choice_metric_labels_smoke()`
- [ ] API container restarted
- [ ] `/metrics` endpoint exposes `applylens_autofill_style_choice_total`

### Prometheus

- [ ] Prometheus scraping API `/metrics`
- [ ] Metric visible in Prometheus UI
- [ ] PromQL queries return data
- [ ] All label combinations present (source, host_family, segment_key)

### Grafana

- [ ] Dashboard imported successfully
- [ ] All 10 panels load without errors
- [ ] Datasource configured correctly
- [ ] Panels show non-zero data after aggregator runs
- [ ] Time range selector works
- [ ] Refresh works (30s default)

---

## 6. Troubleshooting

### Metric Not Appearing

**Symptom**: `applylens_autofill_style_choice_total` not in `/metrics`

**Solutions**:
```bash
# Check if metric is defined
docker exec applylens-api-prod python -c "
from app.autofill_aggregator import autofill_style_choice_total
print(autofill_style_choice_total)
"

# Restart API
docker restart applylens-api-prod

# Re-check /metrics
curl http://localhost:8000/metrics | grep applylens_autofill
```

### Metric Always Zero

**Symptom**: Metric exists but all values are 0

**Solutions**:
```bash
# Run aggregator manually
docker exec applylens-api-prod python -c "
from app.autofill_aggregator import run_aggregator
result = run_aggregator(days=30)
print(f'Updated {result} profiles')
"

# Check if profiles were actually updated
docker exec applylens-api-prod python -c "
from app.db import SessionLocal
from app.models_learning_db import FormProfile

db = SessionLocal()
count = db.query(FormProfile).filter(
    FormProfile.style_hint.isnot(None)
).count()
print(f'{count} profiles with style hints')
db.close()
"
```

### Grafana Panels Empty

**Symptom**: Dashboard imports but panels show "No data"

**Solutions**:

1. **Check Prometheus datasource**:
   ```
   Grafana UI → Configuration → Data Sources → Prometheus
   - URL: http://prometheus:9090
   - Click "Save & Test"
   ```

2. **Verify time range**:
   - Dashboard time range: Last 7 days
   - If aggregator just ran, try "Last 1 hour"

3. **Test PromQL directly**:
   ```promql
   # In Grafana Explore or Prometheus UI
   applylens_autofill_style_choice_total
   ```

4. **Check for label mismatches**:
   - Dashboard expects `source`, `host_family`, `segment_key`
   - Metric must have exact same label names

### Label Cardinality Warning

**Symptom**: Prometheus warns about high cardinality

**Analysis**:
```python
# Maximum label combinations
sources = 4         # form, segment, family, none
families = 6        # greenhouse, lever, workday, ashby, bamboohr, other
segments = 5        # senior, junior, intern, default, ""
max_series = 4 * 6 * 5 = 120 time series
```

**This is acceptable** - Prometheus handles 120 series easily. Only concern if you see >10,000 series.

---

## 7. Monitoring Best Practices

### Alert on Low Segment Coverage

If segment coverage drops below 20%, it indicates Phase 5.2 isn't being used effectively:

```yaml
# prometheus/alerts/applylens.yml
groups:
  - name: applylens_learning
    rules:
      - alert: LowSegmentCoverage
        expr: |
          100 * sum(rate(applylens_autofill_style_choice_total{source="segment"}[1h]))
          / sum(rate(applylens_autofill_style_choice_total[1h])) < 20
        for: 4h
        labels:
          severity: warning
        annotations:
          summary: "Phase 5.2 segment coverage below 20%"
          description: "Only {{ $value | humanizePercentage }} of profiles using segment-based recommendations"
```

### Track Recommendation Quality by Source

Compare helpful_ratio for recommendations from different sources:

```promql
# Would require additional metrics (future enhancement)
avg by (source) (
  applylens_autofill_helpful_ratio{has_recommendation="true"}
)
```

### Monitor Segment Distribution

Ensure segment derivation is working:

```bash
# Database query
docker exec applylens-api-prod python -c "
from app.db import SessionLocal
from sqlalchemy import func
from app.models_learning_db import AutofillEvent

db = SessionLocal()
result = db.execute('''
    SELECT segment_key, COUNT(*) as cnt
    FROM autofill_events
    WHERE segment_key IS NOT NULL
    GROUP BY segment_key
    ORDER BY cnt DESC
''')

for row in result:
    print(f'{row.segment_key}: {row.cnt}')
db.close()
"
```

Expected distribution:
- senior: 30-40%
- default: 30-40%
- junior: 15-25%
- intern: 5-10%

---

## 8. Next Steps

### Phase 5.3 Enhancements

**Additional Metrics**:
```python
# Helpful ratio by source
autofill_helpful_ratio_by_source = Gauge(
    "applylens_autofill_helpful_ratio_by_source",
    "Helpful ratio for recommendations by source",
    ["source", "host_family"],
)

# Segment sample counts
autofill_segment_sample_counts = Gauge(
    "applylens_autofill_segment_sample_counts",
    "Number of samples per segment",
    ["host_family", "segment_key"],
)
```

**Dashboard Enhancements**:
- Add helpful_ratio comparison panel
- Add edit distance by source panel
- Add segment sample size heatmap
- Add source transition analysis (form→segment→family over time)

---

## Summary

Phase 5.2 metrics provide comprehensive visibility into:

✅ **Source Distribution** - How often each hierarchical level is used  
✅ **Segment Coverage** - Percentage of segment-based recommendations (Phase 5.2 KPI)  
✅ **ATS Family Breakdown** - Which platforms benefit most from segmentation  
✅ **Role Level Patterns** - Fallback behavior for senior vs junior vs intern  

**Key Success Metrics**:
- Segment coverage: **25-35%** (target for Phase 5.2)
- Form coverage: **30-40%** (mature forms)
- Total coverage: **≥80%** (form + segment + family)

The Grafana dashboard provides real-time monitoring to ensure Phase 5.2 is delivering value.
