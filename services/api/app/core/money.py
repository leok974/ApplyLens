"""
Money Mode - Phase 6: Receipt tracking and duplicate detection

Features:
- Detect receipt/invoice emails
- Extract amounts from email body
- Export to CSV for expense tracking
- Detect duplicate charges (same merchant + amount within 7 days)
"""

import re
import csv
import io
from typing import List, Dict, Any, Tuple
from datetime import datetime


# Regex patterns for amount extraction
AMT_RE = re.compile(r"(\$|USD\s*)\s?([0-9]+(?:\.[0-9]{2})?)")


def is_receipt(email: Dict[str, Any]) -> bool:
    """
    Determine if an email is a receipt/invoice.

    Heuristics:
    - Subject contains: receipt, invoice, order, payment
    - Category is finance
    - Sender domain is known payment processor

    Args:
        email: Email dict with subject, category, sender_domain

    Returns:
        True if email appears to be a receipt
    """
    subject = (email.get("subject") or "").lower()
    category = email.get("category") or ""
    sender_domain = email.get("sender_domain") or ""

    # Receipt keywords in subject
    receipt_keywords = [
        "receipt",
        "invoice",
        "order",
        "payment",
        "purchase",
        "transaction",
        "confirmation",
        "bill",
        "statement",
    ]

    if any(kw in subject for kw in receipt_keywords):
        return True

    # Finance category
    if category == "finance":
        return True

    # Known payment processors
    payment_domains = [
        "paypal.com",
        "stripe.com",
        "square.com",
        "venmo.com",
        "amazon.com",
        "shopify.com",
        "ebay.com",
    ]

    if any(domain in sender_domain for domain in payment_domains):
        return True

    return False


def extract_amount(text: str) -> float | None:
    """
    Extract dollar amount from email text.

    Looks for patterns like:
    - $123.45
    - USD 99.99
    - Total: $50.00

    Args:
        text: Email body text or subject

    Returns:
        Amount as float, or None if not found
    """
    if not text:
        return None

    match = AMT_RE.search(text)
    if match:
        return float(match.group(2))

    return None


def build_receipts_csv(docs: List[Dict[str, Any]]) -> bytes:
    """
    Export receipt emails to CSV format.

    Columns:
    - date: received_at
    - merchant: sender_domain or sender
    - amount: extracted from body or stored field
    - email_id: unique identifier
    - subject: email subject
    - category: email category

    Args:
        docs: List of email documents

    Returns:
        CSV data as bytes
    """
    buf = io.StringIO()
    writer = csv.writer(buf)

    # Header
    writer.writerow(["date", "merchant", "amount", "email_id", "subject", "category"])

    # Rows
    for doc in docs:
        # Extract fields
        date = doc.get("received_at", "")
        if isinstance(date, datetime):
            date = date.isoformat()

        merchant = doc.get("sender_domain") or doc.get("sender") or "Unknown"

        # Try to get amount from doc or extract from body
        amount = doc.get("amount")
        if amount is None:
            body_text = doc.get("body_text", "")
            amount = extract_amount(body_text)

        email_id = doc.get("id") or doc.get("_id") or ""
        subject = doc.get("subject", "")
        category = doc.get("category", "")

        writer.writerow(
            [
                date,
                merchant,
                amount if amount is not None else "",
                email_id,
                subject,
                category,
            ]
        )

    return buf.getvalue().encode("utf-8")


def detect_duplicates(
    receipts: List[Dict[str, Any]], window_days: int = 7
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """
    Detect potential duplicate charges.

    A duplicate is defined as:
    - Same merchant (sender_domain)
    - Same amount (within $0.01)
    - Within N days of each other

    Args:
        receipts: List of receipt documents with date, merchant, amount
        window_days: Time window for duplicate detection (default 7 days)

    Returns:
        List of tuples (earlier_receipt, later_receipt) representing duplicates
    """
    # Group by merchant + amount
    groups: Dict[Tuple[str, float], List[Dict[str, Any]]] = {}

    for receipt in receipts:
        merchant = receipt.get("merchant") or receipt.get("sender_domain") or ""
        amount = receipt.get("amount")

        if not merchant or amount is None:
            continue

        # Round amount to nearest cent
        amount = round(float(amount), 2)
        key = (merchant.lower(), amount)

        if key not in groups:
            groups[key] = []

        groups[key].append(receipt)

    # Find duplicates within time window
    duplicates = []

    for key, items in groups.items():
        if len(items) < 2:
            continue  # Need at least 2 transactions to have a duplicate

        # Sort by date
        items_sorted = sorted(
            items, key=lambda x: x.get("date") or x.get("received_at") or ""
        )

        # Check pairs within window
        for i in range(len(items_sorted) - 1):
            earlier = items_sorted[i]
            later = items_sorted[i + 1]

            # Parse dates
            date1 = earlier.get("date") or earlier.get("received_at")
            date2 = later.get("date") or later.get("received_at")

            if isinstance(date1, str):
                date1 = datetime.fromisoformat(date1.replace("Z", "+00:00"))
            if isinstance(date2, str):
                date2 = datetime.fromisoformat(date2.replace("Z", "+00:00"))

            # Check if within window
            if date1 and date2:
                delta = abs((date2 - date1).days)
                if delta <= window_days:
                    duplicates.append((earlier, later))

    return duplicates


def summarize_spending(receipts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate spending summary statistics.

    Args:
        receipts: List of receipt documents

    Returns:
        Dictionary with:
        - total_amount: Sum of all amounts
        - count: Number of receipts
        - by_merchant: Dict of merchant -> total amount
        - by_month: Dict of month -> total amount
        - avg_amount: Average transaction amount
    """
    total = 0.0
    by_merchant: Dict[str, float] = {}
    by_month: Dict[str, float] = {}

    for receipt in receipts:
        amount = receipt.get("amount")
        if amount is None:
            continue

        amount = float(amount)
        total += amount

        # By merchant
        merchant = receipt.get("merchant") or receipt.get("sender_domain") or "Unknown"
        by_merchant[merchant] = by_merchant.get(merchant, 0.0) + amount

        # By month
        date = receipt.get("date") or receipt.get("received_at")
        if date:
            if isinstance(date, str):
                date = datetime.fromisoformat(date.replace("Z", "+00:00"))
            month = date.strftime("%Y-%m")
            by_month[month] = by_month.get(month, 0.0) + amount

    return {
        "total_amount": round(total, 2),
        "count": len(receipts),
        "by_merchant": {k: round(v, 2) for k, v in by_merchant.items()},
        "by_month": {k: round(v, 2) for k, v in by_month.items()},
        "avg_amount": round(total / len(receipts), 2) if receipts else 0.0,
    }
