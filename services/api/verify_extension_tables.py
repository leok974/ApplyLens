"""Verify extension tables in SQLite."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "dev_extension.db"


def verify_tables():
    """Check that extension tables exist with correct schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"📋 All tables in {db_path.name}:")
    for table in tables:
        print(f"  - {table}")

    print("\n" + "=" * 60)

    # Check extension_applications
    if "extension_applications" in tables:
        print("\n✓ extension_applications table:")
        cursor.execute("PRAGMA table_info('extension_applications');")
        for row in cursor.fetchall():
            print(
                f"  {row[1]:20} {row[2]:15} {'NOT NULL' if row[3] else 'NULL':10} {f'DEFAULT {row[4]}' if row[4] else ''}"
            )
    else:
        print("\n✗ extension_applications table NOT FOUND")

    print("\n" + "=" * 60)

    # Check extension_outreach
    if "extension_outreach" in tables:
        print("\n✓ extension_outreach table:")
        cursor.execute("PRAGMA table_info('extension_outreach');")
        for row in cursor.fetchall():
            print(
                f"  {row[1]:20} {row[2]:15} {'NOT NULL' if row[3] else 'NULL':10} {f'DEFAULT {row[4]}' if row[4] else ''}"
            )
    else:
        print("\n✗ extension_outreach table NOT FOUND")

    conn.close()


if __name__ == "__main__":
    verify_tables()
