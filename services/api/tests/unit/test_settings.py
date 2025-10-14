"""
Unit tests for settings and environment variable precedence.
"""

import importlib


def test_db_url_from_env(monkeypatch):
    """Test that DATABASE_URL environment variable overrides default."""
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/applylens"
    )

    # Reload settings module to pick up env
    import app.settings as s

    importlib.reload(s)

    assert s.settings.DATABASE_URL.endswith("@localhost:5433/applylens")


def test_settings_has_required_attrs():
    """Verify settings object has required configuration attributes."""
    from app.settings import settings

    # Database settings
    assert hasattr(settings, "DATABASE_URL")

    # Basic sanity checks
    assert settings.DATABASE_URL is not None
    assert isinstance(settings.DATABASE_URL, str)
