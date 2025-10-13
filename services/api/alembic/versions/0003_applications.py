"""update applications status values and add fields

Revision ID: 0003_applications
Revises: 0002b_create_actiontype_enum
Create Date: 2025-10-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_applications"
down_revision = "0002b_create_actiontype_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new status values to existing enum
    op.execute("ALTER TYPE appstatus ADD VALUE IF NOT EXISTS 'hr_screen'")
    op.execute("ALTER TYPE appstatus ADD VALUE IF NOT EXISTS 'on_hold'")
    op.execute("ALTER TYPE appstatus ADD VALUE IF NOT EXISTS 'ghosted'")
    
    # Add new columns to applications table
    op.add_column("applications", sa.Column("gmail_thread_id", sa.String(length=128), nullable=True))
    op.add_column("applications", sa.Column("last_email_snippet", sa.Text(), nullable=True))
    
    # Create index on gmail_thread_id
    op.create_index("ix_applications_gmail_thread", "applications", ["gmail_thread_id"])


def downgrade() -> None:
    # Drop index
    op.drop_index("ix_applications_gmail_thread", table_name="applications")
    
    # Drop columns
    op.drop_column("applications", "last_email_snippet")
    op.drop_column("applications", "gmail_thread_id")
    
    # Note: Cannot remove enum values in PostgreSQL easily

