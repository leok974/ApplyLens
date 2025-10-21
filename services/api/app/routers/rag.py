# services/api/app/routers/rag.py
"""
Phase 4 AI Feature: RAG-powered Search
Provides semantic search over email corpus using Elasticsearch with highlights.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

from elasticsearch import Elasticsearch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])

# Feature flag
FEATURE_RAG_SEARCH = os.getenv("FEATURE_RAG_SEARCH", "true").lower() == "true"

# Elasticsearch configuration
ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ES_INDEX = os.getenv("ELASTICSEARCH_INDEX", "emails")
ES_TIMEOUT = int(os.getenv("ELASTICSEARCH_TIMEOUT_MS", "5000")) / 1000  # Convert to seconds


# ---------- Models ----------


class RagQueryRequest(BaseModel):
    """Request for semantic search"""
    q: str = Field(..., min_length=1, max_length=500, description="Search query")
    k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    
    class Config:
        json_schema_extra = {
            "example": {
                "q": "interview scheduling conflict",
                "k": 5
            }
        }


class RagHit(BaseModel):
    """Single search result with highlights"""
    thread_id: str
    message_id: str
    score: float
    highlights: List[str] = Field(default_factory=list, description="Highlighted snippets")
    sender: str
    subject: str
    date: str  # ISO 8601
    
    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "thread-abc",
                "message_id": "msg-123",
                "score": 0.85,
                "highlights": ["...scheduling <em>conflict</em> next week..."],
                "sender": "john@example.com",
                "subject": "Re: Interview Schedule",
                "date": "2025-01-15T10:30:00Z"
            }
        }


class RagQueryResponse(BaseModel):
    """Response with search results"""
    hits: List[RagHit]
    total: int = Field(description="Total number of matching documents")
    
    class Config:
        json_schema_extra = {
            "example": {
                "hits": [
                    {
                        "thread_id": "thread-abc",
                        "message_id": "msg-123",
                        "score": 0.85,
                        "highlights": ["...scheduling <em>conflict</em>..."],
                        "sender": "john@example.com",
                        "subject": "Interview Schedule",
                        "date": "2025-01-15T10:30:00Z"
                    }
                ],
                "total": 12
            }
        }


# ---------- Mock data for demo ----------


def get_mock_search_results(query: str, k: int) -> RagQueryResponse:
    """
    Returns mock search results for demo purposes.
    In production, this would query Elasticsearch.
    """
    # Demo data - Bianca interview thread
    mock_hits = [
        RagHit(
            thread_id="demo-1",
            message_id="msg-001",
            score=0.92,
            highlights=[
                "...initial <em>interview</em> <em>scheduling</em> for next week...",
                "...prefer Tuesday or Wednesday afternoon..."
            ],
            sender="bianca@techcorp.com",
            subject="Interview Scheduling - Software Engineer Position",
            date="2025-01-14T09:00:00Z"
        ),
        RagHit(
            thread_id="demo-1",
            message_id="msg-002",
            score=0.88,
            highlights=[
                "...Tuesday at 2 PM works perfectly...",
                "...looking forward to the <em>interview</em>..."
            ],
            sender="hiring@startup.io",
            subject="Re: Interview Scheduling",
            date="2025-01-14T14:30:00Z"
        ),
        RagHit(
            thread_id="demo-1",
            message_id="msg-003",
            score=0.75,
            highlights=[
                "...unfortunately a <em>conflict</em> has come up...",
                "...would Wednesday at 3 PM work instead?..."
            ],
            sender="bianca@techcorp.com",
            subject="Re: Interview Scheduling - Time Change",
            date="2025-01-15T10:45:00Z"
        ),
    ]
    
    # Filter based on query keywords (simple mock matching)
    query_lower = query.lower()
    keywords = ["interview", "schedule", "scheduling", "conflict", "time", "change"]
    
    if any(kw in query_lower for kw in keywords):
        return RagQueryResponse(
            hits=mock_hits[:k],
            total=len(mock_hits)
        )
    else:
        # Return empty results for non-matching queries
        return RagQueryResponse(hits=[], total=0)


# ---------- Elasticsearch helpers ----------


def get_es_client() -> Optional[Elasticsearch]:
    """
    Returns Elasticsearch client if available.
    Returns None if ES is not configured or unavailable.
    """
    try:
        client = Elasticsearch(
            [ES_HOST],
            request_timeout=ES_TIMEOUT,
            max_retries=1,
            retry_on_timeout=False
        )
        # Quick health check
        if not client.ping():
            logger.warning("Elasticsearch ping failed, using mock data")
            return None
        return client
    except Exception as e:
        logger.warning(f"Elasticsearch unavailable: {e}, using mock data")
        return None


def search_elasticsearch(query: str, k: int) -> RagQueryResponse:
    """
    Searches Elasticsearch index with highlights.
    Falls back to mock data if ES is unavailable.
    """
    es = get_es_client()
    
    if es is None:
        logger.info("Using mock search results (ES unavailable)")
        return get_mock_search_results(query, k)
    
    try:
        # Build search query with multi-match across fields
        es_query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["subject^2", "body_text", "sender"],
                    "type": "best_fields"
                }
            },
            "highlight": {
                "fields": {
                    "subject": {"number_of_fragments": 0},
                    "body_text": {
                        "fragment_size": 150,
                        "number_of_fragments": 3,
                        "pre_tags": ["<em>"],
                        "post_tags": ["</em>"]
                    }
                }
            },
            "size": k,
            "_source": ["thread_id", "message_id", "sender", "subject", "date"]
        }
        
        response = es.search(index=ES_INDEX, body=es_query)
        
        hits = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            highlights = []
            
            # Extract highlights
            if "highlight" in hit:
                if "subject" in hit["highlight"]:
                    highlights.extend(hit["highlight"]["subject"])
                if "body_text" in hit["highlight"]:
                    highlights.extend(hit["highlight"]["body_text"])
            
            hits.append(RagHit(
                thread_id=source.get("thread_id", ""),
                message_id=source.get("message_id", hit["_id"]),
                score=round(hit["_score"], 2),
                highlights=highlights,
                sender=source.get("sender", "unknown"),
                subject=source.get("subject", ""),
                date=source.get("date", "")
            ))
        
        total = response["hits"]["total"]["value"] if isinstance(response["hits"]["total"], dict) else response["hits"]["total"]
        
        return RagQueryResponse(hits=hits, total=total)
        
    except Exception as e:
        logger.error(f"Elasticsearch query failed: {e}", exc_info=True)
        # Fallback to mock data on error
        return get_mock_search_results(query, k)


# ---------- Endpoints ----------


@router.post("/query", response_model=RagQueryResponse)
async def query_rag(request: RagQueryRequest):
    """
    RAG-powered semantic search across email corpus.
    
    Returns ranked results with highlighted snippets showing
    where the query terms appear in the email content.
    
    Falls back to mock data if Elasticsearch is unavailable.
    """
    if not FEATURE_RAG_SEARCH:
        raise HTTPException(
            status_code=503,
            detail="RAG search feature is disabled (FEATURE_RAG_SEARCH=false)"
        )
    
    logger.info(f"RAG query: '{request.q}' (k={request.k})")
    
    try:
        results = search_elasticsearch(request.q, request.k)
        logger.info(f"RAG query returned {len(results.hits)} hits (total={results.total})")
        return results
        
    except Exception as e:
        logger.error(f"RAG query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/health")
def rag_health():
    """
    Check RAG search service health.
    Returns ES status and feature flag state.
    """
    es = get_es_client()
    
    return {
        "feature_enabled": FEATURE_RAG_SEARCH,
        "elasticsearch_available": es is not None,
        "elasticsearch_host": ES_HOST,
        "elasticsearch_index": ES_INDEX,
        "fallback_mode": "mock" if es is None else "live"
    }
