"""add contact fields to resume_profiles

Revision ID: c5d6e7f8g9h0
Revises: bf7f93a3b301
Create Date: 2025-12-05 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c5d6e7f8g9h0"
down_revision = "bf7f93a3b301"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add contact fields to resume_profiles table
    op.add_column("resume_profiles", sa.Column("name", sa.String(255), nullable=True))
    op.add_column("resume_profiles", sa.Column("email", sa.String(320), nullable=True))
    op.add_column("resume_profiles", sa.Column("phone", sa.String(50), nullable=True))
    op.add_column("resume_profiles", sa.Column("linkedin", sa.Text, nullable=True))


def downgrade() -> None:
    # Remove contact fields from resume_profiles table
    op.drop_column("resume_profiles", "linkedin")
    op.drop_column("resume_profiles", "phone")
    op.drop_column("resume_profiles", "email")
    op.drop_column("resume_profiles", "name")
