"""Add user_agent and page_url to extension logs

Revision ID: 20251112_0002
Revises: 20251112_0001
Create Date: 2025-11-12 13:10:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251112_0002"
down_revision = "0034_extension_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "extension_applications", sa.Column("user_agent", sa.Text(), nullable=True)
    )
    op.add_column(
        "extension_applications", sa.Column("page_url", sa.Text(), nullable=True)
    )
    op.add_column(
        "extension_outreach", sa.Column("user_agent", sa.Text(), nullable=True)
    )
    op.add_column("extension_outreach", sa.Column("page_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("extension_outreach", "page_url")
    op.drop_column("extension_outreach", "user_agent")
    op.drop_column("extension_applications", "page_url")
    op.drop_column("extension_applications", "user_agent")
