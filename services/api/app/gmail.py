"""
Gmail client for fetching threads and extracting email content.

Uses single-user OAuth2 with refresh token. Configuration via environment variables:
- GMAIL_CLIENT_ID
- GMAIL_CLIENT_SECRET
- GMAIL_REFRESH_TOKEN
- GMAIL_USER (email address)

All variables must be set for Gmail integration to work. If missing, endpoints
gracefully fall back to using request body content.
"""

import os
import base64
from typing import Optional, Dict, List, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def is_configured() -> bool:
    """Check if all required Gmail environment variables are set."""
    required = [
        "GMAIL_CLIENT_ID",
        "GMAIL_CLIENT_SECRET", 
        "GMAIL_REFRESH_TOKEN",
        "GMAIL_USER"
    ]
    return all(os.getenv(var) for var in required)


def get_gmail_service():
    """
    Create Gmail API service with OAuth2 credentials.
    
    Raises:
        ValueError: If Gmail is not configured (missing env vars)
    """
    if not is_configured():
        raise ValueError("gmail_not_configured")
    
    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GMAIL_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GMAIL_CLIENT_ID"),
        client_secret=os.getenv("GMAIL_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/gmail.readonly"]
    )
    
    service = build("gmail", "v1", credentials=creds)
    return service, os.getenv("GMAIL_USER")


def decode_base64url(data: str) -> str:
    """Decode base64url-encoded string (Gmail format)."""
    # Gmail uses base64url: replace - with + and _ with /
    b64 = data.replace("-", "+").replace("_", "/")
    # Add padding if needed
    padding = len(b64) % 4
    if padding:
        b64 += "=" * (4 - padding)
    
    try:
        decoded = base64.b64decode(b64)
        return decoded.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def flatten_parts(part: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten nested MIME parts into a single list.
    
    Gmail messages can have nested multipart structures. This recursively
    extracts all parts for easier processing.
    """
    result = []
    stack = [part]
    
    while stack:
        current = stack.pop()
        result.append(current)
        
        if "parts" in current:
            for child in current.get("parts", []):
                stack.append(child)
    
    return result


def extract_headers(payload: Dict[str, Any]) -> Dict[str, str]:
    """Extract headers from Gmail message payload."""
    headers = {}
    for header in payload.get("headers", []):
        name = header.get("name", "")
        value = header.get("value", "")
        if name:
            headers[name] = value
    return headers


def extract_body(payload: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """
    Extract text and HTML body from Gmail message payload.
    
    Returns:
        tuple: (text_content, html_content)
        
    Prefers text/plain for text, falls back to text/html.
    Returns both if available.
    """
    parts = flatten_parts(payload)
    
    text_content = None
    html_content = None
    
    for part in parts:
        mime_type = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data", "")
        
        if not data:
            continue
        
        decoded = decode_base64url(data)
        
        if mime_type == "text/plain" and not text_content:
            text_content = decoded
        elif mime_type == "text/html" and not html_content:
            html_content = decoded
    
    return text_content, html_content


async def fetch_thread_latest(thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the latest message from a Gmail thread and extract content.
    
    Args:
        thread_id: Gmail thread ID
        
    Returns:
        dict with keys: subject, from, headers, text, html
        Returns None if thread not found or Gmail not configured
    """
    try:
        service, user = get_gmail_service()
        
        # Fetch thread with full message format
        thread = service.users().threads().get(
            userId=user,
            id=thread_id,
            format="full"
        ).execute()
        
        messages = thread.get("messages", [])
        if not messages:
            return None
        
        # Sort by internalDate (newest first)
        messages.sort(key=lambda m: int(m.get("internalDate", "0")), reverse=True)
        latest = messages[0]
        
        # Extract content from latest message
        payload = latest.get("payload", {})
        headers = extract_headers(payload)
        text, html = extract_body(payload)
        
        return {
            "subject": headers.get("Subject", headers.get("subject", "")),
            "from": headers.get("From", headers.get("from", "")),
            "headers": headers,
            "text": text or "",
            "html": html or ""
        }
        
    except HttpError as e:
        # Thread not found or permission denied
        print(f"Gmail API error fetching thread {thread_id}: {e}")
        return None
    except ValueError as e:
        # Gmail not configured
        if "gmail_not_configured" in str(e):
            return None
        raise
    except Exception as e:
        # Unexpected error - log but don't crash
        print(f"Unexpected error fetching Gmail thread {thread_id}: {e}")
        return None


def sync_fetch_thread_latest(thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Synchronous wrapper for fetch_thread_latest.
    
    FastAPI routes can be sync or async. This allows both patterns.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(fetch_thread_latest(thread_id))
