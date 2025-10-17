"""add agent_metrics_daily table for quality tracking

Revision ID: 0024_agent_metrics_daily
Revises: 0023_agent_approvals
Create Date: 2025-10-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0024_agent_metrics_daily"
down_revision = "0023_agent_approvals"
branch_labels = None
depends_on = None


def upgrade():
    """Add agent_metrics_daily table for daily quality tracking.
    
    Captures:
    - Execution metrics (runs, success/failure rates)
    - Quality metrics (scores, samples)
    - User feedback (thumbs up/down, satisfaction rate)
    - Performance metrics (latency percentiles)
    - Cost tracking
    - Invariant pass/fail counts
    - Red-team attack tracking
    """
    op.create_table(
        'agent_metrics_daily',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agent', sa.String(length=128), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        
        # Execution metrics
        sa.Column('total_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_rate', sa.Float(), nullable=True),
        
        # Quality metrics
        sa.Column('avg_quality_score', sa.Float(), nullable=True),
        sa.Column('median_quality_score', sa.Float(), nullable=True),
        sa.Column('p95_quality_score', sa.Float(), nullable=True),
        sa.Column('quality_samples', sa.Integer(), nullable=False, server_default='0'),
        
        # User feedback
        sa.Column('thumbs_up', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('thumbs_down', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('feedback_rate', sa.Float(), nullable=True),
        sa.Column('satisfaction_rate', sa.Float(), nullable=True),
        
        # Performance metrics
        sa.Column('avg_latency_ms', sa.Float(), nullable=True),
        sa.Column('median_latency_ms', sa.Float(), nullable=True),
        sa.Column('p95_latency_ms', sa.Float(), nullable=True),
        sa.Column('p99_latency_ms', sa.Float(), nullable=True),
        
        # Cost tracking
        sa.Column('total_cost_weight', sa.Float(), nullable=False, server_default='0'),
        sa.Column('avg_cost_per_run', sa.Float(), nullable=True),
        
        # Invariant tracking
        sa.Column('invariants_passed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('invariants_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_invariant_ids', postgresql.ARRAY(sa.Text()), nullable=True),
        
        # Red-team tracking
        sa.Column('redteam_attacks_detected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('redteam_attacks_missed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('redteam_false_positives', sa.Integer(), nullable=False, server_default='0'),
        
        # Breakdown by difficulty
        sa.Column('quality_by_difficulty', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes
    op.create_index('ix_agent_metrics_daily_agent', 'agent_metrics_daily', ['agent'])
    op.create_index('ix_agent_metrics_daily_date', 'agent_metrics_daily', ['date'])
    op.create_index(
        'ix_agent_metrics_daily_agent_date',
        'agent_metrics_daily',
        ['agent', 'date'],
        unique=True
    )
    op.create_index(
        'ix_agent_metrics_daily_date_desc',
        'agent_metrics_daily',
        [sa.text('date DESC')]
    )


def downgrade():
    """Remove agent_metrics_daily table."""
    op.drop_index('ix_agent_metrics_daily_date_desc', table_name='agent_metrics_daily')
    op.drop_index('ix_agent_metrics_daily_agent_date', table_name='agent_metrics_daily')
    op.drop_index('ix_agent_metrics_daily_date', table_name='agent_metrics_daily')
    op.drop_index('ix_agent_metrics_daily_agent', table_name='agent_metrics_daily')
    op.drop_table('agent_metrics_daily')
