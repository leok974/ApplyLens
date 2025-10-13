from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Enum, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ApplicationStatus(str):
    APPLIED = "applied"
    HR_SCREEN = "hr_screen"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    ON_HOLD = "on_hold"
    GHOSTED = "ghosted"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(160), index=True)
    role: Mapped[str] = mapped_column(String(200), index=True)
    source: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(
        Enum(
            ApplicationStatus.APPLIED,
            ApplicationStatus.HR_SCREEN,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
            ApplicationStatus.ON_HOLD,
            ApplicationStatus.GHOSTED,
            name="application_status",
        ),
        default=ApplicationStatus.APPLIED,
        index=True,
    )
    last_email_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gmail_thread_id: Mapped[Optional[str]] = mapped_column(
        String(128), index=True, nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
    )
