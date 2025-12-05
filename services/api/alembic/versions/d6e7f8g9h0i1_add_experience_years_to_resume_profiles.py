"""add experience_years to resume_profiles

Revision ID: d6e7f8g9h0i1
Revises: c5d6e7f8g9h0
Create Date: 2025-12-05 13:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d6e7f8g9h0i1"
down_revision = "c5d6e7f8g9h0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add experience_years field to resume_profiles table
    op.add_column(
        "resume_profiles", sa.Column("experience_years", sa.Integer, nullable=True)
    )


def downgrade() -> None:
    # Remove experience_years field from resume_profiles table
    op.drop_column("resume_profiles", "experience_years")
