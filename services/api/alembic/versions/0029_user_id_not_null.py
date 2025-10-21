"""Set oauth_tokens.user_id NOT NULL after backfill

Revision ID: 0029_user_id_not_null
Revises: 0028_multi_user_auth
Create Date: 2025-10-20 20:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0029_user_id_not_null"
down_revision: Union[str, None] = "0028_multi_user_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Set user_id NOT NULL on oauth_tokens after backfill script has run.
    
    NOTE: Run backfill_users.py BEFORE applying this migration:
      docker exec applylens-api-prod python -m app.scripts.backfill_users \\
        --leo-email "leoklemet.pa@gmail.com" --make-demo
    """
    # Set user_id to NOT NULL (backfill should have filled all NULL values)
    op.alter_column(
        'oauth_tokens',
        'user_id',
        existing_type=sa.String(64),
        nullable=False
    )


def downgrade() -> None:
    """Allow user_id to be NULL again."""
    op.alter_column(
        'oauth_tokens',
        'user_id',
        existing_type=sa.String(64),
        nullable=True
    )
