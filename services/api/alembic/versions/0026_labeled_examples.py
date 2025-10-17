"""add labeled_examples table for active learning

Revision ID: 0026_labeled_examples
Revises: 0025_runtime_settings
Create Date: 2025-10-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0026_labeled_examples"
down_revision = "0025_runtime_settings"
branch_labels = None
depends_on = None


def upgrade():
    """Add labeled_examples table for active learning.
    
    Stores labeled training data from:
    - Agent approvals (user decisions)
    - Feedback API (thumbs up/down)
    - Gold sets (curated examples)
    - Synthetic tasks (generated examples)
    """
    op.create_table(
        'labeled_examples',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agent', sa.String(length=64), nullable=False),
        sa.Column('key', sa.String(length=256), nullable=False),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('label', sa.String(length=64), nullable=False),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('source_id', sa.String(length=128), nullable=True),
        sa.Column('version', sa.String(length=16), nullable=False, server_default='v1'),
        sa.Column('confidence', sa.Integer(), nullable=True),
        sa.Column('notes', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for efficient queries
    op.create_index('ix_labeled_examples_agent', 'labeled_examples', ['agent'])
    op.create_index('ix_labeled_examples_key', 'labeled_examples', ['key'])
    op.create_index('ix_labeled_examples_label', 'labeled_examples', ['label'])
    op.create_index('ix_labeled_examples_source', 'labeled_examples', ['source'])
    op.create_index('ix_labeled_examples_agent_source', 'labeled_examples', ['agent', 'source'])
    op.create_index('ix_labeled_examples_agent_label', 'labeled_examples', ['agent', 'label'])
    op.create_index('ix_labeled_examples_created_at_desc', 'labeled_examples', [sa.text('created_at DESC')])


def downgrade():
    """Remove labeled_examples table."""
    op.drop_index('ix_labeled_examples_created_at_desc', table_name='labeled_examples')
    op.drop_index('ix_labeled_examples_agent_label', table_name='labeled_examples')
    op.drop_index('ix_labeled_examples_agent_source', table_name='labeled_examples')
    op.drop_index('ix_labeled_examples_source', table_name='labeled_examples')
    op.drop_index('ix_labeled_examples_label', table_name='labeled_examples')
    op.drop_index('ix_labeled_examples_key', table_name='labeled_examples')
    op.drop_index('ix_labeled_examples_agent', table_name='labeled_examples')
    op.drop_table('labeled_examples')
