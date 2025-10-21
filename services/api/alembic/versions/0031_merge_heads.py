"""Merge multiple heads

Revision ID: 0031_merge_heads
Revises: 0030_tokens_binary, 0019_archive_fields, 0018_consent_log
Create Date: 2025-10-20 21:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0031_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0030_tokens_binary",
    "0019_archive_fields",
    "0018_consent_log"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge migration - no schema changes."""
    pass


def downgrade() -> None:
    """Merge migration - no schema changes."""
    pass
