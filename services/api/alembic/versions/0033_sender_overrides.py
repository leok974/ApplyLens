"""add user_sender_overrides table

Revision ID: 0033_sender_overrides
Revises: 0032_encryption_keys
Create Date: 2025-10-25

Schema changes:
1. Create `user_sender_overrides` table for sender-level mute/safe preferences
2. Unique constraint on (user_id, sender) - one override per user per sender
3. Supports both full email addresses and domain wildcards (@example.com)

Features:
- OR semantics: once muted/safe, stays that way until deleted
- Indexed for fast lookups during email ingestion and triage
- Adaptive classification: mark_safe automatically creates override
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0033_sender_overrides'
down_revision = '0032_encryption_keys'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_sender_overrides',
        sa.Column('id', sa.String(length=36), nullable=False, comment='UUID as string'),
        sa.Column('user_id', sa.String(length=255), nullable=False, index=True),
        sa.Column('sender', sa.String(length=512), nullable=False, index=True, comment='Full email or @domain.com'),
        sa.Column('muted', sa.Boolean(), nullable=False, server_default='false', comment='User muted this sender'),
        sa.Column('safe', sa.Boolean(), nullable=False, server_default='false', comment='User marked sender safe'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Unique constraint: one override per user per sender
    op.create_index(
        'idx_user_sender_unique',
        'user_sender_overrides',
        ['user_id', 'sender'],
        unique=True,
    )
    
    # Index for fast user lookups (list all overrides for user)
    op.create_index('ix_sender_overrides_user_id', 'user_sender_overrides', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_sender_overrides_user_id', table_name='user_sender_overrides')
    op.drop_index('idx_user_sender_unique', table_name='user_sender_overrides')
    op.drop_table('user_sender_overrides')
