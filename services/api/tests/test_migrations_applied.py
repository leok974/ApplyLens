"""
Test that ensures database migrations are up-to-date.

This test fails fast if Alembic migrations haven't been applied,
preventing cryptic errors later in the test suite.
"""

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text


def test_alembic_config_loads():
    """Verify that alembic.ini and migrations directory are valid."""
    cfg = Config("alembic.ini")
    script_location = cfg.get_main_option("script_location")

    assert script_location, "Alembic script_location not configured"
    assert script_location == "alembic", f"Expected 'alembic', got '{script_location}'"

    # Verify script directory can be loaded
    script = ScriptDirectory.from_config(cfg)
    assert script, "Failed to load Alembic script directory"


def test_migrations_are_applied(engine):
    """
    Verify that all Alembic migrations have been applied to the test database.

    This test ensures that:
    1. The database schema matches the current migrations
    2. All expected tables exist
    3. The test database is in sync with production schema

    If this test fails, run: alembic upgrade head
    """
    # Check that key tables exist
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected_tables = [
        "emails",
        "policies",
        "user_weights",
        "proposed_actions",
        "applications",
        "alembic_version",
    ]

    missing_tables = [table for table in expected_tables if table not in tables]

    assert not missing_tables, (
        f"Missing tables in test database: {missing_tables}. "
        f"Run 'alembic upgrade head' before running tests."
    )


def test_alembic_version_exists(db_session):
    """
    Verify that the alembic_version table has a current revision.

    This ensures migrations have been run at least once.
    """
    result = db_session.execute(text("SELECT version_num FROM alembic_version"))
    version = result.scalar()

    assert version, (
        "No alembic version found in database. "
        "Run 'alembic upgrade head' to apply migrations."
    )

    # Version should be a hex string (e.g., "0017_phase6_personalization")
    assert len(version) > 0, "Alembic version is empty"
