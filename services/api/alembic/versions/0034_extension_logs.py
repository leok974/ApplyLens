"""extension logs

Revision ID: 0034_extension_logs
Revises: 0033_sender_overrides
Create Date: 2025-11-12

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0034_extension_logs"
down_revision = "0033_sender_overrides"
branch_labels = None
depends_on = None


def upgrade():
    """Create extension_applications and extension_outreach tables."""

    # extension_applications table
    op.create_table(
        "extension_applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_email", sa.String(length=320), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=512), nullable=False),
        sa.Column("job_url", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_extension_applications_user_email",
        "extension_applications",
        ["user_email"],
        unique=False,
    )
    op.create_index(
        "ix_extension_applications_company",
        "extension_applications",
        ["company"],
        unique=False,
    )
    op.create_index(
        "ix_extension_applications_source",
        "extension_applications",
        ["source"],
        unique=False,
    )

    # extension_outreach table
    op.create_table(
        "extension_outreach",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_email", sa.String(length=320), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=512), nullable=False),
        sa.Column("recruiter_name", sa.String(length=255), nullable=True),
        sa.Column("recruiter_profile_url", sa.Text(), nullable=True),
        sa.Column("message_preview", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_extension_outreach_user_email",
        "extension_outreach",
        ["user_email"],
        unique=False,
    )
    op.create_index(
        "ix_extension_outreach_company", "extension_outreach", ["company"], unique=False
    )
    op.create_index(
        "ix_extension_outreach_source", "extension_outreach", ["source"], unique=False
    )


def downgrade():
    """Drop extension tables."""
    op.drop_index("ix_extension_outreach_source", table_name="extension_outreach")
    op.drop_index("ix_extension_outreach_company", table_name="extension_outreach")
    op.drop_index("ix_extension_outreach_user_email", table_name="extension_outreach")
    op.drop_table("extension_outreach")

    op.drop_index(
        "ix_extension_applications_source", table_name="extension_applications"
    )
    op.drop_index(
        "ix_extension_applications_company", table_name="extension_applications"
    )
    op.drop_index(
        "ix_extension_applications_user_email", table_name="extension_applications"
    )
    op.drop_table("extension_applications")
