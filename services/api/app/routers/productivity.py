"""
Productivity tools for email-based reminders and tasks.

Creates calendar events and task reminders from email content.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import datetime as dt

router = APIRouter(prefix="/productivity", tags=["productivity"])


class Reminder(BaseModel):
    """Single reminder/task to create."""
    email_id: str
    title: str
    due_at: Optional[str] = None  # ISO 8601 string
    source: Optional[str] = "mailbox"
    notes: Optional[str] = None


class CreateRemindersRequest(BaseModel):
    """Batch create reminders request."""
    items: List[Reminder] = Field(default_factory=list)


@router.post("/reminders/create")
def create_reminders(req: CreateRemindersRequest):
    """
    Create reminders/tasks from email content.
    
    For MVP: stores to actions_audit_v1 audit trail.
    Future: integrate with Google Calendar/Tasks API.
    
    Args:
        req: List of reminders to create
        
    Returns:
        Count of reminders created
        
    Raises:
        HTTPException: If no reminders provided
        
    Example:
        POST /productivity/reminders/create
        {
          "items": [
            {
              "email_id": "bill_123",
              "title": "Pay electric bill",
              "due_at": "2025-10-15T17:00:00Z",
              "notes": "Due on 15th"
            }
          ]
        }
        
        Response:
        {
          "created": 1
        }
    """
    if not req.items:
        raise HTTPException(400, "No reminders provided")
    
    # Store to audit trail (future: integrate with calendar APIs)
    from app.logic.audit_es import emit_audit
    
    now = dt.datetime.utcnow().isoformat() + "Z"
    
    for r in req.items:
        emit_audit({
            "email_id": r.email_id,
            "action": "create_reminder",
            "actor": "agent",
            "policy_id": "calendar-reminder",
            "confidence": 0.95,
            "rationale": r.notes or "bill/event reminder",
            "status": "executed",
            "created_at": now,
            "payload": r.dict()
        })
    
    return {"created": len(req.items)}


class CalendarEvent(BaseModel):
    """Calendar event to create from email."""
    email_id: str
    title: str
    start_time: str  # ISO 8601
    end_time: Optional[str] = None  # ISO 8601
    location: Optional[str] = None
    description: Optional[str] = None
    attendees: Optional[List[str]] = None


class CreateEventsRequest(BaseModel):
    """Batch create calendar events request."""
    items: List[CalendarEvent] = Field(default_factory=list)


@router.post("/calendar/create")
def create_calendar_events(req: CreateEventsRequest):
    """
    Create calendar events from email content.
    
    For MVP: stores to actions_audit_v1 audit trail.
    Future: integrate with Google Calendar API.
    
    Args:
        req: List of calendar events to create
        
    Returns:
        Count of events created
        
    Raises:
        HTTPException: If no events provided
        
    Example:
        POST /productivity/calendar/create
        {
          "items": [
            {
              "email_id": "invite_456",
              "title": "Team Meeting",
              "start_time": "2025-10-12T14:00:00Z",
              "end_time": "2025-10-12T15:00:00Z",
              "location": "Conference Room A",
              "attendees": ["alice@example.com", "bob@example.com"]
            }
          ]
        }
        
        Response:
        {
          "created": 1
        }
    """
    if not req.items:
        raise HTTPException(400, "No events provided")
    
    from app.logic.audit_es import emit_audit
    
    now = dt.datetime.utcnow().isoformat() + "Z"
    
    for event in req.items:
        emit_audit({
            "email_id": event.email_id,
            "action": "create_calendar_event",
            "actor": "agent",
            "policy_id": "calendar-event",
            "confidence": 0.95,
            "rationale": f"Calendar event: {event.title}",
            "status": "executed",
            "created_at": now,
            "payload": event.dict()
        })
    
    return {"created": len(req.items)}


@router.get("/reminders/list")
def list_reminders(limit: int = 50):
    """
    List recent reminders created.
    
    Queries the audit trail for reminder creation events.
    
    Args:
        limit: Maximum number of reminders to return
        
    Returns:
        List of reminders with metadata
        
    Example:
        GET /productivity/reminders/list?limit=10
        
        Response:
        {
          "items": [
            {
              "email_id": "bill_123",
              "title": "Pay electric bill",
              "due_at": "2025-10-15T17:00:00Z",
              "created_at": "2025-10-10T12:00:00Z"
            }
          ],
          "total": 1
        }
    """
    from app.logic.search import es_client
    
    try:
        es = es_client()
        
        result = es.search(
            index="actions_audit_v1",
            body={
                "query": {
                    "term": {"action": "create_reminder"}
                },
                "sort": [{"created_at": "desc"}],
                "size": limit
            }
        )
        
        items = []
        for hit in result["hits"]["hits"]:
            payload = hit["_source"].get("payload", {})
            items.append({
                "email_id": payload.get("email_id"),
                "title": payload.get("title"),
                "due_at": payload.get("due_at"),
                "notes": payload.get("notes"),
                "created_at": hit["_source"].get("created_at")
            })
        
        return {
            "items": items,
            "total": result["hits"]["total"]["value"]
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch reminders: {e}")
