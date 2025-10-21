"""Add archive and auto-delete fields to applications

Revision ID: 0019_archive_fields
Revises: 0017_phase6_personalization
Create Date: 2025-10-20 15:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0019_archive_fields"
down_revision: Union[str, None] = "0017_phase6_personalization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add archive lifecycle fields to applications table."""
    # Add archive/delete timestamp columns
    op.add_column(
        "applications",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    
    # Add opt-out flags
    op.add_column(
        "applications",
        sa.Column(
            "archive_opt_out",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "applications",
        sa.Column(
            "auto_delete_opt_out",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    
    # Create indexes for efficient querying
    op.create_index(
        "ix_applications_archived_at",
        "applications",
        ["archived_at"],
    )
    op.create_index(
        "ix_applications_deleted_at",
        "applications",
        ["deleted_at"],
    )
    
    # Create composite index for archive cleanup job queries
    op.create_index(
        "ix_applications_status_archived",
        "applications",
        ["status", "archived_at"],
    )


def downgrade() -> None:
    """Remove archive lifecycle fields from applications table."""
    op.drop_index("ix_applications_status_archived", table_name="applications")
    op.drop_index("ix_applications_deleted_at", table_name="applications")
    op.drop_index("ix_applications_archived_at", table_name="applications")
    op.drop_column("applications", "auto_delete_opt_out")
    op.drop_column("applications", "archive_opt_out")
    op.drop_column("applications", "deleted_at")
    op.drop_column("applications", "archived_at")
