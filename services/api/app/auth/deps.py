"""FastAPI dependencies for authentication."""
from typing import Optional
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from .session import verify_session


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency to get current authenticated user.
    
    Raises HTTPException 401 if not authenticated.
    """
    user = verify_session(db, request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def optional_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Dependency to get current user if authenticated, None otherwise."""
    return verify_session(db, request)
