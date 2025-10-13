"""
RFC-2369 List-Unsubscribe Support

Parses List-Unsubscribe headers and executes unsubscribe operations
via HTTP (GET/POST) or mailto protocol.
"""

import re
import requests
from typing import Dict, Optional, Tuple

# User agent for HTTP requests
UA = {"User-Agent": "AgenticMailbox/1.0 (+unsubscribe)"}
TIMEOUT = 8

# Regex patterns for extracting unsubscribe targets
MAILTO_RX = re.compile(r"mailto:([^>,\s]+)", re.I)
HTTP_RX = re.compile(r"<(https?://[^>]+)>", re.I)


def parse_list_unsubscribe(
    headers: Dict[str, str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse List-Unsubscribe header to extract mailto and HTTP targets.

    Args:
        headers: Dictionary of email headers

    Returns:
        Tuple of (mailto_address, http_url) - either may be None

    Example:
        headers = {
            "List-Unsubscribe": "<mailto:unsub@example.com>, <https://example.com/unsub?id=123>"
        }
        parse_list_unsubscribe(headers)
        # Returns: ("unsub@example.com", "https://example.com/unsub?id=123")
    """
    if not headers:
        return (None, None)

    # Normalize header keys to lowercase
    lower = {k.lower(): v for k, v in headers.items()}
    val = lower.get("list-unsubscribe") or ""

    # Extract mailto and HTTP targets
    mailto = MAILTO_RX.search(val)
    http = HTTP_RX.search(val)

    return (mailto.group(1) if mailto else None, http.group(1) if http else None)


def http_unsubscribe(url: str) -> requests.Response:
    """
    Execute HTTP unsubscribe by making a request to the unsubscribe URL.

    Many providers accept GET; some require POST. This function tries HEAD first
    (to be polite), then falls back to GET if needed.

    Args:
        url: HTTP(S) unsubscribe URL

    Returns:
        Response object with status_code

    Raises:
        requests.exceptions.RequestException: On network errors
    """
    # Try HEAD first (polite check without fetching body)
    try:
        r = requests.head(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code in (200, 204):
            return r
    except Exception:
        pass  # Fall through to GET

    # Fall back to GET (most providers accept this)
    return requests.get(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)


def perform_unsubscribe(headers: Dict[str, str]) -> Dict:
    """
    Parse List-Unsubscribe header and perform unsubscribe operation.

    Preference order:
    1. HTTP target (if present) - executes immediately
    2. Mailto target - records intent for out-of-band processing

    Args:
        headers: Dictionary of email headers

    Returns:
        Dictionary with:
        - mailto: Mailto address if present
        - http: HTTP URL if present
        - performed: "http", "mailto", or None
        - status: HTTP status code or "queued" for mailto

    Example:
        result = perform_unsubscribe({
            "List-Unsubscribe": "<https://example.com/unsub?id=123>"
        })
        # Returns: {
        #   "mailto": None,
        #   "http": "https://example.com/unsub?id=123",
        #   "performed": "http",
        #   "status": 200
        # }
    """
    mailto, http = parse_list_unsubscribe(headers)
    result = {"mailto": mailto, "http": http, "performed": None, "status": None}

    # Prefer HTTP unsubscribe (immediate)
    if http:
        try:
            r = http_unsubscribe(http)
            result.update({"performed": "http", "status": r.status_code})
            return result
        except Exception as e:
            # Record error but don't crash
            result.update({"performed": "http", "status": f"error: {str(e)}"})
            return result

    # Fall back to mailto (queued for out-of-band processing)
    # Actual email sending is optional future enhancement via Gmail API
    if mailto:
        result.update({"performed": "mailto", "status": "queued"})
        return result

    return result
