"""
Analytics Report Builder

Generates markdown insight summaries with anomaly detection and recommendations.
"""

from pathlib import Path
from datetime import date as date_type


def write_markdown_report(trend: dict, date: str, out_path: Path):
    """
    Write analytics report to markdown file.

    Args:
        trend: Trend data with anomalies
        date: Date string (YYYY-MM-DD)
        out_path: Output file path
    """
    md = "# Analytics Insight Summary\n\n"
    md += f"**Date:** {date}\n\n"

    # ... existing report sections would go here ...

    # Phase 51.3 — Recommendations (optional)
    try:
        from analytics.recommenders.weights import recommend_weight_diffs

        # Load latest merged day to pass into recommender
        from analytics.collectors.nightly_loader import load_nightly

        merged_today = load_nightly(date_type.fromisoformat(date))  # date from trend
        rec = recommend_weight_diffs(merged_today, trend.get("anomalies", []))

        if rec:
            md += "\n\n## Recommendations\n"
            md += f"{rec.rationale}\n\n"
            md += "**Proposed weight deltas:**\n\n"
            for k, v in rec.weight_diffs.items():
                md += f"- `{k}`: {v:+.3f}\n"
            md += "\n**Evidence:**\n"
            for e in rec.evidence:
                md += f"- {e}\n"
    except Exception as _e:
        md += "\n\n> _recommendations unavailable (error suppressed for robustness)_\n"

    # Write report
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
