"""High-precision labeling rules for email categorization.

This module provides deterministic rules that achieve high precision
for common email categories: newsletters, promos, recruiting, bills.

Rules are designed to be conservative - they only fire when confident.
The ML model handles the remaining ambiguous cases.
"""

import re
from tldextract import extract as tldx

# Known ATS (Applicant Tracking System) domains
ATS_DOMAINS = {
    "lever.co",
    "greenhouse.io",
    "workday.com",
    "smartrecruiters.com",
    "myworkdayjobs.com",
    "icims.com",
    "jobvite.com",
    "taleo.net",
}

# Regex patterns for content-based detection
BANK_UTILITY_RX = re.compile(
    r"\b(invoice|receipt|payment|statement|utility|bank|past due|due date|account balance)\b",
    re.IGNORECASE,
)

DEAL_RX = re.compile(
    r"\b(deal|sale|promo|coupon|% off|offer|discount|limited time|shop now|save \$)\b",
    re.IGNORECASE,
)

DUE_DATE_RX = re.compile(
    r"\b(due\s+(on|by)?\s*\w+ \d{1,2}|\bby \d{1,2}/\d{1,2}/\d{2,4})\b", re.IGNORECASE
)

PRECEDENCE_BULK = re.compile(r"\bprecedence:\s*bulk\b", re.IGNORECASE)

# Known promotional domains
PROMO_DOMAINS = {
    ".promotions",
    "marketing.",
    "newsletter.",
    "promo.",
}


def get_domain(addr: str) -> str:
    """Extract registered domain from email address.

    Args:
        addr: Email address (e.g., "user@subdomain.example.com")

    Returns:
        Registered domain (e.g., "example.com") or empty string
    """
    if not addr or "@" not in addr:
        return ""

    domain_part = addr.split("@")[-1]
    extracted = tldx(domain_part)
    return extracted.registered_domain or ""


def rule_labels(doc: dict) -> tuple[str | None, str]:
    """Apply high-precision labeling rules to an email document.

    Args:
        doc: Email document with fields:
            - subject: Email subject line
            - body_text: Plain text email body
            - sender: Sender email address
            - sender_domain: Pre-extracted sender domain (optional)
            - list_unsubscribe: Unsubscribe header value (optional)
            - headers: List of raw email headers (optional)

    Returns:
        Tuple of (category, reason) where:
            - category: One of ["newsletter", "promo", "recruiting", "bill"] or None
            - reason: Human-readable explanation of why this rule fired

    Examples:
        >>> doc = {"subject": "Deal: 50% off", "body_text": "Shop now!"}
        >>> rule_labels(doc)
        ("promo", "Promo keywords")

        >>> doc = {"list_unsubscribe": "http://example.com/unsub"}
        >>> rule_labels(doc)
        ("newsletter", "Unsubscribe/List-Id header")
    """
    # Extract fields with safe defaults
    subj = doc.get("subject", "")
    body = doc.get("body_text", "")
    sender = doc.get("sender", "")
    dom = doc.get("sender_domain") or get_domain(sender)

    # Build headers blob for header-based detection
    headers_blob = ""
    if doc.get("headers"):
        headers_blob = " ".join(doc["headers"])

    # Rule 1: Newsletter detection via headers
    if doc.get("list_unsubscribe"):
        return "newsletter", "Unsubscribe header present"

    if headers_blob and "list-id" in headers_blob.lower():
        return "newsletter", "List-Id header present"

    if PRECEDENCE_BULK.search(headers_blob):
        return "newsletter", "Precedence: bulk header"

    # Rule 2: Promotional domain detection
    if any(dom.endswith(d) or d in dom for d in PROMO_DOMAINS):
        return "promo", f"Promotional domain ({dom})"

    # Rule 3: Promotional content keywords
    if DEAL_RX.search(subj) or DEAL_RX.search(body):
        return "promo", "Promotional keywords in content"

    # Rule 4: ATS / recruiting systems
    if any(dom.endswith(d) for d in ATS_DOMAINS):
        return "recruiting", f"Known ATS domain ({dom})"

    # Rule 5: Bills and financial documents
    if BANK_UTILITY_RX.search(subj):
        return "bill", "Finance/billing keywords in subject"

    if BANK_UTILITY_RX.search(body) and DUE_DATE_RX.search(body):
        return "bill", "Finance keywords + due date in body"

    if "invoice" in subj.lower() or "receipt" in subj.lower():
        return "bill", "Invoice/receipt in subject"

    # No high-precision rule matched
    return None, "No high-precision rule matched"


def get_weak_label(doc: dict) -> str | None:
    """Get weak label for training data generation.

    This is a wrapper around rule_labels() that returns just the category
    for use in generating training datasets.

    Args:
        doc: Email document (same format as rule_labels)

    Returns:
        Category string or None if no rule matched
    """
    category, _ = rule_labels(doc)
    return category
