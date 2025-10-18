"""0016_incidents

Revision ID: 0016_incidents
Revises: 0015_add_security_policies
Create Date: 2025-10-17

Phase 5.4 PR1: Incident tracking tables
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0016_incidents'
down_revision = '0015_add_security_policies'
branch_labels = None
depends_on = None


def upgrade():
    # Create incidents table
    op.create_table(
        'incidents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=64), nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mitigated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('summary', sa.String(length=256), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('issue_url', sa.String(length=512), nullable=True),
        sa.Column('playbooks', sa.JSON(), nullable=True),
        sa.Column('assigned_to', sa.String(length=128), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for incidents
    op.create_index('idx_incident_status', 'incidents', ['status'], unique=False)
    op.create_index('idx_incident_severity', 'incidents', ['severity'], unique=False)
    op.create_index('idx_incident_kind_key', 'incidents', ['kind', 'key'], unique=False)
    op.create_index('idx_incident_created_at', 'incidents', ['created_at'], unique=False)
    op.create_index('idx_incident_assigned', 'incidents', ['assigned_to'], unique=False)
    
    # Create incident_actions table
    op.create_table(
        'incident_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('incident_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=64), nullable=False),
        sa.Column('action_name', sa.String(length=128), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('executed_by', sa.String(length=128), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('dry_run', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('approval_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for incident_actions
    op.create_index('idx_incident_action_incident', 'incident_actions', ['incident_id'], unique=False)
    op.create_index('idx_incident_action_status', 'incident_actions', ['status'], unique=False)


def downgrade():
    # Drop incident_actions
    op.drop_index('idx_incident_action_status', table_name='incident_actions')
    op.drop_index('idx_incident_action_incident', table_name='incident_actions')
    op.drop_table('incident_actions')
    
    # Drop incidents
    op.drop_index('idx_incident_assigned', table_name='incidents')
    op.drop_index('idx_incident_created_at', table_name='incidents')
    op.drop_index('idx_incident_kind_key', table_name='incidents')
    op.drop_index('idx_incident_severity', table_name='incidents')
    op.drop_index('idx_incident_status', table_name='incidents')
    op.drop_table('incidents')
