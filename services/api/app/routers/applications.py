from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db import get_db
from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationOut
from app.services.email_parse import extract_company, extract_role, extract_source

router = APIRouter(prefix="/applications", tags=["applications"]) 


@router.get("/", response_model=List[ApplicationOut])
def list_applications(
    status: Optional[str] = Query(None, description="Filter by status"),
    q: Optional[str] = Query(None, description="Search company/role"),
    db: Session = Depends(get_db),
):
    query = db.query(Application)
    if status:
        query = query.filter(Application.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter((Application.company.ilike(like)) | (Application.role.ilike(like)))
    return query.order_by(Application.updated_at.desc()).all()


@router.post("/", response_model=ApplicationOut)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    app = Application(**payload.model_dump())
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    return app


@router.patch("/{app_id}", response_model=ApplicationOut)
def update_application(app_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(app, k, v)
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.delete("/{app_id}", status_code=204)
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(app)
    db.commit()
    return None


@router.post("/from-email", response_model=ApplicationOut)
def create_from_email(
    *,
    thread_id: str,
    company: Optional[str] = None,
    role: Optional[str] = None,
    snippet: Optional[str] = None,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    body_text: Optional[str] = None,
    headers: Optional[dict] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Create an application row from a Gmail thread.

    Accepts thread_id plus optional parsed company/role/snippet.
    The client can call this via a "Create application" button in the email view.
    """
    inferred_company = company or extract_company(sender or "", body_text or "", subject or "")
    inferred_role = role or extract_role(subject or "", body_text or "")
    inferred_source = source or extract_source(headers or {}, sender or "", subject or "", body_text or "")
    
    app = Application(
        company=inferred_company or "(Unknown)",
        role=inferred_role or "(Unknown Role)",
        source=inferred_source or "Email",
        gmail_thread_id=thread_id,
        last_email_snippet=snippet,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app
