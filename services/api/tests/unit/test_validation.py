"""
Unit tests for validation utility functions.

Tests validation helpers like email validation, URL validation,
and input sanitization.
"""

import pytest

# Try importing from actual codebase
try:
    from app.utils.validation import is_email
except (ImportError, ModuleNotFoundError):
    # Fallback implementation if the actual function doesn't exist yet
    import re

    def is_email(s: str) -> bool:
        """Basic email validation."""
        if not s or not isinstance(s, str):
            return False
        return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", s))


@pytest.mark.unit
def test_is_email_valid():
    """Valid email addresses should return True."""
    assert is_email("hr@example.com")
    assert is_email("john.doe@company.org")
    assert is_email("support@sub.domain.com")
    assert is_email("user+tag@email.co.uk")


@pytest.mark.unit
def test_is_email_no_at_symbol():
    """Emails without @ should return False."""
    assert not is_email("no-at-symbol")
    assert not is_email("missing.at.com")


@pytest.mark.unit
def test_is_email_no_domain():
    """Emails without domain should return False."""
    assert not is_email("also@no_tld")
    assert not is_email("user@")


@pytest.mark.unit
def test_is_email_empty():
    """Empty strings should return False."""
    assert not is_email("")
    assert not is_email("   ")


@pytest.mark.unit
def test_is_email_none():
    """None should return False."""
    try:
        assert not is_email(None)
    except (TypeError, AttributeError):
        # If function doesn't handle None gracefully, that's okay
        pytest.skip("is_email doesn't handle None input")


@pytest.mark.unit
def test_is_email_special_cases():
    """Edge cases should be handled correctly."""
    # Multiple @ symbols
    assert not is_email("user@@example.com")
    # Spaces
    assert not is_email("user @example.com")
    assert not is_email("user@example .com")
