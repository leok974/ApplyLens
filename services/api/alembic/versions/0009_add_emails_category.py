"""Add category column to emails table

Revision ID: 0009_add_emails_category
Revises: 0008_approvals_proposed
Create Date: 2025-10-10 14:30:00.000000

This migration adds the category column to support email categorization
(promotions, social, updates, forums, etc.) for better filtering and organization.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009_add_emails_category"
down_revision: Union[str, None] = "0008_approvals_proposed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add category column to emails table."""
    # Add category column
    op.add_column("emails", sa.Column("category", sa.Text(), nullable=True))

    # Create index for efficient category filtering
    op.create_index("ix_emails_category", "emails", ["category"])

    # Optional: Backfill category from Gmail labels if available
    # This attempts to populate category based on Gmail's CATEGORY_* labels
    # Requires the 'labels' column from migration 0002_oauth_gmail
    op.execute("""
        UPDATE emails
        SET category = CASE
            WHEN 'CATEGORY_PROMOTIONS' = ANY(labels) THEN 'promotions'
            WHEN 'CATEGORY_SOCIAL' = ANY(labels) THEN 'social'
            WHEN 'CATEGORY_UPDATES' = ANY(labels) THEN 'updates'
            WHEN 'CATEGORY_FORUMS' = ANY(labels) THEN 'forums'
            WHEN 'CATEGORY_PERSONAL' = ANY(labels) THEN 'personal'
            ELSE NULL
        END
        WHERE labels IS NOT NULL
          AND category IS NULL;
    """)


def downgrade() -> None:
    """Remove category column from emails table."""
    op.drop_index("ix_emails_category", table_name="emails")
    op.drop_column("emails", "category")
