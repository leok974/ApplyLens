# Analytics Phase 51 - Quick Runbook

## Local Testing

### 1. Run Pipeline (generates CSVs)

```bash
# After you've run the original pipeline at least once
python -m analytics.pipeline --window-days 7
```

**Expected Output:**

```
✅ CSV dashboards exported:
   kpis_csv: analytics/outputs/dashboards/kpis.csv
   kpis_long_csv: analytics/outputs/dashboards/kpis_long.csv
```

### 2. Check CSV Files

```powershell
# View CSV content
Get-Content analytics\outputs\dashboards\kpis.csv

# Should show:
# date,seo_coverage_pct,playwright_pass_pct,avg_p95_ms,autofix_delta_count
# 2025-10-01,95.2,98.5,245,12
```

### 3. Test Search API

```powershell
# Search for SEO issues
curl "http://localhost:8003/analytics/search?q=seo+coverage+drop&k=5"

# Expected response:
# {
#   "query": "seo coverage drop",
#   "k": 5,
#   "results": [...]
# }
```

### 4. View Latest Report

```powershell
# Get latest insights
curl http://localhost:8003/analytics/latest

# Open report in editor
code analytics\outputs\insight-summary.md
```

## Quick Commands

```bash
# Export CSVs only
python -c "
from pathlib import Path
from analytics.dashboards.exporter import export_csv_series
export_csv_series(Path('analytics/data'), Path('analytics/outputs/dashboards'))
"

# Test recommendations
python -c "
from analytics.recommenders.weights import recommend_weight_diffs
merged = {'seo': {'pages': [{'path': '/pricing', 'ok': False}]}, 'playwright': {'tests': []}}
anomalies = [{'field': 'seo_coverage_pct', 'z': -2.5}]
rec = recommend_weight_diffs(merged, anomalies)
if rec:
    print(f'Recommendations: {len(rec.weight_diffs)} weight adjustments')
    for k, v in rec.weight_diffs.items():
        print(f'  {k}: {v:+.3f}')
"

# Check API endpoints
curl http://localhost:8003/analytics/latest
curl http://localhost:8003/analytics/dashboards/kpis.csv
curl "http://localhost:8003/analytics/search?q=test&k=3"
```

## File Locations

| File | Purpose |
|------|---------|
| `analytics/data/*.json` | Daily metrics input |
| `analytics/outputs/dashboards/kpis.csv` | Wide CSV export |
| `analytics/outputs/dashboards/kpis_long.csv` | Long CSV export |
| `analytics/outputs/insight-summary.md` | Report with recommendations |
| `analytics/rag/vector_store.sqlite` | Search index |

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analytics/latest` | GET | Latest markdown report |
| `/analytics/search?q=...&k=6` | GET | Search insights |
| `/analytics/dashboards/kpis.csv` | GET | CSV preview |

## Common Issues

### "Vector store not built yet"

```bash
# Run pipeline to create vector store
python -m analytics.pipeline --window-days 7
```

### "kpis.csv not found"

```bash
# Export CSVs
python -m analytics.dashboards.exporter
```

### "No recommendations"

- Check if anomalies exist in your data
- Verify `analytics/data/*.json` files have proper structure
- Look for error suppression message in report

## Next Steps

1. ✅ Test CSV export
2. ✅ Test analytics endpoints
3. ⏭️ Create sample data files
4. ⏭️ Configure Grafana (optional)
5. ⏭️ Add frontend analytics page
6. ⏭️ Set up PR comment workflow
