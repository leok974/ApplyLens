"""
High-precision rule-based email categorization.

This module provides deterministic pattern matching for email categories
with very high precision. Rules are preferred over ML predictions when they match.
"""
import re
import fnmatch
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from dateutil import parser as date_parser


# Regex patterns for extracting structured data
RX_MONEY = re.compile(r'[$€£]\s?\d[\d,]*(\.\d{2})?')
RX_AMOUNT_DUE = re.compile(
    r'(?:amount due|total due|balance due|you owe)\s*:?\s*[$€£]?\s*([\d,]+(?:\.\d{2})?)',
    re.IGNORECASE
)
RX_DATE_EXPIRY = re.compile(
    r'\b(?:valid thru|expires?|expiry|expire[sd]? on|by)\s*[:\-]?\s*'
    r'([A-Z][a-z]{2,9}\s+\d{1,2}(?:,?\s+\d{4})?|\d{1,2}/\d{1,2}/\d{2,4})',
    re.IGNORECASE
)
RX_EVENT_DATE = re.compile(
    r'\b(?:on|at|date|when)\s+(?:[A-Z][a-z]{2,9}\s+\d{1,2}(?:,?\s+\d{4})?)\b|'
    r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
    re.IGNORECASE
)
RX_DUE_DATE = re.compile(
    r'\b(?:due date|payment due|due by)\s*:?\s*'
    r'([A-Z][a-z]{2,9}\s+\d{1,2}(?:,?\s+\d{4})?|\d{1,2}/\d{1,2}/\d{2,4})',
    re.IGNORECASE
)


def load_rules() -> Dict[str, Any]:
    """Load categorization rules from YAML file."""
    rules_path = Path(__file__).parent / "rules.yaml"
    with open(rules_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# Load rules at module import
RULES = load_rules()


def hdr_contains(headers: Dict[str, str], needles: list) -> bool:
    """Check if any header contains any of the needle strings."""
    headers_text = "\n".join([f"{k}: {v}" for k, v in headers.items() if v])
    headers_lower = headers_text.lower()
    return any(needle.lower() in headers_lower for needle in needles)


def domain_in(patterns: list, sender_domain: str) -> bool:
    """Check if sender domain matches any pattern (supports wildcards)."""
    sender_domain = sender_domain.lower()
    for pattern in patterns:
        if pattern.startswith("*."):
            # Wildcard subdomain match
            if fnmatch.fnmatch(sender_domain, pattern.replace("*.", "*")):
                return True
        elif sender_domain.endswith(pattern):
            # Exact suffix match
            return True
        elif pattern in sender_domain:
            # Contains match
            return True
    return False


def match_rules(email: Dict[str, Any]) -> Dict[str, bool]:
    """
    Apply high-precision rules to categorize email.
    
    Args:
        email: Dict with keys: headers, sender_domain, body_text, subject
        
    Returns:
        Dict of category -> bool matches
    """
    headers = email.get("headers", {})
    sender_domain = email.get("sender_domain", "").lower()
    body = email.get("body_text", "")[:10000]  # Limit text length
    subject = email.get("subject", "")
    text = f"{subject}\n{body}"
    text_lower = text.lower()

    matches = {
        "promotions": (
            hdr_contains(headers, RULES["promotions"]["headers"]) or
            domain_in(RULES["promotions"]["from_domains"], sender_domain) or
            any(lexeme in text_lower for lexeme in RULES["promotions"]["lexicon_any"])
        ),
        "ats": domain_in(RULES["ats"]["domains"], sender_domain),
        "bills": any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in RULES["bills"]["regex_any"]
        ),
        "banks": domain_in(RULES["banks"]["domains"], sender_domain),
        "events": any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in RULES["events"]["regex_any"]
        ),
    }
    
    return matches


def extract_extras(email: Dict[str, Any]) -> Tuple[Optional[int], Optional[datetime], Optional[datetime]]:
    """
    Extract structured data from email content.
    
    Args:
        email: Dict with keys: subject, body_text
        
    Returns:
        Tuple of (amount_cents, expires_at, event_start_at)
    """
    body = f'{email.get("subject", "")}\n{email.get("body_text", "")}'
    
    # Extract amount (convert to cents)
    amount_cents = None
    m_amount = RX_AMOUNT_DUE.search(body)
    if m_amount:
        try:
            amount_str = m_amount.group(1).replace(",", "")
            amount_cents = int(round(float(amount_str) * 100))
        except (ValueError, AttributeError):
            pass
    
    # Extract expiry date
    expires_at = None
    m_expiry = RX_DATE_EXPIRY.search(body)
    if m_expiry:
        try:
            date_str = m_expiry.group(1)
            expires_at = date_parser.parse(date_str, fuzzy=True)
        except (ValueError, AttributeError):
            pass
    
    # Extract event date
    event_start_at = None
    m_event = RX_EVENT_DATE.search(body)
    if m_event:
        try:
            date_str = m_event.group(0)
            event_start_at = date_parser.parse(date_str, fuzzy=True)
        except (ValueError, AttributeError):
            pass
    
    # Extract due date (for bills)
    if not expires_at:
        m_due = RX_DUE_DATE.search(body)
        if m_due:
            try:
                date_str = m_due.group(1)
                expires_at = date_parser.parse(date_str, fuzzy=True)
            except (ValueError, AttributeError):
                pass
    
    return amount_cents, expires_at, event_start_at
