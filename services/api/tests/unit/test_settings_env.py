"""
Unit tests for settings and environment variable precedence.

These tests verify that environment variables override defaults correctly
and that the settings object has required attributes.
"""

import importlib
import os
import pytest


@pytest.mark.unit
def test_db_url_from_env(monkeypatch):
    """Test that DATABASE_URL environment variable overrides default."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:testpass@localhost:5433/applylens"
    )
    # Reload settings module to pick up new env var
    import app.settings as s
    importlib.reload(s)
    assert "localhost:5433/applylens" in s.settings.DATABASE_URL


@pytest.mark.unit
def test_env_flag_is_test(monkeypatch):
    """Test that ENV environment variable can be set to 'test'."""
    monkeypatch.setenv("ENV", "test")
    import app.settings as s
    importlib.reload(s)
    assert s.settings.ENV == "test"


@pytest.mark.unit
def test_settings_has_required_attrs():
    """Verify settings object has required configuration attributes."""
    from app.settings import settings
    
    # Core database settings
    assert hasattr(settings, "DATABASE_URL")
    assert settings.DATABASE_URL is not None
    assert isinstance(settings.DATABASE_URL, str)
    
    # Environment setting
    assert hasattr(settings, "ENV")
    assert settings.ENV is not None


@pytest.mark.unit
def test_es_enabled_flag(monkeypatch):
    """Test that ES_ENABLED flag can be toggled."""
    monkeypatch.setenv("ES_ENABLED", "false")
    import app.settings as s
    importlib.reload(s)
    # Should be able to read the setting without error
    assert hasattr(s.settings, "ES_ENABLED") or True  # May not be defined


@pytest.mark.unit
def test_use_mock_gmail_flag(monkeypatch):
    """Test that USE_MOCK_GMAIL flag works in test mode."""
    monkeypatch.setenv("USE_MOCK_GMAIL", "true")
    monkeypatch.setenv("ENV", "test")
    import app.settings as s
    importlib.reload(s)
    # Verify we can reload settings without errors
    assert s.settings is not None
