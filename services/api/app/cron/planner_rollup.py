"""Weekly planner diff rollup job.

Analyzes planner V1 vs V2 decisions from audit logs and generates
a weekly summary markdown report with:
- Traffic split percentage
- Agent selection differences
- Notable divergences
- Recommendations
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any
from collections import Counter

from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AgentAuditLog


def analyze_planner_diffs(
    db: Session, start_date: datetime, end_date: datetime
) -> Dict[str, Any]:
    """Analyze planner decisions over date range.

    Args:
        db: Database session
        start_date: Analysis start date
        end_date: Analysis end date

    Returns:
        Analysis dict with stats and divergences
    """
    # Query runs in date range with planner_meta
    runs = (
        db.query(AgentAuditLog)
        .filter(
            AgentAuditLog.started_at >= start_date,
            AgentAuditLog.started_at < end_date,
            AgentAuditLog.plan.isnot(None),
        )
        .all()
    )

    # Extract planner metadata
    v1_count = 0
    v2_count = 0
    diffs = []
    agent_changes = Counter()

    for run in runs:
        if not run.plan or not isinstance(run.plan, dict):
            continue

        planner_meta = run.plan.get("planner_meta", {})
        if not planner_meta:
            continue

        selected = planner_meta.get("selected")
        if selected == "v1":
            v1_count += 1
        elif selected == "v2":
            v2_count += 1

        # Collect diff info
        diff = planner_meta.get("diff", {})
        if diff.get("agent_changed"):
            v1_agent = diff.get("v1_agent", "unknown")
            v2_agent = diff.get("v2_agent", "unknown")
            agent_changes[(v1_agent, v2_agent)] += 1

            # Store notable divergences
            diffs.append(
                {
                    "run_id": run.run_id,
                    "objective": run.objective[:100],
                    "v1_agent": v1_agent,
                    "v2_agent": v2_agent,
                    "selected": selected,
                    "started_at": run.started_at,
                }
            )

    # Compute stats
    total_runs = v1_count + v2_count
    v2_pct = (v2_count / total_runs * 100) if total_runs > 0 else 0.0
    agent_change_rate = (
        (sum(1 for d in diffs) / total_runs * 100) if total_runs > 0 else 0.0
    )

    # Top disagreements
    top_disagreements = agent_changes.most_common(5)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_runs": total_runs,
        "v1_count": v1_count,
        "v2_count": v2_count,
        "v2_pct": v2_pct,
        "agent_change_rate": agent_change_rate,
        "top_disagreements": top_disagreements,
        "notable_diffs": diffs[:20],  # Top 20 divergences
    }


def generate_weekly_report(analysis: Dict[str, Any]) -> str:
    """Generate markdown report from analysis.

    Args:
        analysis: Analysis dictionary

    Returns:
        Markdown report string
    """
    start = analysis["start_date"].strftime("%Y-%m-%d")
    end = analysis["end_date"].strftime("%Y-%m-%d")
    week_num = analysis["start_date"].isocalendar()[1]
    year = analysis["start_date"].year

    lines = [
        f"# Planner Weekly Report — {year}-W{week_num}",
        "",
        f"**Period:** {start} to {end}",
        f"**Total Runs:** {analysis['total_runs']}",
        "",
        "## Traffic Split",
        "",
        f"- **V1 (original):** {analysis['v1_count']} runs ({100 - analysis['v2_pct']:.1f}%)",
        f"- **V2 (canary):** {analysis['v2_count']} runs ({analysis['v2_pct']:.1f}%)",
        "",
        "## Decision Differences",
        "",
        f"- **Agent change rate:** {analysis['agent_change_rate']:.1f}% (V1 vs V2 chose different agents)",
        "",
    ]

    # Top disagreements
    if analysis["top_disagreements"]:
        lines.extend(
            [
                "### Top Agent Disagreements",
                "",
                "| V1 Agent | V2 Agent | Count |",
                "|----------|----------|-------|",
            ]
        )
        for (v1_agent, v2_agent), count in analysis["top_disagreements"]:
            lines.append(f"| `{v1_agent}` | `{v2_agent}` | {count} |")
        lines.append("")

    # Notable divergences
    if analysis["notable_diffs"]:
        lines.extend(
            [
                "### Notable Divergences (Sample)",
                "",
                "| Objective | V1 Chose | V2 Chose | Selected |",
                "|-----------|----------|----------|----------|",
            ]
        )
        for diff in analysis["notable_diffs"][:10]:  # Top 10
            lines.append(
                f"| {diff['objective'][:50]}... | "
                f"`{diff['v1_agent']}` | "
                f"`{diff['v2_agent']}` | "
                f"**{diff['selected'].upper()}** |"
            )
        lines.append("")

    # Recommendations
    lines.extend(
        [
            "## Recommendations",
            "",
        ]
    )

    if analysis["v2_pct"] < 5:
        lines.append(
            "- ✅ **Increase canary to 10%** - V2 traffic is very low, consider ramping up"
        )
    elif analysis["v2_pct"] < 20:
        lines.append(
            "- ✅ **Maintain current split** - Good canary percentage for evaluation"
        )
    else:
        lines.append(
            "- ⚠️ **High canary traffic** - Consider gradual rollout to avoid risk"
        )

    if analysis["agent_change_rate"] > 30:
        lines.append(
            "- ⚠️ **High disagreement rate** - V1 and V2 choosing different agents frequently"
        )
        lines.append("  - Review skill scoring weights in PlannerV2")
        lines.append("  - Add targeted golden tasks for top disagreement scenarios")
    elif analysis["agent_change_rate"] < 5:
        lines.append("- ✅ **Low disagreement rate** - V1 and V2 are aligned")

    lines.extend(
        [
            "",
            "## Actions",
            "",
            "- [ ] Review top disagreements for correctness",
            "- [ ] Check quality metrics dashboard for V1 vs V2 performance",
            "- [ ] Consider adjusting canary percentage based on confidence",
            "",
            "---",
            f"*Generated on {datetime.utcnow().isoformat()}*",
        ]
    )

    return "\n".join(lines)


def run_weekly_rollup(output_path: str = "agent/artifacts/planner"):
    """Run weekly planner rollup job.

    Args:
        output_path: Directory to save report
    """
    # Get date range (last 7 days)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    # Get database session
    db = next(get_db())

    try:
        # Analyze planner diffs
        print(f"Analyzing planner decisions from {start_date} to {end_date}...")
        analysis = analyze_planner_diffs(db, start_date, end_date)

        # Generate report
        print("Generating weekly report...")
        report = generate_weekly_report(analysis)

        # Save to file
        os.makedirs(output_path, exist_ok=True)
        week_num = start_date.isocalendar()[1]
        year = start_date.year
        filename = f"weekly_{year}_W{week_num}.md"
        filepath = os.path.join(output_path, filename)

        with open(filepath, "w") as f:
            f.write(report)

        print(f"✅ Report saved to {filepath}")
        print("\nSummary:")
        print(f"  Total runs: {analysis['total_runs']}")
        print(f"  V2 traffic: {analysis['v2_pct']:.1f}%")
        print(f"  Agent change rate: {analysis['agent_change_rate']:.1f}%")

    finally:
        db.close()


if __name__ == "__main__":
    # Allow custom output path from CLI
    output_path = sys.argv[1] if len(sys.argv) > 1 else "agent/artifacts/planner"
    run_weekly_rollup(output_path)
