"""add agent_audit_log table for agent execution tracking

Revision ID: 0022_agent_audit_log
Revises: 0021_applications_catchup
Create Date: 2025-10-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0022_agent_audit_log"
down_revision = "0021_applications_catchup"
branch_labels = None
depends_on = None


def upgrade():
    """Add agent_audit_log table for tracking agent executions.
    
    Stores:
    - Run metadata (run_id, agent name, objective)
    - Execution status and timing
    - Plans and artifacts (JSONB)
    - Error messages
    - User attribution
    """
    op.create_table(
        'agent_audit_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=128), nullable=False),
        sa.Column('agent', sa.String(length=128), nullable=False),
        sa.Column('objective', sa.String(length=512), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        
        # Timestamps
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        
        # Execution details
        sa.Column('plan', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('artifacts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.String(length=2048), nullable=True),
        
        # Metadata
        sa.Column('user_email', sa.String(length=320), nullable=True),
        sa.Column('dry_run', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for common queries
    op.create_index('ix_agent_audit_log_run_id', 'agent_audit_log', ['run_id'], unique=True)
    op.create_index('ix_agent_audit_log_agent', 'agent_audit_log', ['agent'])
    op.create_index('ix_agent_audit_log_status', 'agent_audit_log', ['status'])
    op.create_index('ix_agent_audit_log_user_email', 'agent_audit_log', ['user_email'])
    op.create_index('ix_agent_audit_log_started_at', 'agent_audit_log', ['started_at'])
    
    # Composite indexes for common queries
    op.create_index('ix_agent_audit_log_agent_status', 'agent_audit_log', ['agent', 'status'])
    op.create_index(
        'ix_agent_audit_log_started_at_desc',
        'agent_audit_log',
        [sa.text('started_at DESC')]
    )


def downgrade():
    """Remove agent_audit_log table and all indexes."""
    op.drop_index('ix_agent_audit_log_started_at_desc', table_name='agent_audit_log')
    op.drop_index('ix_agent_audit_log_agent_status', table_name='agent_audit_log')
    op.drop_index('ix_agent_audit_log_started_at', table_name='agent_audit_log')
    op.drop_index('ix_agent_audit_log_user_email', table_name='agent_audit_log')
    op.drop_index('ix_agent_audit_log_status', table_name='agent_audit_log')
    op.drop_index('ix_agent_audit_log_agent', table_name='agent_audit_log')
    op.drop_index('ix_agent_audit_log_run_id', table_name='agent_audit_log')
    op.drop_table('agent_audit_log')
