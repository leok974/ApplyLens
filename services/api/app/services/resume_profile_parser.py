# app/services/resume_profile_parser.py
"""
Lightweight contact extractor for resumes.

Parses basic contact information (email, phone, LinkedIn, name) from resume text.
This is a simple regex-based parser - can be upgraded with LLM extraction later.
"""

import datetime
import re
from dataclasses import dataclass
from typing import Optional


EMAIL_REGEX = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
PHONE_REGEX = re.compile(
    r"""
    (?:
        \+?\d{1,3}[\s\-\.]?
    )?
    (?:\(?\d{3}\)?[\s\-\.]?)?
    \d{3}[\s\-\.]?\d{4}
    """,
    re.VERBOSE,
)
LINKEDIN_REGEX = re.compile(
    r"(https?://(www\.)?linkedin\.com/[^\s]+)",
    re.IGNORECASE,
)
YEARS_EXPERIENCE_REGEX = re.compile(
    r"\b(\d{1,2})\+?\s+years?\s+(?:of\s+)?(?:experience|exp)\b",
    re.IGNORECASE,
)
START_YEAR_REGEX = re.compile(r"\b(20[01]\d|202[0-9])\b")  # 2000–2029-ish


@dataclass
class ParsedResumeContact:
    """Structured contact information extracted from resume."""

    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    years_experience: Optional[int] = None  # NEW: inferred years of experience


def _infer_years_experience(text: str) -> Optional[int]:
    """
    Infer years of experience from resume text using two strategies:

    1. Look for explicit "X years of experience" statements
    2. Fallback: Calculate from earliest start year found in resume

    Args:
        text: Raw resume text

    Returns:
        Inferred years of experience (0-40 range), or None if not found
    """
    # 1) Look for explicit "X years of experience"
    m = YEARS_EXPERIENCE_REGEX.search(text)
    if m:
        try:
            years = int(m.group(1))
            if 0 < years <= 40:
                return years
        except ValueError:
            pass

    # 2) Fallback: derive from earliest start year
    years = None
    year_matches = [int(y) for y in START_YEAR_REGEX.findall(text)]
    if year_matches:
        earliest = min(year_matches)
        current_year = datetime.date.today().year
        rough = current_year - earliest
        if 0 < rough <= 40:
            years = rough

    return years


def parse_contact_from_resume(text: str) -> ParsedResumeContact:
    """
    Very lightweight contact extractor for resumes.
    You can upgrade this later with LLM extraction, but this is enough to get unblocked.

    Args:
        text: Raw resume text extracted from PDF/DOCX

    Returns:
        ParsedResumeContact with extracted contact fields
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # 1) Email
    email_match = EMAIL_REGEX.search(text)
    email = email_match.group(0) if email_match else None

    # 2) LinkedIn
    linkedin_match = LINKEDIN_REGEX.search(text)
    linkedin = linkedin_match.group(1) if linkedin_match else None

    # 3) Phone
    phone_match = PHONE_REGEX.search(text)
    phone = phone_match.group(0) if phone_match else None

    # 4) Full name (best-effort: first non-shouty line that looks "name-like")
    full_name = None
    for ln in lines[:5]:
        if (
            len(ln.split()) <= 4
            and not ln.endswith(":")
            and "@" not in ln
            and "linkedin.com" not in ln.lower()
            and not any(ch.isdigit() for ch in ln)
        ):
            full_name = ln
            break

    # 5) Years of experience (NEW)
    years_experience = _infer_years_experience(text)

    return ParsedResumeContact(
        full_name=full_name,
        email=email,
        phone=phone,
        linkedin=linkedin,
        years_experience=years_experience,
    )
