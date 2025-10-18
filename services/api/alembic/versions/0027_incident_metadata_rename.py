"""Rename incident metadata column to incident_metadata

Revision ID: 0027_incident_metadata_rename
Revises: 0026_labeled_examples
Create Date: 2025-10-18 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0027_incident_metadata_rename'
down_revision: Union[str, None] = '0026_labeled_examples'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename metadata column to incident_metadata to avoid SQLAlchemy reserved attribute conflict."""
    # Rename the column in the incidents table
    op.alter_column('incidents', 'metadata', new_column_name='incident_metadata')


def downgrade() -> None:
    """Revert incident_metadata column back to metadata."""
    # Rename back to original name
    op.alter_column('incidents', 'incident_metadata', new_column_name='metadata')
