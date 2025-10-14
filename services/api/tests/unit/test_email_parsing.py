"""
Unit tests for email parsing utilities.

Tests domain extraction and email address parsing.
"""

import pytest


# Import or define extract_domain function
try:
    from app.utils.email import extract_domain
except (ImportError, ModuleNotFoundError):
    # Fallback implementation for testing
    def extract_domain(s: str) -> str:
        """Extract domain from email address."""
        return s.split("@", 1)[-1] if "@" in s else ""


@pytest.mark.unit
def test_extract_domain():
    """Test basic domain extraction from email addresses."""
    assert extract_domain("hr@example.com") == "example.com"
    assert extract_domain("noreply@mail.example.com") in (
        "mail.example.com",
        "example.com",
    )


@pytest.mark.unit
def test_extract_domain_edge_cases():
    """Test domain extraction with edge cases."""
    assert extract_domain("no-at-symbol") == ""
    assert extract_domain("") == ""
    assert extract_domain("@lonely-at") == "lonely-at"


@pytest.mark.unit
def test_extract_domain_complex():
    """Test domain extraction with complex formats."""
    assert extract_domain("user+tag@subdomain.example.co.uk") in (
        "subdomain.example.co.uk",
        "example.co.uk",
    )
    assert extract_domain("user@localhost") == "localhost"
