"""
Gmail client with provider pattern for single-user, multi-user, and mock modes.

Supports:
- Single-user OAuth (env variables)
- Multi-user OAuth (DB-backed tokens)
- Mock provider (for testing)
- Optional PDF text extraction from attachments
"""

from __future__ import annotations
import base64
import io
import re
from typing import Optional, Dict, Any, List, Protocol, Callable, Awaitable
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from .settings import settings

# Type alias for extractable email content
Extractable = Dict[str, Any]


class GmailProvider(Protocol):
    """Protocol for Gmail providers (single-user, multi-user, mock)."""

    async def fetch_thread_latest(
        self, thread_id: str, user_email: Optional[str] = None
    ) -> Optional[Extractable]:
        """Fetch latest message from thread, return extractable dict or None."""
        ...


def _decode_body(data_b64url: str) -> str:
    """Decode Gmail's base64url-encoded body data."""
    if not data_b64url:
        return ""

    # Convert base64url to standard base64
    b64 = data_b64url.replace("-", "+").replace("_", "/")

    # Add padding if needed
    padding = len(b64) % 4
    if padding:
        b64 += "=" * (4 - padding)

    try:
        decoded = base64.b64decode(b64)
        return decoded.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _flatten_parts(part: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Flatten nested MIME multipart structure into single list.

    Gmail messages can have deeply nested parts. This recursively
    extracts all parts for easier processing.
    """
    if not part:
        return []

    stack = [part]
    out: List[Dict[str, Any]] = []

    while stack:
        current = stack.pop()
        out.append(current)

        # Add child parts to stack
        for child in current.get("parts", []):
            stack.append(child)

    return out


def _parts_to_extractable(msg: Dict[str, Any]) -> Extractable:
    """
    Convert Gmail message to extractable format.

    Returns dict with: subject, from, headers, text, html, attachments
    """
    payload = msg.get("payload") or {}
    headers_list = payload.get("headers") or []

    # Build headers dict
    headers = {}
    for h in headers_list:
        if "name" in h:
            headers[h["name"]] = h.get("value", "")

    # Extract common headers
    subject = headers.get("Subject") or headers.get("subject")
    from_ = headers.get("From") or headers.get("from")

    # Flatten MIME parts
    parts = _flatten_parts(payload)

    # Find text/plain and text/html parts
    text_part = next((p for p in parts if p.get("mimeType") == "text/plain"), None)
    html_part = next((p for p in parts if p.get("mimeType") == "text/html"), None)

    text = None
    html = None

    if text_part and text_part.get("body", {}).get("data"):
        text = _decode_body(text_part["body"]["data"])

    if html_part and html_part.get("body", {}).get("data"):
        html = _decode_body(html_part["body"]["data"])

    # Extract attachment metadata
    attachments = []
    for p in parts:
        mime_type = p.get("mimeType") or ""
        filename = p.get("filename") or ""
        body = p.get("body") or {}
        size = body.get("size") or 0

        # Only include actual attachments (not inline text parts)
        if (
            filename
            and size
            and not re.search(r"text/(plain|html)", mime_type, re.IGNORECASE)
        ):
            attachments.append(
                {
                    "filename": filename,
                    "mimeType": mime_type,
                    "size": size,
                    "attachmentId": body.get("attachmentId"),
                }
            )

    return {
        "subject": subject,
        "from": from_,
        "headers": headers,
        "text": text,
        "html": html,
        "attachments": attachments,
    }


async def _maybe_parse_pdf_text(
    service, user_id: str, msg: Dict[str, Any], base: Extractable
) -> Extractable:
    """
    Optionally extract text from PDF attachments and add to email text.

    Controlled by settings.GMAIL_PDF_PARSE and settings.GMAIL_PDF_MAX_BYTES.
    Only processes PDFs below size threshold.
    """
    if not settings.GMAIL_PDF_PARSE:
        return base

    max_bytes = settings.GMAIL_PDF_MAX_BYTES
    out = dict(base)

    # Get all parts
    parts = _flatten_parts(msg.get("payload") or {})

    for p in parts:
        mime_type = p.get("mimeType") or ""
        if not re.search(r"application/pdf", mime_type, re.IGNORECASE):
            continue

        body = p.get("body") or {}
        size = int(body.get("size") or 0)

        # Size guard
        if size <= 0 or size > max_bytes:
            continue

        att_id = body.get("attachmentId")
        if not att_id:
            continue

        try:
            # Fetch attachment data
            att = (
                service.users()
                .messages()
                .attachments()
                .get(userId=user_id, messageId=msg["id"], id=att_id)
                .execute()
            )

            data_b64 = att.get("data")
            if not data_b64:
                continue

            # Decode PDF bytes
            pdf_bytes = base64.b64decode(data_b64.replace("-", "+").replace("_", "/"))
            buf = io.BytesIO(pdf_bytes)

            # Extract text using pdfminer.six
            try:
                from pdfminer.high_level import extract_text as pdf_extract_text

                pdf_text = pdf_extract_text(buf) or ""
                pdf_text = pdf_text.strip()

                if pdf_text:
                    # Store in _pdfText field for extractor
                    out["_pdfText"] = pdf_text

                    # Also prepend to text field
                    existing_text = out.get("text") or ""
                    combined = (pdf_text + "\n\n---\n\n" + existing_text).strip()
                    out["text"] = combined
            except ImportError:
                # pdfminer.six not installed
                print("Warning: GMAIL_PDF_PARSE=True but pdfminer.six not installed")
            except Exception as e:
                # PDF parsing failed - log but continue
                print(f"PDF parsing failed: {e}")

        except Exception as e:
            # Attachment fetch failed - log but continue
            print(f"Failed to fetch PDF attachment: {e}")

    return out


def _build_service(creds: Credentials):
    """Build Gmail API service with credentials."""
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def single_user_provider() -> GmailProvider:
    """
    Gmail provider using single-user OAuth from environment variables.

    Requires: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, GMAIL_USER
    """

    class SingleUserProvider:
        async def fetch_thread_latest(
            self, thread_id: str, user_email: Optional[str] = None
        ) -> Optional[Extractable]:
            # Check if configured
            if not (
                settings.GMAIL_CLIENT_ID
                and settings.GMAIL_CLIENT_SECRET
                and settings.GMAIL_REFRESH_TOKEN
                and settings.GMAIL_USER
            ):
                return None

            try:
                # Create credentials
                creds = Credentials(
                    token=None,
                    refresh_token=settings.GMAIL_REFRESH_TOKEN,
                    client_id=settings.GMAIL_CLIENT_ID,
                    client_secret=settings.GMAIL_CLIENT_SECRET,
                    token_uri="https://oauth2.googleapis.com/token",
                )

                # Refresh access token if needed
                if not creds.valid:
                    creds.refresh(Request())

                # Build service
                svc = _build_service(creds)

                # Fetch thread
                thread = (
                    svc.users()
                    .threads()
                    .get(userId=settings.GMAIL_USER, id=thread_id, format="full")
                    .execute()
                )

                msgs = thread.get("messages") or []
                if not msgs:
                    return None

                # Get latest message by internalDate
                latest = sorted(
                    msgs, key=lambda m: int(m.get("internalDate", "0")), reverse=True
                )[0]

                # Convert to extractable format
                base = _parts_to_extractable(latest)

                # Optional PDF parsing
                enriched = await _maybe_parse_pdf_text(
                    svc, settings.GMAIL_USER, latest, base
                )

                return enriched

            except HttpError as e:
                # Thread not found or permission denied
                print(f"Gmail API error: {e}")
                return None
            except Exception as e:
                # Unexpected error
                print(f"Unexpected Gmail error: {e}")
                return None

    return SingleUserProvider()


def db_backed_provider(
    get_token_by_email: Callable[[str], Awaitable[Optional[Dict[str, Any]]]],
) -> GmailProvider:
    """
    Gmail provider using per-user tokens from database.

    Falls back to single-user env vars if no user token found.

    Args:
        get_token_by_email: Async function that returns token dict for user email
    """

    class DbBackedProvider:
        async def fetch_thread_latest(
            self, thread_id: str, user_email: Optional[str] = None
        ) -> Optional[Extractable]:
            # Try per-user token if email provided
            if user_email:
                tok = await get_token_by_email(user_email)

                if tok and settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET:
                    try:
                        # Create credentials from DB token
                        creds = Credentials(
                            token=tok.get("access_token"),
                            refresh_token=tok.get("refresh_token"),
                            client_id=settings.GMAIL_CLIENT_ID,
                            client_secret=settings.GMAIL_CLIENT_SECRET,
                            token_uri="https://oauth2.googleapis.com/token",
                        )

                        # Refresh if needed
                        if not creds.valid:
                            try:
                                creds.refresh(Request())
                            except Exception as e:
                                print(f"Token refresh failed for {user_email}: {e}")
                                return None

                        # Build service
                        svc = _build_service(creds)

                        # Fetch thread
                        thread = (
                            svc.users()
                            .threads()
                            .get(userId=user_email, id=thread_id, format="full")
                            .execute()
                        )

                        msgs = thread.get("messages") or []
                        if not msgs:
                            return None

                        # Get latest message
                        latest = sorted(
                            msgs,
                            key=lambda m: int(m.get("internalDate", "0")),
                            reverse=True,
                        )[0]

                        # Convert to extractable
                        base = _parts_to_extractable(latest)

                        # Optional PDF parsing
                        enriched = await _maybe_parse_pdf_text(
                            svc, user_email, latest, base
                        )

                        return enriched

                    except HttpError as e:
                        print(f"Gmail API error for {user_email}: {e}")
                        return None
                    except Exception as e:
                        print(f"Unexpected error for {user_email}: {e}")
                        return None

            # Fallback to single-user provider
            return await single_user_provider().fetch_thread_latest(thread_id, None)

    return DbBackedProvider()


def mock_provider(seed_map: Dict[str, List[Extractable]]) -> GmailProvider:
    """
    Mock Gmail provider for testing.

    Args:
        seed_map: Dict mapping thread_id to list of message dicts
    """

    class MockProvider:
        async def fetch_thread_latest(
            self, thread_id: str, user_email: Optional[str] = None
        ) -> Optional[Extractable]:
            msgs = seed_map.get(thread_id) or []
            # Return latest message (last in list)
            return msgs[-1] if msgs else None

    return MockProvider()


# Backward compatibility helpers


def is_configured() -> bool:
    """Check if single-user Gmail is configured via env vars."""
    return bool(
        settings.GMAIL_CLIENT_ID
        and settings.GMAIL_CLIENT_SECRET
        and settings.GMAIL_REFRESH_TOKEN
        and settings.GMAIL_USER
    )


async def fetch_thread_latest(thread_id: str) -> Optional[Extractable]:
    """Fetch thread using single-user provider (backward compatibility)."""
    provider = single_user_provider()
    return await provider.fetch_thread_latest(thread_id)


def sync_fetch_thread_latest(thread_id: str) -> Optional[Extractable]:
    """Synchronous wrapper for backward compatibility."""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(fetch_thread_latest(thread_id))
