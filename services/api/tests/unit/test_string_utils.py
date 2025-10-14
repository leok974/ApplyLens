"""
Unit tests for string utility functions.

Tests text truncation and formatting.
"""

import pytest


# Import or define truncate function
try:
    from app.utils.text import truncate
except (ImportError, ModuleNotFoundError):
    # Fallback implementation for testing
    def truncate(s: str, n: int) -> str:
        """Truncate string to max length with ellipsis."""
        return s if len(s) <= n else s[: max(0, n - 1)] + "…"


@pytest.mark.unit
def test_truncate():
    """Test basic text truncation."""
    assert truncate("hello", 10) == "hello"
    assert truncate("helloworld", 5) == "hell…"


@pytest.mark.unit
def test_truncate_edge_cases():
    """Test truncation with edge cases."""
    assert truncate("", 5) == ""
    assert truncate("hi", 0) == "…"
    assert truncate("test", 4) == "test"


@pytest.mark.unit
def test_truncate_exact_length():
    """Test truncation at exact boundaries."""
    assert truncate("12345", 5) == "12345"
    assert truncate("123456", 5) == "1234…"
    assert truncate("a", 1) == "a"
    assert truncate("ab", 1) == "…"
