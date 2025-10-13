"""
Email extraction service - Company, Role, Source detection with confidence scoring.

Uses heuristics to parse email content and detect:
- Company name (from sender domain, signature, display name)
- Role/Position (from subject line patterns)
- Source/ATS (Greenhouse, Lever, Workday, etc.)
- Confidence score (0.0 to 1.0) based on signal strength
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

# Free email providers (not company emails)
FREE_PROVIDERS = {"gmail", "outlook", "yahoo", "icloud", "hotmail", "protonmail", "aol"}

# Known ATS/recruiting platforms
KNOWN_SOURCES = ("Greenhouse", "Lever", "Workday")

# Role extraction pattern
ROLE_RE = re.compile(
    r"(?:\bfor\b|[–—-])\s*([A-Za-z0-9()\/,&.\- ]*"
    r"(?:engineer|designer|manager|scientist|analyst|developer|lead|architect|"
    r"director|coordinator|specialist|consultant|intern|associate)[A-Za-z0-9()\/,&.\- ]*)",
    re.IGNORECASE,
)


def _sanitize(s: Optional[str]) -> str:
    """Remove HTML tags and normalize whitespace."""
    if not s:
        return ""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", s)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _headers_concat(h: Optional[Dict[str, Optional[str]]]) -> str:
    """Concatenate all headers into searchable string."""
    if not h:
        return ""
    return "\n".join(f"{k}:{(v or '')}" for k, v in h.items())


def _clean_company(c: str) -> str:
    """Clean and normalize company name."""
    # Remove special characters except &, ., -, and spaces
    cleaned = re.sub(r"[^A-Za-z0-9&.\- ]+", " ", c).strip()
    # Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _company_from_from_header(from_hdr: Optional[str]) -> Optional[str]:
    """
    Extract company name from From header.

    Examples:
        "Acme Recruiting <recruiting@acme.ai>" -> "Acme"
        "Jane @ Acme <jane@acme.ai>" -> "Acme"
        "jobs@company.com" -> "company"
    """
    if not from_hdr:
        return None

    # Extract display name (before email address)
    display = re.sub(r"<.*?>", "", from_hdr).strip()

    # Pattern: "from [Company]"
    m = re.search(r"\bfrom\s+([A-Z][\w&.\- ]{1,40})", display, re.IGNORECASE)
    if m:
        return _clean_company(m.group(1))

    # Pattern: "[Company] Recruiting/Careers/Talent/HR"
    m = re.search(
        r"\b([A-Z][\w&.\- ]{1,40})\s+(Recruiting|Careers|Talent|HR)\b",
        display,
        re.IGNORECASE,
    )
    if m:
        return _clean_company(m.group(1))

    # Pattern: "@ [Company]"
    m = re.search(r"@\s+([A-Z][\w&.\- ]{1,40})", display, re.IGNORECASE)
    if m:
        return _clean_company(m.group(1))

    # Extract from email domain
    m = re.search(r"[\w.+-]+@([\w.-]+\.[a-z]{2,})", from_hdr, re.IGNORECASE)
    if m:
        domain = m.group(1).lower()
        parts = domain.split(".")

        # Find the core domain part (skip subdomains like "mail", "jobs", etc.)
        core = None
        for p in parts[:-1]:  # Exclude TLD
            if p not in {
                "mail",
                "email",
                "jobs",
                "careers",
                "apply",
                "recruiting",
                "hr",
                "www",
            }:
                core = p
                break

        if core and core not in FREE_PROVIDERS:
            return _clean_company(core)

    return None


def _company_from_signature(text: str) -> Optional[str]:
    """
    Extract company name from email signature.

    Looks for company names in first ~30 lines of email body.
    """
    lines = [
        line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()
    ]  # noqa: E741

    for line in lines[:30]:
        # Pattern: "Acme Inc." or "Acme - Recruiting"
        if re.match(
            r"^[A-Z][\w&.\- ]{1,40}(,? (Inc\.?|LLC|Ltd\.?|Corp\.?))?(\s*[•—-]\s*(Talent|Recruiting|Careers))?$",
            line,
        ):
            # Exclude common email phrases
            if not re.match(
                r"^(Thanks|Best|Regards|Sent from|On \w{3}|.+@.+)$",
                line,
                re.IGNORECASE,
            ):
                # Remove suffix like "- Recruiting"
                company = re.sub(r"\s*[•—-].*$", "", line)
                return _clean_company(company)

    return None


def _role_from_subject(subject: str) -> Optional[str]:
    """
    Extract role/position from email subject.

    Examples:
        "Application for Senior Engineer" -> "Senior Engineer"
        "Interview - Software Developer" -> "Software Developer"
    """
    m = ROLE_RE.search(subject or "")
    if m:
        role = m.group(1).strip()
        # Normalize whitespace
        role = re.sub(r"\s+", " ", role)
        return role
    return None


def _detect_source(
    headers: Optional[Dict[str, Optional[str]]], body: str
) -> tuple[Optional[str], float]:
    """
    Detect email source/ATS and return confidence score.

    Returns:
        (source_name, confidence) tuple where confidence is 0.0-1.0
    """
    headers = headers or {}
    hay = _headers_concat(headers)

    # Extract specific headers (case-insensitive)
    lu = headers.get("List-Unsubscribe") or headers.get("list-unsubscribe") or ""
    via = (
        headers.get("X-Mailer")
        or headers.get("x-mailer")
        or headers.get("x-ses-outgoing")
        or ""
    )
    rpath = headers.get("Return-Path") or headers.get("return-path") or ""
    dkim = headers.get("DKIM-Signature") or headers.get("dkim-signature") or ""
    auth = (
        headers.get("Authentication-Results")
        or headers.get("authentication-results")
        or ""
    )

    # Known ATS detection (high confidence)
    if re.search(r"greenhouse\.io|mailer[-.]greenhouse\.io", hay, re.IGNORECASE):
        return ("Greenhouse", 0.9)
    if re.search(r"hire\.lever\.co|lever\.co|mailer\..*lever", hay, re.IGNORECASE):
        return ("Lever", 0.9)
    if re.search(r"workday\.com|myworkday", hay, re.IGNORECASE):
        return ("Workday", 0.9)

    # Generic mailing list
    if re.search(r"unsubscribe", lu, re.IGNORECASE):
        return ("mailing-list", 0.6)

    # Email service providers
    if re.search(r"ses\.amazonaws\.com", via, re.IGNORECASE):
        return ("SES", 0.5)
    if re.search(r"sendgrid|mailgun|postmark", hay, re.IGNORECASE):
        return ("ESP", 0.5)

    # DKIM / Return-Path / Authentication-Results signals (strong signals)
    auth_all = rpath + dkim + auth
    if re.search(r"greenhouse\.io", auth_all, re.IGNORECASE):
        return ("Greenhouse", 0.85)
    if re.search(r"lever\.co", auth_all, re.IGNORECASE):
        return ("Lever", 0.85)
    if re.search(r"workday\.com|myworkday", auth_all, re.IGNORECASE):
        return ("Workday", 0.85)

    # No clear source detected
    return (None, 0.4)


@dataclass
class ExtractInput:
    """Input data for email extraction."""

    subject: Optional[str] = None
    from_: Optional[str] = None
    headers: Optional[Dict[str, Optional[str]]] = None
    text: Optional[str] = None
    html: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    pdf_text: Optional[str] = None  # Internal hint from PDF parsing


@dataclass
class ExtractResult:
    """Result of email extraction with confidence scoring."""

    company: Optional[str]
    role: Optional[str]
    source: Optional[str]
    source_confidence: float
    debug: Dict[str, Any] = field(default_factory=dict)


def extract_from_email(inp: ExtractInput) -> ExtractResult:
    """
    Extract company, role, and source from email content.

    Uses multiple heuristics and signals to determine:
    1. Company name (from sender, domain, signature)
    2. Role/position (from subject line)
    3. Source/ATS (from headers and body patterns)
    4. Confidence score (based on signal strength)

    Args:
        inp: ExtractInput with email content

    Returns:
        ExtractResult with extracted fields and confidence
    """
    # Sanitize text inputs
    subject = _sanitize(inp.subject)
    body = _sanitize(inp.text or inp.html or "")

    # If PDF text was extracted, prepend it to body
    if inp.pdf_text:
        body = (inp.pdf_text.strip() + "\n\n---\n\n" + body).strip()

    # Extract role from subject
    role = _role_from_subject(subject)

    # Extract company from multiple sources
    company_from_header = _company_from_from_header(inp.from_)
    company_from_sig = _company_from_signature(body)
    company = company_from_header or company_from_sig

    # Detect source and get initial confidence
    source, confidence = _detect_source(inp.headers, body)

    # Confidence adjustments based on additional signals

    # Known ATS sources get boosted confidence
    if source in KNOWN_SOURCES:
        confidence = max(confidence, 0.95)

    # Subject line mentions known ATS
    if re.search(r"greenhouse|lever|workday", subject, re.IGNORECASE):
        confidence = max(confidence, 0.90)

    # Job-related keywords in body (weak signal)
    if not source and re.search(
        r"apply|requisition|job|opening|position", body, re.IGNORECASE
    ):
        confidence = max(confidence, 0.55)

    # PDF attachment hints (interview invites, schedules)
    if inp.attachments:
        has_interview_pdf = any(
            re.search(r"application/pdf", a.get("mimeType") or "", re.IGNORECASE)
            and re.search(
                r"(invite|interview|schedule|onsite|loop|agenda)",
                (a.get("filename") or "").lower(),
            )
            for a in inp.attachments
        )
        if has_interview_pdf:
            confidence = max(confidence, 0.60)

    return ExtractResult(
        company=company or None,
        role=role or None,
        source=source,
        source_confidence=confidence,
        debug={
            "company_from_header": company_from_header,
            "company_from_signature": company_from_sig,
            "matched_role": bool(role),
            "has_pdf_text": bool(inp.pdf_text),
        },
    )
