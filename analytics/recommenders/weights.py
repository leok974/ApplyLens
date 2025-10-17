"""
Phase 51.3 — Auto-recommend "weights" diffs (heuristic)

Analyzes anomalies to recommend safe adjustments to layout/test weights,
A/B variant weights, scheduler priorities, and page fix ordering.

Based on:
- SEO failures (pages with ok == false)
- Playwright test failures with path extraction
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import re
from collections import Counter

PAGE_RE = re.compile(r"(\/[a-zA-Z0-9\/\-\._]+)")


@dataclass
class Recommendation:
    """Weight adjustment recommendation with evidence."""

    rationale: str
    evidence: list[str]
    weight_diffs: dict[str, float]  # key -> delta


def _extract_paths_from_tests(tests: list[dict]) -> list[str]:
    """Extract page paths from failed Playwright tests."""
    paths = []
    for t in tests:
        if t.get("status") == "failed":
            name = " ".join([t.get("name", ""), t.get("title", "")])
            m = PAGE_RE.search(name)
            if m:
                paths.append(m.group(1))
            for hint in ("path", "url", "page"):
                if t.get(hint):
                    paths.append(str(t[hint]))
    return paths


def _load_page_map() -> dict[str, str]:
    """
    Optional: developer-provided hints (test name -> path).

    Create analytics/config/test_page_map.json with mappings like:
    {
        "login flow test": "/login",
        "checkout test": "/checkout"
    }
    """
    path = Path("analytics/config/test_page_map.json")
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _failed_seo_paths(seo: dict) -> list[str]:
    """Extract paths from SEO pages that failed checks."""
    paths = []
    for p in seo.get("pages", []):
        if not p.get("ok"):
            paths.append(p.get("path") or p.get("url") or "")
    return [p for p in paths if p]


def recommend_weight_diffs(
    merged: dict, anomalies: list[dict]
) -> Recommendation | None:
    """
    Generate weight adjustment recommendations based on anomalies.

    Args:
        merged: Daily merged metrics (seo, playwright, etc.)
        anomalies: List of detected anomalies with field and z-score

    Returns:
        Recommendation object with proposed weight changes, or None if no recommendations
    """
    if not anomalies:
        return None

    seo_paths = _failed_seo_paths(merged.get("seo", {}))
    pw_tests = merged.get("playwright", {}).get("tests", [])
    page_map = _load_page_map()

    test_failed_paths = _extract_paths_from_tests(pw_tests)

    # Map named tests via hints
    for t in pw_tests:
        nm = t.get("name") or t.get("title")
        if t.get("status") == "failed" and nm in page_map:
            test_failed_paths.append(page_map[nm])

    # Aggregate "pressure" by path
    pressure = Counter([*seo_paths, *test_failed_paths])
    if not pressure:
        return None

    # Heuristic: increase priority weight for failing pages
    # decrease weight for risky variants if you use them
    # We'll emit a generic weight key per path; your UI can translate to actual knobs
    # (e.g., "page_priority:/pricing")
    weight_diffs = {}
    evidence = []

    for path, count in pressure.most_common(8):
        delta = min(0.05 * count, 0.2)  # cap per run
        weight_diffs[f"page_priority:{path}"] = round(+delta, 3)
        evidence.append(f"{path} (+{delta:.2f}) from {count} failure signals")

    # If Playwright pass rate dropped, bias "stability-first" variant selection
    playwright_drop = any(
        a["field"] == "playwright_pass_pct" and a["z"] < -2 for a in anomalies
    )
    if playwright_drop:
        weight_diffs["variant:stability_over_speed"] = +0.1
        evidence.append("Playwright drop → prefer stability variant (+0.10)")

    rationale = (
        "Elevate attention to pages implicated by SEO/Test failures; "
        "prefer stable variants until green."
    )

    return Recommendation(
        rationale=rationale, evidence=evidence, weight_diffs=weight_diffs
    )
