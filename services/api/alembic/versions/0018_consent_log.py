"""Add consent tracking tables

Revision ID: 0018_consent_log
Revises: 0017_policy_bundles
Create Date: 2025-10-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0018_consent_log'
down_revision = '0017_policy_bundles'
branch_labels = None
depends_on = None


def upgrade():
    # Create consent_records table
    op.create_table(
        'consent_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('consent_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('granted_at', sa.DateTime(), nullable=True),
        sa.Column('withdrawn_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_consent_records_user_id', 'consent_records', ['user_id'])
    op.create_index('ix_consent_records_consent_type', 'consent_records', ['consent_type'])
    op.create_index('ix_consent_records_status', 'consent_records', ['status'])
    
    # Create data_subject_requests table
    op.create_table(
        'data_subject_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(length=50), nullable=False, unique=True),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('user_email', sa.String(length=255), nullable=False),
        sa.Column('right_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('requested_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('data_export_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_dsr_request_id', 'data_subject_requests', ['request_id'])
    op.create_index('ix_dsr_user_id', 'data_subject_requests', ['user_id'])
    op.create_index('ix_dsr_status', 'data_subject_requests', ['status'])
    op.create_index('ix_dsr_requested_at', 'data_subject_requests', ['requested_at'])
    
    # Create pii_audit_log table
    op.create_table(
        'pii_audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('pii_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('justification', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_pii_audit_user_id', 'pii_audit_log', ['user_id'])
    op.create_index('ix_pii_audit_timestamp', 'pii_audit_log', ['timestamp'])
    op.create_index('ix_pii_audit_resource', 'pii_audit_log', ['resource_id', 'resource_type'])
    
    # Create data_retention_policies table
    op.create_table(
        'data_retention_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data_type', sa.String(length=100), nullable=False, unique=True),
        sa.Column('retention_days', sa.Integer(), nullable=False),
        sa.Column('legal_basis', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insert default retention policies
    op.execute("""
        INSERT INTO data_retention_policies (data_type, retention_days, legal_basis, description)
        VALUES
            ('user_profile', 2555, 'contract', 'User account and profile data'),
            ('email_content', 365, 'consent', 'Email messages and attachments'),
            ('analytics_events', 90, 'legitimate_interest', 'Usage analytics and metrics'),
            ('audit_logs', 2555, 'legal_obligation', 'Security and compliance audit logs'),
            ('marketing_data', 730, 'consent', 'Marketing preferences and campaign data')
    """)


def downgrade():
    op.drop_table('data_retention_policies')
    op.drop_index('ix_pii_audit_resource', table_name='pii_audit_log')
    op.drop_index('ix_pii_audit_timestamp', table_name='pii_audit_log')
    op.drop_index('ix_pii_audit_user_id', table_name='pii_audit_log')
    op.drop_table('pii_audit_log')
    op.drop_index('ix_dsr_requested_at', table_name='data_subject_requests')
    op.drop_index('ix_dsr_status', table_name='data_subject_requests')
    op.drop_index('ix_dsr_user_id', table_name='data_subject_requests')
    op.drop_index('ix_dsr_request_id', table_name='data_subject_requests')
    op.drop_table('data_subject_requests')
    op.drop_index('ix_consent_records_status', table_name='consent_records')
    op.drop_index('ix_consent_records_consent_type', table_name='consent_records')
    op.drop_index('ix_consent_records_user_id', table_name='consent_records')
    op.drop_table('consent_records')
