# Backend Thread Endpoint Implementation Guide

**Quick reference for implementing the `/api/threads/:threadId` endpoint**

## Endpoint Specification

```text
GET /api/threads/:threadId
```text

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 20 | Maximum number of messages to return |

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `threadId` | string | Gmail/Elasticsearch thread_id |

## Response Format

```json
{
  "messages": [
    {
      "id": "gmail_msg_id_001",
      "from": "sender@example.com",
      "from_addr": "sender@example.com",
      "date": "2025-10-11T10:30:00Z",
      "received_at": "2025-10-11T10:30:00Z",
      "snippet": "This is a preview of the message content...",
      "body_html": "<html><body><p>Full HTML content</p></body></html>",
      "body_text": "Plain text version of the email content"
    },
    {
      "id": "gmail_msg_id_002",
      "from": "reply@example.com",
      "from_addr": "reply@example.com",
      "date": "2025-10-11T14:45:00Z",
      "received_at": "2025-10-11T14:45:00Z",
      "snippet": "This is the reply message preview...",
      "body_html": "<html><body><p>Reply HTML content</p></body></html>",
      "body_text": "Plain text reply"
    }
  ]
}
```text

## Implementation Options

### Option 1: Elasticsearch Query (Recommended)

```python
from fastapi import APIRouter, Query
from app.services.es import es_client

router = APIRouter()

@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str, limit: int = Query(20, ge=1, le=100)):
    """
    Fetch all messages in a thread by thread_id
    """
    # Query Elasticsearch for all messages with this thread_id
    result = await es_client.search(
        index="emails",
        body={
            "query": {
                "term": {"thread_id.keyword": thread_id}
            },
            "sort": [{"received_at": "asc"}],  # Oldest first
            "size": limit,
            "_source": [
                "id", "from", "from_addr", "date", "received_at",
                "snippet", "body_html", "body_text"
            ]
        }
    )
    
    messages = [
        {
            "id": hit["_source"].get("id") or hit["_id"],
            "from": hit["_source"].get("from", ""),
            "from_addr": hit["_source"].get("from_addr", ""),
            "date": hit["_source"].get("date"),
            "received_at": hit["_source"].get("received_at"),
            "snippet": hit["_source"].get("snippet", ""),
            "body_html": hit["_source"].get("body_html"),
            "body_text": hit["_source"].get("body_text"),
        }
        for hit in result["hits"]["hits"]
    ]
    
    return {"messages": messages}
```text

### Option 2: Database Query (Alternative)

```python
from fastapi import APIRouter, Query
from sqlalchemy.orm import Session
from app.models.email import Email
from app.database import get_db

router = APIRouter()

@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str, 
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Fetch all messages in a thread from database
    """
    emails = db.query(Email)\
        .filter(Email.thread_id == thread_id)\
        .order_by(Email.received_at.asc())\
        .limit(limit)\
        .all()
    
    messages = [
        {
            "id": email.id,
            "from": email.from_addr,
            "from_addr": email.from_addr,
            "date": email.date.isoformat() if email.date else None,
            "received_at": email.received_at.isoformat() if email.received_at else None,
            "snippet": email.body_preview or email.subject[:100],
            "body_html": email.body_html,
            "body_text": email.body_text,
        }
        for email in emails
    ]
    
    return {"messages": messages}
```text

### Option 3: Gmail API (Real-time)

```python
from fastapi import APIRouter, Query
from app.services.gmail import gmail_service

router = APIRouter()

@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str, limit: int = Query(20, ge=1, le=100)):
    """
    Fetch thread directly from Gmail API
    """
    thread = gmail_service.users().threads().get(
        userId='me',
        id=thread_id,
        format='full'
    ).execute()
    
    messages = []
    for msg in thread['messages'][:limit]:
        payload = msg['payload']
        headers = {h['name']: h['value'] for h in payload.get('headers', [])}
        
        # Extract body
        body_html = None
        body_text = None
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    body_html = base64.urlsafe_b64decode(part['body']['data']).decode()
                elif part['mimeType'] == 'text/plain':
                    body_text = base64.urlsafe_b64decode(part['body']['data']).decode()
        
        messages.append({
            "id": msg['id'],
            "from": headers.get('From', ''),
            "from_addr": headers.get('From', ''),
            "date": headers.get('Date'),
            "received_at": headers.get('Date'),
            "snippet": msg.get('snippet', ''),
            "body_html": body_html,
            "body_text": body_text,
        })
    
    return {"messages": messages}
```text

## Error Handling

```python
from fastapi import HTTPException

@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str, limit: int = Query(20, ge=1, le=100)):
    try:
        # ... implementation ...
        
        if not messages:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        return {"messages": messages}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch thread: {str(e)}")
```text

## Performance Considerations

1. **Caching**: Cache thread results for 5-10 minutes

   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_cached_thread(thread_id: str):
       # ...
   ```

2. **Pagination**: Limit to 20 messages by default

   ```python
   limit: int = Query(20, ge=1, le=100)
   ```

3. **Field Selection**: Only return necessary fields

   ```python
   "_source": ["id", "from", "date", "snippet", "body_html", "body_text"]
   ```

4. **Async Operations**: Use async/await for I/O

   ```python
   async def get_thread(...):
       result = await es_client.search(...)
   ```

## Testing

### Test with curl

```bash
# Get thread with default limit
curl http://localhost:8000/api/threads/thread_abc123

# Get thread with custom limit
curl http://localhost:8000/api/threads/thread_abc123?limit=10

# Expected response
{
  "messages": [
    {
      "id": "msg_001",
      "from": "sender@example.com",
      "from_addr": "sender@example.com",
      "date": "2025-10-11T10:30:00Z",
      "received_at": "2025-10-11T10:30:00Z",
      "snippet": "Message preview...",
      "body_html": "<p>HTML content</p>",
      "body_text": "Plain text"
    }
  ]
}
```text

### Test with Python

```python
import requests

response = requests.get("http://localhost:8000/api/threads/thread_abc123")
print(response.json())
```text

## Integration Points

### 1. Update Email Model

Ensure the Email model includes `thread_id`:

```python
class Email(Base):
    __tablename__ = "emails"
    
    id = Column(String, primary_key=True)
    thread_id = Column(String, index=True)  # <-- Add index for performance
    from_addr = Column(String)
    # ... other fields
```text

### 2. Add to Router

```python
# app/routers/__init__.py
from .threads import router as threads_router

app.include_router(threads_router, prefix="/api")
```text

### 3. Update Elasticsearch Index

Ensure `thread_id` is indexed:

```json
{
  "mappings": {
    "properties": {
      "thread_id": {
        "type": "keyword"
      }
    }
  }
}
```text

## Migration Path

If you don't have thread data yet:

1. **Phase 1**: Return empty array

   ```python
   return {"messages": []}
   ```

2. **Phase 2**: Populate thread_id from Gmail

   ```python
   # Backfill script
   for email in emails:
       email.thread_id = fetch_from_gmail(email.gmail_id)
   ```

3. **Phase 3**: Enable full thread support

   ```python
   # Use actual thread_id from database
   ```

## Expected Frontend Behavior

The frontend will:

1. Call `getThread(threadId)` when opening an email
2. Display all messages in chronological order
3. Allow user to navigate between messages
4. Update the current view instantly (no additional API calls)

## Quick Start

1. Copy one of the implementation options above
2. Create `app/routers/threads.py`
3. Add the router to your FastAPI app
4. Test with curl/Postman
5. Verify response format matches spec

---

**Priority**: Medium  
**Estimated Effort**: 2-4 hours  
**Dependencies**: Elasticsearch/Database with thread_id field  
**Testing**: Frontend integration test available
