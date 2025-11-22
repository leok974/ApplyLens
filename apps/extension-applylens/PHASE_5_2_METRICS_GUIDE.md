# Phase 5.2 – Prometheus Metrics for Style Tuning

## Overview
Add observability for feedback-aware style tuning to track:
- How often each source is used (form, segment, family, none)
- Which ATS families are benefiting from segment-based recommendations
- Coverage across different user segments (intern, junior, senior, default)

## 1. Metric Design

### Counter Definition

**Metric Name:** `applylens_autofill_style_choice_total`

**Labels:**
- `source`: Which source provided the style recommendation
  - `"form"` - Form-specific data (highest priority)
  - `"segment"` - Segment-level aggregation (user type)
  - `"family"` - ATS family fallback
  - `"none"` - No recommendation available
- `host_family`: ATS platform family
  - `"greenhouse"`, `"lever"`, `"workday"`, `"ashby"`, `"bamboohr"`, `"other"`
- `segment_key`: User segment identifier
  - `"intern"`, `"junior"`, `"senior"`, `"default"`, `""` (empty when not applicable)

### Usage
Increment once per FormProfile updated in `_update_style_hints()` after determining the best style.

## 2. Backend Implementation

### File: `services/api/app/autofill_aggregator.py`

#### 2.1 Add Import and Metric Definition

At the top of the file, add:

```python
from prometheus_client import Counter

# Phase 5.2: Track style choice sources for observability
applylens_autofill_style_choice_total = Counter(
    "applylens_autofill_style_choice_total",
    "Total style recommendations chosen per profile aggregation",
    ["source", "host_family", "segment_key"],
)
```

**Note:** If a counter with a similar name already exists, reuse it instead of creating a new one.

#### 2.2 Increment Metric in `_update_style_hints()`

Locate where `style_hint["preferred_style_id"]` is set and add metric tracking:

```python
def _update_style_hints(
    session: Session,
    profiles: List[FormProfile],
    style_map: Dict[tuple, Dict[str, StyleStats]],
    segment_stats: Dict[tuple, Dict[str, StyleStats]],
    family_stats: Dict[str, Dict[str, StyleStats]],
) -> int:
    """
    Update FormProfile.style_hint with preferred_style_id.
    
    Priority:
    1. Form-specific data (if sufficient samples)
    2. Segment-level aggregation (user type: intern/junior/senior)
    3. ATS family fallback
    4. None
    """
    updated = 0
    
    for profile in profiles:
        key = (profile.host, profile.schema_hash)
        
        # Get all possible style sources
        form_styles = style_map.get(key, {})
        segment_key = infer_segment_from_profile(profile)  # Your existing logic
        segment_styles = segment_stats.get((profile.host, segment_key), {})
        family = get_host_family(profile.host)
        family_styles = family_stats.get(family, {})
        
        # Choose best source with sufficient data
        best_style = None
        source = "none"
        chosen_segment_key = ""
        
        # Priority 1: Form-specific (need >= 5 samples)
        if form_styles:
            best_candidate = pick_best_style(form_styles)
            if best_candidate and best_candidate.total_runs >= 5:
                best_style = best_candidate
                source = "form"
        
        # Priority 2: Segment-level
        if not best_style and segment_styles:
            best_candidate = pick_best_style(segment_styles)
            if best_candidate and best_candidate.total_runs >= 3:
                best_style = best_candidate
                source = "segment"
                chosen_segment_key = segment_key or ""
        
        # Priority 3: ATS family
        if not best_style and family_styles:
            best_candidate = pick_best_style(family_styles)
            if best_candidate:
                best_style = best_candidate
                source = "family"
        
        # Update profile if we found a style
        if best_style:
            hint = (profile.style_hint or {}).copy()
            hint["preferred_style_id"] = best_style.style_id
            hint["source"] = source  # Track source in profile for debugging
            
            # Include stats for transparency
            hint["style_stats"] = {
                sid: {
                    "helpful": s.helpful,
                    "unhelpful": s.unhelpful,
                    "total_runs": s.total_runs,
                    "helpful_ratio": s.helpful_ratio,
                    "avg_edit_chars": s.avg_edit_chars,
                }
                for sid, s in (form_styles or segment_styles or family_styles).items()
            }
            
            profile.style_hint = hint
            updated += 1
            
            # Phase 5.2: Track metric
            host_family = family or "other"
            seg_key_label = chosen_segment_key or ""
            
            applylens_autofill_style_choice_total.labels(
                source=source,
                host_family=host_family,
                segment_key=seg_key_label,
            ).inc()
    
    return updated
```

#### 2.3 Helper Functions (if needed)

Add these if they don't already exist:

```python
def get_host_family(host: str) -> str:
    """
    Map host domain to ATS family.
    
    Examples:
        greenhouse.io -> "greenhouse"
        lever.co -> "lever"
        myworkday.com -> "workday"
    """
    host_lower = host.lower()
    
    if "greenhouse" in host_lower:
        return "greenhouse"
    elif "lever" in host_lower:
        return "lever"
    elif "workday" in host_lower:
        return "workday"
    elif "ashby" in host_lower:
        return "ashby"
    elif "bamboohr" in host_lower:
        return "bamboohr"
    else:
        return "other"


def infer_segment_from_profile(profile: FormProfile) -> Optional[str]:
    """
    Infer user segment from profile metadata or form fields.
    
    Returns:
        "intern" | "junior" | "senior" | "default" | None
    """
    # Implementation depends on your data model
    # Examples:
    # - Check profile.metadata for explicit segment
    # - Parse common field names like "experience_level"
    # - Use heuristics from canonicalMap field names
    
    metadata = profile.style_hint or {}
    if "segment" in metadata:
        return metadata["segment"]
    
    # Fallback heuristics
    canonical = profile.canonical_map or {}
    field_names = set(canonical.values())
    
    if any("intern" in f.lower() for f in field_names):
        return "intern"
    elif any("years_experience" in f.lower() for f in field_names):
        # Could parse actual value if available
        return "default"
    
    return "default"
```

## 3. Backend Tests

### File: `services/api/tests/test_learning_style_tuning.py`

Add smoke test at the bottom:

```python
def test_style_choice_metric_labels_smoke() -> None:
    """Smoke test: verify metric labels work without errors."""
    from app.autofill_aggregator import applylens_autofill_style_choice_total

    # Should not raise, and internal storage should create a sample
    counter = applylens_autofill_style_choice_total.labels(
        source="segment",
        host_family="greenhouse",
        segment_key="senior"
    )
    counter.inc()
    
    # Verify counter can be read
    assert counter._value.get() >= 1
    
    # Test all source types
    for source in ["form", "segment", "family", "none"]:
        applylens_autofill_style_choice_total.labels(
            source=source,
            host_family="workday",
            segment_key="junior"
        ).inc()
    
    # Test empty segment_key (common case)
    applylens_autofill_style_choice_total.labels(
        source="family",
        host_family="other",
        segment_key=""
    ).inc()
```

### Run Tests

```bash
cd services/api
pytest tests/test_learning_style_tuning.py::test_style_choice_metric_labels_smoke -v
```

Expected output:
```
test_learning_style_tuning.py::test_style_choice_metric_labels_smoke PASSED
```

## 4. Grafana Dashboards

### 4.1 Dashboard Setup

Create new dashboard or add to existing "ApplyLens Learning" dashboard.

**Dashboard JSON skeleton** (if creating new):

```json
{
  "title": "ApplyLens – Companion Style Tuning (Phase 5.x)",
  "uid": "applylens-style-tuning",
  "schemaVersion": 39,
  "version": 1,
  "panels": [],
  "time": {
    "from": "now-7d",
    "to": "now"
  },
  "timezone": "browser",
  "editable": true,
  "graphTooltip": 1
}
```

### 4.2 Panel 1 – Style Source Breakdown (Time Series)

**Goal:** Track how often each source is used over time

```json
{
  "id": 1,
  "type": "timeseries",
  "title": "Style Choice Source (form vs segment vs family)",
  "datasource": {
    "type": "prometheus",
    "uid": "Prometheus"
  },
  "targets": [
    {
      "refId": "A",
      "expr": "sum by (source) (rate(applylens_autofill_style_choice_total[5m]))",
      "legendFormat": "{{source}}",
      "interval": "",
      "format": "time_series"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "ops",
      "custom": {
        "lineInterpolation": "smooth",
        "lineWidth": 2,
        "fillOpacity": 10,
        "showPoints": "auto"
      }
    },
    "overrides": [
      {
        "matcher": { "id": "byName", "options": "form" },
        "properties": [{ "id": "color", "value": { "mode": "fixed", "fixedColor": "green" } }]
      },
      {
        "matcher": { "id": "byName", "options": "segment" },
        "properties": [{ "id": "color", "value": { "mode": "fixed", "fixedColor": "blue" } }]
      },
      {
        "matcher": { "id": "byName", "options": "family" },
        "properties": [{ "id": "color", "value": { "mode": "fixed", "fixedColor": "orange" } }]
      },
      {
        "matcher": { "id": "byName", "options": "none" },
        "properties": [{ "id": "color", "value": { "mode": "fixed", "fixedColor": "red" } }]
      }
    ]
  },
  "options": {
    "legend": {
      "displayMode": "table",
      "placement": "right",
      "calcs": ["lastNotNull", "mean"]
    },
    "tooltip": {
      "mode": "multi",
      "sort": "desc"
    }
  },
  "gridPos": { "h": 9, "w": 12, "x": 0, "y": 0 }
}
```

**Insights:**
- Green (form): Best case - form-specific data available
- Blue (segment): Good - using user segment aggregation
- Orange (family): Fallback - ATS family patterns
- Red (none): No recommendation - needs more data

### 4.3 Panel 2 – Segment Coverage by ATS Family (Bar Chart)

**Goal:** Show which ATS families benefit from segment recommendations

```json
{
  "id": 2,
  "type": "barchart",
  "title": "Segment-based Recommendations by ATS Family",
  "datasource": {
    "type": "prometheus",
    "uid": "Prometheus"
  },
  "targets": [
    {
      "refId": "A",
      "expr": "sum by (host_family, segment_key) (increase(applylens_autofill_style_choice_total{source=\"segment\"}[$__range]))",
      "format": "time_series",
      "legendFormat": "{{host_family}} / {{segment_key}}"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "custom": {
        "drawStyle": "bars",
        "barAlignment": 0,
        "lineWidth": 1,
        "fillOpacity": 80,
        "gradientMode": "none"
      },
      "mappings": [],
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "value": null, "color": "blue" }
        ]
      }
    },
    "overrides": []
  },
  "options": {
    "orientation": "horizontal",
    "legend": {
      "displayMode": "table",
      "placement": "right",
      "calcs": ["sum"]
    },
    "tooltip": {
      "mode": "single"
    },
    "xTickLabelRotation": -45,
    "xTickLabelSpacing": 0
  },
  "gridPos": { "h": 9, "w": 12, "x": 12, "y": 0 }
}
```

**Insights:**
- Identify which ATS families have good segment coverage
- See distribution across intern/junior/senior segments
- Spot gaps where more data is needed

### 4.4 Panel 3 – Source Mix per Segment (Pie Chart)

**Goal:** For a selected segment, show source distribution

```json
{
  "id": 3,
  "type": "piechart",
  "title": "Source Mix for Senior Applicants",
  "datasource": {
    "type": "prometheus",
    "uid": "Prometheus"
  },
  "targets": [
    {
      "refId": "A",
      "expr": "sum by (source) (increase(applylens_autofill_style_choice_total{segment_key=\"senior\"}[$__range]))",
      "legendFormat": "{{source}}",
      "format": "time_series"
    }
  ],
  "options": {
    "legend": {
      "displayMode": "table",
      "placement": "right",
      "calcs": ["lastNotNull", "percent"]
    },
    "reduceOptions": {
      "calcs": ["lastNotNull"],
      "fields": "",
      "values": false
    },
    "displayLabels": ["name", "value", "percent"],
    "pieType": "pie",
    "tooltip": {
      "mode": "single"
    }
  },
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "custom": {
        "hideFrom": {
          "tooltip": false,
          "viz": false,
          "legend": false
        }
      }
    },
    "overrides": []
  },
  "gridPos": { "h": 9, "w": 8, "x": 0, "y": 9 }
}
```

**Variations:**
Clone this panel and change `segment_key` to create comparison views:
- `segment_key="intern"` - Intern Source Mix
- `segment_key="junior"` - Junior Source Mix
- `segment_key="default"` - Default Source Mix

### 4.5 Panel 4 – Total Recommendations by Family (Stat Panel)

**Goal:** Quick overview of total recommendations per ATS family

```json
{
  "id": 4,
  "type": "stat",
  "title": "Total Recommendations by ATS Family",
  "datasource": {
    "type": "prometheus",
    "uid": "Prometheus"
  },
  "targets": [
    {
      "refId": "A",
      "expr": "sum by (host_family) (increase(applylens_autofill_style_choice_total[$__range]))",
      "legendFormat": "{{host_family}}",
      "format": "time_series"
    }
  ],
  "options": {
    "orientation": "auto",
    "reduceOptions": {
      "values": false,
      "calcs": ["lastNotNull"],
      "fields": ""
    },
    "textMode": "value_and_name",
    "colorMode": "value",
    "graphMode": "area",
    "justifyMode": "auto"
  },
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "mappings": [],
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "value": null, "color": "green" },
          { "value": 100, "color": "yellow" },
          { "value": 500, "color": "red" }
        ]
      }
    },
    "overrides": []
  },
  "gridPos": { "h": 9, "w": 8, "x": 8, "y": 9 }
}
```

### 4.6 Panel 5 – Recommendation Quality Heatmap

**Goal:** Show helpful ratio by source and family

```json
{
  "id": 5,
  "type": "heatmap",
  "title": "Recommendation Success Rate (source × family)",
  "datasource": {
    "type": "prometheus",
    "uid": "Prometheus"
  },
  "targets": [
    {
      "refId": "A",
      "expr": "sum by (source, host_family) (rate(applylens_autofill_feedback_helpful_total[5m])) / sum by (source, host_family) (rate(applylens_autofill_style_choice_total[5m]))",
      "format": "time_series",
      "legendFormat": "{{source}} / {{host_family}}"
    }
  ],
  "options": {
    "calculate": false,
    "calculation": {},
    "cellGap": 2,
    "color": {
      "exponent": 0.5,
      "fill": "dark-orange",
      "mode": "scheme",
      "reverse": false,
      "scale": "exponential",
      "scheme": "RdYlGn",
      "steps": 64
    },
    "exemplars": {
      "color": "rgba(255,0,255,0.7)"
    },
    "filterValues": {
      "le": 1e-9
    },
    "legend": {
      "show": true
    },
    "rowsFrame": {
      "layout": "auto"
    },
    "tooltip": {
      "show": true,
      "yHistogram": false
    },
    "yAxis": {
      "axisPlacement": "left",
      "reverse": false
    }
  },
  "gridPos": { "h": 9, "w": 16, "x": 0, "y": 18 }
}
```

**Note:** This assumes you also have a `applylens_autofill_feedback_helpful_total` metric. If not, you can skip this panel.

## 5. Deployment Checklist

### 5.1 Backend Changes

- [ ] **Add metric to `autofill_aggregator.py`**
  - Import `Counter` from `prometheus_client`
  - Define `applylens_autofill_style_choice_total`
  - Add helper functions: `get_host_family()`, `infer_segment_from_profile()`

- [ ] **Update `_update_style_hints()` function**
  - Implement source priority logic (form → segment → family → none)
  - Track `source`, `host_family`, `segment_key` for each profile
  - Call `.labels(...).inc()` after setting `preferred_style_id`

- [ ] **Add smoke test**
  - Create `test_style_choice_metric_labels_smoke()` in `test_learning_style_tuning.py`
  - Test all label combinations
  - Verify counter increments work

- [ ] **Run tests**
  ```bash
  pytest tests/test_learning_style_tuning.py -v
  ```

### 5.2 Infrastructure

- [ ] **Rebuild API image**
  ```bash
  cd services/api
  docker build -t applylens-api:5.2 .
  ```

- [ ] **Redeploy to staging**
  - Update deployment with new image
  - Verify `/metrics` endpoint exposes new counter

- [ ] **Configure Prometheus scrape**
  - Ensure Prometheus is scraping API `/metrics` endpoint
  - Scrape interval: 15-30 seconds recommended

### 5.3 Grafana Setup

- [ ] **Import dashboard JSON**
  - Go to Grafana → Dashboards → New → Import
  - Paste complete JSON with all panels
  - Select Prometheus datasource

- [ ] **Verify panels render**
  - Check "Style Source Breakdown" shows data
  - Verify "Segment Coverage" has bars
  - Confirm pie charts display correctly

- [ ] **Set up alerts** (optional)
  - Alert if `source="none"` rate is high (>20%)
  - Alert if total recommendations drop significantly

### 5.4 Validation

- [ ] **Run aggregator manually**
  ```python
  from app.autofill_aggregator import run_aggregator
  updated = run_aggregator(days=30)
  print(f"Updated {updated} profiles")
  ```

- [ ] **Check Prometheus**
  - Go to Prometheus UI → Graph
  - Query: `applylens_autofill_style_choice_total`
  - Should see multiple series with different labels

- [ ] **Verify Grafana**
  - Open dashboard
  - Check all panels show non-zero data
  - Verify labels appear correctly (greenhouse, lever, etc.)

- [ ] **Monitor for 24h**
  - Ensure metrics accumulate correctly
  - Check for any label cardinality issues
  - Verify dashboard updates in real-time

## 6. Example Queries

### Prometheus Queries

**Total recommendations by source (last 7 days):**
```promql
sum by (source) (increase(applylens_autofill_style_choice_total[7d]))
```

**Segment coverage for Greenhouse:**
```promql
sum by (segment_key) (increase(applylens_autofill_style_choice_total{host_family="greenhouse", source="segment"}[7d]))
```

**Percentage of form-specific recommendations:**
```promql
sum(increase(applylens_autofill_style_choice_total{source="form"}[7d])) / sum(increase(applylens_autofill_style_choice_total[7d])) * 100
```

**Top 5 ATS families by recommendation count:**
```promql
topk(5, sum by (host_family) (increase(applylens_autofill_style_choice_total[24h])))
```

### Grafana Variables (Optional)

Add dashboard variables for filtering:

```json
{
  "name": "host_family",
  "type": "query",
  "datasource": "Prometheus",
  "query": "label_values(applylens_autofill_style_choice_total, host_family)",
  "multi": true,
  "includeAll": true
}
```

```json
{
  "name": "segment_key",
  "type": "query",
  "datasource": "Prometheus",
  "query": "label_values(applylens_autofill_style_choice_total, segment_key)",
  "multi": true,
  "includeAll": true
}
```

Then use `$host_family` and `$segment_key` in panel queries.

## 7. Troubleshooting

### Metric not appearing in Prometheus

**Check:**
1. API `/metrics` endpoint returns the metric
   ```bash
   curl http://localhost:8000/metrics | grep applylens_autofill_style_choice
   ```

2. Prometheus scrape config includes API target
   ```yaml
   scrape_configs:
     - job_name: 'applylens-api'
       static_configs:
         - targets: ['api:8000']
   ```

3. Run aggregator to generate data
   ```python
   from app.autofill_aggregator import run_aggregator
   run_aggregator(days=30)
   ```

### High label cardinality warning

**Solution:** Limit `segment_key` values to predefined set:
```python
ALLOWED_SEGMENTS = {"intern", "junior", "senior", "default", ""}

seg_key_label = segment_key if segment_key in ALLOWED_SEGMENTS else "default"
```

### Panels show "No data"

**Check:**
1. Time range is appropriate (data might be sparse)
2. Datasource is correctly configured
3. Query syntax is valid for your Prometheus version
4. Metric labels match exactly (case-sensitive)

### Aggregator not updating metrics

**Debug:**
```python
# Add logging before metric increment
import logging
logger = logging.getLogger(__name__)

logger.info(
    f"Recording style choice: source={source}, "
    f"family={host_family}, segment={seg_key_label}"
)

applylens_autofill_style_choice_total.labels(
    source=source,
    host_family=host_family,
    segment_key=seg_key_label,
).inc()
```

## 8. Success Metrics

After deployment, you should see:

- **Week 1:** Baseline established
  - Mix of sources visible
  - Segment coverage identified
  
- **Week 2-4:** Optimization in progress
  - `source="form"` percentage increasing (more form-specific data)
  - Segment recommendations stabilizing for common paths

- **Month 2+:** Mature system
  - 60%+ recommendations from form-specific data
  - 30% from segment-level
  - <10% family fallback
  - <5% none

**Red flags:**
- `source="none"` consistently >20% → Need more data collection
- Single ATS family dominates →Might need better family detection
- No segment diversity → Segmentation logic needs work

## Summary

Phase 5.2 adds comprehensive observability for style tuning:

✅ **Metric tracking** - Every recommendation captured with source/family/segment labels  
✅ **Grafana dashboards** - 5 panels covering different analysis angles  
✅ **Smoke tests** - Ensure metric labels work correctly  
✅ **Documentation** - Complete deployment and troubleshooting guide  

**Next steps:**
1. Implement backend changes in `services/api/`
2. Deploy and validate metrics appear
3. Import Grafana dashboards
4. Monitor for 1 week and iterate on thresholds
