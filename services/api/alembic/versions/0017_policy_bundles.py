"""0017_policy_bundles

Revision ID: 0017_policy_bundles
Revises: 0016_incidents
Create Date: 2025-10-17 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0017_policy_bundles'
down_revision: Union[str, None] = '0016_incidents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create policy_bundles table."""
    op.create_table(
        'policy_bundles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('version', sa.String(length=16), nullable=False),
        sa.Column('rules', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('notes', sa.String(length=512), nullable=True),
        sa.Column('created_by', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('canary_pct', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('activated_by', sa.String(length=128), nullable=True),
        sa.Column('approval_id', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(length=128), nullable=True),
        sa.Column('source_signature', sa.String(length=256), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version')
    )
    
    # Create indexes
    op.create_index('ix_policy_bundles_active', 'policy_bundles', ['active'])
    op.create_index('ix_policy_bundles_version', 'policy_bundles', ['version'])
    op.create_index('ix_policy_bundles_created_at', 'policy_bundles', ['created_at'])


def downgrade() -> None:
    """Drop policy_bundles table."""
    op.drop_index('ix_policy_bundles_created_at', table_name='policy_bundles')
    op.drop_index('ix_policy_bundles_version', table_name='policy_bundles')
    op.drop_index('ix_policy_bundles_active', table_name='policy_bundles')
    op.drop_table('policy_bundles')
