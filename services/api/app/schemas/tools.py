"""Pydantic schemas for tool results."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel


class GmailMessage(BaseModel):
    """A Gmail message."""
    
    id: str
    thread_id: str
    subject: str
    from_addr: str
    received_at: str


class GmailSearchResponse(BaseModel):
    """Response from Gmail search."""
    
    messages: List[GmailMessage]


class BQQueryResult(BaseModel):
    """Result from BigQuery query."""
    
    rows: List[Dict[str, Any]]
    stats: Dict[str, Any]


class DbtRunResult(BaseModel):
    """Result from dbt run."""
    
    success: bool
    elapsed_sec: float
    artifacts_path: str | None = None


class ESSearchHit(BaseModel):
    """A single Elasticsearch search hit."""
    
    id: str
    score: float
    source: Dict[str, Any]


class ESSearchResponse(BaseModel):
    """Response from Elasticsearch search."""
    
    hits: List[ESSearchHit]
