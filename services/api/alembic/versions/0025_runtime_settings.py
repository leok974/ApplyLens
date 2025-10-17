"""add runtime_settings table for canary controls

Revision ID: 0025_runtime_settings
Revises: 0024_agent_metrics_daily
Create Date: 2025-10-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0025_runtime_settings"
down_revision = "0024_agent_metrics_daily"
branch_labels = None
depends_on = None


def upgrade():
    """Add runtime_settings table for dynamic configuration.
    
    Singleton table (single row) stores:
    - Planner canary percentage
    - Planner kill switch
    - Feature flags
    - Audit trail (updated_by, update_reason)
    """
    op.create_table(
        'runtime_settings',
        sa.Column('id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('planner_canary_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('planner_kill_switch', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('feature_flags', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.Column('update_reason', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insert default row
    op.execute("""
        INSERT INTO runtime_settings (id, planner_canary_pct, planner_kill_switch, feature_flags, updated_by, update_reason)
        VALUES (1, 0.0, false, '{}', 'system', 'initial_setup')
    """)


def downgrade():
    """Remove runtime_settings table."""
    op.drop_table('runtime_settings')
