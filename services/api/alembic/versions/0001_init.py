"""Initial migration

Revision ID: 0001_init
Revises: 
Create Date: 2025-10-08

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'emails',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('thread_id', sa.String(128), index=True),
        sa.Column('from_addr', sa.String(320)),
        sa.Column('to_addr', sa.String(320)),
        sa.Column('subject', sa.String(512)),
        sa.Column('body_text', sa.Text),
        sa.Column('label', sa.String(64), index=True),
        sa.Column('received_at', sa.DateTime(timezone=True))
    )
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('company', sa.String(256), index=True),
        sa.Column('role', sa.String(256), index=True),
        sa.Column('location', sa.String(256)),
        sa.Column('source', sa.String(128)),
        sa.Column('status', sa.String(64)),
        sa.Column('job_url', sa.String(1024)),
        sa.Column('last_email_at', sa.DateTime(timezone=True)),
    )


def downgrade():
    op.drop_table('applications')
    op.drop_table('emails')
