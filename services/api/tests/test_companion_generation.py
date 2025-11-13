"""
Phase 3.1: Tests for LLM Generation and Guardrails
"""

from app.llm.companion_guardrails import (
    sanitize_answer,
    sanitize_answers,
    validate_answers,
)


def test_sanitize_answer_trims_long_text():
    """Ensure answers respect length limits."""
    long_text = "A" * 3000
    result = sanitize_answer(long_text, field_type="summary")

    assert len(result) <= 503  # MAX_SUMMARY_CHARS + "..."
    assert result.endswith("...")


def test_sanitize_answer_strips_urls():
    """URLs should be removed from answers."""
    text = "Check my portfolio at https://example.com for more info"
    result = sanitize_answer(text)

    assert "http" not in result
    assert "example.com" not in result
    assert "Check my portfolio" in result
    assert "for more info" in result


def test_sanitize_answer_removes_forbidden_phrases():
    """Forbidden phrases indicating hallucination should be removed."""
    text = "I worked at FakeCorp doing AI engineering. I have 5 years of experience."
    result = sanitize_answer(text)

    assert "I worked at" not in result
    assert "FakeCorp" not in result  # Whole sentence removed
    assert "I have 5 years of experience" in result


def test_sanitize_answer_removes_multiple_forbidden_phrases():
    """Multiple forbidden phrases should be removed."""
    text = "I was employed at BadCo last year. I currently work at EvilCorp. I am available."
    result = sanitize_answer(text)

    assert "I was employed at" not in result
    assert "I currently work at" not in result
    assert "BadCo" not in result
    assert "EvilCorp" not in result
    assert "I am available" in result


def test_sanitize_answer_preserves_email_for_email_fields():
    """Email addresses should be preserved for email fields."""
    text = "test@example.com"
    result = sanitize_answer(text, field_type="email")

    assert result == "test@example.com"


def test_sanitize_answer_strips_email_from_non_email_fields():
    """Email addresses should be removed from non-email fields."""
    text = "Contact me at test@example.com for details"
    result = sanitize_answer(text, field_type="summary")

    assert "@" not in result
    assert "test@example.com" not in result
    assert "Contact me at" in result
    assert "for details" in result


def test_sanitize_answer_handles_none():
    """None input should return empty string."""
    result = sanitize_answer(None)  # type: ignore

    assert result == ""


def test_sanitize_answer_cleans_whitespace():
    """Multiple spaces should be normalized."""
    text = "This  has   multiple    spaces"
    result = sanitize_answer(text)

    assert result == "This has multiple spaces"


def test_sanitize_answers_applies_to_all_fields():
    """Guardrails should apply to entire answers dict."""
    answers = {
        "summary": "Experienced engineer. I worked at BadCo last year.",
        "email": "test@example.com",
        "website": "Visit https://mysite.com",
    }

    result = sanitize_answers(answers)

    assert "I worked at" not in result["summary"]
    assert "BadCo" not in result["summary"]
    assert result["email"] == "test@example.com"  # Email preserved
    assert "https://" not in result["website"]
    assert "mysite.com" not in result["website"]


def test_sanitize_answers_preserves_safe_content():
    """Safe answers should pass through unchanged."""
    answers = {
        "first_name": "John",
        "last_name": "Doe",
        "summary": "Experienced software engineer with 5 years of Python development.",
    }

    result = sanitize_answers(answers)

    assert result == answers


def test_validate_answers_checks_required_fields():
    """Validation should detect missing required fields."""
    answers = {
        "first_name": "John",
        "last_name": "",
        "email": "john@example.com",
    }

    is_valid, missing = validate_answers(
        answers, required_fields=["first_name", "last_name", "email"]
    )

    assert not is_valid
    assert "last_name" in missing
    assert "first_name" not in missing
    assert "email" not in missing


def test_validate_answers_passes_when_all_present():
    """Validation should pass when all required fields have values."""
    answers = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
    }

    is_valid, missing = validate_answers(
        answers, required_fields=["first_name", "last_name", "email"]
    )

    assert is_valid
    assert missing == []


def test_validate_answers_treats_whitespace_as_missing():
    """Whitespace-only values should be treated as missing."""
    answers = {
        "first_name": "   ",
        "last_name": "Doe",
    }

    is_valid, missing = validate_answers(
        answers, required_fields=["first_name", "last_name"]
    )

    assert not is_valid
    assert "first_name" in missing


def test_validate_answers_handles_missing_keys():
    """Missing keys should be detected."""
    answers = {
        "first_name": "John",
    }

    is_valid, missing = validate_answers(
        answers, required_fields=["first_name", "last_name", "email"]
    )

    assert not is_valid
    assert "last_name" in missing
    assert "email" in missing


def test_combined_url_and_phrase_guardrails():
    """Multiple guardrails should be applied together."""
    text = "I worked at EvilCorp https://evil.com doing bad things. I am a great candidate!"
    result = sanitize_answer(text)

    # Both guardrails applied
    assert "I worked at" not in result
    assert "https://" not in result
    assert "EvilCorp" not in result
    assert "evil.com" not in result

    # Safe content preserved
    assert "I am a great candidate" in result


def test_sanitize_answer_case_insensitive_phrase_matching():
    """Forbidden phrases should match case-insensitively."""
    text = "I WORKED AT BigCorp. I WAS EMPLOYED AT TechCo."
    result = sanitize_answer(text)

    assert "BigCorp" not in result
    assert "TechCo" not in result
    assert "WORKED" not in result
    assert "EMPLOYED" not in result
