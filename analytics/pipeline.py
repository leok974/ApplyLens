"""
Analytics Pipeline - Main Entry Point

Phase 51.1 integration: CSV dashboard export
"""

from pathlib import Path

# Configuration
DATA_DIR = Path("analytics/data")
OUT_DIR = Path("analytics/outputs")


def run_pipeline():
    """Main pipeline execution."""
    # ... existing pipeline logic would go here ...

    # Phase 51.1 — CSV dashboards
    from analytics.dashboards.exporter import export_csv_series

    csv_files = export_csv_series(DATA_DIR, OUT_DIR / "dashboards")

    if csv_files:
        print("✅ CSV dashboards exported:")
        for name, path in csv_files.items():
            print(f"   {name}: {path}")


if __name__ == "__main__":
    run_pipeline()
