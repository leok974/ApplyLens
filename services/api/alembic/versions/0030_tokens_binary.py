"""Convert oauth_tokens to LargeBinary for encrypted storage

Revision ID: 0030_tokens_binary
Revises: 0029_user_id_not_null
Create Date: 2025-10-20 21:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0030_tokens_binary"
down_revision: Union[str, None] = "0029_user_id_not_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Convert access_token and refresh_token columns to LargeBinary
    for encrypted token storage using AES-GCM.
    
    NOTE: This migration will clear existing tokens. Users will need to
    re-authenticate after applying this migration.
    """
    # PostgreSQL specific: Use USING clause to handle type conversion
    # Since we're switching from Text to LargeBinary, we need to clear data
    op.execute("UPDATE oauth_tokens SET access_token = '', refresh_token = NULL")
    
    # Convert access_token to LargeBinary
    op.alter_column(
        'oauth_tokens',
        'access_token',
        existing_type=sa.Text(),
        type_=sa.LargeBinary(),
        existing_nullable=False,
        postgresql_using='access_token::bytea'
    )
    
    # Convert refresh_token to LargeBinary
    op.alter_column(
        'oauth_tokens',
        'refresh_token',
        existing_type=sa.Text(),
        type_=sa.LargeBinary(),
        existing_nullable=True,
        postgresql_using='refresh_token::bytea'
    )


def downgrade() -> None:
    """Convert back to Text (will lose encrypted data)."""
    # Clear encrypted data
    op.execute("UPDATE oauth_tokens SET access_token = '', refresh_token = NULL")
    
    # Convert back to Text
    op.alter_column(
        'oauth_tokens',
        'access_token',
        existing_type=sa.LargeBinary(),
        type_=sa.Text(),
        existing_nullable=False,
        postgresql_using='access_token::text'
    )
    
    op.alter_column(
        'oauth_tokens',
        'refresh_token',
        existing_type=sa.LargeBinary(),
        type_=sa.Text(),
        existing_nullable=True,
        postgresql_using='refresh_token::text'
    )
