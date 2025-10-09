"""
Analytics KPI Extractor

Extracts key performance indicators from daily metrics blob.
"""


def extract_kpis(blob: dict) -> dict:
    """
    Extract KPI metrics from daily analytics blob.
    
    Args:
        blob: Raw daily metrics dictionary
        
    Returns:
        Dict with KPI fields: seo_coverage_pct, playwright_pass_pct, avg_p95_ms, autofix_delta_count
    """
    kpi = {}
    
    # SEO coverage
    seo = blob.get("seo", {})
    total_pages = len(seo.get("pages", []))
    if total_pages > 0:
        ok_pages = sum(1 for p in seo.get("pages", []) if p.get("ok"))
        kpi["seo_coverage_pct"] = round((ok_pages / total_pages) * 100, 2)
    else:
        kpi["seo_coverage_pct"] = None
    
    # Playwright pass rate
    pw = blob.get("playwright", {})
    tests = pw.get("tests", [])
    if tests:
        passed = sum(1 for t in tests if t.get("status") == "passed")
        kpi["playwright_pass_pct"] = round((passed / len(tests)) * 100, 2)
    else:
        kpi["playwright_pass_pct"] = None
    
    # Performance: avg p95 latency
    perf = blob.get("performance", {})
    kpi["avg_p95_ms"] = perf.get("p95_ms")
    
    # Autofix delta count
    autofix = blob.get("autofix", {})
    kpi["autofix_delta_count"] = autofix.get("delta_count", 0)
    
    return kpi
