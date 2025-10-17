"""create appstatus enum type

Revision ID: 0002a_create_appstatus_enum
Revises: 0002_oauth_gmail
Create Date: 2025-10-13
"""

from alembic import op

revision = "0002a_create_appstatus_enum"
down_revision = "0002_oauth_gmail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the appstatus enum type if it doesn't exist."""
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appstatus') THEN
        CREATE TYPE appstatus AS ENUM ('applied', 'interview', 'offer', 'rejected');
      END IF;
    END$$;
    """)

    # Alter the applications.status column to use the enum type
    # First check if it's currently text/varchar
    op.execute("""
    DO $$
    BEGIN
      -- Only alter if column is not already using the enum type
      IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'applications' 
        AND column_name = 'status' 
        AND data_type IN ('character varying', 'text')
      ) THEN
        ALTER TABLE applications 
        ALTER COLUMN status TYPE appstatus 
        USING status::appstatus;
      END IF;
    END$$;
    """)


def downgrade() -> None:
    """Convert status column back to text and optionally drop the enum."""
    # Convert column back to text
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'applications' 
        AND column_name = 'status'
      ) THEN
        ALTER TABLE applications 
        ALTER COLUMN status TYPE VARCHAR(64) 
        USING status::text;
      END IF;
    END$$;
    """)

    # Drop the enum type if it exists and no other columns use it
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appstatus') THEN
        DROP TYPE appstatus;
      END IF;
    END$$;
    """)
