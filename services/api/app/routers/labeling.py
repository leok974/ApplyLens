"""
API endpoints for ML-based email labeling and categorization.

Provides:
- POST /ml/label/rebuild - Reprocess emails with ML model + rules
- GET /ml/label/preview - Preview emails by category
- POST /ml/label/email - Label a single email
- GET /ml/stats - Get labeling statistics
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime
from typing import Optional
import logging
import os

from app.db import get_db
from app.models import Email
from app.ml.predict_label import score_email
from app.ml.rules import extract_extras
from dateutil import parser as date_parser


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml", tags=["ml"])

# Elasticsearch configuration
try:
    from elasticsearch import Elasticsearch
    ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200")
    ES_INDEX = os.getenv("ELASTICSEARCH_INDEX", "gmail_emails")  # Use same index as search
    ES_ENABLED = True
except ImportError:
    ES_ENABLED = False
    logging.warning("Elasticsearch not available - labels will only update PostgreSQL")


def get_es_client():
    """Get Elasticsearch client if available."""
    if not ES_ENABLED:
        return None
    try:
        return Elasticsearch(ES_URL)
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")
        return None


@router.post("/label/rebuild")
def label_rebuild(
    limit: int = 2000,
    user_email: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Rebuild labels for recent emails using ML model + rules.
    
    Args:
        limit: Max number of emails to process (default 2000)
        user_email: Optional - only process emails for this user
        
    Returns:
        Dict with updated count and category breakdown
    """
    logger.info(f"Starting label rebuild: limit={limit}, user_email={user_email}")
    
    # Build query
    query = db.query(Email).order_by(Email.received_at.desc()).limit(limit)
    if user_email:
        query = query.filter(Email.recipient == user_email)
    
    emails = query.all()
    
    if not emails:
        return {"updated": 0, "message": "No emails found"}
    
    logger.info(f"Processing {len(emails)} emails...")
    
    updated = 0
    category_counts = {}
    errors = []
    
    for email_row in emails:
        try:
            # Prepare payload for scoring
            headers_dict = {}
            if email_row.raw and isinstance(email_row.raw, dict):
                headers_list = email_row.raw.get("payload", {}).get("headers", [])
                if isinstance(headers_list, list):
                    headers_dict = {
                        h.get("name", ""): h.get("value", "")
                        for h in headers_list
                    }
            
            payload = {
                "headers": headers_dict,
                "sender_domain": (email_row.sender or "").split("@")[-1],
                "body_text": email_row.body_text or "",
                "subject": email_row.subject or "",
            }
            
            # Score with ML model
            category, scores, features = score_email(payload)
            
            # Extract structured data
            amount_cents, expires_at, event_start_at = extract_extras(payload)
            
            # Update email record
            email_row.category = category
            email_row.ml_scores = scores
            email_row.ml_features = features
            email_row.amount_cents = amount_cents
            email_row.expires_at = expires_at
            email_row.event_start_at = event_start_at
            
            # Track stats
            category_counts[category] = category_counts.get(category, 0) + 1
            updated += 1
            
            # Commit in batches
            if updated % 100 == 0:
                db.commit()
                logger.info(f"Progress: {updated}/{len(emails)} emails processed")
        
        except Exception as e:
            logger.error(f"Error processing email {email_row.id}: {e}")
            errors.append({"email_id": email_row.id, "error": str(e)})
    
    # Final commit
    db.commit()
    
    logger.info(f"Label rebuild complete: {updated} emails updated")
    logger.info(f"Category breakdown: {category_counts}")
    
    # Sync to Elasticsearch (if available)
    es_synced = 0
    if ES_ENABLED:
        try:
            es_client = get_es_client()
            if es_client:
                bulk_body = []
                
                for email_row in emails:
                    if hasattr(email_row, 'category') and email_row.gmail_id:
                        # Add update action with upsert
                        bulk_body.append({"update": {"_index": ES_INDEX, "_id": email_row.gmail_id}})
                        
                        # Add document with ML fields
                        doc = {
                            "category": email_row.category,
                            "amount_cents": email_row.amount_cents,
                            "ml_scores": email_row.ml_scores,
                            "ml_features": email_row.ml_features,
                        }
                        
                        # Add datetime fields (convert to ISO format) - only if they exist
                        if hasattr(email_row, 'expires_at') and email_row.expires_at:
                            doc["expires_at"] = email_row.expires_at.isoformat()
                        if hasattr(email_row, 'event_start_at') and email_row.event_start_at:
                            doc["event_start_at"] = email_row.event_start_at.isoformat()
                        if hasattr(email_row, 'event_location') and email_row.event_location:
                            doc["event_location"] = email_row.event_location
                        
                        # Use doc_as_upsert=True to handle missing documents
                        bulk_body.append({"doc": doc, "doc_as_upsert": True})
                
                if bulk_body:
                    response = es_client.bulk(body=bulk_body, refresh=True)
                    es_synced = len(bulk_body) // 2
                    
                    if response.get("errors"):
                        # Log detailed error information
                        for item in response.get("items", []):
                            if "error" in item.get("update", {}):
                                error_detail = item["update"]["error"]
                                logger.error(f"ES update failed: {error_detail}")
                        logger.warning(f"ES bulk update had errors (processed {es_synced} docs)")
                    else:
                        logger.info(f"✅ Synced {es_synced} emails to Elasticsearch")
        except Exception as e:
            logger.error(f"Failed to sync to Elasticsearch: {e}")
    
    return {
        "updated": updated,
        "categories": category_counts,
        "es_synced": es_synced,
        "errors": errors[:10] if errors else None  # Return first 10 errors
    }


@router.get("/label/preview")
def label_preview(
    category: str,
    limit: int = 20,
    user_email: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Preview emails by category.
    
    Args:
        category: Category to preview (promotions, ats, bills, banks, events, other)
        limit: Max number of results (default 20)
        user_email: Optional - filter by user
        
    Returns:
        List of email objects
    """
    query = (
        db.query(Email)
        .filter(Email.category == category)
        .order_by(desc(Email.received_at))
        .limit(limit)
    )
    
    if user_email:
        query = query.filter(Email.recipient == user_email)
    
    emails = query.all()
    
    return [
        {
            "id": e.id,
            "gmail_id": e.gmail_id,
            "subject": e.subject,
            "sender": e.sender,
            "received_at": e.received_at.isoformat() if e.received_at else None,
            "category": e.category,
            "ml_scores": e.ml_scores,
            "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            "event_start_at": e.event_start_at.isoformat() if e.event_start_at else None,
            "amount_cents": e.amount_cents,
        }
        for e in emails
    ]


@router.post("/label/email/{email_id}")
def label_single_email(email_id: int, db: Session = Depends(get_db)):
    """
    Label a single email by ID.
    
    Args:
        email_id: Database ID of email
        
    Returns:
        Updated email with category and scores
    """
    email_row = db.query(Email).filter(Email.id == email_id).first()
    
    if not email_row:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Prepare payload
    headers_dict = {}
    if email_row.raw and isinstance(email_row.raw, dict):
        headers_list = email_row.raw.get("payload", {}).get("headers", [])
        if isinstance(headers_list, list):
            headers_dict = {
                h.get("name", ""): h.get("value", "")
                for h in headers_list
            }
    
    payload = {
        "headers": headers_dict,
        "sender_domain": (email_row.sender or "").split("@")[-1],
        "body_text": email_row.body_text or "",
        "subject": email_row.subject or "",
    }
    
    # Score and update
    category, scores, features = score_email(payload)
    amount_cents, expires_at, event_start_at = extract_extras(payload)
    
    email_row.category = category
    email_row.ml_scores = scores
    email_row.ml_features = features
    email_row.amount_cents = amount_cents
    email_row.expires_at = expires_at
    email_row.event_start_at = event_start_at
    
    db.commit()
    
    return {
        "id": email_row.id,
        "category": category,
        "ml_scores": scores,
        "ml_features": features,
        "amount_cents": amount_cents,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "event_start_at": event_start_at.isoformat() if event_start_at else None,
    }


@router.get("/stats")
def get_labeling_stats(user_email: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get labeling statistics.
    
    Args:
        user_email: Optional - filter by user
        
    Returns:
        Dict with category counts and coverage
    """
    query = db.query(
        Email.category,
        func.count(Email.id).label("count")
    ).group_by(Email.category)
    
    if user_email:
        query = query.filter(Email.recipient == user_email)
    
    results = query.all()
    
    total = sum(r.count for r in results)
    labeled = sum(r.count for r in results if r.category)
    
    return {
        "total_emails": total,
        "labeled_emails": labeled,
        "coverage": round(labeled / total * 100, 2) if total > 0 else 0,
        "categories": {r.category or "unlabeled": r.count for r in results},
    }
