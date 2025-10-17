from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..deps.user import get_current_user_email
from ..schemas import EmailOut

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("/", response_model=list[EmailOut])
def list_emails(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of emails to return"),
    offset: int = Query(0, ge=0, description="Number of emails to skip"),
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """List emails for the current user, newest first."""
    rows = (
        db.query(models.Email)
        .filter(models.Email.owner_email == user_email)
        .order_by(models.Email.received_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows
