"""Add features_json column to emails table

Revision ID: 0012_add_emails_features_json
Revises: 0011_add_emails_expires_profile
Create Date: 2025-10-10 16:27:00.000000

This migration adds the features_json column for storing extracted features
used for ML classification and email analysis. This is a JSONB column for
efficient storage and querying of semi-structured feature data.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '0012_add_emails_features_json'
down_revision = '0011_add_emails_expires_profile'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add features_json column."""
    # Add features_json column as JSONB for efficient storage and querying
    op.add_column('emails', sa.Column('features_json', JSONB, nullable=True))
    
    # Add comment for documentation
    op.execute("COMMENT ON COLUMN emails.features_json IS 'Extracted features for ML/classification (JSONB for efficient queries)'")


def downgrade() -> None:
    """Remove features_json column."""
    op.drop_column('emails', 'features_json')
