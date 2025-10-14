# app/migrate.py
from sqlalchemy import text

from .db import Base, engine
from .models import Application, Email, OAuthToken  # noqa


def run():
    """Run database migration to create all tables and columns"""
    with engine.connect() as conn:
        # Add new columns to emails table if they don't exist
        try:
            conn.execute(
                text(
                    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS gmail_id VARCHAR(128)"
                )
            )
            conn.execute(
                text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS sender VARCHAR(512)")
            )
            conn.execute(
                text(
                    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS recipient VARCHAR(512)"
                )
            )
            conn.execute(
                text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS labels VARCHAR[]")
            )
            conn.execute(
                text(
                    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS label_heuristics VARCHAR[]"
                )
            )
            conn.execute(text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS raw JSON"))
            conn.execute(
                text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS company VARCHAR(256)")
            )
            conn.execute(
                text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS role VARCHAR(512)")
            )
            conn.execute(
                text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS source VARCHAR(128)")
            )
            conn.execute(
                text(
                    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS source_confidence FLOAT"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS application_id INTEGER REFERENCES applications(id)"
                )
            )

            # Add indexes
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_emails_gmail_id ON emails(gmail_id)"
                )
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_emails_sender ON emails(sender)")
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_emails_recipient ON emails(recipient)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_emails_received_at ON emails(received_at)"
                )
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_emails_company ON emails(company)")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_emails_role ON emails(role)")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_emails_source ON emails(source)")
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_emails_search ON emails(subject, sender, recipient)"
                )
            )

            # Alter received_at to allow null
            conn.execute(
                text("ALTER TABLE emails ALTER COLUMN received_at DROP DEFAULT")
            )
            conn.execute(
                text("ALTER TABLE emails ALTER COLUMN received_at DROP NOT NULL")
            )

            # Make subject TEXT instead of VARCHAR
            conn.execute(text("ALTER TABLE emails ALTER COLUMN subject TYPE TEXT"))

            conn.commit()
            print("✅ Added new columns to emails table")
        except Exception as e:
            print(f"⚠️  Email columns migration: {e}")
            conn.rollback()

    # Create all tables (applications, etc.)
    Base.metadata.create_all(bind=engine)
    print("✅ Database migration completed successfully")


if __name__ == "__main__":
    run()
