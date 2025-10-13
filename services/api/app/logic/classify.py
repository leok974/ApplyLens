"""
Email classification logic module

Provides rule-based and heuristic email categorization:
- promotions: Marketing emails with unsubscribe links and deals
- bills: Invoices, receipts, payment reminders
- security: Password resets, suspicious activity alerts
- applications: Job application responses (ATS systems)
- personal: Default category for everything else

Future: Can be enhanced with ML models trained on user feedback
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

# Category detection patterns
PROMO_HINTS = re.compile(
    r"\b(save|deal|sale|% off|coupon|limited time|expires|discount|offer|"
    r"buy now|shop|free shipping|clearance|flash sale)\b",
    re.IGNORECASE,
)

BILL_HINTS = re.compile(
    r"\b(invoice|receipt|statement|due|amount|balance|payment|bill|"
    r"transaction|charged|subscription|renewal|overdue)\b",
    re.IGNORECASE,
)

SECURITY_HINTS = re.compile(
    r"\b(verify account|password reset|unusual activity|urgent|suspicious|"
    r"security alert|confirm|unauthorized|locked|breach|phishing)\b",
    re.IGNORECASE,
)

APPLICATION_HINTS = re.compile(
    r"\b(application|interview|candidate|position|role|opportunity|"
    r"greenhouse|lever|workday|jobvite|applied|resume|cover letter)\b",
    re.IGNORECASE,
)

# Known ATS domains (Application Tracking Systems)
ATS_DOMAINS = {
    "greenhouse.io",
    "lever.co",
    "workday.com",
    "jobvite.com",
    "icims.com",
    "taleo.net",
    "smartrecruiters.com",
    "breezy.hr",
    "recruitee.com",
    "ashbyhq.com",
}

# High-risk indicators for security scoring
RISK_INDICATORS = {
    "urgent_language": (r"\b(urgent|immediate|act now|expire|suspended)\b", 10),
    "suspicious_links": (r"bit\.ly|tinyurl|short\.link", 15),
    "money_request": (r"\b(wire transfer|bitcoin|gift card|verify payment)\b", 20),
    "credential_phishing": (
        r"\b(verify credentials|confirm password|update payment)\b",
        25,
    ),
    "external_sender": (
        r"@(?!.*?(gmail|yahoo|outlook|hotmail))",
        5,
    ),  # Not major email providers
}


def weak_category(email: Dict[str, Any]) -> str:
    """
    Classify email into one of: promotions, bills, security, applications, personal

    Args:
        email: Dict with fields like subject, body_text, sender, sender_domain, has_unsubscribe

    Returns:
        Category string

    Examples:
        >>> weak_category({"has_unsubscribe": True, "subject": "20% off sale"})
        'promotions'
        >>> weak_category({"subject": "Your invoice is ready"})
        'bills'
    """
    subject = email.get("subject", "")
    body = email.get("body_text", "")
    combined = f"{subject} {body}"
    sender_domain = email.get("sender_domain", "")

    # High-priority: Security threats (check first)
    if SECURITY_HINTS.search(combined) or email.get("risk_score", 0) >= 80:
        return "security"

    # Application tracking system emails
    if sender_domain in ATS_DOMAINS or APPLICATION_HINTS.search(combined):
        # Additional check: avoid false positives from promo emails about "job opportunities"
        if not (email.get("has_unsubscribe") and PROMO_HINTS.search(combined)):
            return "applications"

    # Promotions: Has unsubscribe link + promotional keywords
    if email.get("has_unsubscribe") and PROMO_HINTS.search(combined):
        return "promotions"

    # Bills and financial: Invoice/payment keywords
    if BILL_HINTS.search(combined):
        return "bills"

    # Default category
    return "personal"


def calculate_risk_score(email: Dict[str, Any]) -> float:
    """
    Calculate risk score (0-100) based on suspicious indicators

    Higher score = more likely spam/phishing

    Args:
        email: Email dict with subject, body_text, sender, urls, etc.

    Returns:
        Risk score between 0 and 100
    """
    score = 0.0
    subject = email.get("subject", "")
    body = email.get("body_text", "")
    combined = f"{subject} {body}"
    sender = email.get("sender", "")

    # Check each risk indicator
    for indicator_name, (pattern, points) in RISK_INDICATORS.items():
        if re.search(pattern, combined, re.IGNORECASE):
            score += points

    # URL analysis
    urls = email.get("urls", [])
    if isinstance(urls, list) and len(urls) > 10:
        score += 10  # Excessive links (common in spam)

    # Mismatch between sender display name and email domain
    if sender and "@" in sender:
        # Simple heuristic: check if display name looks like a brand but domain doesn't match
        sender_lower = sender.lower()
        if any(brand in sender_lower for brand in ["paypal", "amazon", "bank", "irs"]):
            if not any(
                brand in sender_lower.split("@")[1] for brand in ["paypal", "amazon"]
            ):
                score += 30  # Likely phishing

    # Cap at 100
    return min(score, 100.0)


def extract_expiry_date(email: Dict[str, Any]) -> Optional[datetime]:
    """
    Extract expiration/deadline date from email content

    Looks for patterns like:
    - "expires on Oct 15"
    - "valid until 2025-10-20"
    - "offer ends 10/15/2025"

    Args:
        email: Email dict with subject, body_text, dates array

    Returns:
        datetime of expiry, or None if not found
    """
    # First check if dates array has future dates
    dates = email.get("dates", [])
    if dates and isinstance(dates, list):
        future_dates = [
            d
            for d in dates
            if isinstance(d, (datetime, str))
            and (datetime.fromisoformat(d) if isinstance(d, str) else d)
            > datetime.now()
        ]
        if future_dates:
            # Return the earliest future date as likely expiry
            return min(
                future_dates,
                key=lambda d: datetime.fromisoformat(d) if isinstance(d, str) else d,
            )

    # Pattern matching for expiry language
    email.get("subject", "")
    email.get("body_text", "")

    # For MVP, return None and rely on dates array
    # Full date parsing can be added with dateutil library
    return None


def extract_profile_tags(
    email: Dict[str, Any], user_interests: List[str] = None
) -> List[str]:
    """
    Extract personalization tags based on email content and user profile

    Args:
        email: Email dict
        user_interests: List of user's known interests/preferences

    Returns:
        List of relevant tags for this user

    Examples:
        Tags: ["tech", "shopping", "urgent", "high-value"]
    """
    tags = []
    subject = email.get("subject", "")
    body = email.get("body_text", "")
    combined = f"{subject} {body}".lower()

    # Interest matching
    if user_interests:
        for interest in user_interests:
            if interest.lower() in combined:
                tags.append(f"interest:{interest}")

    # Urgency detection
    if re.search(
        r"\b(urgent|expires today|last chance|ending soon)\b", combined, re.IGNORECASE
    ):
        tags.append("urgent")

    # Value detection
    money_amounts = email.get("money_amounts", [])
    if money_amounts:
        max_amount = max(money_amounts)
        if max_amount > 100:
            tags.append("high-value")
        elif max_amount > 1000:
            tags.append("very-high-value")

    # Category-based tags
    category = email.get("category") or weak_category(email)
    if category == "promotions":
        # Brand detection (simplified)
        for brand in ["amazon", "target", "walmart", "nike", "apple"]:
            if brand in combined:
                tags.append(f"brand:{brand}")

    return list(set(tags))  # Remove duplicates


def classify_email(
    email: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Full email classification: category, risk score, expiry, tags

    This is the main entry point for email classification.

    Args:
        email: Email dict to classify
        user_profile: Optional user profile with interests, preferences

    Returns:
        Dict with classification results:
        {
            "category": str,
            "risk_score": float,
            "expires_at": datetime | None,
            "profile_tags": List[str],
            "confidence": float  # 0-1, how confident we are in the classification
        }
    """
    category = weak_category(email)
    risk_score = calculate_risk_score(email)
    expires_at = extract_expiry_date(email)

    user_interests = []
    if user_profile:
        user_interests = user_profile.get("interests", [])

    profile_tags = extract_profile_tags(email, user_interests)

    # Confidence heuristic (simplified)
    confidence = 0.7  # Base confidence for rule-based

    # Increase confidence for clear signals
    if email.get("has_unsubscribe") and category == "promotions":
        confidence = 0.9
    if email.get("sender_domain") in ATS_DOMAINS and category == "applications":
        confidence = 0.95
    if risk_score > 80:
        confidence = 0.85

    return {
        "category": category,
        "risk_score": risk_score,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "profile_tags": profile_tags,
        "confidence": confidence,
    }


# Convenience function for bulk classification
def classify_batch(
    emails: List[Dict[str, Any]], user_profile: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Classify multiple emails in batch

    Args:
        emails: List of email dicts
        user_profile: Optional user profile

    Returns:
        List of classification results (same order as input)
    """
    return [classify_email(email, user_profile) for email in emails]
