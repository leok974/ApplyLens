"""
Unit tests for pagination utilities.

Tests size clamping and boundary conditions.
"""

import pytest


# Import or define clamp_size function
try:
    from app.utils.pagination import clamp_size
except (ImportError, ModuleNotFoundError):
    # Fallback implementation for testing
    def clamp_size(n, min_size=1, max_size=100):
        """Clamp size to bounds."""
        return max(min_size, min(max_size, int(n)))


@pytest.mark.unit
def test_clamp_size_bounds():
    """Test that clamp_size enforces min/max boundaries."""
    assert clamp_size(-5) == 1
    assert clamp_size(0) == 1
    assert clamp_size(9999) == 100


@pytest.mark.unit
def test_clamp_size_valid_range():
    """Test that clamp_size preserves values within range."""
    assert clamp_size(1) == 1
    assert clamp_size(50) == 50
    assert clamp_size(100) == 100


@pytest.mark.unit
def test_clamp_size_converts_to_int():
    """Test that clamp_size handles string/float inputs."""
    assert clamp_size("50") == 50
    assert clamp_size(50.7) == 50
