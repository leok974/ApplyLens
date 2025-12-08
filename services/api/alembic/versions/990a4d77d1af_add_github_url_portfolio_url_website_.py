"""Add github_url portfolio_url website_url target_roles to resume_profiles

Revision ID: 990a4d77d1af
Revises: d6e7f8g9h0i1
Create Date: 2025-12-08 11:05:12.437108

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "990a4d77d1af"
down_revision = "d6e7f8g9h0i1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to resume_profiles table
    op.add_column("resume_profiles", sa.Column("github_url", sa.Text(), nullable=True))
    op.add_column(
        "resume_profiles", sa.Column("portfolio_url", sa.Text(), nullable=True)
    )
    op.add_column("resume_profiles", sa.Column("website_url", sa.Text(), nullable=True))
    op.add_column(
        "resume_profiles", sa.Column("target_roles", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    # Remove new columns from resume_profiles table
    op.drop_column("resume_profiles", "target_roles")
    op.drop_column("resume_profiles", "website_url")
    op.drop_column("resume_profiles", "portfolio_url")
    op.drop_column("resume_profiles", "github_url")
