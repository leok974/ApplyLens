"""Create approvals_proposed table

Revision ID: 0008_approvals_proposed
Revises: 0006_reply_metrics
Create Date: 2025-10-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0008_approvals_proposed'
down_revision: Union[str, None] = '0006_reply_metrics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create approvals_proposed table for approval workflow."""
    op.create_table(
        'approvals_proposed',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('email_id', sa.Text(), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('policy_id', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='proposed'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        comment='Approval workflow: proposed actions from policy engine'
    )
    
    # Indexes for efficient querying
    op.create_index(
        'ix_approvals_proposed_status_policy',
        'approvals_proposed',
        ['status', 'policy_id']
    )
    op.create_index(
        'ix_approvals_proposed_email_id',
        'approvals_proposed',
        ['email_id']
    )
    op.create_index(
        'ix_approvals_proposed_created_at',
        'approvals_proposed',
        ['created_at']
    )


def downgrade() -> None:
    """Drop approvals_proposed table and indexes."""
    op.drop_index('ix_approvals_proposed_created_at', table_name='approvals_proposed')
    op.drop_index('ix_approvals_proposed_email_id', table_name='approvals_proposed')
    op.drop_index('ix_approvals_proposed_status_policy', table_name='approvals_proposed')
    op.drop_table('approvals_proposed')
