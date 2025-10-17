"""create actiontype enum type

Revision ID: 0002b_create_actiontype_enum
Revises: 0002a_create_appstatus_enum
Create Date: 2025-10-13
"""

from alembic import op

revision = "0002b_create_actiontype_enum"
down_revision = "0002a_create_appstatus_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the actiontype enum type if it doesn't exist."""
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'actiontype') THEN
        CREATE TYPE actiontype AS ENUM (
            'label_email',
            'archive_email',
            'move_to_folder',
            'unsubscribe_via_header',
            'create_calendar_event',
            'create_task',
            'block_sender',
            'quarantine_attachment'
        );
      END IF;
    END$$;
    """)


def downgrade() -> None:
    """Drop the actiontype enum type if it exists and no columns depend on it."""
    # Note: In practice, we keep enum types since columns may depend on them.
    # If you need to drop it, first convert all columns back to text.
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'actiontype') THEN
        -- Uncomment if you need to drop the type:
        -- ALTER TABLE actions ALTER COLUMN action TYPE text USING action::text;
        -- ALTER TABLE proposed_actions ALTER COLUMN action TYPE text USING action::text;
        -- DROP TYPE actiontype;
        NULL;
      END IF;
    END$$;
    """)
