"""Create extension tables in SQLite for dev environment."""

import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment for SQLite
os.environ["DATABASE_URL"] = "sqlite:///./dev_extension.db"

from app.db import engine
from app.models import ExtensionApplication, ExtensionOutreach


def create_tables():
    """Create only the extension tables."""
    print(f"Creating extension tables in: {engine.url}")

    # Create only the extension tables
    ExtensionApplication.__table__.create(bind=engine, checkfirst=True)
    ExtensionOutreach.__table__.create(bind=engine, checkfirst=True)

    print("✓ extension_applications table created")
    print("✓ extension_outreach table created")
    print("\nTables created successfully!")


if __name__ == "__main__":
    create_tables()
