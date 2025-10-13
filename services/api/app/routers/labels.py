"""FastAPI router for applying category labels to emails.

This router provides endpoints for:
1. Applying labels to emails using rules + ML fallback
2. Batch processing large email collections
3. Updating Elasticsearch with enriched metadata

The labeling process:
    1. Try high-precision rules first (rules.py)
    2. If no rule matches, use ML model (if available)
    3. Extract additional features (URL count, money mentions, etc.)
    4. Write category, confidence, reason, and features back to ES
"""

from fastapi import APIRouter, Body, HTTPException
import httpx
import os
import joblib
from typing import AsyncIterator

from ..labeling.rules import rule_labels

router = APIRouter(prefix="/labels", tags=["labels"])

# Elasticsearch configuration
ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200")
INDEX = os.getenv("ES_EMAIL_INDEX", "emails_v1-000001")

# Model configuration
MODEL_PATH = os.getenv("LABEL_MODEL_PATH", "services/api/app/labeling/label_model.joblib")

# Cache for ML model
_model_cache = None


def get_model():
    """Load ML model from disk (cached).
    
    Returns:
        Trained scikit-learn pipeline or None if model not found
    """
    global _model_cache
    
    if _model_cache is None:
        if os.path.exists(MODEL_PATH):
            try:
                _model_cache = joblib.load(MODEL_PATH)
                print(f"✅ Loaded ML model from {MODEL_PATH}")
            except Exception as e:
                print(f"⚠️  Failed to load model: {e}")
                _model_cache = None
        else:
            print(f"⚠️  Model not found at {MODEL_PATH}")
            _model_cache = None
    
    return _model_cache


async def _iter_docs(
    client: httpx.AsyncClient,
    query: dict,
    batch_size: int = 200,
) -> AsyncIterator[dict]:
    """Iterate over all documents matching query using scroll API.
    
    Args:
        client: HTTP client for Elasticsearch requests
        query: Elasticsearch query dict
        batch_size: Number of documents per scroll batch
        
    Yields:
        Document dicts with _id, _source, etc.
    """
    # Initial search with scroll
    search_body = {
        "query": query,
        "size": batch_size,
        "sort": [{"received_at": {"order": "desc"}}],
    }
    
    response = await client.post(
        f"{ES_URL}/{INDEX}/_search?scroll=2m",
        json=search_body,
    )
    response.raise_for_status()
    
    data = response.json()
    scroll_id = data.get("_scroll_id")
    hits = data["hits"]["hits"]
    
    # Yield initial batch
    for hit in hits:
        yield hit
    
    # Continue scrolling
    while hits:
        response = await client.post(
            f"{ES_URL}/_search/scroll",
            json={"scroll": "2m", "scroll_id": scroll_id},
        )
        response.raise_for_status()
        
        data = response.json()
        hits = data["hits"]["hits"]
        
        for hit in hits:
            yield hit


def build_features(doc: dict) -> dict:
    """Extract features from email document for ML model.
    
    Args:
        doc: Email document from Elasticsearch _source
        
    Returns:
        Feature dict with text and numeric features
    """
    # Combine subject and body
    text = f"{doc.get('subject', '')} \n {doc.get('body_text', '')}"
    
    # Count URLs
    urls = doc.get("urls") or []
    url_count = len(urls)
    
    # Detect money mentions
    money_hits = 1 if ("$" in text or "€" in text or "£" in text) else 0
    
    # Detect due date mentions
    due_date_hit = 1 if "due" in text.lower() else 0
    
    # Sender term frequency (placeholder - could compute from corpus)
    sender_tf = 1
    
    return {
        "text": text,
        "url_count": url_count,
        "money_hits": money_hits,
        "due_date_hit": due_date_hit,
        "sender_tf": sender_tf,
    }


@router.post("/apply")
async def apply_labels(
    query: dict = Body(default={"match_all": {}}),
    batch_size: int = 200,
) -> dict:
    """Apply category labels to all emails matching query.
    
    Process:
        1. Scroll through all matching documents
        2. Apply rule-based labels (high precision)
        3. Fall back to ML model if no rule matches
        4. Write category, confidence, reason, and features to ES
        
    Args:
        query: Elasticsearch query (default: match all)
        batch_size: Documents per scroll batch (default: 200)
        
    Returns:
        Dict with:
            - updated: Number of documents updated
            - by_category: Breakdown by category
            - by_method: Breakdown by labeling method (rule vs ML)
            
    Example:
        POST /labels/apply
        {
            "query": {"range": {"received_at": {"gte": "now-7d"}}},
            "batch_size": 100
        }
        
        Response:
        {
            "updated": 1234,
            "by_category": {"promo": 456, "newsletter": 321, ...},
            "by_method": {"rule": 890, "ml": 344}
        }
    """
    model = get_model()
    
    # Tracking stats
    updated = 0
    category_counts = {}
    method_counts = {"rule": 0, "ml": 0, "default": 0}
    
    async with httpx.AsyncClient(timeout=30) as client:
        async for hit in _iter_docs(client, query, batch_size):
            doc = hit["_source"]
            doc_id = hit["_id"]
            
            # Try rule-based labeling first
            category, reason = rule_labels(doc)
            confidence = 0.95 if category else 0.0
            method = "rule" if category else None
            
            # Fall back to ML model if no rule matched
            if not category and model:
                try:
                    features = build_features(doc)
                    prediction = model.predict([features])[0]
                    probabilities = model.predict_proba([features])[0]
                    max_prob = float(max(probabilities))
                    
                    category = prediction
                    confidence = max_prob
                    reason = f"ML prediction ({prediction})"
                    method = "ml"
                except Exception as e:
                    print(f"⚠️  ML prediction failed for {doc_id}: {e}")
                    category = None
            
            # Default fallback
            if not category:
                category = "other"
                reason = "No rule or ML match"
                confidence = 0.01
                method = "default"
            
            # Build feature dict for storage
            feature_dict = {
                "url_count": len(doc.get("urls") or []),
                "money_hits": 1 if ("$" in (doc.get("subject", "") + doc.get("body_text", ""))) else 0,
                "due_date_hit": 1 if "due" in (doc.get("subject", "") + doc.get("body_text", "")).lower() else 0,
            }
            
            # Update document in Elasticsearch
            patch = {
                "doc": {
                    "category": category,
                    "confidence": confidence,
                    "reason": reason,
                    "features": feature_dict,
                }
            }
            
            try:
                response = await client.post(
                    f"{ES_URL}/{INDEX}/_update/{doc_id}",
                    json=patch,
                )
                response.raise_for_status()
                
                # Update stats
                updated += 1
                category_counts[category] = category_counts.get(category, 0) + 1
                method_counts[method] = method_counts.get(method, 0) + 1
                
                # Log progress every 100 docs
                if updated % 100 == 0:
                    print(f"   Processed {updated} documents...")
                    
            except Exception as e:
                print(f"⚠️  Failed to update {doc_id}: {e}")
                continue
    
    return {
        "updated": updated,
        "by_category": category_counts,
        "by_method": method_counts,
    }


@router.post("/apply-batch")
async def apply_labels_batch(
    doc_ids: list[str] = Body(..., description="List of document IDs to label"),
) -> dict:
    """Apply labels to a specific batch of documents by ID.
    
    Useful for re-labeling specific emails or handling updates.
    
    Args:
        doc_ids: List of Elasticsearch document IDs
        
    Returns:
        Dict with updated count and category breakdown
        
    Example:
        POST /labels/apply-batch
        {
            "doc_ids": ["abc123", "def456", "ghi789"]
        }
    """
    if not doc_ids:
        raise HTTPException(status_code=400, detail="doc_ids cannot be empty")
    
    model = get_model()
    updated = 0
    category_counts = {}
    
    async with httpx.AsyncClient(timeout=30) as client:
        for doc_id in doc_ids:
            try:
                # Fetch document
                response = await client.get(f"{ES_URL}/{INDEX}/_doc/{doc_id}")
                response.raise_for_status()
                doc = response.json()["_source"]
                
                # Apply labeling logic
                category, reason = rule_labels(doc)
                confidence = 0.95 if category else 0.0
                
                if not category and model:
                    features = build_features(doc)
                    prediction = model.predict([features])[0]
                    max_prob = float(max(model.predict_proba([features])[0]))
                    category = prediction
                    confidence = max_prob
                    reason = f"ML prediction ({prediction})"
                
                if not category:
                    category = "other"
                    reason = "No rule or ML match"
                    confidence = 0.01
                
                # Build features
                feature_dict = {
                    "url_count": len(doc.get("urls") or []),
                    "money_hits": 1 if "$" in (doc.get("subject", "") + doc.get("body_text", "")) else 0,
                    "due_date_hit": 1 if "due" in (doc.get("subject", "") + doc.get("body_text", "")).lower() else 0,
                }
                
                # Update document
                patch = {
                    "doc": {
                        "category": category,
                        "confidence": confidence,
                        "reason": reason,
                        "features": feature_dict,
                    }
                }
                
                response = await client.post(
                    f"{ES_URL}/{INDEX}/_update/{doc_id}",
                    json=patch,
                )
                response.raise_for_status()
                
                updated += 1
                category_counts[category] = category_counts.get(category, 0) + 1
                
            except Exception as e:
                print(f"⚠️  Failed to process {doc_id}: {e}")
                continue
    
    return {
        "updated": updated,
        "by_category": category_counts,
    }


@router.get("/stats")
async def label_stats() -> dict:
    """Get statistics about labeled emails.
    
    Returns breakdown by category, confidence distribution, etc.
    
    Returns:
        Dict with:
            - total: Total documents
            - by_category: Count by category
            - avg_confidence: Average confidence score
            - low_confidence: Count with confidence < 0.5
    """
    body = {
        "size": 0,
        "aggs": {
            "by_category": {
                "terms": {"field": "category", "size": 20}
            },
            "avg_confidence": {
                "avg": {"field": "confidence"}
            },
            "low_confidence": {
                "filter": {"range": {"confidence": {"lt": 0.5}}}
            }
        }
    }
    
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{ES_URL}/{INDEX}/_search", json=body)
        response.raise_for_status()
        
        data = response.json()
        aggs = data["aggregations"]
        
        return {
            "total": data["hits"]["total"]["value"],
            "by_category": [
                {"category": b["key"], "count": b["doc_count"]}
                for b in aggs["by_category"]["buckets"]
            ],
            "avg_confidence": aggs["avg_confidence"]["value"],
            "low_confidence_count": aggs["low_confidence"]["doc_count"],
        }
