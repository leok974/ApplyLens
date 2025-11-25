"""Job aggregator email detection and parsing.

Detects emails from job aggregators (Indeed, LinkedIn, Handshake, ZipRecruiter)
and extracts job opportunities into structured format.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Known job aggregator domains
AGGREGATOR_DOMAINS = {
    "indeed.com",
    "linkedin.com",
    "joinhandshake.com",
    "ziprecruiter.com",
    "glassdoor.com",
    "monster.com",
    "careerbuilder.com",
    "dice.com",
}

# Subject line hints for job aggregator emails
SUBJECT_HINTS = [
    "new job",
    "job alert",
    "recommended for you",
    "jobs matching",
    "opportunities",
    "job recommendation",
    "career opportunity",
    "hiring now",
]


@dataclass
class OpportunityPayload:
    """Structured job opportunity data."""

    title: str
    company: str
    location: Optional[str] = None
    remote_flag: Optional[bool] = None
    salary_text: Optional[str] = None
    level: Optional[str] = None
    tech_stack: Optional[list[str]] = None
    apply_url: Optional[str] = None
    posted_at: Optional[datetime] = None


def is_job_aggregator_email(sender: str, subject: str) -> tuple[bool, Optional[str]]:
    """Detect if email is from a job aggregator.

    Args:
        sender: Email sender address
        subject: Email subject line

    Returns:
        (is_aggregator, source_name) tuple
    """
    sender_lower = sender.lower()
    subject_lower = subject.lower()

    # Check sender domain
    for domain in AGGREGATOR_DOMAINS:
        if domain in sender_lower:
            # Determine source name from domain
            if "indeed" in domain:
                return True, "indeed"
            elif "linkedin" in domain:
                return True, "linkedin"
            elif "handshake" in domain:
                return True, "handshake"
            elif "ziprecruiter" in domain:
                return True, "ziprecruiter"
            elif "glassdoor" in domain:
                return True, "glassdoor"
            elif "monster" in domain:
                return True, "monster"
            elif "careerbuilder" in domain:
                return True, "careerbuilder"
            elif "dice" in domain:
                return True, "dice"

    # Check subject hints as fallback
    for hint in SUBJECT_HINTS:
        if hint in subject_lower:
            logger.info(
                f"Job aggregator detected by subject hint: {hint} in '{subject}'"
            )
            return True, "unknown"

    return False, None


def extract_opportunities_from_email(
    body: str, source: str
) -> list[OpportunityPayload]:
    """Extract job opportunities from aggregator email body.

    Args:
        body: Email body text
        source: Aggregator source name (indeed, linkedin, etc.)

    Returns:
        List of extracted opportunities
    """
    if source == "indeed":
        return _extract_indeed_opportunities(body)
    elif source == "linkedin":
        return _extract_linkedin_opportunities(body)
    elif source == "handshake":
        return _extract_handshake_opportunities(body)
    elif source == "ziprecruiter":
        return _extract_ziprecruiter_opportunities(body)
    else:
        # Generic extraction for unknown sources
        return _extract_generic_opportunities(body)


def _extract_indeed_opportunities(body: str) -> list[OpportunityPayload]:
    """Extract opportunities from Indeed email."""
    opportunities = []

    # Indeed pattern: Look for job titles followed by company names
    # Pattern: Title\nCompany\nLocation
    # Example:
    # Senior Python Developer
    # Google
    # Mountain View, CA

    lines = body.split("\n")
    i = 0
    while i < len(lines) - 2:
        line = lines[i].strip()

        # Skip empty lines and common headers
        if (
            not line
            or line.lower().startswith("recommended")
            or line.lower().startswith("jobs for you")
        ):
            i += 1
            continue

        # Check if next line could be a company
        company_line = lines[i + 1].strip()
        location_line = lines[i + 2].strip() if i + 2 < len(lines) else ""

        # Basic heuristic: title is capitalized, company is short, location has comma or "Remote"
        if (
            len(line) > 10
            and len(company_line) > 2
            and len(company_line) < 100
            and (
                "," in location_line
                or "remote" in location_line.lower()
                or "hybrid" in location_line.lower()
            )
        ):
            # Try to find apply URL in next few lines
            apply_url = None
            for j in range(i, min(i + 10, len(lines))):
                if "http" in lines[j]:
                    apply_url = lines[j].strip()
                    break

            opportunities.append(
                OpportunityPayload(
                    title=line,
                    company=company_line,
                    location=location_line if location_line else None,
                    remote_flag="remote" in location_line.lower()
                    if location_line
                    else None,
                    apply_url=apply_url,
                )
            )
            i += 3
        else:
            i += 1

    logger.info(f"Extracted {len(opportunities)} opportunities from Indeed email")
    return opportunities


def _extract_linkedin_opportunities(body: str) -> list[OpportunityPayload]:
    """Extract opportunities from LinkedIn email."""
    opportunities = []

    # LinkedIn often has structured HTML with job cards
    # Look for patterns like:
    # <Job Title> at <Company>
    # or
    # <Company> is hiring: <Job Title>

    title_company_pattern = re.compile(
        r"(.+?)\s+at\s+(.+?)(?:\n|$)", re.IGNORECASE | re.MULTILINE
    )
    hiring_pattern = re.compile(
        r"(.+?)\s+is hiring:\s+(.+?)(?:\n|$)", re.IGNORECASE | re.MULTILINE
    )

    # Try "Title at Company" pattern
    for match in title_company_pattern.finditer(body):
        title = match.group(1).strip()
        company = match.group(2).strip()
        if len(title) > 5 and len(company) > 2:
            opportunities.append(
                OpportunityPayload(
                    title=title,
                    company=company,
                )
            )

    # Try "Company is hiring: Title" pattern
    for match in hiring_pattern.finditer(body):
        company = match.group(1).strip()
        title = match.group(2).strip()
        if len(title) > 5 and len(company) > 2:
            opportunities.append(
                OpportunityPayload(
                    title=title,
                    company=company,
                )
            )

    logger.info(f"Extracted {len(opportunities)} opportunities from LinkedIn email")
    return opportunities


def _extract_handshake_opportunities(body: str) -> list[OpportunityPayload]:
    """Extract opportunities from Handshake email."""
    opportunities = []

    # Handshake format is similar to Indeed
    # Use same extraction logic
    opportunities = _extract_indeed_opportunities(body)

    logger.info(f"Extracted {len(opportunities)} opportunities from Handshake email")
    return opportunities


def _extract_ziprecruiter_opportunities(body: str) -> list[OpportunityPayload]:
    """Extract opportunities from ZipRecruiter email."""
    opportunities = []

    # ZipRecruiter pattern similar to LinkedIn
    # Look for "Company - Job Title" or "Job Title - Company"
    dash_pattern = re.compile(r"(.+?)\s*-\s*(.+?)(?:\n|$)", re.MULTILINE)

    for match in dash_pattern.finditer(body):
        part1 = match.group(1).strip()
        part2 = match.group(2).strip()

        # Heuristic: shorter part is likely company, longer is title
        if len(part1) < len(part2):
            company, title = part1, part2
        else:
            title, company = part1, part2

        if len(title) > 5 and len(company) > 2 and len(company) < 100:
            opportunities.append(
                OpportunityPayload(
                    title=title,
                    company=company,
                )
            )

    logger.info(f"Extracted {len(opportunities)} opportunities from ZipRecruiter email")
    return opportunities


def _extract_generic_opportunities(body: str) -> list[OpportunityPayload]:
    """Generic opportunity extraction for unknown sources."""
    opportunities = []

    # Try multiple patterns and combine results
    opportunities.extend(_extract_indeed_opportunities(body))
    opportunities.extend(_extract_linkedin_opportunities(body))

    # Deduplicate by (title, company) tuple
    seen = set()
    unique_opps = []
    for opp in opportunities:
        key = (opp.title.lower(), opp.company.lower())
        if key not in seen:
            seen.add(key)
            unique_opps.append(opp)

    logger.info(
        f"Extracted {len(unique_opps)} unique opportunities from unknown source"
    )
    return unique_opps
