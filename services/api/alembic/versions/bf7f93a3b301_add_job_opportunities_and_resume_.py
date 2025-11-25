"""add job opportunities and resume profiles tables

Revision ID: bf7f93a3b301
Revises: 09308884b950
Create Date: 2025-11-24 19:03:38.785643

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "bf7f93a3b301"
down_revision = "09308884b950"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create job_opportunities table
    op.create_table(
        "job_opportunities",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_email", sa.String, nullable=False, index=True),
        sa.Column("source", sa.String, nullable=True),
        sa.Column("source_message_id", sa.String, nullable=True),
        sa.Column("title", sa.String, nullable=True),
        sa.Column("company", sa.String, nullable=True, index=True),
        sa.Column("location", sa.String, nullable=True),
        sa.Column("remote_flag", sa.Boolean, nullable=True),
        sa.Column("salary_text", sa.Text, nullable=True),
        sa.Column("level", sa.String, nullable=True),
        sa.Column("tech_stack", sa.JSON, nullable=True),
        sa.Column("apply_url", sa.Text, nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create resume_profiles table
    op.create_table(
        "resume_profiles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_email", sa.String, nullable=False, index=True),
        sa.Column("source", sa.String, nullable=False),  # 'upload' for now
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("headline", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("skills", sa.JSON, nullable=True),
        sa.Column("experiences", sa.JSON, nullable=True),
        sa.Column("projects", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create opportunity_matches table
    op.create_table(
        "opportunity_matches",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_email", sa.String, nullable=False, index=True),
        sa.Column(
            "opportunity_id",
            sa.Integer,
            sa.ForeignKey("job_opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "resume_profile_id",
            sa.Integer,
            sa.ForeignKey("resume_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("match_bucket", sa.String, nullable=False),
        sa.Column("match_score", sa.Integer, nullable=False),
        sa.Column("reasons", sa.JSON, nullable=True),
        sa.Column("missing_skills", sa.JSON, nullable=True),
        sa.Column("resume_tweaks", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    # Drop tables in reverse order due to foreign keys
    op.drop_table("opportunity_matches")
    op.drop_table("resume_profiles")
    op.drop_table("job_opportunities")
