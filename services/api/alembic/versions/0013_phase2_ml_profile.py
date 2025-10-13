"""Add ML and event fields to emails table and create profile tables

Revision ID: 0013_phase2_ml_profile
Revises: 0012_add_emails_features_json
Create Date: 2025-10-12 10:00:00.000000

This migration completes the Phase 2 ML labeling system:
- Adds event_start_at, event_location for event tracking
- Adds ml_features (JSONB) for ML feature vectors
- Adds ml_scores (JSONB) for category probability scores  
- Adds amount_cents for bill amounts
- Adds due_date for bill/invoice due dates
- Creates profile_sender_stats table for sender analytics
- Creates profile_category_stats table for category analytics
- Creates profile_interests table for user interest tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '0013_phase2_ml_profile'
down_revision = '0012_add_emails_features_json'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add ML/event fields to emails and create profile tables."""
    
    # Add new fields to emails table
    op.add_column('emails', sa.Column('event_start_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('emails', sa.Column('event_location', sa.Text(), nullable=True))
    op.add_column('emails', sa.Column('ml_features', JSONB, nullable=True))
    op.add_column('emails', sa.Column('ml_scores', JSONB, nullable=True))
    op.add_column('emails', sa.Column('amount_cents', sa.Integer(), nullable=True))
    op.add_column('emails', sa.Column('due_date', sa.Date(), nullable=True))
    
    # Create indexes for efficient queries
    op.create_index('ix_emails_event_start_at', 'emails', ['event_start_at'], unique=False)
    op.create_index('ix_emails_due_date', 'emails', ['due_date'], unique=False)
    
    # Add comments for documentation
    op.execute("COMMENT ON COLUMN emails.event_start_at IS 'Start date/time for events, webinars, meetings'")
    op.execute("COMMENT ON COLUMN emails.event_location IS 'Location/venue for events (physical or virtual URL)'")
    op.execute("COMMENT ON COLUMN emails.ml_features IS 'Extracted ML features (TF-IDF, counts, etc.)'")
    op.execute("COMMENT ON COLUMN emails.ml_scores IS 'ML model probability scores per category'")
    op.execute("COMMENT ON COLUMN emails.amount_cents IS 'Bill/invoice amount in cents (USD)'")
    op.execute("COMMENT ON COLUMN emails.due_date IS 'Due date for bills, invoices, payments'")
    
    # Create profile_sender_stats table
    op.create_table(
        'profile_sender_stats',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_email', sa.String(320), nullable=False, index=True),
        sa.Column('sender_domain', sa.String(255), nullable=False, index=True),
        sa.Column('total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('categories', JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('open_rate', sa.Float(), nullable=True),
    )
    op.create_index('ix_profile_sender_stats_user_domain', 'profile_sender_stats', 
                    ['user_email', 'sender_domain'], unique=True)
    
    # Create profile_category_stats table
    op.create_table(
        'profile_category_stats',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_email', sa.String(320), nullable=False, index=True),
        sa.Column('category', sa.String(64), nullable=False, index=True),
        sa.Column('total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_received_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_profile_category_stats_user_cat', 'profile_category_stats',
                    ['user_email', 'category'], unique=True)
    
    # Create profile_interests table
    op.create_table(
        'profile_interests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_email', sa.String(320), nullable=False, index=True),
        sa.Column('interest', sa.String(128), nullable=False, index=True),
        sa.Column('score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_profile_interests_user_interest', 'profile_interests',
                    ['user_email', 'interest'], unique=True)


def downgrade() -> None:
    """Remove ML/event fields and profile tables."""
    
    # Drop profile tables
    op.drop_table('profile_interests')
    op.drop_table('profile_category_stats')
    op.drop_table('profile_sender_stats')
    
    # Drop indexes from emails
    op.drop_index('ix_emails_due_date', table_name='emails')
    op.drop_index('ix_emails_event_start_at', table_name='emails')
    
    # Drop columns from emails
    op.drop_column('emails', 'due_date')
    op.drop_column('emails', 'amount_cents')
    op.drop_column('emails', 'ml_scores')
    op.drop_column('emails', 'ml_features')
    op.drop_column('emails', 'event_location')
    op.drop_column('emails', 'event_start_at')
