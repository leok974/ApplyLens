# Analytics Phase 51

This directory contains the Analytics Phase 51 upgrade (51.1 → 51.3) for ApplyLens.

## Structure

```text
analytics/
├── README.md                          # This file
├── .gitignore                         # Ignore data/outputs
├── pipeline.py                        # Main pipeline entry point
├── collectors/
│   ├── kpi_extractor.py              # Extract KPIs from metrics
│   └── nightly_loader.py             # Load daily JSON data
├── dashboards/
│   └── exporter.py                   # CSV export for dashboards
├── rag/
│   ├── embedder_local.py             # Text embedding (stub)
│   └── query_engine.py               # Vector store search
├── recommenders/
│   └── weights.py                    # Weight adjustment logic
├── summarizers/
│   └── report_builder.py             # Markdown report generator
└── config/
    └── test_page_map.json.example    # Optional test mapping
```text

## Quick Start

### 1. Run Pipeline

```bash
python -m analytics.pipeline --window-days 7
```text

### 2. View Outputs

```bash
# CSV dashboards
cat analytics/outputs/dashboards/kpis.csv

# Markdown report with recommendations
cat analytics/outputs/insight-summary.md
```text

### 3. Test API

```bash
curl http://localhost:8003/analytics/latest
curl "http://localhost:8003/analytics/search?q=seo&k=5"
curl http://localhost:8003/analytics/dashboards/kpis.csv
```text

## Data Format

Place daily metrics in `analytics/data/` as JSON files:

```json
// analytics/data/2025-10-09.json
{
  "seo": {
    "pages": [
      {"path": "/pricing", "ok": true},
      {"path": "/about", "ok": false}
    ]
  },
  "playwright": {
    "tests": [
      {"name": "login flow", "status": "passed"},
      {"name": "checkout /checkout", "status": "failed"}
    ]
  },
  "performance": {
    "p95_ms": 245
  },
  "autofix": {
    "delta_count": 12
  }
}
```text

## Components

### Phase 51.1 — CSV Dashboards

- **Purpose:** Export KPI time-series to CSV for dashboards
- **Output:** `outputs/dashboards/kpis.csv` (wide) and `kpis_long.csv` (long)
- **KPIs:** SEO coverage %, Playwright pass %, P95 latency, Autofix count

### Phase 51.2 — Search API

- **Purpose:** Semantic search over analytics insights
- **Endpoints:** `/analytics/latest`, `/analytics/search`, `/analytics/dashboards/kpis.csv`
- **Backend:** SQLite vector store with text embeddings

### Phase 51.3 — Weight Recommendations

- **Purpose:** Recommend safe weight adjustments based on anomalies
- **Logic:** Analyze SEO failures + Playwright test failures → suggest page priorities
- **Output:** Recommendations section in markdown reports

## Configuration

### Optional: Test-to-Page Mapping

Create `analytics/config/test_page_map.json`:

```json
{
  "login flow test": "/login",
  "checkout test": "/checkout",
  "homepage performance": "/"
}
```text

This helps extract page paths from test names.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analytics/latest` | GET | Latest markdown report |
| `/analytics/search?q=...&k=6` | GET | Search insights (k results) |
| `/analytics/dashboards/kpis.csv` | GET | CSV preview with metadata |

## Outputs

All generated files are gitignored:

- `analytics/data/*.json` - Input data (you provide)
- `analytics/outputs/dashboards/*.csv` - Exported CSVs
- `analytics/outputs/insight-summary.md` - Markdown report
- `analytics/rag/vector_store.sqlite` - Search index

## Documentation

See project root for comprehensive docs:

- `ANALYTICS_PHASE_51_COMPLETE.md` - Full implementation guide (500+ lines)
- `ANALYTICS_PHASE_51_QUICKSTART.md` - Quick runbook (150+ lines)
- `ANALYTICS_PHASE_51_SUMMARY.md` - Implementation summary

## Integration

The analytics module is auto-registered in `services/api/app/main.py`:

```python
# Phase 51.2 — Analytics endpoints (optional, gated)
try:
    from .routers.analytics import router as analytics_router
    app.include_router(analytics_router)
except ImportError:
    pass  # Analytics module not available
```text

This ensures the API doesn't break if analytics modules are missing.

## Development

### Replace Dummy Embedder

The current embedder is a stub. Replace with a real model:

```python
# analytics/rag/embedder_local.py
from sentence_transformers import SentenceTransformer

def ensure_embedder():
    return SentenceTransformer('all-MiniLM-L6-v2')
```text

### Improve Vector Search

Implement proper cosine similarity in `analytics/rag/query_engine.py`:

```python
import numpy as np

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
```text

## Testing

```bash
# Test CSV export
python -c "
from pathlib import Path
from analytics.dashboards.exporter import export_csv_series
result = export_csv_series(Path('analytics/data'), Path('analytics/outputs/dashboards'))
print('Exported:', result)
"

# Test recommendations
python -c "
from analytics.recommenders.weights import recommend_weight_diffs
merged = {'seo': {'pages': [{'path': '/pricing', 'ok': False}]}}
anomalies = [{'field': 'seo_coverage_pct', 'z': -2.5}]
rec = recommend_weight_diffs(merged, anomalies)
print(rec)
"
```text

## License

Same as ApplyLens project.
