from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Status = Literal[
    "applied",
    "hr_screen",
    "interview",
    "offer",
    "rejected",
    "on_hold",
    "ghosted",
]


class ApplicationBase(BaseModel):
    company: str = Field(..., max_length=160)
    role: str = Field(..., max_length=200)
    source: Optional[str] = Field(None, max_length=120)
    status: Status = "applied"
    last_email_snippet: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    notes: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    source: Optional[str] = None
    status: Optional[Status] = None
    last_email_snippet: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    notes: Optional[str] = None


class ApplicationOut(ApplicationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
