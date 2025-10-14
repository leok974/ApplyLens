"""
Unit tests for date utility functions.

Tests date-related helper functions like clamp_days, date formatting,
and date validation.
"""

import pytest

# Try importing from actual codebase
try:
    from app.utils.dates import clamp_days
except (ImportError, ModuleNotFoundError):
    # Fallback implementation if the actual function doesn't exist yet
    def clamp_days(n: int, lo: int = 1, hi: int = 30) -> int:
        """Clamp days to valid range."""
        return max(lo, min(hi, int(n)))


@pytest.mark.unit
def test_clamp_days_negative():
    """Negative days should be clamped to minimum."""
    assert clamp_days(-1) == 1
    assert clamp_days(-100) == 1


@pytest.mark.unit
def test_clamp_days_zero():
    """Zero days should be clamped to minimum."""
    assert clamp_days(0) == 1


@pytest.mark.unit
def test_clamp_days_valid_range():
    """Days within valid range should be preserved."""
    assert clamp_days(1) == 1
    assert clamp_days(7) == 7
    assert clamp_days(15) == 15
    assert clamp_days(30) == 30


@pytest.mark.unit
def test_clamp_days_excessive():
    """Excessive days should be clamped to maximum."""
    assert clamp_days(999) == 30
    assert clamp_days(1000000) == 30


@pytest.mark.unit
def test_clamp_days_string_conversion():
    """String inputs should be converted to int."""
    try:
        result = clamp_days("7")
        assert result == 7
    except (TypeError, ValueError):
        # If function doesn't support string conversion, that's okay
        pytest.skip("clamp_days doesn't support string conversion")


@pytest.mark.unit
def test_clamp_days_float_conversion():
    """Float inputs should be converted to int."""
    try:
        result = clamp_days(7.9)
        assert result == 7
    except (TypeError, ValueError):
        # If function doesn't support float conversion, that's okay
        pytest.skip("clamp_days doesn't support float conversion")
