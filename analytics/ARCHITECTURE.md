# Analytics Phase 51 - Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Analytics Phase 51                          │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  Phase 51.1 │  │  Phase 51.2 │  │  Phase 51.3 │                │
│  │     CSV     │  │   Search    │  │   Weights   │                │
│  │  Dashboards │  │     API     │  │    Recs     │                │
│  └────────────┘  └────────────┘  └────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         Input Layer                               │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    analytics/data/*.json
                    (Daily metrics files)
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Processing Layer                             │
│                                                                    │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │  kpi_extractor   │◄────────│ nightly_loader   │              │
│  │   .extract_kpis  │         │  .load_nightly   │              │
│  └──────────────────┘         └──────────────────┘              │
│           │                                                        │
│           ▼                                                        │
│  ┌──────────────────┐                                            │
│  │   pipeline.py    │───────┐                                    │
│  │  (Main runner)   │       │                                    │
│  └──────────────────┘       │                                    │
└──────────────────────────────│────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Export Layer (51.1)                         │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              dashboards/exporter.py                       │   │
│  │         .export_csv_series(data_dir, out_dir)            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                               │                                    │
│                               ▼                                    │
│           ┌───────────────────────────────────┐                  │
│           │  outputs/dashboards/kpis.csv      │                  │
│           │  outputs/dashboards/kpis_long.csv │                  │
│           └───────────────────────────────────┘                  │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Indexing Layer (51.2)                         │
│                                                                    │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │ embedder_local   │────────▶│  query_engine    │              │
│  │ .ensure_embedder │         │   VectorStore    │              │
│  └──────────────────┘         └──────────────────┘              │
│                                        │                           │
│                                        ▼                           │
│                          rag/vector_store.sqlite                  │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                  Recommendation Layer (51.3)                      │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │          recommenders/weights.py                          │   │
│  │       .recommend_weight_diffs(merged, anomalies)         │   │
│  │                                                            │   │
│  │  Analyzes:                                                │   │
│  │  • SEO page failures (ok == false)                       │   │
│  │  • Playwright test failures (with path extraction)       │   │
│  │                                                            │   │
│  │  Outputs:                                                 │   │
│  │  • page_priority:/{path} deltas                          │   │
│  │  • variant:stability_over_speed flag                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                               │                                    │
│                               ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │          summarizers/report_builder.py                    │   │
│  │         .write_markdown_report(trend, date)              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                               │                                    │
│                               ▼                                    │
│                 outputs/insight-summary.md                        │
│                 (with Recommendations section)                    │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                        API Layer (51.2)                           │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │            services/api/app/routers/analytics.py          │   │
│  │                                                            │   │
│  │  GET /analytics/latest                                    │   │
│  │  ├─▶ Returns: insight-summary.md                         │   │
│  │                                                            │   │
│  │  GET /analytics/search?q=...&k=6                         │   │
│  │  ├─▶ VectorStore.search(embedder, query, k)             │   │
│  │  └─▶ Returns: {query, k, results}                       │   │
│  │                                                            │   │
│  │  GET /analytics/dashboards/kpis.csv                      │   │
│  │  ├─▶ Read: outputs/dashboards/kpis.csv                  │   │
│  │  └─▶ Returns: {status, path, preview, total_rows}       │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Integration Layer                            │
│                                                                    │
│  ┌────────────────────────────────────────────────────┐          │
│  │  services/api/app/main.py                          │          │
│  │  ├─▶ Auto-register analytics router (try/except)   │          │
│  │  └─▶ Graceful fallback if module missing          │          │
│  └────────────────────────────────────────────────────┘          │
│                                                                    │
│  ┌────────────────────────────────────────────────────┐          │
│  │  .github/workflows/analytics-pr-comment.yml        │          │
│  │  ├─▶ Run analytics pipeline on PR                  │          │
│  │  ├─▶ Extract insights section                      │          │
│  │  ├─▶ Extract recommendations section               │          │
│  │  └─▶ Post sticky comments to PR                    │          │
│  └────────────────────────────────────────────────────┘          │
└──────────────────────────────────────────────────────────────────┘
```

## Component Interactions

```
┌─────────────────────────────────────────────────────────────────┐
│                        Daily Pipeline Run                         │
└─────────────────────────────────────────────────────────────────┘

Step 1: Load Data
    nightly_loader.load_nightly(date)
    ↓
    Returns: {seo: {...}, playwright: {...}, performance: {...}}

Step 2: Extract KPIs
    kpi_extractor.extract_kpis(blob)
    ↓
    Returns: {seo_coverage_pct: 95.2, playwright_pass_pct: 98.5, ...}

Step 3: Export CSVs (Phase 51.1)
    exporter.export_csv_series(data_dir, out_dir)
    ↓
    Creates: kpis.csv, kpis_long.csv

Step 4: Detect Anomalies
    (Existing anomaly detection logic)
    ↓
    Returns: [{field: "seo_coverage_pct", z: -2.5}, ...]

Step 5: Generate Recommendations (Phase 51.3)
    weights.recommend_weight_diffs(merged, anomalies)
    ↓
    Analyzes:
      • Failed SEO pages → extract paths
      • Failed Playwright tests → extract paths
      • Aggregate pressure by path
      • Calculate deltas (0.05 per failure, cap 0.2)
    ↓
    Returns: Recommendation(rationale, evidence, weight_diffs)

Step 6: Build Report
    report_builder.write_markdown_report(trend, date, out_path)
    ↓
    Writes: insight-summary.md
    Includes: ## Recommendations section

Step 7: Index for Search (Phase 51.2)
    VectorStore.add(text, metadata)
    ↓
    Updates: vector_store.sqlite
```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Graceful Degradation                           │
└─────────────────────────────────────────────────────────────────┘

API Router Registration (main.py)
    try:
        from .routers.analytics import router
        app.include_router(router)
    except ImportError:
        pass  # No error, analytics just unavailable
        ↓
    Result: API starts normally, analytics endpoints return 404

Recommendations (report_builder.py)
    try:
        rec = recommend_weight_diffs(merged, anomalies)
        # Add recommendations section
    except Exception:
        md += "> _recommendations unavailable_\n"
        ↓
    Result: Report still generated, just without recommendations

Vector Store Search (analytics.py)
    if not vs_path.exists():
        raise HTTPException(409, "Vector store not built yet")
        ↓
    Result: Clear error message, user knows to run pipeline

CSV Preview (analytics.py)
    if not csv_path.exists():
        raise HTTPException(404, "kpis.csv not found")
        ↓
    Result: Clear error message, user knows to run pipeline
```

## File Dependencies

```
analytics/dashboards/exporter.py
    └─▶ analytics/collectors/kpi_extractor.py (optional)

analytics/recommenders/weights.py
    └─▶ analytics/config/test_page_map.json (optional)

analytics/summarizers/report_builder.py
    ├─▶ analytics/recommenders/weights.py
    └─▶ analytics/collectors/nightly_loader.py

services/api/app/routers/analytics.py
    ├─▶ analytics/rag/embedder_local.py
    ├─▶ analytics/rag/query_engine.py
    └─▶ analytics/outputs/... (runtime)

.github/workflows/analytics-pr-comment.yml
    └─▶ analytics/pipeline.py (runtime)
```

## Output Files

```
analytics/
├── outputs/
│   ├── dashboards/
│   │   ├── kpis.csv           # Wide format: date, metric1, metric2, ...
│   │   └── kpis_long.csv      # Long format: date, metric, value
│   └── insight-summary.md     # Markdown report with recommendations
└── rag/
    └── vector_store.sqlite    # Search index

Generated by:
├── kpis.csv           ← exporter.export_csv_series()
├── kpis_long.csv      ← exporter.export_csv_series()
├── insight-summary.md ← report_builder.write_markdown_report()
└── vector_store.sqlite ← VectorStore.add()
```

## Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Integrations                          │
└─────────────────────────────────────────────────────────────────┘

1. FastAPI (services/api/app/main.py)
   ├─▶ Auto-registers /analytics/* endpoints
   └─▶ Graceful fallback if analytics not available

2. Grafana (optional)
   ├─▶ CSV datasource → kpis.csv
   ├─▶ Time-series panel → date column as X-axis
   └─▶ Metric columns as Y-axis

3. GitHub Actions (.github/workflows/analytics-pr-comment.yml)
   ├─▶ Runs pipeline on PR open/sync
   ├─▶ Extracts insights and recommendations
   └─▶ Posts sticky comments to PR

4. Frontend (future integration)
   ├─▶ GET /analytics/latest → render markdown
   ├─▶ GET /analytics/search → search box
   └─▶ GET /analytics/dashboards/kpis.csv → render table/chart
```

## Security & Safety

```
┌─────────────────────────────────────────────────────────────────┐
│                     Safety Guarantees                             │
└─────────────────────────────────────────────────────────────────┘

✓ Non-breaking
  • All additions wrapped in try/except
  • Missing modules don't crash the app
  • Analytics endpoints optional

✓ Conservative recommendations
  • Weight deltas capped at 0.2 per run
  • Evidence provided for all suggestions
  • User decides whether to apply

✓ Data isolation
  • All outputs gitignored (analytics/.gitignore)
  • No modification of source data
  • Read-only operations on inputs

✓ Error resilience
  • 404/409 for missing resources
  • Graceful degradation everywhere
  • Clear error messages
```
