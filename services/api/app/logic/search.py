# ES-backed implementations for mailbox queries.
import os
import datetime as dt
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch

ES_INDEX = os.getenv("ES_EMAIL_INDEX", "emails_v1")


def es_client() -> Elasticsearch:
    """Create Elasticsearch client with optional API key authentication."""
    url = os.getenv("ES_URL", "http://localhost:9200")
    api_key = os.getenv("ES_API_KEY")  # optional
    if api_key:
        return Elasticsearch(url, api_key=api_key)
    return Elasticsearch(url)


def _hit_to_email(hit: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize ES hit to email dict format."""
    src = hit.get("_source", {})
    # normalize minimal fields we rely on elsewhere
    return {
        "id": src.get("id") or hit.get("_id"),
        "category": src.get("category"),
        "expires_at": src.get("expires_at"),
        "received_at": src.get("received_at"),
        "risk_score": src.get("risk_score"),
        "has_unsubscribe": src.get("has_unsubscribe"),
        "sender_domain": src.get("sender_domain"),
        "subject": src.get("subject"),
        "body_text": src.get("body_text"),
    }


async def find_expired_promos(days: int = 7, limit: int = 200) -> List[Dict[str, Any]]:
    """
    Promotions that already expired; restricted to items received within N days to keep it relevant.
    
    Args:
        days: Look back this many days for expired promos
        limit: Maximum number of results to return
        
    Returns:
        List of email dictionaries with at least: id, category, expires_at, received_at
    """
    now = dt.datetime.utcnow()
    since = (now - dt.timedelta(days=days)).isoformat() + "Z"
    client = es_client()
    body = {
        "size": limit,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"category": "promotions"}},
                    {"range": {"expires_at": {"lt": "now"}}},
                    {"range": {"received_at": {"gte": since}}},
                ]
            }
        },
        "_source": [
            "id",
            "category",
            "expires_at",
            "received_at",
            "subject",
            "has_unsubscribe",
            "sender_domain",
        ],
    }
    res = client.search(index=ES_INDEX, body=body)
    return [_hit_to_email(h) for h in res["hits"]["hits"]]


async def find_high_risk(limit: int = 50, min_risk: float = 80.0) -> List[Dict[str, Any]]:
    """
    Find emails with high risk scores (potential phishing/spam).
    
    Args:
        limit: Maximum number of results to return
        min_risk: Minimum risk score threshold (default 80.0)
        
    Returns:
        List of email dictionaries with at least: id, risk_score, category, sender_domain
    """
    client = es_client()
    body = {
        "size": limit,
        "query": {"range": {"risk_score": {"gte": min_risk}}},
        "sort": [{"risk_score": "desc"}, {"received_at": "desc"}],
        "_source": [
            "id",
            "risk_score",
            "category",
            "sender_domain",
            "subject",
            "received_at",
        ],
    }
    res = client.search(index=ES_INDEX, body=body)
    return [_hit_to_email(h) for h in res["hits"]["hits"]]


async def find_unsubscribe_candidates(
    days: int = 60, limit: int = 200
) -> List[Dict[str, Any]]:
    """
    Simple heuristic: newsletters (has_unsubscribe) older than N days (implies low recency/interest).
    If you track opens, refine with open_rate==0 or unopened_count>=K.
    
    Args:
        days: Look for emails older than this many days
        limit: Maximum number of results to return
        
    Returns:
        List of email dictionaries with at least: id, has_unsubscribe, sender_domain, received_at
    """
    before = (dt.datetime.utcnow() - dt.timedelta(days=days)).isoformat() + "Z"
    client = es_client()
    body = {
        "size": limit,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"has_unsubscribe": True}},
                    {"range": {"received_at": {"lte": before}}},
                ]
            }
        },
        "aggs": {  # de-dup by sender to propose one action per list/sender if you like
            "by_sender": {"terms": {"field": "sender_domain", "size": 200}}
        },
        "_source": [
            "id",
            "has_unsubscribe",
            "sender_domain",
            "subject",
            "received_at",
        ],
    }
    res = client.search(index=ES_INDEX, body=body)
    return [_hit_to_email(h) for h in res["hits"]["hits"]]


async def find_by_filter(
    filter_query: Dict[str, Any],
    limit: int = 500,
    fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Generic finder used by policy execution route. Pass a valid Elasticsearch bool/range/term query.
    
    Args:
        filter_query: Valid ES DSL query (e.g., {"bool":{"filter":[...]}})
        limit: Maximum number of results
        fields: Fields to return (None = default set)
        
    Returns:
        List of email dictionaries
    """
    client = es_client()
    body = {
        "size": limit,
        "query": filter_query,
        "_source": fields
        or [
            "id",
            "category",
            "expires_at",
            "received_at",
            "risk_score",
            "has_unsubscribe",
            "sender_domain",
            "subject",
        ],
    }
    res = client.search(index=ES_INDEX, body=body)
    return [_hit_to_email(h) for h in res["hits"]["hits"]]


async def search_emails(
    category: str = None,
    sender_domain: str = None,
    min_risk: float = None,
    has_unsubscribe: bool = None,
    received_after: str = None,
    received_before: str = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    General-purpose email search with multiple filters.
    
    Args:
        category: Filter by email category
        sender_domain: Filter by sender domain
        min_risk: Minimum risk score
        has_unsubscribe: Filter by unsubscribe header presence
        received_after: ISO datetime string
        received_before: ISO datetime string
        limit: Maximum results
        
    Returns:
        List of email dictionaries
    """
    filters = []
    if category:
        filters.append({"term": {"category": category}})
    if sender_domain:
        filters.append({"term": {"sender_domain": sender_domain}})
    if min_risk is not None:
        filters.append({"range": {"risk_score": {"gte": min_risk}}})
    if has_unsubscribe is not None:
        filters.append({"term": {"has_unsubscribe": has_unsubscribe}})
    if received_after:
        filters.append({"range": {"received_at": {"gte": received_after}}})
    if received_before:
        filters.append({"range": {"received_at": {"lte": received_before}}})

    query = {"bool": {"filter": filters}} if filters else {"match_all": {}}
    return await find_by_filter(query, limit=limit)
