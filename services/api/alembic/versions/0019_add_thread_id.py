"""add thread_id column to applications table

Revision ID: 0019_add_thread_id
Revises: 0018_split_fk_cycles
Create Date: 2025-10-14
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0019_add_thread_id"
down_revision = "0018_split_fk_cycles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add thread_id column to applications table if it doesn't exist."""
    # Use raw SQL with conditional logic to avoid errors if column exists
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'thread_id'
        ) THEN
            ALTER TABLE applications ADD COLUMN thread_id VARCHAR(128);
            CREATE INDEX ix_applications_thread_id ON applications (thread_id);
        END IF;
    END $$;
    """)


def downgrade() -> None:
    """Remove thread_id column from applications table."""
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'thread_id'
        ) THEN
            DROP INDEX IF EXISTS ix_applications_thread_id;
            ALTER TABLE applications DROP COLUMN thread_id;
        END IF;
    END $$;
    """)
