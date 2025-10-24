"""
Phase 51.2 — Analytics API Router

Provides search and dashboard endpoints for analytics data.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/latest")
def latest():
    """Get the latest analytics insight summary."""
    p = Path("analytics/outputs/insight-summary.md")
    if not p.exists():
        return {"status": "pending"}
    return {"status": "ok", "markdown": p.read_text(encoding="utf-8")}


@router.get("/search/")
def search(q: str = Query(..., min_length=2), k: int = 6):
    """
    Search analytics vector store for relevant insights.

    Args:
        q: Search query (min 2 chars)
        k: Number of results to return (default 6)
    """
    vs_path = Path("analytics/rag/vector_store.sqlite")
    if not vs_path.exists():
        raise HTTPException(409, "Vector store not built yet; run analytics pipeline")

    # Import locally to avoid hard dependency
    try:
        from analytics.rag.embedder_local import ensure_embedder
        from analytics.rag.query_engine import VectorStore
    except ImportError:
        raise HTTPException(500, "Analytics RAG modules not available")

    embed = ensure_embedder()
    vs = VectorStore(vs_path)
    hits = vs.search(embed, q, k=k)
    return {"query": q, "k": k, "results": hits}


@router.get("/dashboards/kpis.csv")
def dashboards_kpis_csv():
    """Get CSV preview of KPI dashboard data."""
    csv_path = Path("analytics/outputs/dashboards/kpis.csv")
    if not csv_path.exists():
        raise HTTPException(404, "kpis.csv not found; run analytics pipeline")

    lines = csv_path.read_text(encoding="utf-8").splitlines()
    return {
        "status": "ok",
        "path": str(csv_path),
        "preview": lines[:10],
        "total_rows": len(lines) - 1,  # excluding header
    }
