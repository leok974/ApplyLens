"""Schema version guard for database migrations.

This module provides utilities to ensure the database schema is at a minimum
required version before running operations that depend on specific columns or tables.

Usage:
    from app.utils.schema_guard import require_min_migration, check_column_exists
    
    # At the start of a long-running job
    require_min_migration("0009_add_emails_category")
    
    # Or check specific columns
    if not check_column_exists("emails", "category"):
        raise RuntimeError("emails.category column is missing")
"""
from typing import Optional
from sqlalchemy import text, inspect
from app.db import engine


def get_current_migration() -> Optional[str]:
    """Get the current Alembic migration version from the database.
    
    Returns:
        str: Current migration version (e.g., "0009_add_emails_category")
        None: If alembic_version table doesn't exist
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"Warning: Could not read alembic_version: {e}")
        return None


def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a specific column exists in a table.
    
    Args:
        table_name: Name of the table
        column_name: Name of the column
        
    Returns:
        bool: True if column exists, False otherwise
    """
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        print(f"Warning: Could not inspect table {table_name}: {e}")
        return False


def require_min_migration(min_version: str, friendly_name: Optional[str] = None) -> None:
    """Require database to be at minimum migration version.
    
    Raises RuntimeError if the database is below the required version.
    
    Args:
        min_version: Minimum required migration version (e.g., "0009_add_emails_category")
        friendly_name: Human-readable name for the migration (optional)
        
    Raises:
        RuntimeError: If database is below required version
        
    Example:
        require_min_migration("0009_add_emails_category", "emails.category column")
    """
    current = get_current_migration()
    
    if current is None:
        raise RuntimeError(
            "Cannot determine database migration version. "
            "alembic_version table may not exist."
        )
    
    # Simple string comparison works for our sequential versioning scheme
    # e.g., "0008" < "0009"
    if current < min_version:
        msg = (
            f"Database schema is too old. "
            f"Current: {current}, Required: {min_version}"
        )
        if friendly_name:
            msg += f" ({friendly_name})"
        msg += (
            "\n\n"
            "Please run migrations:\n"
            "  cd services/api\n"
            "  alembic upgrade head\n"
            "\n"
            "Or in Docker:\n"
            "  cd infra\n"
            "  docker-compose exec api alembic upgrade head"
        )
        raise RuntimeError(msg)
    
    print(f"✓ Schema version check passed: {current} >= {min_version}")


def require_columns(table_name: str, *column_names: str) -> None:
    """Require specific columns to exist in a table.
    
    Raises RuntimeError if any column is missing.
    
    Args:
        table_name: Name of the table
        *column_names: One or more column names to check
        
    Raises:
        RuntimeError: If any column is missing
        
    Example:
        require_columns("emails", "category", "risk_score", "expires_at")
    """
    missing = []
    for col in column_names:
        if not check_column_exists(table_name, col):
            missing.append(col)
    
    if missing:
        raise RuntimeError(
            f"Missing required columns in {table_name}: {', '.join(missing)}\n"
            f"\n"
            f"These columns may be added by running:\n"
            f"  cd services/api\n"
            f"  alembic upgrade head"
        )
    
    print(f"✓ Column check passed: {table_name}.{', '.join(column_names)}")


def get_migration_info() -> dict:
    """Get detailed information about database migrations.
    
    Returns:
        dict: Information about current migration, available columns, etc.
    """
    info = {
        "current_migration": get_current_migration(),
        "tables": {},
    }
    
    try:
        inspector = inspect(engine)
        for table_name in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            info["tables"][table_name] = {
                "columns": columns,
                "indexes": [idx['name'] for idx in inspector.get_indexes(table_name)],
            }
    except Exception as e:
        info["error"] = str(e)
    
    return info


if __name__ == "__main__":
    """Print current migration info when run as a script."""
    import json
    
    print("Database Migration Info")
    print("=" * 60)
    
    info = get_migration_info()
    
    print(f"\nCurrent Migration: {info['current_migration']}")
    print("\nTables and Columns:")
    print("-" * 60)
    
    for table_name, table_info in info.get("tables", {}).items():
        print(f"\n{table_name}:")
        print(f"  Columns: {', '.join(table_info['columns'])}")
        if table_info['indexes']:
            print(f"  Indexes: {', '.join(table_info['indexes'])}")
    
    if "error" in info:
        print(f"\n⚠ Error: {info['error']}")
