from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models
from ..schemas import EmailOut

router = APIRouter(prefix="/emails", tags=["emails"])

@router.get("/", response_model=list[EmailOut])
def list_emails(db: Session = Depends(get_db)):
    rows = db.query(models.Email).order_by(models.Email.received_at.desc()).limit(50).all()
    return rows
