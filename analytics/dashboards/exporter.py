"""
Phase 51.1 — CSV Dashboard Exporter

Exports daily KPI metrics to CSV format for dashboards and visualization tools.
Generates both wide-format (columns per metric) and long-format (metric,value pairs).
"""

from __future__ import annotations
import csv
import json
from pathlib import Path

KPI_FIELDS = [
    "seo_coverage_pct",
    "playwright_pass_pct",
    "avg_p95_ms",
    "autofix_delta_count",
]


def _load_daily(path: Path) -> dict:
    """Load daily metrics from JSON file, extracting KPI fields."""
    blob = json.loads(path.read_text())
    kpi = blob.get("kpi")
    if not kpi:  # compute on the fly if needed
        from analytics.collectors.kpi_extractor import extract_kpis

        kpi = extract_kpis(blob)
    return {"date": path.stem, **{k: kpi.get(k) for k in KPI_FIELDS}}


def export_csv_series(data_dir: Path, out_dir: Path) -> dict[str, Path]:
    """
    Export KPI time-series to CSV files.

    Args:
        data_dir: Directory containing daily *.json files
        out_dir: Output directory for CSV files

    Returns:
        Dict mapping CSV type to file path
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [_load_daily(p) for p in sorted(data_dir.glob("*.json"))]
    if not rows:
        return {}

    # 1) Wide KPI series (date, seo_coverage_pct, playwright_pass_pct, ...)
    kpi_csv = out_dir / "kpis.csv"
    with kpi_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", *KPI_FIELDS])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # 2) Long form for quick charts (date, metric, value)
    long_csv = out_dir / "kpis_long.csv"
    with long_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "metric", "value"])
        w.writeheader()
        for r in rows:
            d = r.pop("date")
            for k, v in r.items():
                if v is not None:
                    w.writerow({"date": d, "metric": k, "value": v})

    return {"kpis_csv": kpi_csv, "kpis_long_csv": long_csv}
