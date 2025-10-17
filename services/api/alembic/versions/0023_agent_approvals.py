"""add agent_approvals table for approval workflow

Revision ID: 0023_agent_approvals
Revises: 0022_agent_audit_log
Create Date: 2025-10-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0023_agent_approvals"
down_revision = "0022_agent_audit_log"
branch_labels = None
depends_on = None


def upgrade():
    """Add agent_approvals table for human-in-the-loop approval workflow.
    
    Stores:
    - Approval request metadata (request_id, agent, action, context)
    - Policy decision (rule_id, reason)
    - Approval lifecycle (status, requested_by, reviewed_by, timestamps)
    - Security (HMAC signature, nonce, nonce_used flag)
    - Execution tracking (executed, result)
    """
    op.create_table(
        'agent_approvals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.String(length=128), nullable=False),
        
        # Agent context
        sa.Column('agent', sa.String(length=128), nullable=False),
        sa.Column('action', sa.String(length=128), nullable=False),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        
        # Policy decision
        sa.Column('policy_rule_id', sa.String(length=128), nullable=True),
        sa.Column('reason', sa.String(length=1024), nullable=False),
        
        # Approval lifecycle
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('requested_by', sa.String(length=320), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('reviewed_by', sa.String(length=320), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        
        # Security
        sa.Column('signature', sa.String(length=128), nullable=False),
        sa.Column('nonce', sa.String(length=64), nullable=False),
        sa.Column('nonce_used', sa.Boolean(), nullable=False, server_default='false'),
        
        # Execution tracking
        sa.Column('executed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for common queries
    op.create_index('ix_agent_approvals_request_id', 'agent_approvals', ['request_id'], unique=True)
    op.create_index('ix_agent_approvals_agent', 'agent_approvals', ['agent'], unique=False)
    op.create_index('ix_agent_approvals_status', 'agent_approvals', ['status'], unique=False)
    op.create_index('ix_agent_approvals_requested_by', 'agent_approvals', ['requested_by'], unique=False)
    op.create_index('ix_agent_approvals_expires_at', 'agent_approvals', ['expires_at'], unique=False)
    op.create_index('ix_agent_approvals_nonce', 'agent_approvals', ['nonce'], unique=True)
    op.create_index('ix_agent_approvals_signature', 'agent_approvals', ['signature'], unique=True)
    op.create_index('ix_agent_approvals_agent_status', 'agent_approvals', ['agent', 'status'], unique=False)
    op.create_index('ix_agent_approvals_requested_at_desc', 'agent_approvals', [sa.text('requested_at DESC')], unique=False)


def downgrade():
    """Drop agent_approvals table and indexes."""
    op.drop_index('ix_agent_approvals_requested_at_desc', table_name='agent_approvals')
    op.drop_index('ix_agent_approvals_agent_status', table_name='agent_approvals')
    op.drop_index('ix_agent_approvals_signature', table_name='agent_approvals')
    op.drop_index('ix_agent_approvals_nonce', table_name='agent_approvals')
    op.drop_index('ix_agent_approvals_expires_at', table_name='agent_approvals')
    op.drop_index('ix_agent_approvals_requested_by', table_name='agent_approvals')
    op.drop_index('ix_agent_approvals_status', table_name='agent_approvals')
    op.drop_index('ix_agent_approvals_agent', table_name='agent_approvals')
    op.drop_index('ix_agent_approvals_request_id', table_name='agent_approvals')
    op.drop_table('agent_approvals')
