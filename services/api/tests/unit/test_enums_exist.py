"""
Test that PostgreSQL enum types exist in the database.

This ensures that Alembic migrations have properly created the required enum types
(appstatus, actiontype) before they are used in table columns.
"""

import pytest
import sqlalchemy as sa
from sqlalchemy import text

from app.settings import settings


@pytest.mark.unit
def test_pg_enums_exist(engine):
    """
    Verify that required PostgreSQL enum types exist in the database.
    
    This test catches regressions where enum types are referenced in migrations
    before being created, which causes "type does not exist" errors.
    
    Required enums:
    - appstatus: Used in applications.status column
    - actiontype: Used in actions tables
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT typname FROM pg_type WHERE typtype = 'e' ORDER BY typname")
        )
        enum_names = {row[0] for row in result}
    
    # Check that critical enum types exist
    required_enums = {"appstatus", "actiontype"}
    missing_enums = required_enums - enum_names
    
    assert not missing_enums, (
        f"Missing required enum types: {missing_enums}. "
        f"Found enums: {sorted(enum_names)}. "
        "Ensure Alembic migrations 0002a_create_appstatus_enum and "
        "0002b_create_actiontype_enum have run successfully."
    )
    
    # For debugging, log all found enums
    print(f"✓ Found {len(enum_names)} enum types: {sorted(enum_names)}")
