"""security policies table

Revision ID: 0015_add_security_policies
Revises: 0014_add_security_fields
Create Date: 2025-10-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP

revision = "0015_add_security_policies"
down_revision = "0014_add_security_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "security_policies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String(320), nullable=True),  # single-user OK (NULL)
        sa.Column(
            "auto_quarantine_high_risk",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "auto_archive_expired_promos",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "auto_unsubscribe_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "auto_unsubscribe_threshold",
            sa.Integer,
            nullable=False,
            server_default="10",
        ),
        sa.Column(
            "updated_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", name="uq_security_policies_user"),
    )


def downgrade():
    op.drop_table("security_policies")
