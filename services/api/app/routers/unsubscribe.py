"""
Unsubscribe Router

Provides endpoints for previewing and executing email unsubscribe operations
using RFC-2369 List-Unsubscribe headers.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
from app.logic.unsubscribe import perform_unsubscribe
from app.db import audit_action

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])


class UnsubRequest(BaseModel):
    """Request model for unsubscribe operations."""
    email_id: str
    headers: Dict[str, str]


@router.post("/preview")
def preview_unsubscribe(req: UnsubRequest):
    """
    Preview an unsubscribe operation without executing it.
    
    Parses List-Unsubscribe headers and shows what action would be taken,
    but does not actually perform any network operations.
    
    Args:
        req: UnsubRequest with email_id and headers
        
    Returns:
        Dictionary with email_id and result showing available targets
        
    Example:
        POST /unsubscribe/preview
        {
            "email_id": "msg123",
            "headers": {
                "List-Unsubscribe": "<mailto:unsub@example.com>, <https://example.com/unsub?id=123>"
            }
        }
        
        Response:
        {
            "email_id": "msg123",
            "result": {
                "mailto": "unsub@example.com",
                "http": "https://example.com/unsub?id=123",
                "performed": null,
                "status": null
            }
        }
    """
    # Parse headers but don't execute
    from app.logic.unsubscribe import parse_list_unsubscribe
    mailto, http = parse_list_unsubscribe(req.headers)
    
    res = {
        "mailto": mailto,
        "http": http,
        "performed": None,  # Never perform in preview mode
        "status": None
    }
    
    return {"email_id": req.email_id, "result": res}


@router.post("/execute")
def execute_unsubscribe(req: UnsubRequest):
    """
    Execute an unsubscribe operation.
    
    Parses List-Unsubscribe headers and performs the unsubscribe action.
    Prefers HTTP unsubscribe (immediate), falls back to mailto (queued).
    All operations are logged to the audit trail.
    
    Args:
        req: UnsubRequest with email_id and headers
        
    Returns:
        Dictionary with email_id and result showing what was performed
        
    Raises:
        HTTPException(400): If no List-Unsubscribe targets are found
        
    Example:
        POST /unsubscribe/execute
        {
            "email_id": "msg123",
            "headers": {
                "List-Unsubscribe": "<https://example.com/unsub?id=123>"
            }
        }
        
        Response:
        {
            "email_id": "msg123",
            "result": {
                "mailto": null,
                "http": "https://example.com/unsub?id=123",
                "performed": "http",
                "status": 200
            }
        }
    """
    # Execute unsubscribe operation
    res = perform_unsubscribe(req.headers)
    
    # Validate that we found unsubscribe targets
    if not res.get("mailto") and not res.get("http"):
        raise HTTPException(400, "No List-Unsubscribe targets found")
    
    # Audit the action
    audit_action(
        email_id=req.email_id,
        action="unsubscribe",
        payload=res,
        policy_id="unsubscribe-exec",
        confidence=0.95,
        rationale="List-Unsubscribe header"
    )
    
    return {"email_id": req.email_id, "result": res}
