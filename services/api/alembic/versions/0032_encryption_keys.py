"""add encryption_keys table and key_version to oauth_tokens

Revision ID: 0032_encryption_keys
Revises: 0031_merge_heads
Create Date: 2025-10-20

This migration prepares for envelope encryption with KMS-backed key rotation.

Schema changes:
1. Create `encryption_keys` table to store multiple key versions
2. Add `key_version` column to `oauth_tokens` table
3. Backfill existing tokens with version=1 (current ephemeral key)

Future workflow:
- New AES data key generated -> wrapped with GCP/AWS KMS
- Stored in encryption_keys table with version number
- On rotate: new version added, old marked inactive
- Tokens reference which key version encrypted them
- Optional background job to re-encrypt old tokens
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0032_encryption_keys'
down_revision = '0031_merge_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create encryption_keys table
    op.create_table(
        'encryption_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('kms_wrapped_key', sa.LargeBinary(), nullable=False, comment='KMS-encrypted AES key'),
        sa.Column('algorithm', sa.String(length=32), nullable=False, server_default='AES-GCM-256'),
        sa.Column('kms_key_id', sa.String(length=512), nullable=True, comment='GCP/AWS KMS key resource ID'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('rotated_at', sa.DateTime(), nullable=True, comment='When this key was deactivated'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version', name='uq_encryption_keys_version')
    )
    
    # Index for active key lookup
    op.create_index('ix_encryption_keys_active', 'encryption_keys', ['active', 'version'])
    
    # Add key_version column to oauth_tokens
    op.add_column(
        'oauth_tokens',
        sa.Column('key_version', sa.Integer(), nullable=True, comment='Encryption key version used')
    )
    
    # Backfill existing tokens with version=1 (current key)
    # Note: This assumes all existing encrypted tokens use the same key
    op.execute("UPDATE oauth_tokens SET key_version = 1 WHERE key_version IS NULL")
    
    # Add index for key version lookups (useful for re-encryption jobs)
    op.create_index('ix_oauth_tokens_key_version', 'oauth_tokens', ['key_version'])


def downgrade() -> None:
    # Drop indices
    op.drop_index('ix_oauth_tokens_key_version', table_name='oauth_tokens')
    op.drop_index('ix_encryption_keys_active', table_name='encryption_keys')
    
    # Drop columns
    op.drop_column('oauth_tokens', 'key_version')
    
    # Drop table
    op.drop_table('encryption_keys')
