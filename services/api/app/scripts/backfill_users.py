"""
Backfill existing oauth_tokens with proper user references.
Usage (inside API container):
  python -m app.scripts.backfill_users --leo-email "leoklemet.pa@gmail.com" --make-demo
  
Note: This script links OAuth tokens to users. Email and Application models use
owner_email for single-user mode, not user_id foreign keys.
"""
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import User, OAuthToken
import argparse
import sys
import uuid

DEMO_EMAIL = "demo@applylens.app"


def ensure_user(db: Session, email: str, name: str | None = None, demo: bool = False) -> User:
    """Find or create a user by email."""
    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            is_demo=demo
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created user: {email} (demo={demo})")
    else:
        print(f"User already exists: {email}")
    return user


def run(db: Session, leo_email: str, make_demo: bool):
    """Backfill orphaned oauth_tokens to proper users."""
    # Ensure Leo's user exists
    leo = ensure_user(db, leo_email, name="Leo Klemet")
    
    # Ensure demo user exists
    demo = ensure_user(db, DEMO_EMAIL, name="Demo User", demo=make_demo)

    # Attach orphaned OAuth tokens to users by matching email
    updated_tokens = 0
    
    # Check for oauth_tokens without user_id
    from app.models import OAuthToken
    orphaned_tokens = db.query(OAuthToken).filter(OAuthToken.user_id.is_(None)).all()
    
    for token in orphaned_tokens:
        # Match by user_email field
        if token.user_email == leo_email:
            token.user_id = leo.id
            updated_tokens += 1
        elif token.user_email == DEMO_EMAIL:
            token.user_id = demo.id
            updated_tokens += 1
        else:
            # Default to Leo for unknown emails
            print(f"Warning: Unknown email {token.user_email}, assigning to {leo_email}")
            token.user_id = leo.id
            updated_tokens += 1
    
    db.commit()
    print(f"✅ Attached {updated_tokens} OAuth tokens to users")
    print(f"✅ Demo user: {demo.email} (is_demo={demo.is_demo})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill users for existing data")
    parser.add_argument("--leo-email", required=True, help="Leo's email address")
    parser.add_argument("--make-demo", action="store_true", help="Mark demo user as demo")
    args = parser.parse_args()
    
    try:
        with SessionLocal() as db:
            run(db, args.leo_email, args.make_demo)
        print("✅ Backfill completed successfully")
    except Exception as e:
        print(f"❌ Backfill failed: {e}", file=sys.stderr)
        sys.exit(1)
