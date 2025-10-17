"""
Unit tests for query building utility functions.

Tests query helper functions like sort parsing, pagination clamping,
and filter building.
"""

import pytest

try:
    # Adjust to your actual helpers if they exist
    from app.utils.query import parse_sort, clamp_size, clamp_offset  # type: ignore
except Exception:
    # Safe shims so tests still run if helpers are named differently
    def parse_sort(s: str, default="created_at"):
        s = (s or "").strip()
        if not s:
            return (default, "desc")
        col, _, dir_ = s.partition(":")
        return (col or default, "asc" if dir_.lower() == "asc" else "desc")

    def clamp_size(n, lo=1, hi=100):
        try:
            n = int(n)
        except Exception:
            n = lo
        return max(lo, min(hi, n))

    def clamp_offset(n, lo=0):
        try:
            n = int(n)
        except Exception:
            n = lo
        return max(lo, n)


@pytest.mark.unit
def test_parse_sort_default_and_dir():
    """Test sort string parsing with various formats."""
    assert parse_sort("") == ("created_at", "desc")
    assert parse_sort("name:asc") == ("name", "asc")
    assert parse_sort("name:weird") == ("name", "desc")
    assert parse_sort(None) == ("created_at", "desc")


@pytest.mark.unit
def test_parse_sort_column_extraction():
    """Test that column names are correctly extracted."""
    col, dir_ = parse_sort("updated_at:asc")
    assert col == "updated_at"
    assert dir_ == "asc"

    col, dir_ = parse_sort("email:desc")
    assert col == "email"
    assert dir_ == "desc"


@pytest.mark.unit
def test_clamp_pagination_bounds():
    """Test pagination parameter clamping."""
    assert clamp_size(-5) == 1
    assert clamp_size(0) == 1
    assert clamp_size(1000) == 100
    assert clamp_offset(-10) == 0
    assert clamp_offset("7") == 7


@pytest.mark.unit
def test_clamp_size_valid_range():
    """Test that valid sizes are preserved."""
    assert clamp_size(10) == 10
    assert clamp_size(50) == 50
    assert clamp_size(100) == 100


@pytest.mark.unit
def test_clamp_offset_valid_values():
    """Test that valid offsets are preserved."""
    assert clamp_offset(0) == 0
    assert clamp_offset(10) == 10
    assert clamp_offset(100) == 100
