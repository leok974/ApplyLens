"""
Phase 3.1: Safety Guardrails for LLM-Generated Application Answers

Prevents hallucinated employment, URLs, excessive length, and other issues.
"""

import re
from typing import Dict, List, Tuple

# Configuration
MAX_FIELD_CHARS = 2000
MAX_SUMMARY_CHARS = 500

# Forbidden phrases that might indicate hallucination
FORBIDDEN_PHRASES = [
    "I worked at",
    "I was employed at",
    "I currently work at",
    "My experience at",
    "During my time at",
    # Add more as needed
]

# URL patterns to strip
URL_PATTERN = re.compile(r"https?://\S+")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def sanitize_answer(text: str, field_type: str = "text") -> str:
    """
    Apply safety guardrails to a single answer.

    Args:
        text: Raw answer text from LLM
        field_type: Field semantic type (e.g. "summary", "first_name")

    Returns:
        Sanitized answer text
    """
    if text is None:
        return ""

    text = text.strip()

    # 1. Length limits
    max_len = MAX_SUMMARY_CHARS if field_type == "summary" else MAX_FIELD_CHARS
    if len(text) > max_len:
        # Trim at word boundary
        text = text[:max_len].rsplit(" ", 1)[0] + "..."

    # 2. Strip URLs (most ATS forms reject them)
    text = URL_PATTERN.sub("", text)

    # 3. Strip email addresses if not an email field
    if field_type != "email":
        text = EMAIL_PATTERN.sub("", text)

    # 4. Remove forbidden phrases (hallucination indicators)
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in text.lower():
            # Remove the phrase and surrounding sentence
            text = re.sub(
                rf"[^.!?]*{re.escape(phrase)}[^.!?]*[.!?]",
                "",
                text,
                flags=re.IGNORECASE,
            )

    # 5. Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def sanitize_answers(answers: Dict[str, str]) -> Dict[str, str]:
    """
    Apply guardrails to all answers in a dict.

    Args:
        answers: Dict mapping semantic_key to answer text

    Returns:
        Sanitized answers dict
    """
    return {
        key: sanitize_answer(value, field_type=key) for key, value in answers.items()
    }


def validate_answers(
    answers: Dict[str, str],
    required_fields: List[str],
) -> Tuple[bool, List[str]]:
    """
    Validate that all required fields have non-empty answers.

    Args:
        answers: Generated answers dict
        required_fields: List of semantic keys that must have values

    Returns:
        Tuple of (is_valid, list_of_missing_fields)
    """
    missing = [field for field in required_fields if not answers.get(field, "").strip()]

    return len(missing) == 0, missing
