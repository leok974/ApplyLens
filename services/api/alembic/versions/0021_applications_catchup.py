"""add missing columns to applications table (schema catch-up)

Revision ID: 0021_applications_catchup
Revises: 0020_add_last_email_id
Create Date: 2025-10-14
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0021_applications_catchup"
down_revision = "0020_add_last_email_id"
branch_labels = None
depends_on = None


def upgrade():
    """
    Add missing columns to applications table that exist in the model but not in migrations.
    
    This is a "catch-up" migration to fix schema drift between models.py and migrations.
    The Application model has evolved over time but some column additions weren't migrated.
    
    Missing columns:
    - notes: Text field for user notes about the application
    - created_at: Timestamp when application was created
    - updated_at: Timestamp when application was last modified
    
    Note: Other columns (thread_id, gmail_thread_id, last_email_id, last_email_snippet)
    were added in migrations 0003, 0019, and 0020.
    """
    op.execute("""
    DO $$
    BEGIN
        -- Add notes column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'notes'
        ) THEN
            ALTER TABLE applications 
                ADD COLUMN notes TEXT NULL;
        END IF;
        
        -- Add created_at column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'created_at'
        ) THEN
            ALTER TABLE applications 
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        END IF;
        
        -- Add updated_at column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'updated_at'
        ) THEN
            ALTER TABLE applications 
                ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        END IF;
    END$$;
    """)


def downgrade():
    """
    Remove the added columns.
    """
    op.execute("""
    DO $$
    BEGIN
        -- Drop columns if they exist
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'updated_at'
        ) THEN
            ALTER TABLE applications DROP COLUMN updated_at;
        END IF;
        
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'created_at'
        ) THEN
            ALTER TABLE applications DROP COLUMN created_at;
        END IF;
        
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'notes'
        ) THEN
            ALTER TABLE applications DROP COLUMN notes;
        END IF;
    END$$;
    """)
