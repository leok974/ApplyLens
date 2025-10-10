"""Add risk_score column to emails table

Revision ID: 0010_add_emails_risk_score
Revises: 0009_add_emails_category
Create Date: 2025-10-10 16:10:00.000000

This migration adds the risk_score column to track email security/spam risk.
The column is indexed for efficient queries and initialized to 0 as a baseline.

Risk score is a float 0-100 where:
- 0 = trusted/safe
- 100 = high risk/suspicious
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0010_add_emails_risk_score'
down_revision = '0009_add_emails_category'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add risk_score column with index and initialize to 0."""
    # Add risk_score column
    op.add_column('emails', sa.Column('risk_score', sa.Float(), nullable=True))
    
    # Create index for efficient queries
    op.create_index('ix_emails_risk_score', 'emails', ['risk_score'], unique=False)
    
    # Initialize to 0 as baseline (neutral/unknown risk)
    # This provides a cheap baseline that can be updated by risk calculation jobs
    op.execute("UPDATE emails SET risk_score = 0 WHERE risk_score IS NULL")


def downgrade() -> None:
    """Remove risk_score column and index."""
    op.drop_index('ix_emails_risk_score', table_name='emails')
    op.drop_column('emails', 'risk_score')
