"""add gmail_tokens table for multi-user OAuth

Revision ID: 0005_add_gmail_tokens
Revises: 0004_add_source_confidence
Create Date: 2025-10-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_add_gmail_tokens"
down_revision = "0004_add_source_confidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create gmail_tokens table (if it doesn't exist)
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    
    if 'gmail_tokens' not in tables:
        op.create_table(
            "gmail_tokens",
            sa.Column("user_email", sa.String(length=255), nullable=False, primary_key=True),
            sa.Column("access_token", sa.Text(), nullable=True),
            sa.Column("refresh_token", sa.Text(), nullable=False),
            sa.Column("expiry_date", sa.BigInteger(), nullable=True, comment="milliseconds since epoch"),
            sa.Column("scope", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        
        # Create trigger to auto-update updated_at
        # Note: PostgreSQL-specific
        op.execute("""
            CREATE OR REPLACE FUNCTION update_gmail_tokens_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        op.execute("""
            CREATE TRIGGER gmail_tokens_updated_at_trigger
            BEFORE UPDATE ON gmail_tokens
            FOR EACH ROW
            EXECUTE FUNCTION update_gmail_tokens_updated_at();
        """)


def downgrade() -> None:
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS gmail_tokens_updated_at_trigger ON gmail_tokens")
    op.execute("DROP FUNCTION IF EXISTS update_gmail_tokens_updated_at()")
    
    # Drop table
    op.drop_table("gmail_tokens")
