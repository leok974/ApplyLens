"""
RAG (Retrieval-Augmented Generation) search over Elasticsearch.

Combines keyword (BM25) and semantic (vector) search for better email retrieval.
Supports structured filters for category, risk score, sender domain, and date ranges.
"""

from typing import Dict, Any, List, Optional
from .text import embed_query


def rag_search(
    es,
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    k: int = 50,
    user_id: Optional[int] = None,
    mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform hybrid keyword + semantic search over emails.
    
    Args:
        es: Elasticsearch client
        query: User's search query
        filters: Optional structured filters:
            - category: str (e.g., "promotions", "jobs", "suspicious")
            - risk_min: int (minimum risk score, 0-100)
            - risk_max: int (maximum risk score, 0-100)
            - sender_domain: str (e.g., "linkedin.com")
            - date_from: str (ISO format, e.g., "2025-10-01")
            - date_to: str (ISO format, e.g., "2025-10-31")
            - labels: List[str] (e.g., ["needs_reply", "newsletter"])
        k: Number of results to return (default 50)
        user_id: Optional user ID for multi-tenant filtering
        
    Returns:
        Dictionary with:
            - docs: List of email documents with id, subject, sender, etc.
            - total: Total number of matching documents
            - query: Original query (for debugging)
    """
    filters = filters or {}
    
    # Build Elasticsearch query
    must: List[Dict[str, Any]] = []
    
    # Keyword search across multiple fields
    if query.strip():
        must.append({
            "multi_match": {
                "query": query,
                "fields": [
                    "subject^3",      # Subject is most important
                    "body_text^2",    # Body text is important
                    "sender^1.5",     # Sender is moderately important
                    "recipient",
                    "labels",
                ],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        })
    
    # Apply filters
    if category := filters.get("category"):
        must.append({"term": {"category": category}})
    
    if risk_min := filters.get("risk_min"):
        must.append({"range": {"risk_score": {"gte": risk_min}}})
    
    if risk_max := filters.get("risk_max"):
        must.append({"range": {"risk_score": {"lte": risk_max}}})
    
    if sender_domain := filters.get("sender_domain"):
        must.append({"term": {"sender_domain": sender_domain}})
    
    if labels := filters.get("labels"):
        if isinstance(labels, list):
            must.append({"terms": {"labels": labels}})
        else:
            must.append({"term": {"labels": labels}})
    
    # Date range filter
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if date_from or date_to:
        range_filter: Dict[str, Any] = {}
        if date_from:
            range_filter["gte"] = date_from
        if date_to:
            range_filter["lte"] = date_to
        must.append({"range": {"received_at": range_filter}})
    
    # Multi-tenant filtering
    if user_id:
        must.append({"term": {"user_id": user_id}})
    
    # Phase 6: ATS boosting - Boost urgent recruiter emails
    should: List[Dict[str, Any]] = [
        # High ghosting risk (likely being ghosted)
        {"range": {"ats.ghosting_risk": {"gte": 0.6}}},
        # Critical stages (Onsite, Offer)
        {"terms": {"ats.stage": ["Onsite", "Offer", "Final Round", "Negotiation"]}}
    ]
    
    # Phase 6: Mode-specific boosts
    if mode == "networking":
        should.extend([
            {"term": {"category": "event"}},
            {"match": {"subject": "meetup"}},
            {"match": {"subject": "conference"}},
            {"match": {"subject": "webinar"}}
        ])
    elif mode == "money":
        should.extend([
            {"match": {"subject": "receipt"}},
            {"match": {"subject": "invoice"}},
            {"match": {"subject": "payment"}},
            {"term": {"category": "finance"}}
        ])
    
    # Keyword search
    body: Dict[str, Any] = {
        "size": k,
        "query": {
            "bool": {
                "must": must if must else [{"match_all": {}}],
                "should": should,  # Optional boosts
                "minimum_should_match": 0  # Don't require should clauses
            }
        },
        "sort": [
            {"_score": {"order": "desc"}},
            {"received_at": {"order": "desc"}}
        ],
        "_source": [
            "subject", "sender", "sender_domain", "recipient",
            "received_at", "category", "labels", "risk_score",
            "body_text", "expires_at"
        ]
    }
    
    try:
        kw_response = es.search(index="emails", body=body)
        kw_hits = kw_response["hits"]["hits"]
        total = kw_response["hits"]["total"]["value"]
    except Exception as e:
        print(f"Keyword search error: {e}")
        kw_hits = []
        total = 0
    
    # Semantic search (optional - only if body_vector field exists)
    knn_hits: List[Dict[str, Any]] = []
    try:
        if query.strip():
            qv = embed_query(query)
            
            # KNN search for semantic similarity
            knn_body = {
                "knn": {
                    "field": "body_vector",
                    "query_vector": qv,
                    "k": k,
                    "num_candidates": max(100, k * 2)
                },
                "_source": [
                    "subject", "sender", "sender_domain", "recipient",
                    "received_at", "category", "labels", "risk_score"
                ]
            }
            
            # Apply same filters to KNN search
            if must:
                knn_body["knn"]["filter"] = {"bool": {"must": must}}
            
            knn_response = es.search(index="emails", body=knn_body)
            knn_hits = knn_response["hits"]["hits"]
    except Exception as e:
        # Semantic search is optional - fail gracefully
        print(f"Semantic search not available or failed: {e}")
        knn_hits = []
    
    # Merge results (favor keyword top hits, then add unique semantic matches)
    seen_ids = set()
    docs: List[Dict[str, Any]] = []
    
    # Add keyword results first (higher priority)
    for hit in kw_hits:
        _id = hit["_id"]
        if _id in seen_ids:
            continue
        seen_ids.add(_id)
        
        source = hit.get("_source", {})
        docs.append({
            "id": _id,
            "score": hit.get("_score", 0),
            "search_type": "keyword",
            **source
        })
        
        if len(docs) >= k:
            break
    
    # Add semantic results (fill remaining slots)
    for hit in knn_hits:
        _id = hit["_id"]
        if _id in seen_ids:
            continue
        seen_ids.add(_id)
        
        source = hit.get("_source", {})
        docs.append({
            "id": _id,
            "score": hit.get("_score", 0),
            "search_type": "semantic",
            **source
        })
        
        if len(docs) >= k:
            break
    
    return {
        "docs": docs,
        "total": total,
        "query": query,
        "filters": filters,
        "count": len(docs)
    }


def search_by_email_id(es, email_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch specific emails by their IDs.
    
    Args:
        es: Elasticsearch client
        email_ids: List of email IDs to fetch
        
    Returns:
        List of email documents
    """
    try:
        body = {
            "query": {
                "ids": {
                    "values": email_ids
                }
            },
            "size": len(email_ids),
            "_source": [
                "subject", "sender", "sender_domain", "recipient",
                "received_at", "category", "labels", "risk_score",
                "body_text"
            ]
        }
        
        response = es.search(index="emails", body=body)
        hits = response["hits"]["hits"]
        
        return [
            {"id": hit["_id"], **hit.get("_source", {})}
            for hit in hits
        ]
    except Exception as e:
        print(f"Error fetching emails by ID: {e}")
        return []
