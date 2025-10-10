"""Add expires_at and profile_tags columns to emails table

Revision ID: 0011_add_emails_expires_profile
Revises: 0010_add_emails_risk_score
Create Date: 2025-10-10 16:25:00.000000

This migration adds the remaining email automation system fields:
- expires_at: DateTime field for time-sensitive content (bill due dates, promo end dates, event dates)
- profile_tags: Array field for user-specific tags for personalization

Both columns are indexed for efficient queries.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


# revision identifiers, used by Alembic.
revision = '0011_add_emails_expires_profile'
down_revision = '0010_add_emails_risk_score'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add expires_at and profile_tags columns with indexes."""
    # Add expires_at column
    op.add_column('emails', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add profile_tags column
    op.add_column('emails', sa.Column('profile_tags', ARRAY(sa.Text), nullable=True))
    
    # Create indexes for efficient queries
    op.create_index('ix_emails_expires_at', 'emails', ['expires_at'], unique=False)
    
    # Add comments for documentation
    op.execute("COMMENT ON COLUMN emails.expires_at IS 'When email content expires (e.g., bill due date, promo end date, event date)'")
    op.execute("COMMENT ON COLUMN emails.profile_tags IS 'User-specific tags for email personalization and organization'")


def downgrade() -> None:
    """Remove expires_at and profile_tags columns and indexes."""
    op.drop_index('ix_emails_expires_at', table_name='emails')
    op.drop_column('emails', 'profile_tags')
    op.drop_column('emails', 'expires_at')
